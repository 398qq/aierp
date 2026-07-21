"""Expiry alert service tests — Stage 18 / Production Batch Management.

Covers the 4-bucket expiry scan (expired / 7d / 30d / 90d) and edge cases
(status filtering, warehouse filter, empty result).
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import uuid
import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.product import InventoryBatchORM, Product, Warehouse
from app.services.expiry_alert_service import (
    BUCKET_30D,
    BUCKET_7D,
    BUCKET_90D,
    EXPIRED,
    VALID_BUCKETS,
    expiry_alert_service,
)

pytestmark = pytest.mark.asyncio


# ── helpers ─────────────────────────────────────────────────────────


async def _make_warehouse(db: AsyncSession) -> Warehouse:
    wh = Warehouse(name="测试仓", location="深圳")
    db.add(wh)
    await db.flush()
    return wh


async def _make_product(db: AsyncSession) -> Product:
    p = Product(name="测试产品", sku="TEST-001", unit="PCS")
    db.add(p)
    await db.flush()
    return p


async def _make_batch(
    db: AsyncSession,
    *,
    product_id: int,
    warehouse_id: int,
    days_until_expiry: int | None,
    quantity: int = 10,
    status: str = "available",
) -> InventoryBatchORM:
    expiry = None
    if days_until_expiry is not None:
        expiry = datetime.now(timezone.utc) + timedelta(days=days_until_expiry)
    # Use uuid hex to guarantee uniqueness across tests (composite uq on
    # product_id + warehouse_id + batch_no would collide on same-second runs).
    batch = InventoryBatchORM(
        product_id=product_id,
        warehouse_id=warehouse_id,
        batch_no=f"B-{uuid.uuid4().hex[:8]}",
        quantity=quantity,
        expiry_date=expiry,
        status=status,
    )
    db.add(batch)
    await db.flush()
    return batch


# ── tests ───────────────────────────────────────────────────────────


class TestExpiryScan:
    async def test_buckets_are_4(self):
        """The 4 expected buckets must exist (expired/7d/30d/90d)."""
        assert VALID_BUCKETS == {EXPIRED, BUCKET_7D, BUCKET_30D, BUCKET_90D}

    async def test_scan_empty_returns_empty_buckets(
        self, db_session: AsyncSession
    ):
        """No batches in DB → all buckets empty, no errors."""
        result = await expiry_alert_service.scan(db_session)
        assert set(result.keys()) == VALID_BUCKETS
        for v in result.values():
            assert v == []

    async def test_expired_batch_lands_in_expired_bucket(
        self, db_session: AsyncSession
    ):
        """A batch with expiry_date in the past → 'expired' bucket."""
        wh = await _make_warehouse(db_session)
        p = await _make_product(db_session)
        await _make_batch(
            db_session, product_id=p.id, warehouse_id=wh.id,
            days_until_expiry=-3,
        )
        result = await expiry_alert_service.scan(db_session)
        assert len(result[EXPIRED]) == 1
        assert result[EXPIRED][0]["days_until_expiry"] == -3
        assert all(len(v) == 0 for k, v in result.items() if k != EXPIRED)

    async def test_7d_bucket_catches_within_7_days(
        self, db_session: AsyncSession
    ):
        """Expiry within 1–7 days → '7d' bucket; exactly 0 days → expired."""
        wh = await _make_warehouse(db_session)
        p = await _make_product(db_session)
        await _make_batch(
            db_session, product_id=p.id, warehouse_id=wh.id, days_until_expiry=3
        )
        await _make_batch(
            db_session, product_id=p.id, warehouse_id=wh.id, days_until_expiry=7
        )
        await _make_batch(
            db_session, product_id=p.id, warehouse_id=wh.id, days_until_expiry=0
        )
        result = await expiry_alert_service.scan(db_session)
        assert len(result[BUCKET_7D]) == 2
        assert len(result[EXPIRED]) == 1

    async def test_30d_bucket_includes_8_to_30_days(
        self, db_session: AsyncSession
    ):
        """8–30 days → 30d bucket; 31+ days → 90d bucket."""
        wh = await _make_warehouse(db_session)
        p = await _make_product(db_session)
        await _make_batch(
            db_session, product_id=p.id, warehouse_id=wh.id, days_until_expiry=15
        )
        await _make_batch(
            db_session, product_id=p.id, warehouse_id=wh.id, days_until_expiry=30
        )
        await _make_batch(
            db_session, product_id=p.id, warehouse_id=wh.id, days_until_expiry=45
        )
        result = await expiry_alert_service.scan(db_session)
        assert len(result[BUCKET_30D]) == 2
        assert len(result[BUCKET_90D]) == 1

    async def test_consumed_and_zero_qty_batches_excluded(
        self, db_session: AsyncSession
    ):
        """Batches with status=consumed/recalled or quantity<=0 → excluded."""
        wh = await _make_warehouse(db_session)
        p = await _make_product(db_session)
        # Expiring soon but consumed → excluded
        await _make_batch(
            db_session, product_id=p.id, warehouse_id=wh.id,
            days_until_expiry=5, status="consumed",
        )
        # Expiring soon but quantity 0 → excluded
        await _make_batch(
            db_session, product_id=p.id, warehouse_id=wh.id,
            days_until_expiry=5, quantity=0,
        )
        # Recalled → excluded
        await _make_batch(
            db_session, product_id=p.id, warehouse_id=wh.id,
            days_until_expiry=5, status="recalled",
        )
        # Available + qty>0 → included
        await _make_batch(
            db_session, product_id=p.id, warehouse_id=wh.id,
            days_until_expiry=5, quantity=10, status="available",
        )
        result = await expiry_alert_service.scan(db_session)
        assert len(result[BUCKET_7D]) == 1

    async def test_warehouse_filter_narrows_results(
        self, db_session: AsyncSession
    ):
        """Warehouse filter returns only batches from that warehouse."""
        wh_a = await _make_warehouse(db_session)
        wh_b = Warehouse(name="测试仓B", location="上海")
        db_session.add(wh_b)
        await db_session.flush()
        p = await _make_product(db_session)
        await _make_batch(
            db_session, product_id=p.id, warehouse_id=wh_a.id,
            days_until_expiry=10,
        )
        await _make_batch(
            db_session, product_id=p.id, warehouse_id=wh_b.id,
            days_until_expiry=10,
        )
        result = await expiry_alert_service.scan(
            db_session, warehouse_id=wh_a.id
        )
        total = sum(len(v) for v in result.values())
        assert total == 1

    async def test_no_expiry_date_excluded(self, db_session: AsyncSession):
        """Batches with expiry_date=NULL are excluded from all buckets."""
        wh = await _make_warehouse(db_session)
        p = await _make_product(db_session)
        await _make_batch(
            db_session, product_id=p.id, warehouse_id=wh.id,
            days_until_expiry=None,
        )
        result = await expiry_alert_service.scan(db_session)
        assert sum(len(v) for v in result.values()) == 0

    async def test_invalid_bucket_raises_value_error(
        self, db_session: AsyncSession
    ):
        """Unknown bucket name → ValueError (API translates to 400)."""
        with pytest.raises(ValueError, match="未知 bucket"):
            await expiry_alert_service.scan(db_session, buckets=["bogus_bucket"])

    async def test_summary_returns_counts_per_bucket(
        self, db_session: AsyncSession
    ):
        """Summary returns total + per-bucket counts + widget-friendly list."""
        wh = await _make_warehouse(db_session)
        p = await _make_product(db_session)
        await _make_batch(
            db_session, product_id=p.id, warehouse_id=wh.id, days_until_expiry=-1
        )
        await _make_batch(
            db_session, product_id=p.id, warehouse_id=wh.id, days_until_expiry=2
        )
        await _make_batch(
            db_session, product_id=p.id, warehouse_id=wh.id, days_until_expiry=20
        )
        summary = await expiry_alert_service.get_summary(db_session)
        assert summary["total_expiring"] == 3
        assert summary["counts_by_bucket"][EXPIRED] == 1
        assert summary["counts_by_bucket"][BUCKET_7D] == 1
        assert summary["counts_by_bucket"][BUCKET_30D] == 1
        # 90d has no hits
        assert summary["counts_by_bucket"][BUCKET_90D] == 0
        # Widget payload has all 4 buckets (even when count=0)
        assert len(summary["buckets"]) == 4
        assert {b["severity"] for b in summary["buckets"]} == {
            "critical", "high", "medium", "low"
        }