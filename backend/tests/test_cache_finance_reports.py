"""v5 cache tests — finance and reports endpoints.

Covers:
- HIT/MISS cycle for stats endpoints
- HIT/MISS cycle for list endpoints (with param-based keys)
- Write-path invalidation across dependent families
- Cache hit/miss Prometheus counters

Note on permissions:
- `finance.py` endpoints (invoices/payments/contracts/targets) use only
  `get_current_user`, so the regular `auth_headers` (sales role) work.
- `finance_accounts.py` (accounts/journal-entries/pnl/ap/bank) and
  `reports.py` (templates/predefined/*) use `require_perm`, so they
  require `admin_headers`.
"""

from __future__ import annotations

import pytest
from httpx import AsyncClient


@pytest.fixture(autouse=True)
def _reset_metrics():
    """Reset Prometheus counters and L1 cache between tests."""
    from app.core.observability.metrics import reset_all
    from app.services.cache_service import _l1_cache, _l1_epochs

    reset_all()
    if _l1_cache is not None:
        _l1_cache.clear()
    _l1_epochs.clear()
    yield
    reset_all()
    if _l1_cache is not None:
        _l1_cache.clear()
    _l1_epochs.clear()


async def _seed_sales_order(
    async_client: AsyncClient, auth_headers: dict, customer_id: int
) -> int:
    """Helper: create a sales order to satisfy FK requirements for invoices/payments."""
    resp = await async_client.post(
        "/api/v1/sales-orders",
        headers=auth_headers,
        json={
            "customer_id": customer_id,
            "status": "pending",
            "total_amount": 5000,
            "items": [
                {
                    "product_name": "Test Item",
                    "quantity": 1,
                    "unit_price": 5000,
                    "total_price": 5000,
                }
            ],
        },
    )
    assert resp.status_code in (200, 201), resp.text
    return resp.json()["data"]["id"]


class TestFinanceStatsCache:
    """Verify HIT/MISS cycle for /finance stats endpoints (use get_current_user only)."""

    async def test_payments_stats_miss_then_hit(
        self, async_client: AsyncClient, auth_headers: dict
    ):
        r1 = await async_client.get("/api/v1/payments/stats", headers=auth_headers)
        assert r1.status_code == 200, r1.text
        assert r1.headers.get("X-Cache") == "MISS"

        r2 = await async_client.get("/api/v1/payments/stats", headers=auth_headers)
        assert r2.status_code == 200, r2.text
        assert r2.headers.get("X-Cache") == "HIT"
        assert r2.json() == r1.json()

    async def test_target_stats_miss_then_hit(
        self, async_client: AsyncClient, auth_headers: dict
    ):
        r1 = await async_client.get("/api/v1/targets/stats", headers=auth_headers)
        assert r1.status_code == 200, r1.text
        assert r1.headers.get("X-Cache") == "MISS"

        r2 = await async_client.get("/api/v1/targets/stats", headers=auth_headers)
        assert r2.headers.get("X-Cache") == "HIT"
        assert r2.json() == r1.json()


class TestFinanceListCache:
    """Verify HIT/MISS for paginated list endpoints (finance.py, no perm gate)."""

    async def test_invoices_list_keys_differ_by_filters(
        self, async_client: AsyncClient, auth_headers: dict
    ):
        r1 = await async_client.get(
            "/api/v1/invoices?page=1&page_size=20", headers=auth_headers
        )
        assert r1.status_code == 200, r1.text
        assert r1.headers.get("X-Cache") == "MISS"

        r2 = await async_client.get(
            "/api/v1/invoices?page=1&page_size=20", headers=auth_headers
        )
        assert r2.headers.get("X-Cache") == "HIT"

        r3 = await async_client.get(
            "/api/v1/invoices?page=1&page_size=20&status=draft", headers=auth_headers
        )
        assert r3.headers.get("X-Cache") == "MISS"

    async def test_payments_list_miss_then_hit(
        self, async_client: AsyncClient, auth_headers: dict
    ):
        r1 = await async_client.get(
            "/api/v1/payments?page=1&page_size=20", headers=auth_headers
        )
        assert r1.headers.get("X-Cache") == "MISS"
        r2 = await async_client.get(
            "/api/v1/payments?page=1&page_size=20", headers=auth_headers
        )
        assert r2.headers.get("X-Cache") == "HIT"

    async def test_contracts_list_miss_then_hit(
        self, async_client: AsyncClient, auth_headers: dict
    ):
        r1 = await async_client.get(
            "/api/v1/contracts?page=1&page_size=20", headers=auth_headers
        )
        assert r1.headers.get("X-Cache") == "MISS"
        r2 = await async_client.get(
            "/api/v1/contracts?page=1&page_size=20", headers=auth_headers
        )
        assert r2.headers.get("X-Cache") == "HIT"

    async def test_targets_list_miss_then_hit(
        self, async_client: AsyncClient, auth_headers: dict
    ):
        r1 = await async_client.get(
            "/api/v1/targets?page=1&page_size=20", headers=auth_headers
        )
        assert r1.headers.get("X-Cache") == "MISS"
        r2 = await async_client.get(
            "/api/v1/targets?page=1&page_size=20", headers=auth_headers
        )
        assert r2.headers.get("X-Cache") == "HIT"


