"""Tests for GET /customers/{id}/follow-ups with pagination, filters, counts.

Spec: docs/frontend/followup-list-migration-plan.md
"""

from datetime import datetime, timedelta, timezone

from httpx import AsyncClient


async def _create_customer(client: AsyncClient, headers: dict, suffix: str = "") -> int:
    resp = await client.post(
        "/api/v1/customers",
        headers=headers,
        json={"name": f"followup-cust-{suffix}-{datetime.now().isoformat()}", "type": "终端客户"},
    )
    assert resp.status_code in (200, 201), resp.text
    return resp.json()["data"]["id"]


async def _create_followup(
    client: AsyncClient, headers: dict, cid: int, **payload
) -> int:
    resp = await client.post(
        f"/api/v1/customers/{cid}/follow-ups",
        headers=headers,
        json=payload,
    )
    assert resp.status_code == 201, resp.text
    return resp.json()["data"]["id"]


class TestFollowUpsListPagination:

    async def test_default_returns_new_shape_with_counts(
        self, async_client: AsyncClient, auth_headers: dict
    ):
        cid = await _create_customer(async_client, auth_headers)
        now = datetime.now(timezone.utc)
        await _create_followup(
            async_client, auth_headers, cid,
            status="planned", priority="high",
            planned_at=(now - timedelta(days=2)).isoformat(), content="a",
        )
        await _create_followup(
            async_client, auth_headers, cid,
            status="planned", priority="medium",
            planned_at=(now + timedelta(hours=2)).isoformat(), content="b",
        )
        await _create_followup(
            async_client, auth_headers, cid,
            status="completed", priority="low",
            planned_at=(now - timedelta(days=1)).isoformat(),
            completed_at=now.isoformat(), content="c",
        )
        resp = await async_client.get(
            f"/api/v1/customers/{cid}/follow-ups", headers=auth_headers,
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["code"] == 0
        data = body["data"]
        assert set(data.keys()) == {"list", "total", "counts"}
        assert isinstance(data["list"], list)
        assert data["total"] == 3
        assert data["counts"]["high"] == 1
        assert data["counts"]["completed"] == 1
        assert data["counts"]["overdue"] == 1
        # "b" inserted with planned_at = now + 2h → today bucket
        assert data["counts"]["today"] == 1

    async def test_pagination_meta_page_size(
        self, async_client: AsyncClient, auth_headers: dict
    ):
        cid = await _create_customer(async_client, auth_headers)
        for i in range(5):
            await _create_followup(
                async_client, auth_headers, cid,
                content=f"fup{i}", status="planned",
                planned_at=(datetime.now(timezone.utc) + timedelta(days=i + 1)).isoformat(),
            )
        resp = await async_client.get(
            f"/api/v1/customers/{cid}/follow-ups", headers=auth_headers,
            params={"page": 2, "page_size": 2},
        )
        body = resp.json()["data"]
        assert resp.status_code == 200
        assert body["total"] == 5
        assert len(body["list"]) == 2
        resp3 = await async_client.get(
            f"/api/v1/customers/{cid}/follow-ups", headers=auth_headers,
            params={"page": 3, "page_size": 2},
        )
        assert len(resp3.json()["data"]["list"]) == 1

    async def test_filter_by_status(
        self, async_client: AsyncClient, auth_headers: dict
    ):
        cid = await _create_customer(async_client, auth_headers)
        for s in ["planned", "in_progress", "completed", "cancelled"]:
            await _create_followup(async_client, auth_headers, cid, status=s)
        resp = await async_client.get(
            f"/api/v1/customers/{cid}/follow-ups", headers=auth_headers,
            params={"status": "planned"},
        )
        data = resp.json()["data"]
        assert resp.status_code == 200
        assert data["total"] == 1
        assert data["list"][0]["status"] == "planned"

    async def test_filter_by_priority(
        self, async_client: AsyncClient, auth_headers: dict
    ):
        cid = await _create_customer(async_client, auth_headers)
        for p in ["high", "medium", "low"]:
            await _create_followup(async_client, auth_headers, cid, priority=p)
        resp = await async_client.get(
            f"/api/v1/customers/{cid}/follow-ups", headers=auth_headers,
            params={"priority": "high"},
        )
        data = resp.json()["data"]
        assert data["total"] == 1
        assert data["list"][0]["priority"] == "high"

    async def test_filter_by_due_bucket_overdue(
        self, async_client: AsyncClient, auth_headers: dict
    ):
        cid = await _create_customer(async_client, auth_headers)
        now = datetime.now(timezone.utc)
        await _create_followup(
            async_client, auth_headers, cid, planned_at=(now - timedelta(days=3)).isoformat(),
        )
        await _create_followup(
            async_client, auth_headers, cid, planned_at=(now + timedelta(days=3)).isoformat(),
        )
        await _create_followup(async_client, auth_headers, cid, planned_at=None)
        resp = await async_client.get(
            f"/api/v1/customers/{cid}/follow-ups", headers=auth_headers,
            params={"due_bucket": "overdue"},
        )
        data = resp.json()["data"]
        assert resp.status_code == 200
        assert data["total"] == 1
        assert data["list"][0]["due_bucket"] == "overdue"

    async def test_filter_by_due_bucket_today(
        self, async_client: AsyncClient, auth_headers: dict
    ):
        cid = await _create_customer(async_client, auth_headers)
        now = datetime.now(timezone.utc)
        same_day = now.replace(hour=10, minute=0, second=0, microsecond=0)
        await _create_followup(async_client, auth_headers, cid, planned_at=same_day.isoformat())
        resp = await async_client.get(
            f"/api/v1/customers/{cid}/follow-ups", headers=auth_headers,
            params={"due_bucket": "today"},
        )
        data = resp.json()["data"]
        assert data["total"] == 1
        assert data["list"][0]["due_bucket"] == "today"

    async def test_filter_by_due_bucket_unscheduled(
        self, async_client: AsyncClient, auth_headers: dict
    ):
        cid = await _create_customer(async_client, auth_headers)
        await _create_followup(async_client, auth_headers, cid, planned_at=None)
        await _create_followup(
            async_client, auth_headers, cid,
            planned_at=(datetime.now(timezone.utc) + timedelta(days=1)).isoformat(),
        )
        resp = await async_client.get(
            f"/api/v1/customers/{cid}/follow-ups", headers=auth_headers,
            params={"due_bucket": "unscheduled"},
        )
        data = resp.json()["data"]
        assert data["total"] == 1
        assert data["list"][0]["due_bucket"] == "unscheduled"

    async def test_filter_by_due_bucket_closed(
        self, async_client: AsyncClient, auth_headers: dict
    ):
        cid = await _create_customer(async_client, auth_headers)
        for s in ["completed", "cancelled"]:
            await _create_followup(
                async_client, auth_headers, cid, status=s,
                completed_at=datetime.now(timezone.utc).isoformat(),
            )
        await _create_followup(async_client, auth_headers, cid, status="planned")
        resp = await async_client.get(
            f"/api/v1/customers/{cid}/follow-ups", headers=auth_headers,
            params={"due_bucket": "closed"},
        )
        data = resp.json()["data"]
        assert data["total"] == 2
        assert all(r["due_bucket"] == "closed" for r in data["list"])

    async def test_each_row_has_due_bucket_field(
        self, async_client: AsyncClient, auth_headers: dict
    ):
        cid = await _create_customer(async_client, auth_headers)
        await _create_followup(
            async_client, auth_headers, cid,
            planned_at=(datetime.now(timezone.utc) - timedelta(days=1)).isoformat(),
        )
        await _create_followup(async_client, auth_headers, cid, planned_at=None)
        resp = await async_client.get(
            f"/api/v1/customers/{cid}/follow-ups", headers=auth_headers,
        )
        rows = resp.json()["data"]["list"]
        assert len(rows) == 2
        assert {r["due_bucket"] for r in rows} == {"overdue", "unscheduled"}

    async def test_invalid_due_bucket_returns_422(
        self, async_client: AsyncClient, auth_headers: dict
    ):
        cid = await _create_customer(async_client, auth_headers)
        resp = await async_client.get(
            f"/api/v1/customers/{cid}/follow-ups", headers=auth_headers,
            params={"due_bucket": "tomorrow-is-not-a-bucket"},
        )
        assert resp.status_code == 422

    async def test_page_size_too_large_returns_422(
        self, async_client: AsyncClient, auth_headers: dict
    ):
        cid = await _create_customer(async_client, auth_headers)
        resp = await async_client.get(
            f"/api/v1/customers/{cid}/follow-ups", headers=auth_headers,
            params={"page_size": 200},
        )
        assert resp.status_code == 422

    async def test_page_zero_returns_422(
        self, async_client: AsyncClient, auth_headers: dict
    ):
        cid = await _create_customer(async_client, auth_headers)
        resp = await async_client.get(
            f"/api/v1/customers/{cid}/follow-ups", headers=auth_headers,
            params={"page": 0},
        )
        assert resp.status_code == 422

    async def test_sort_order_overdue_first(
        self, async_client: AsyncClient, auth_headers: dict
    ):
        cid = await _create_customer(async_client, auth_headers)
        now = datetime.now(timezone.utc)
        await _create_followup(
            async_client, auth_headers, cid, status="planned",
            planned_at=(now + timedelta(days=5)).isoformat(), content="upcoming",
        )
        await _create_followup(
            async_client, auth_headers, cid, status="planned",
            planned_at=(now - timedelta(days=10)).isoformat(), content="overdue-old",
        )
        await _create_followup(
            async_client, auth_headers, cid, planned_at=None, content="unscheduled",
        )
        await _create_followup(
            async_client, auth_headers, cid, status="completed",
            planned_at=(now - timedelta(days=2)).isoformat(),
            completed_at=now.isoformat(), content="closed",
        )
        await _create_followup(
            async_client, auth_headers, cid, status="planned",
            planned_at=(now - timedelta(days=1)).isoformat(), content="overdue-recent",
        )
        resp = await async_client.get(
            f"/api/v1/customers/{cid}/follow-ups", headers=auth_headers,
        )
        rows = resp.json()["data"]["list"]
        # Within overdue bucket: ascending by planned_at (oldest first)
        assert [r["content"] for r in rows] == [
            "overdue-old", "overdue-recent", "upcoming", "unscheduled", "closed",
        ]
        assert [r["due_bucket"] for r in rows] == [
            "overdue", "overdue", "upcoming", "unscheduled", "closed",
        ]

    async def test_counts_aggregate_matches_full_set(
        self, async_client: AsyncClient, auth_headers: dict
    ):
        cid = await _create_customer(async_client, auth_headers)
        now = datetime.now(timezone.utc)
        await _create_followup(
            async_client, auth_headers, cid, status="planned",
            priority="high", planned_at=(now - timedelta(days=2)).isoformat(),
        )
        await _create_followup(
            async_client, auth_headers, cid, status="planned", priority="high",
            planned_at=now.replace(hour=10, minute=0, second=0, microsecond=0).isoformat(),
        )
        await _create_followup(
            async_client, auth_headers, cid, status="planned", priority="low",
            planned_at=(now + timedelta(days=2)).isoformat(),
        )
        await _create_followup(
            async_client, auth_headers, cid, status="planned", priority="low",
            planned_at=None,
        )
        await _create_followup(
            async_client, auth_headers, cid, status="completed", priority="high",
            planned_at=(now - timedelta(days=1)).isoformat(),
            completed_at=now.isoformat(),
        )
        await _create_followup(
            async_client, auth_headers, cid, status="cancelled", priority="low",
        )
        resp = await async_client.get(
            f"/api/v1/customers/{cid}/follow-ups", headers=auth_headers,
            params={"page_size": 100},
        )
        body = resp.json()["data"]
        assert body["total"] == 6
        assert body["counts"]["open"] == 4
        assert body["counts"]["completed"] == 1
        assert body["counts"]["high"] == 3
        assert body["counts"]["overdue"] == 1
        assert body["counts"]["today"] == 1

    async def test_counts_reflect_due_bucket_filter(
        self, async_client: AsyncClient, auth_headers: dict
    ):
        cid = await _create_customer(async_client, auth_headers)
        now = datetime.now(timezone.utc)
        await _create_followup(
            async_client, auth_headers, cid, status="planned",
            planned_at=(now - timedelta(days=2)).isoformat(), priority="high",
        )
        await _create_followup(
            async_client, auth_headers, cid, status="planned",
            planned_at=(now + timedelta(days=2)).isoformat(), priority="high",
        )
        resp = await async_client.get(
            f"/api/v1/customers/{cid}/follow-ups", headers=auth_headers,
        )
        assert resp.json()["data"]["counts"]["overdue"] == 1
        assert resp.json()["data"]["counts"]["high"] == 2
        resp2 = await async_client.get(
            f"/api/v1/customers/{cid}/follow-ups", headers=auth_headers,
            params={"due_bucket": "overdue"},
        )
        body2 = resp2.json()["data"]
        assert body2["total"] == 1
        assert body2["counts"]["overdue"] == 1
        assert body2["counts"]["high"] == 1
        assert body2["counts"]["today"] == 0

    async def test_soft_deleted_excluded(
        self, async_client: AsyncClient, auth_headers: dict
    ):
        cid = await _create_customer(async_client, auth_headers)
        fup_id = await _create_followup(async_client, auth_headers, cid)
        del_resp = await async_client.delete(
            f"/api/v1/customers/{cid}/follow-ups/{fup_id}", headers=auth_headers,
        )
        assert del_resp.status_code == 200
        listed = await async_client.get(
            f"/api/v1/customers/{cid}/follow-ups", headers=auth_headers,
        )
        data = listed.json()["data"]
        assert data["total"] == 0
        assert data["list"] == []
        assert all(v == 0 for v in data["counts"].values())

    async def test_counts_zero_when_no_records(
        self, async_client: AsyncClient, auth_headers: dict
    ):
        cid = await _create_customer(async_client, auth_headers)
        resp = await async_client.get(
            f"/api/v1/customers/{cid}/follow-ups", headers=auth_headers,
        )
        body = resp.json()["data"]
        assert body["total"] == 0
        assert body["list"] == []
        assert body["counts"] == {
            "open": 0, "completed": 0, "high": 0, "overdue": 0, "today": 0,
        }
