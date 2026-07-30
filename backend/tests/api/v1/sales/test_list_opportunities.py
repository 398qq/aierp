"""Tests for GET /api/v1/opportunities with new kanban param + counts block.

Spec: docs/frontend/opportunity-list-design.md
"""

from datetime import datetime, timedelta, timezone

import pytest
from httpx import AsyncClient


async def _make_customer(client, headers, suffix=""):
    resp = await client.post(
        "/api/v1/customers", headers=headers,
        json={"name": f"opp-cust-{suffix}-{datetime.now().isoformat()}", "type": "终端客户"},
    )
    assert resp.status_code in (200, 201), resp.text
    return resp.json()["data"]["id"]


async def _make_opp(client, headers, cid, **payload):
    """POST opportunity. status defaults to 'active' (the only value the
    OpportunityCreate schema accepts); win_probability / amount / dates
    may be overridden via kwargs."""
    base = {"customer_id": cid, "title": f"opp-{datetime.now().isoformat()}", "amount": 100}
    base.update(payload)
    resp = await client.post(
        "/api/v1/opportunities",
        headers=headers,
        json=base,
    )
    assert resp.status_code in (200, 201), resp.text
    return resp.json()["data"]


class TestOpportunitiesListKanban:

    async def test_kanban_false_returns_normal_pagination(
        self, async_client, auth_headers
    ):
        cid = await _make_customer(async_client, auth_headers)
        for _ in range(5):
            await _make_opp(async_client, auth_headers, cid)

        resp = await async_client.get(
            "/api/v1/opportunities", headers=auth_headers,
        )
        body = resp.json()
        assert resp.status_code == 200
        assert body["data"]["page"] == 1
        assert body["data"]["page_size"] == 20
        # counts.count always present in new shape
        assert body["data"]["counts"]["count"] == 5

    async def test_kanban_true_caps_response_at_200(
        self, async_client, auth_headers
    ):
        cid = await _make_customer(async_client, auth_headers)
        for _ in range(120):
            await _make_opp(async_client, auth_headers, cid, amount=10)

        resp = await async_client.get(
            "/api/v1/opportunities",
            headers=auth_headers,
            params={"kanban": "true"},
        )
        body = resp.json()
        assert resp.status_code == 200
        # 120 records < 200 cap -> all returned
        assert len(body["data"]["list"]) == 120
        assert body["data"]["counts"]["count"] == 120
        # page / page_size forced to 1 / 200 regardless of caller values
        assert body["data"]["page"] == 1
        assert body["data"]["page_size"] == 200

    async def test_kanban_true_overrides_explicit_page_params(
        self, async_client, auth_headers
    ):
        cid = await _make_customer(async_client, auth_headers)
        for _ in range(5):
            await _make_opp(async_client, auth_headers, cid)

        resp = await async_client.get(
            "/api/v1/opportunities",
            headers=auth_headers,
            params={"kanban": "true", "page": "99", "page_size": "10"},
        )
        body = resp.json()
        # even with explicit page=99 we still get page 1 / size 200
        assert body["data"]["page"] == 1
        assert body["data"]["page_size"] == 200