class TestFinanceReportsCache:
    """Verify HIT/MISS for /finance/reports/pnl and /finance/reports/ap (require admin)."""

    async def test_pnl_report_miss_then_hit(
        self, async_client: AsyncClient, admin_headers: dict
    ):
        month = "2026-05"
        r1 = await async_client.get(
            f"/api/v1/finance/reports/pnl?month={month}", headers=admin_headers
        )
        assert r1.status_code == 200, r1.text
        assert r1.headers.get("X-Cache") == "MISS"

        r2 = await async_client.get(
            f"/api/v1/finance/reports/pnl?month={month}", headers=admin_headers
        )
        assert r2.headers.get("X-Cache") == "HIT"
        assert r2.json() == r1.json()

    async def test_pnl_keys_differ_by_month(
        self, async_client: AsyncClient, admin_headers: dict
    ):
        r1 = await async_client.get(
            "/api/v1/finance/reports/pnl?month=2026-04", headers=admin_headers
        )
        assert r1.headers.get("X-Cache") == "MISS"
        r2 = await async_client.get(
            "/api/v1/finance/reports/pnl?month=2026-05", headers=admin_headers
        )
        assert r2.headers.get("X-Cache") == "MISS"
        r3 = await async_client.get(
            "/api/v1/finance/reports/pnl?month=2026-04", headers=admin_headers
        )
        assert r3.headers.get("X-Cache") == "HIT"

    async def test_ap_report_miss_then_hit(
        self, async_client: AsyncClient, admin_headers: dict
    ):
        r1 = await async_client.get("/api/v1/finance/reports/ap", headers=admin_headers)
        assert r1.status_code == 200, r1.text
        assert r1.headers.get("X-Cache") == "MISS"
        r2 = await async_client.get("/api/v1/finance/reports/ap", headers=admin_headers)
        assert r2.headers.get("X-Cache") == "HIT"


class TestFinanceWritePathInvalidation:
    """Verify write endpoints bump dependent cache families."""

    async def test_payment_create_invalidates_payments_stats(
        self, async_client: AsyncClient, auth_headers: dict, test_customer: dict
    ):
        await async_client.get("/api/v1/payments/stats", headers=auth_headers)
        cached = await async_client.get("/api/v1/payments/stats", headers=auth_headers)
        assert cached.headers.get("X-Cache") == "HIT"

        order_id = await _seed_sales_order(
            async_client, auth_headers, test_customer["id"]
        )
        resp = await async_client.post(
            "/api/v1/payments",
            headers=auth_headers,
            json={
                "sales_order_id": order_id,
                "customer_id": test_customer["id"],
                "amount": 1500,
                "status": "completed",
            },
        )
        assert resp.status_code == 200, resp.text

        after = await async_client.get("/api/v1/payments/stats", headers=auth_headers)
        assert after.headers.get("X-Cache") == "MISS"

    async def test_invoice_create_invalidates_invoices_list(
        self, async_client: AsyncClient, auth_headers: dict, test_customer: dict
    ):
        await async_client.get(
            "/api/v1/invoices?page=1&page_size=20", headers=auth_headers
        )
        cached = await async_client.get(
            "/api/v1/invoices?page=1&page_size=20", headers=auth_headers
        )
        assert cached.headers.get("X-Cache") == "HIT"

        order_id = await _seed_sales_order(
            async_client, auth_headers, test_customer["id"]
        )
        resp = await async_client.post(
            "/api/v1/invoices",
            headers=auth_headers,
            json={
                "sales_order_id": order_id,
                "customer_id": test_customer["id"],
                "amount": 1000,
                "tax_amount": 0,
            },
        )
        assert resp.status_code == 200, resp.text

        after = await async_client.get(
            "/api/v1/invoices?page=1&page_size=20", headers=auth_headers
        )
        assert after.headers.get("X-Cache") == "MISS"


