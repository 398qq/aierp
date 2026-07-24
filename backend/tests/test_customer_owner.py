"""Customer owner-management feature tests.

Covers the Jul-24 feature (commit 62c1de54): owner claim/release/assign,
assignment rules, release rules, and the transfer-approval workflow — plus the
two scheduler jobs that hold the core rule-matching business logic.

The API surface lives in ``app/api/v1/customers/{owner,assignment_rules,
release_rules,transfer_requests}.py``. The batch jobs live in
``app/jobs/scheduler.py`` (``_run_auto_assign_job``,
``_run_owner_release_check_job``, ``_evaluate_assignment_conditions``).

Scheduler jobs open their own ``app.database.async_session()``; we monkey-patch
the scheduler module's binding so they read/write the test ``db_session``
(same pattern as ``test_batch_expiry_job.py``).
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.customer import (
    Customer,
    CustomerFollowUp,
    CustomerOwnerLog,
    OwnerTransferRequest,
)

# ── helpers ─────────────────────────────────────────────────────────


async def _make_customer(
    db: AsyncSession,
    *,
    name: str,
    owner: str | None = None,
    industry: str | None = None,
    region: str | None = None,
    created_at: datetime | None = None,
) -> Customer:
    c = Customer(name=name, owner=owner, industry=industry, region=region)
    if created_at is not None:
        c.created_at = created_at
    db.add(c)
    await db.flush()
    return c


@asynccontextmanager
async def _session_cm(db: AsyncSession):
    yield db


def _patch_session(monkeypatch, db: AsyncSession) -> None:
    """Bind ``scheduler.async_session()`` to the test session."""
    from app.jobs import scheduler

    monkeypatch.setattr(scheduler, "async_session", lambda: _session_cm(db))


async def _owner_logs(db: AsyncSession, customer_id: int) -> list[CustomerOwnerLog]:
    rows = await db.execute(
        select(CustomerOwnerLog)
        .where(CustomerOwnerLog.customer_id == customer_id)
        .order_by(CustomerOwnerLog.created_at.asc())
    )
    return list(rows.scalars().all())


# ── owner.py: claim / release / assign / history / stats ─────────────


class TestOwnerAssignment:
    async def test_claim_sets_owner_and_writes_log(
        self, async_client: AsyncClient, auth_headers: dict, db_session: AsyncSession
    ):
        c = await _make_customer(db_session, name="认领客户")

        resp = await async_client.post(
            "/api/v1/customers/batch-owner",
            headers=auth_headers,
            json={"ids": [c.id], "action": "claim"},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["code"] == 0
        assert body["data"]["updated"] == 1
        assert body["data"]["owner"] == "testuser"

        await db_session.refresh(c)
        assert c.owner == "testuser"
        logs = await _owner_logs(db_session, c.id)
        assert len(logs) == 1
        assert logs[0].action_type == "claim"
        assert logs[0].to_owner == "testuser"

    async def test_release_clears_owner(
        self, async_client: AsyncClient, auth_headers: dict, db_session: AsyncSession
    ):
        c = await _make_customer(db_session, name="释放客户", owner="testuser")

        resp = await async_client.post(
            "/api/v1/customers/batch-owner",
            headers=auth_headers,
            json={"ids": [c.id], "action": "release"},
        )
        assert resp.status_code == 200
        await db_session.refresh(c)
        assert c.owner is None
        logs = await _owner_logs(db_session, c.id)
        assert logs[-1].action_type == "release"
        assert logs[-1].from_owner == "testuser"
        assert logs[-1].to_owner is None

    async def test_assign_requires_owner(
        self, async_client: AsyncClient, auth_headers: dict, db_session: AsyncSession
    ):
        c = await _make_customer(db_session, name="缺负责人客户")
        resp = await async_client.post(
            "/api/v1/customers/batch-owner",
            headers=auth_headers,
            json={"ids": [c.id], "action": "assign"},
        )
        assert resp.status_code == 400

    async def test_assign_rejects_unknown_owner(
        self, async_client: AsyncClient, auth_headers: dict, db_session: AsyncSession
    ):
        c = await _make_customer(db_session, name="未知负责人客户")
        resp = await async_client.post(
            "/api/v1/customers/batch-owner",
            headers=auth_headers,
            json={"ids": [c.id], "action": "assign", "owner": "ghost_user"},
        )
        assert resp.status_code == 400

    async def test_assign_to_valid_owner(
        self, async_client: AsyncClient, auth_headers: dict, db_session: AsyncSession
    ):
        c = await _make_customer(db_session, name="有效分配客户")
        resp = await async_client.post(
            "/api/v1/customers/batch-owner",
            headers=auth_headers,
            json={"ids": [c.id], "action": "assign", "owner": "testuser"},
        )
        assert resp.status_code == 200
        await db_session.refresh(c)
        assert c.owner == "testuser"

    async def test_batch_owner_no_valid_customers_404(
        self, async_client: AsyncClient, auth_headers: dict
    ):
        resp = await async_client.post(
            "/api/v1/customers/batch-owner",
            headers=auth_headers,
            json={"ids": [999999], "action": "claim"},
        )
        assert resp.status_code == 404

    async def test_assign_endpoint_rejects_unknown_owner(
        self, async_client: AsyncClient, auth_headers: dict, db_session: AsyncSession
    ):
        c = await _make_customer(db_session, name="assign端点客户")
        resp = await async_client.post(
            "/api/v1/customers/assign",
            headers=auth_headers,
            json={"ids": [c.id], "owner": "ghost_user"},
        )
        assert resp.status_code == 400

    async def test_assign_endpoint_success(
        self, async_client: AsyncClient, auth_headers: dict, db_session: AsyncSession
    ):
        c = await _make_customer(db_session, name="assign端点成功")
        resp = await async_client.post(
            "/api/v1/customers/assign",
            headers=auth_headers,
            json={"ids": [c.id], "owner": "testuser"},
        )
        assert resp.status_code == 200
        assert resp.json()["data"]["updated"] == 1

    async def test_owner_history_returns_logs(
        self, async_client: AsyncClient, auth_headers: dict, db_session: AsyncSession
    ):
        c = await _make_customer(db_session, name="历史客户")
        await async_client.post(
            "/api/v1/customers/batch-owner",
            headers=auth_headers,
            json={"ids": [c.id], "action": "claim"},
        )
        await async_client.post(
            "/api/v1/customers/batch-owner",
            headers=auth_headers,
            json={"ids": [c.id], "action": "release"},
        )
        resp = await async_client.get(
            f"/api/v1/customers/{c.id}/owner-history", headers=auth_headers
        )
        assert resp.status_code == 200
        actions = [row["action_type"] for row in resp.json()["data"]["list"]]
        assert "claim" in actions and "release" in actions

    async def test_claim_stats_counts_owned(
        self, async_client: AsyncClient, auth_headers: dict, db_session: AsyncSession
    ):
        c1 = await _make_customer(db_session, name="统计客户1")
        c2 = await _make_customer(db_session, name="统计客户2")
        await async_client.post(
            "/api/v1/customers/batch-owner",
            headers=auth_headers,
            json={"ids": [c1.id, c2.id], "action": "claim"},
        )
        resp = await async_client.get(
            "/api/v1/customers/claim-stats", headers=auth_headers
        )
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["username"] == "testuser"
        assert data["claimed"] == 2


# ── transfer_requests.py: submit → approve / reject / cancel ─────────


class TestTransferRequests:
    async def _create(
        self, client: AsyncClient, headers: dict, customer_id: int, to_owner: str
    ):
        return await client.post(
            "/api/v1/customers/transfer-requests",
            headers=headers,
            json={"customer_id": customer_id, "to_owner": to_owner, "reason": "调整"},
        )

    async def test_create_pending_request(
        self, async_client: AsyncClient, auth_headers: dict, db_session: AsyncSession
    ):
        c = await _make_customer(db_session, name="转移客户", owner="alice")
        resp = await self._create(async_client, auth_headers, c.id, "bob")
        assert resp.status_code == 201
        data = resp.json()["data"]
        assert data["status"] == "pending"
        assert data["from_owner"] == "alice"
        assert data["to_owner"] == "bob"

    async def test_create_for_missing_customer_404(
        self, async_client: AsyncClient, auth_headers: dict
    ):
        resp = await self._create(async_client, auth_headers, 888888, "bob")
        assert resp.status_code == 404

    async def test_duplicate_pending_conflict(
        self, async_client: AsyncClient, auth_headers: dict, db_session: AsyncSession
    ):
        c = await _make_customer(db_session, name="重复转移", owner="alice")
        first = await self._create(async_client, auth_headers, c.id, "bob")
        assert first.status_code == 201
        second = await self._create(async_client, auth_headers, c.id, "carol")
        assert second.status_code == 409

    async def test_approve_executes_owner_change(
        self, async_client: AsyncClient, auth_headers: dict, db_session: AsyncSession
    ):
        c = await _make_customer(db_session, name="审批通过客户", owner="alice")
        created = await self._create(async_client, auth_headers, c.id, "bob")
        req_id = created.json()["data"]["id"]

        resp = await async_client.post(
            f"/api/v1/customers/transfer-requests/{req_id}/approve",
            headers=auth_headers,
            json={"comment": "同意"},
        )
        assert resp.status_code == 200
        assert resp.json()["data"]["status"] == "approved"

        await db_session.refresh(c)
        assert c.owner == "bob"
        logs = await _owner_logs(db_session, c.id)
        assert logs[-1].action_type == "transfer_in"
        assert logs[-1].to_owner == "bob"

    async def test_approve_non_pending_conflict(
        self, async_client: AsyncClient, auth_headers: dict, db_session: AsyncSession
    ):
        c = await _make_customer(db_session, name="重复审批客户", owner="alice")
        created = await self._create(async_client, auth_headers, c.id, "bob")
        req_id = created.json()["data"]["id"]
        await async_client.post(
            f"/api/v1/customers/transfer-requests/{req_id}/approve",
            headers=auth_headers,
            json={},
        )
        again = await async_client.post(
            f"/api/v1/customers/transfer-requests/{req_id}/approve",
            headers=auth_headers,
            json={},
        )
        assert again.status_code == 409

    async def test_reject_sets_status(
        self, async_client: AsyncClient, auth_headers: dict, db_session: AsyncSession
    ):
        c = await _make_customer(db_session, name="驳回客户", owner="alice")
        created = await self._create(async_client, auth_headers, c.id, "bob")
        req_id = created.json()["data"]["id"]
        resp = await async_client.post(
            f"/api/v1/customers/transfer-requests/{req_id}/reject",
            headers=auth_headers,
            json={"comment": "不同意"},
        )
        assert resp.status_code == 200
        assert resp.json()["data"]["status"] == "rejected"
        await db_session.refresh(c)
        assert c.owner == "alice"  # unchanged

    async def test_cancel_by_non_requester_forbidden(
        self, async_client: AsyncClient, auth_headers: dict, db_session: AsyncSession
    ):
        c = await _make_customer(db_session, name="他人撤销客户", owner="alice")
        # A request created by a different user.
        req = OwnerTransferRequest(
            customer_id=c.id,
            from_owner="alice",
            to_owner="bob",
            requested_by="someone_else",
        )
        db_session.add(req)
        await db_session.flush()
        resp = await async_client.post(
            f"/api/v1/customers/transfer-requests/{req.id}/cancel",
            headers=auth_headers,
        )
        assert resp.status_code == 403

    async def test_cancel_by_requester(
        self, async_client: AsyncClient, auth_headers: dict, db_session: AsyncSession
    ):
        c = await _make_customer(db_session, name="自撤销客户", owner="alice")
        created = await self._create(async_client, auth_headers, c.id, "bob")
        req_id = created.json()["data"]["id"]
        resp = await async_client.post(
            f"/api/v1/customers/transfer-requests/{req_id}/cancel",
            headers=auth_headers,
        )
        assert resp.status_code == 200
        assert resp.json()["data"]["status"] == "cancelled"

    async def test_list_filters_by_status(
        self, async_client: AsyncClient, auth_headers: dict, db_session: AsyncSession
    ):
        c = await _make_customer(db_session, name="列表筛选客户", owner="alice")
        await self._create(async_client, auth_headers, c.id, "bob")
        resp = await async_client.get(
            "/api/v1/customers/transfer-requests?status=pending",
            headers=auth_headers,
        )
        assert resp.status_code == 200
        rows = resp.json()["data"]
        assert all(r["status"] == "pending" for r in rows)
        assert any(r["customer_id"] == c.id for r in rows)


# ── assignment_rules.py: CRUD + reorder ──────────────────────────────


class TestAssignmentRules:
    async def test_create_with_conditions(
        self, async_client: AsyncClient, auth_headers: dict
    ):
        resp = await async_client.post(
            "/api/v1/customers/assignment-rules",
            headers=auth_headers,
            json={
                "name": "华东电子分配",
                "priority": 1,
                "condition_logic": "all",
                "assigned_to": "testuser",
                "conditions": [
                    {"field": "industry", "operator": "equals", "value": "电子"},
                    {"field": "region", "operator": "contains", "value": "华东"},
                ],
            },
        )
        assert resp.status_code == 201
        data = resp.json()["data"]
        assert data["name"] == "华东电子分配"
        assert len(data["conditions"]) == 2

    async def test_list_returns_rule(
        self, async_client: AsyncClient, auth_headers: dict
    ):
        await async_client.post(
            "/api/v1/customers/assignment-rules",
            headers=auth_headers,
            json={"name": "列表规则", "assigned_to": "testuser", "conditions": []},
        )
        resp = await async_client.get(
            "/api/v1/customers/assignment-rules", headers=auth_headers
        )
        assert resp.status_code == 200
        names = [r["name"] for r in resp.json()["data"]]
        assert "列表规则" in names

    async def test_update_replaces_conditions(
        self, async_client: AsyncClient, auth_headers: dict
    ):
        created = await async_client.post(
            "/api/v1/customers/assignment-rules",
            headers=auth_headers,
            json={
                "name": "待更新规则",
                "assigned_to": "testuser",
                "conditions": [
                    {"field": "industry", "operator": "equals", "value": "电子"}
                ],
            },
        )
        rule_id = created.json()["data"]["id"]
        resp = await async_client.put(
            f"/api/v1/customers/assignment-rules/{rule_id}",
            headers=auth_headers,
            json={
                "name": "已更新规则",
                "conditions": [
                    {"field": "region", "operator": "equals", "value": "华南"},
                    {"field": "source", "operator": "not_empty", "value": "x"},
                ],
            },
        )
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["name"] == "已更新规则"
        assert len(data["conditions"]) == 2

    async def test_delete_soft_removes(
        self, async_client: AsyncClient, auth_headers: dict
    ):
        created = await async_client.post(
            "/api/v1/customers/assignment-rules",
            headers=auth_headers,
            json={"name": "待删除规则", "assigned_to": "testuser", "conditions": []},
        )
        rule_id = created.json()["data"]["id"]
        resp = await async_client.delete(
            f"/api/v1/customers/assignment-rules/{rule_id}", headers=auth_headers
        )
        assert resp.status_code == 200
        listed = await async_client.get(
            "/api/v1/customers/assignment-rules", headers=auth_headers
        )
        assert rule_id not in [r["id"] for r in listed.json()["data"]]

    async def test_reorder_sets_priority(
        self, async_client: AsyncClient, auth_headers: dict
    ):
        ids = []
        for name in ("排序A", "排序B", "排序C"):
            r = await async_client.post(
                "/api/v1/customers/assignment-rules",
                headers=auth_headers,
                json={"name": name, "assigned_to": "testuser", "conditions": []},
            )
            ids.append(r.json()["data"]["id"])
        reordered = list(reversed(ids))
        resp = await async_client.post(
            "/api/v1/customers/assignment-rules/reorder",
            headers=auth_headers,
            json={"ids": reordered},
        )
        assert resp.status_code == 200
        listed = await async_client.get(
            "/api/v1/customers/assignment-rules", headers=auth_headers
        )
        priority_by_id = {r["id"]: r["priority"] for r in listed.json()["data"]}
        assert priority_by_id[reordered[0]] == 0
        assert priority_by_id[reordered[1]] == 1
        assert priority_by_id[reordered[2]] == 2


# ── release_rules.py: CRUD ───────────────────────────────────────────


class TestReleaseRules:
    async def test_create_and_list(self, async_client: AsyncClient, auth_headers: dict):
        created = await async_client.post(
            "/api/v1/customers/release-rules",
            headers=auth_headers,
            json={
                "name": "90天无跟进释放",
                "rule_type": "no_followup",
                "condition_days": 90,
            },
        )
        assert created.status_code == 201
        listed = await async_client.get(
            "/api/v1/customers/release-rules", headers=auth_headers
        )
        assert "90天无跟进释放" in [r["name"] for r in listed.json()["data"]]

    async def test_update_and_delete(
        self, async_client: AsyncClient, auth_headers: dict
    ):
        created = await async_client.post(
            "/api/v1/customers/release-rules",
            headers=auth_headers,
            json={"name": "待改释放", "rule_type": "no_order", "condition_days": 60},
        )
        rule_id = created.json()["data"]["id"]
        updated = await async_client.put(
            f"/api/v1/customers/release-rules/{rule_id}",
            headers=auth_headers,
            json={"condition_days": 120, "is_enabled": False},
        )
        assert updated.status_code == 200
        assert updated.json()["data"]["condition_days"] == 120
        assert updated.json()["data"]["is_enabled"] is False

        deleted = await async_client.delete(
            f"/api/v1/customers/release-rules/{rule_id}", headers=auth_headers
        )
        assert deleted.status_code == 200
        listed = await async_client.get(
            "/api/v1/customers/release-rules", headers=auth_headers
        )
        assert rule_id not in [r["id"] for r in listed.json()["data"]]

    async def test_create_rejects_invalid_rule_type(
        self, async_client: AsyncClient, auth_headers: dict
    ):
        resp = await async_client.post(
            "/api/v1/customers/release-rules",
            headers=auth_headers,
            json={"name": "非法类型", "rule_type": "nonsense", "condition_days": 30},
        )
        assert resp.status_code == 422


# ── scheduler: _evaluate_assignment_conditions (pure fn) ─────────────


class TestEvaluateConditions:
    def _cond(self, field: str, operator: str, value: str):
        return SimpleNamespace(field=field, operator=operator, value=value)

    def _rule(self, conditions, logic="all"):
        return SimpleNamespace(conditions=conditions, condition_logic=logic)

    def test_no_conditions_matches_all(self):
        from app.jobs.scheduler import _evaluate_assignment_conditions

        cust = SimpleNamespace(industry="电子")
        assert _evaluate_assignment_conditions(cust, self._rule([])) is True

    def test_equals(self):
        from app.jobs.scheduler import _evaluate_assignment_conditions

        cust = SimpleNamespace(industry="电子")
        rule = self._rule([self._cond("industry", "equals", "电子")])
        assert _evaluate_assignment_conditions(cust, rule) is True
        cust2 = SimpleNamespace(industry="机械")
        assert _evaluate_assignment_conditions(cust2, rule) is False

    def test_in_operator(self):
        from app.jobs.scheduler import _evaluate_assignment_conditions

        rule = self._rule([self._cond("region", "in", "华东, 华南 ,华北")])
        assert (
            _evaluate_assignment_conditions(SimpleNamespace(region="华南"), rule)
            is True
        )
        assert (
            _evaluate_assignment_conditions(SimpleNamespace(region="西北"), rule)
            is False
        )

    def test_contains_and_not_empty(self):
        from app.jobs.scheduler import _evaluate_assignment_conditions

        contains = self._rule([self._cond("region", "contains", "华东")])
        assert (
            _evaluate_assignment_conditions(
                SimpleNamespace(region="华东地区"), contains
            )
            is True
        )
        not_empty = self._rule([self._cond("source", "not_empty", "x")])
        assert (
            _evaluate_assignment_conditions(SimpleNamespace(source="展会"), not_empty)
            is True
        )
        assert (
            _evaluate_assignment_conditions(SimpleNamespace(source=None), not_empty)
            is False
        )

    def test_any_vs_all_logic(self):
        from app.jobs.scheduler import _evaluate_assignment_conditions

        conds = [
            self._cond("industry", "equals", "电子"),
            self._cond("region", "equals", "华东"),
        ]
        cust = SimpleNamespace(industry="电子", region="华南")
        assert _evaluate_assignment_conditions(cust, self._rule(conds, "all")) is False
        assert _evaluate_assignment_conditions(cust, self._rule(conds, "any")) is True


# ── scheduler: _run_auto_assign_job ──────────────────────────────────


class TestAutoAssignJob:
    async def _make_rule(self, db, *, assigned_to, conditions, max_customers=None):
        from app.models.customer import AssignmentRule, AssignmentRuleCondition

        rule = AssignmentRule(
            name="自动分配规则",
            assigned_to=assigned_to,
            condition_logic="all",
            max_customers=max_customers,
        )
        db.add(rule)
        await db.flush()
        for field, operator, value in conditions:
            db.add(
                AssignmentRuleCondition(
                    rule_id=rule.id, field=field, operator=operator, value=value
                )
            )
        await db.flush()
        return rule

    async def test_assigns_matching_public_sea_customer(
        self, db_session: AsyncSession, monkeypatch
    ):
        from app.jobs.scheduler import _run_auto_assign_job

        c = await _make_customer(db_session, name="待分配电子", industry="电子")
        await self._make_rule(
            db_session,
            assigned_to="sales_a",
            conditions=[("industry", "equals", "电子")],
        )
        _patch_session(monkeypatch, db_session)

        result = await _run_auto_assign_job()
        assert result["assigned"] == 1

        await db_session.refresh(c)
        assert c.owner == "sales_a"
        logs = await _owner_logs(db_session, c.id)
        assert logs[-1].action_type == "auto_assign"

    async def test_skips_non_matching_customer(
        self, db_session: AsyncSession, monkeypatch
    ):
        from app.jobs.scheduler import _run_auto_assign_job

        c = await _make_customer(db_session, name="机械客户", industry="机械")
        await self._make_rule(
            db_session,
            assigned_to="sales_a",
            conditions=[("industry", "equals", "电子")],
        )
        _patch_session(monkeypatch, db_session)

        result = await _run_auto_assign_job()
        assert result["assigned"] == 0
        await db_session.refresh(c)
        assert c.owner is None

    async def test_respects_max_customers_cap(
        self, db_session: AsyncSession, monkeypatch
    ):
        from app.jobs.scheduler import _run_auto_assign_job

        c1 = await _make_customer(db_session, name="上限客户1", industry="电子")
        c2 = await _make_customer(db_session, name="上限客户2", industry="电子")
        await self._make_rule(
            db_session,
            assigned_to="sales_a",
            conditions=[("industry", "equals", "电子")],
            max_customers=1,
        )
        _patch_session(monkeypatch, db_session)

        result = await _run_auto_assign_job()
        assert result["assigned"] == 1

        await db_session.refresh(c1)
        await db_session.refresh(c2)
        owners = [c1.owner, c2.owner]
        assert owners.count("sales_a") == 1
        assert owners.count(None) == 1

    async def test_no_rules_returns_zero(self, db_session: AsyncSession, monkeypatch):
        from app.jobs.scheduler import _run_auto_assign_job

        _patch_session(monkeypatch, db_session)
        result = await _run_auto_assign_job()
        assert result == {"assigned": 0, "rules_checked": 0}


# ── scheduler: _run_owner_release_check_job ──────────────────────────


class TestReleaseCheckJob:
    async def _make_release_rule(self, db, *, rule_type, days=90):
        from app.models.customer import ReleaseRule

        rule = ReleaseRule(name="释放规则", rule_type=rule_type, condition_days=days)
        db.add(rule)
        await db.flush()
        return rule

    async def test_releases_stale_owner_no_followup(
        self, db_session: AsyncSession, monkeypatch
    ):
        from app.jobs.scheduler import _run_owner_release_check_job

        old = datetime.now(timezone.utc) - timedelta(days=200)
        c = await _make_customer(
            db_session, name="无跟进僵尸客户", owner="sales_a", created_at=old
        )
        await self._make_release_rule(db_session, rule_type="no_followup", days=90)
        _patch_session(monkeypatch, db_session)

        await _run_owner_release_check_job()

        await db_session.refresh(c)
        assert c.owner is None
        logs = await _owner_logs(db_session, c.id)
        assert logs[-1].action_type == "auto_release"

    async def test_keeps_owner_with_recent_followup(
        self, db_session: AsyncSession, monkeypatch
    ):
        from app.jobs.scheduler import _run_owner_release_check_job

        old = datetime.now(timezone.utc) - timedelta(days=200)
        c = await _make_customer(
            db_session, name="有跟进客户", owner="sales_a", created_at=old
        )
        db_session.add(
            CustomerFollowUp(
                customer_id=c.id,
                completed_at=datetime.now(timezone.utc) - timedelta(days=5),
            )
        )
        await db_session.flush()
        await self._make_release_rule(db_session, rule_type="no_followup", days=90)
        _patch_session(monkeypatch, db_session)

        await _run_owner_release_check_job()

        await db_session.refresh(c)
        assert c.owner == "sales_a"

    async def test_keeps_new_customer_within_grace_period(
        self, db_session: AsyncSession, monkeypatch
    ):
        from app.jobs.scheduler import _run_owner_release_check_job

        # created_at defaults to ~now → within the 90-day grace window.
        c = await _make_customer(db_session, name="新客户", owner="sales_a")
        await self._make_release_rule(db_session, rule_type="no_followup", days=90)
        _patch_session(monkeypatch, db_session)

        await _run_owner_release_check_job()

        await db_session.refresh(c)
        assert c.owner == "sales_a"