class TestOpportunitiesListCounts:

    async def test_counts_amount_and_weighted(
        self, async_client, auth_headers
    ):
        cid = await _make_customer(async_client, auth_headers)
        await _make_opp(async_client, auth_headers, cid,
                          amount=200, win_probability=80)
        await _make_opp(async_client, auth_headers, cid,
                          amount=300, win_probability=20)

        resp = await async_client.get(
            "/api/v1/opportunities", headers=auth_headers,
        )
        counts = resp.json()["data"]["counts"]
        assert counts["count"] == 2
        assert counts["amount"] == 500
        # weighted = 200*0.8 + 300*0.2 = 160+60 = 220
        assert abs(counts["weightedAmount"] - 220) < 0.01
        assert counts["active"] == 2

    async def test_counts_overdue_and_due_soon(
        self, async_client, auth_headers
    ):
        cid = await _make_customer(async_client, auth_headers)
        now = datetime.now(timezone.utc)
        # 1 overdue (active, past)
        await _make_opp(async_client, auth_headers, cid,
                         status="active",
                         expected_close_date=(now - timedelta(days=3)).isoformat())
        # 1 due_soon (active, within 14 days)
        await _make_opp(async_client, auth_headers, cid,
                         status="active",
                         expected_close_date=(now + timedelta(days=5)).isoformat())
        # 1 future (>14 days) — still active, not counted in overdue/dueSoon
        await _make_opp(async_client, auth_headers, cid,
                         status="active",
                         expected_close_date=(now + timedelta(days=30)).isoformat())

        resp = await async_client.get(
            "/api/v1/opportunities", headers=auth_headers,
        )
        counts = resp.json()["data"]["counts"]
        assert counts["overdue"] == 1
        assert counts["dueSoon"] == 1

    async def test_counts_filter_aware(
        self, async_client, auth_headers
    ):
        cid_a = await _make_customer(async_client, auth_headers, "a")
        cid_b = await _make_customer(async_client, auth_headers, "b")
        await _make_opp(async_client, auth_headers, cid_a, amount=100)
        await _make_opp(async_client, auth_headers, cid_b, amount=200)

        # Filter to customer A — total + counts should match only A
        resp = await async_client.get(
            "/api/v1/opportunities",
            headers=auth_headers,
            params={"customer_id": cid_a},
        )
        body = resp.json()
        assert body["data"]["counts"]["count"] == 1
        assert body["data"]["counts"]["amount"] == 100

    async def test_counts_at_risk_uses_ai_risk_level_column(
        self, async_client, auth_headers, db_session
    ):
        """ai_risk_level column is populated by the AI scoring job.
        Verify counts.atRisk = count of rows where ai_risk_level='high'."""
        cid = await _make_customer(async_client, auth_headers)
        for _ in range(3):
            await _make_opp(async_client, auth_headers, cid)
        # Direct SQL seed (no public endpoint exposes ai_risk_level)
        from sqlalchemy import update
        from app.models.sales import Opportunity
        from app.schemas.sales import OpportunityCreate  # noqa: F401  ensure import path
        # Update first 2 rows to high risk, leave 3rd as None
        rows = (await db_session.execute(
            update(Opportunity)
            .where(Opportunity.customer_id == cid)
            .values(ai_risk_level="high")
            .returning(Opportunity.id)
        )).scalars().all()
        assert len(rows) == 3
        # Roll back the 3rd
        await db_session.execute(
            update(Opportunity)
            .where(Opportunity.id == rows[-1])
            .values(ai_risk_level=None)
        )
        await db_session.commit()

        resp = await async_client.get(
            "/api/v1/opportunities", headers=auth_headers,
        )
        counts = resp.json()["data"]["counts"]
        assert counts["atRisk"] == 2


class TestOpportunitiesListAI:

    async def test_ai_null_when_include_ai_false(
        self, async_client, auth_headers
    ):
        cid = await _make_customer(async_client, auth_headers)
        for _ in range(3):
            await _make_opp(async_client, auth_headers, cid)

        resp = await async_client.get(
            "/api/v1/opportunities", headers=auth_headers,
        )
        body = resp.json()
        assert resp.status_code == 200
        # ai is null when include_ai is unset (false)
        assert body["data"]["ai"] is None

    async def test_cache_separates_kanban_and_non_kanban(
        self, async_client, auth_headers
    ):
        cid = await _make_customer(async_client, auth_headers)
        for _ in range(2):
            await _make_opp(async_client, auth_headers, cid)

        # First non-kanban fetch populates cache (MISS)
        normal = await async_client.get(
            "/api/v1/opportunities", headers=auth_headers,
        )
        # Second non-kanban fetch should HIT same cache
        cached = await async_client.get(
            "/api/v1/opportunities", headers=auth_headers,
        )
        assert cached.headers.get("X-Cache") == "HIT"

        # Kanban call should MISS (different cache key)
        kanban = await async_client.get(
            "/api/v1/opportunities",
            headers=auth_headers,
            params={"kanban": "true"},
        )
        assert kanban.headers.get("X-Cache") == "MISS"