class TestReportsPredefinedCache:
    """Verify HIT/MISS for /reports/predefined/* endpoints (require admin)."""

    async def test_predefined_sales_miss_then_hit(
        self, async_client: AsyncClient, admin_headers: dict
    ):
        r1 = await async_client.get(
            "/api/v1/reports/predefined/sales?months=12", headers=admin_headers
        )
        assert r1.status_code == 200, r1.text
        assert r1.headers.get("X-Cache") == "MISS"
        r2 = await async_client.get(
            "/api/v1/reports/predefined/sales?months=12", headers=admin_headers
        )
        assert r2.headers.get("X-Cache") == "HIT"

    async def test_predefined_sales_keys_differ_by_months(
        self, async_client: AsyncClient, admin_headers: dict
    ):
        r1 = await async_client.get(
            "/api/v1/reports/predefined/sales?months=12", headers=admin_headers
        )
        assert r1.headers.get("X-Cache") == "MISS"
        r2 = await async_client.get(
            "/api/v1/reports/predefined/sales?months=6", headers=admin_headers
        )
        assert r2.headers.get("X-Cache") == "MISS"

    async def test_predefined_ar_miss_then_hit(
        self, async_client: AsyncClient, admin_headers: dict
    ):
        r1 = await async_client.get(
            "/api/v1/reports/predefined/ar", headers=admin_headers
        )
        assert r1.status_code == 200, r1.text
        assert r1.headers.get("X-Cache") == "MISS"
        r2 = await async_client.get(
            "/api/v1/reports/predefined/ar", headers=admin_headers
        )
        assert r2.headers.get("X-Cache") == "HIT"

    async def test_predefined_inventory_miss_then_hit(
        self, async_client: AsyncClient, admin_headers: dict
    ):
        r1 = await async_client.get(
            "/api/v1/reports/predefined/inventory", headers=admin_headers
        )
        assert r1.status_code == 200, r1.text
        assert r1.headers.get("X-Cache") == "MISS"
        r2 = await async_client.get(
            "/api/v1/reports/predefined/inventory", headers=admin_headers
        )
        assert r2.headers.get("X-Cache") == "HIT"

    async def test_predefined_procurement_miss_then_hit(
        self, async_client: AsyncClient, admin_headers: dict
    ):
        r1 = await async_client.get(
            "/api/v1/reports/predefined/procurement?months=12", headers=admin_headers
        )
        assert r1.status_code == 200, r1.text
        assert r1.headers.get("X-Cache") == "MISS"
        r2 = await async_client.get(
            "/api/v1/reports/predefined/procurement?months=12", headers=admin_headers
        )
        assert r2.headers.get("X-Cache") == "HIT"


class TestReportsTemplatesCache:
    async def test_templates_miss_then_hit(
        self, async_client: AsyncClient, admin_headers: dict
    ):
        r1 = await async_client.get("/api/v1/reports/templates", headers=admin_headers)
        assert r1.status_code == 200, r1.text
        assert r1.headers.get("X-Cache") == "MISS"
        r2 = await async_client.get("/api/v1/reports/templates", headers=admin_headers)
        assert r2.headers.get("X-Cache") == "HIT"

    async def test_template_create_invalidates_list(
        self, async_client: AsyncClient, admin_headers: dict
    ):
        await async_client.get("/api/v1/reports/templates", headers=admin_headers)
        cached = await async_client.get(
            "/api/v1/reports/templates", headers=admin_headers
        )
        assert cached.headers.get("X-Cache") == "HIT"

        resp = await async_client.post(
            "/api/v1/reports/templates",
            headers=admin_headers,
            json={
                "name": "Test Template",
                "type": "sales",
                "config": {},
                "is_public": False,
            },
        )
        assert resp.status_code == 201, resp.text

        after = await async_client.get(
            "/api/v1/reports/templates", headers=admin_headers
        )
        assert after.headers.get("X-Cache") == "MISS"


class TestFinanceAccountsCache:
    async def test_accounts_list_miss_then_hit(
        self, async_client: AsyncClient, admin_headers: dict
    ):
        r1 = await async_client.get("/api/v1/finance/accounts", headers=admin_headers)
        assert r1.status_code == 200, r1.text
        assert r1.headers.get("X-Cache") == "MISS"
        r2 = await async_client.get("/api/v1/finance/accounts", headers=admin_headers)
        assert r2.headers.get("X-Cache") == "HIT"

    async def test_journal_entries_list_miss_then_hit(
        self, async_client: AsyncClient, admin_headers: dict
    ):
        r1 = await async_client.get(
            "/api/v1/finance/journal-entries?page=1&page_size=20", headers=admin_headers
        )
        assert r1.status_code == 200, r1.text
        assert r1.headers.get("X-Cache") == "MISS"
        r2 = await async_client.get(
            "/api/v1/finance/journal-entries?page=1&page_size=20", headers=admin_headers
        )
        assert r2.headers.get("X-Cache") == "HIT"


class TestCacheMetricsIncrement:
    """Verify the Prometheus cache counters track hits/invalidations correctly.

    Note: when Redis is unavailable (L2 down) and L1 is empty, the versioned
    `cache_get_versioned` returns None without incrementing the miss counter
    (a pre-existing edge case in `cache_service.py`). These tests focus on
    hits and invalidations, which are tracked reliably.
    """

    async def test_hits_increment_for_finance_stats(
        self, async_client: AsyncClient, auth_headers: dict
    ):
        from app.core.observability.metrics import cache_hits_total

        # First call populates L1 (and L2 if Redis is up)
        await async_client.get("/api/v1/payments/stats", headers=auth_headers)
        # Second call should hit L1
        await async_client.get("/api/v1/payments/stats", headers=auth_headers)
        hits = cache_hits_total.value(family="payments:stats")
        assert hits >= 1

    async def test_invalidations_increment_on_write(
        self, async_client: AsyncClient, auth_headers: dict, test_customer: dict
    ):
        # Use L1 epoch as a proxy for invalidation: writes must bump the family's
        # L1 epoch regardless of Redis availability.
        from app.services.cache_service import _l1_epochs

        await async_client.get("/api/v1/payments/stats", headers=auth_headers)
        before_epoch = _l1_epochs.get("payments:stats", 0)

        order_id = await _seed_sales_order(
            async_client, auth_headers, test_customer["id"]
        )
        await async_client.post(
            "/api/v1/payments",
            headers=auth_headers,
            json={
                "sales_order_id": order_id,
                "customer_id": test_customer["id"],
                "amount": 200,
                "status": "completed",
            },
        )
        after_epoch = _l1_epochs.get("payments:stats", 0)
        assert after_epoch > before_epoch

        # And verify via the X-Cache header that the next read is a fresh MISS
        after = await async_client.get("/api/v1/payments/stats", headers=auth_headers)
        assert after.headers.get("X-Cache") == "MISS"


class TestCacheHitRatioExposedInPrometheus:
    """Verify the new families appear in the Prometheus text with sampled hit_ratio."""

    async def test_prometheus_text_includes_finance_reports_families(
        self, async_client: AsyncClient, auth_headers: dict
    ):
        # Generate some traffic on user-gated endpoints
        await async_client.get("/api/v1/payments/stats", headers=auth_headers)
        await async_client.get("/api/v1/payments/stats", headers=auth_headers)
        await async_client.get("/api/v1/targets/stats", headers=auth_headers)
        await async_client.get("/api/v1/targets/stats", headers=auth_headers)

        resp = await async_client.get("/metrics/prometheus")
        assert resp.status_code == 200
        body = resp.text
        assert 'cache_hit_ratio{family="payments:stats"}' in body
        assert 'cache_hit_ratio{family="targets:stats"}' in body
