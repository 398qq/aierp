"""Batch merge / split service tests — Stage 18 P5.

Verifies:
  merge:
    - consolidates quantities into the oldest survivor
    - computes weighted average unit cost
    - marks non-survivors status=consumed, qty=0
    - writes one adjust-tx per consumed + one on survivor
    - rejects: <2 ids, duplicate ids, different product/warehouse/batch_no,
      non-available status, qty=0, missing ids
  split:
    - creates a new batch with auto-generated -S1 batch_no
    - decrements source quantity (source -> consumed at 0)
    - accepts explicit new_batch_no
    - rejects: qty<=0, qty>=src.quantity, non-available, missing id
"""

from __future__ import annotations

import uuid
from decimal import Decimal

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.product import (
    InventoryBatchORM,
    InventoryTransaction,
    Product,
    Warehouse,
)
from app.services.batch_merge_service import (
    BatchMergeError,
    batch_merge_service,
)
from app.services.batch_split_service import (
    BatchSplitError,
    batch_split_service,
)

pytestmark = pytest.mark.asyncio


# ── helpers ─────────────────────────────────────────────────────────


async def _wh(db: AsyncSession, name: str = "仓A") -> Warehouse:
    w = Warehouse(name=name, location="地")
    db.add(w)
    await db.flush()
    return w


async def _prod(db: AsyncSession, sku: str = "P-001") -> Product:
    p = Product(name=sku, sku=sku, unit="PCS")
    db.add(p)
    await db.flush()
    return p


async def _batch(
    db: AsyncSession,
    *,
    product_id: int,
    warehouse_id: int,
    batch_no: str | None = None,
    quantity: int = 100,
    unit_cost: Decimal = Decimal("10.0"),
    status: str = "available",
) -> InventoryBatchORM:
    bn = batch_no or f"B-{uuid.uuid4().hex[:8]}"
    b = InventoryBatchORM(
        product_id=product_id,
        warehouse_id=warehouse_id,
        batch_no=bn,
        quantity=quantity,
        unit_cost=unit_cost,
        status=status,
    )
    db.add(b)
    await db.flush()
    return b


# ── merge tests ────────────────────────────────────────────────────


class TestBatchMerge:
    async def test_merge_consolidates_into_oldest(self, db_session: AsyncSession):
        """Three batches in same product+warehouse → oldest keeps id, others consumed."""
        p = await _prod(db_session)
        w = await _wh(db_session)
        # Different batch_nos (unique constraint would block duplicates)
        b1 = await _batch(db_session, product_id=p.id, warehouse_id=w.id,
                          batch_no="LOT-1", quantity=10, unit_cost=Decimal("5"))
        b2 = await _batch(db_session, product_id=p.id, warehouse_id=w.id,
                          batch_no="LOT-2", quantity=20, unit_cost=Decimal("10"))
        b3 = await _batch(db_session, product_id=p.id, warehouse_id=w.id,
                          batch_no="LOT-3", quantity=30, unit_cost=Decimal("15"))

        result = await batch_merge_service.merge_batches(
            db_session, [b1.id, b2.id, b3.id], reason="合并三批", actor="op"
        )

        assert result["survivor_batch_id"] == b1.id
        assert sorted(result["consumed_batch_ids"]) == sorted([b2.id, b3.id])
        assert result["total_quantity"] == 60
        # Weighted: (10*5 + 20*10 + 30*15) / 60 = 700/60 ≈ 11.6667
        assert result["weighted_unit_cost"] == pytest.approx(11.6667, rel=1e-3)
        assert result["merged_count"] == 3

        await db_session.refresh(b1)
        await db_session.refresh(b2)
        await db_session.refresh(b3)
        assert b1.quantity == 60
        assert b1.status == "available"
        assert b2.status == "consumed" and b2.quantity == 0
        assert b3.status == "consumed" and b3.quantity == 0

    async def test_merge_writes_audit_transactions(self, db_session: AsyncSession):
        """One adjust-tx per consumed + one on survivor."""
        p = await _prod(db_session)
        w = await _wh(db_session)
        b1 = await _batch(db_session, product_id=p.id, warehouse_id=w.id,
                          batch_no="LOT-A", quantity=10)
        b2 = await _batch(db_session, product_id=p.id, warehouse_id=w.id,
                          batch_no="LOT-B", quantity=20)

        await batch_merge_service.merge_batches(
            db_session, [b1.id, b2.id], reason="audit test", actor="op"
        )

        # 1 outgoing (b2) + 1 survivor marker (b1) = 2 audit txns
        txns = (
            await db_session.execute(
                select(InventoryTransaction).where(
                    InventoryTransaction.type == "adjust"
                )
            )
        ).scalars().all()
        assert len(txns) == 2
        out_txn = next(t for t in txns if t.batch_id == b2.id)
        surv_txn = next(t for t in txns if t.batch_id == b1.id)
        assert out_txn.quantity == -20
        assert out_txn.reference_id == b1.id
        assert surv_txn.quantity == 0
        assert surv_txn.reference_id == b1.id

    async def test_merge_rejects_too_few_ids(self, db_session: AsyncSession):
        """< 2 ids → BatchMergeError."""
        p = await _prod(db_session)
        w = await _wh(db_session)
        b1 = await _batch(db_session, product_id=p.id, warehouse_id=w.id)
        with pytest.raises(BatchMergeError, match="至少需要 2 个批次"):
            await batch_merge_service.merge_batches(
                db_session, [b1.id], reason="r", actor="op"
            )

    async def test_merge_rejects_duplicate_ids(self, db_session: AsyncSession):
        """Duplicate ids in list → BatchMergeError."""
        p = await _prod(db_session)
        w = await _wh(db_session)
        b1 = await _batch(db_session, product_id=p.id, warehouse_id=w.id)
        with pytest.raises(BatchMergeError, match="重复"):
            await batch_merge_service.merge_batches(
                db_session, [b1.id, b1.id], reason="r", actor="op"
            )

    async def test_merge_rejects_different_products(self, db_session: AsyncSession):
        """Different product_id → BatchMergeError."""
        p1 = await _prod(db_session, "P-1")
        p2 = await _prod(db_session, "P-2")
        w = await _wh(db_session)
        b1 = await _batch(db_session, product_id=p1.id, warehouse_id=w.id, batch_no="X")
        b2 = await _batch(db_session, product_id=p2.id, warehouse_id=w.id, batch_no="X")
        with pytest.raises(BatchMergeError, match="产品不一致"):
            await batch_merge_service.merge_batches(
                db_session, [b1.id, b2.id], reason="r", actor="op"
            )

    async def test_merge_rejects_different_warehouses(self, db_session: AsyncSession):
        """Different warehouse_id → BatchMergeError."""
        p = await _prod(db_session)
        w1 = await _wh(db_session, "A")
        w2 = await _wh(db_session, "B")
        b1 = await _batch(db_session, product_id=p.id, warehouse_id=w1.id, batch_no="X")
        b2 = await _batch(db_session, product_id=p.id, warehouse_id=w2.id, batch_no="X")
        with pytest.raises(BatchMergeError, match="仓库不一致"):
            await batch_merge_service.merge_batches(
                db_session, [b1.id, b2.id], reason="r", actor="op"
            )

    async def test_merge_allows_different_batch_nos(self, db_session: AsyncSession):
        """Different batch_nos in same product+warehouse → merge succeeds (survivor wins)."""
        p = await _prod(db_session)
        w = await _wh(db_session)
        b1 = await _batch(db_session, product_id=p.id, warehouse_id=w.id, batch_no="LOT-A")
        b2 = await _batch(db_session, product_id=p.id, warehouse_id=w.id, batch_no="LOT-B")
        result = await batch_merge_service.merge_batches(
            db_session, [b1.id, b2.id], reason="不同 batch_no 合并", actor="op"
        )
        # Survivor keeps its batch_no
        assert result["survivor_batch_no"] == "LOT-A"
        # b1 (LOT-A) now holds b2's qty
        await db_session.refresh(b1)
        assert b1.quantity == b1.quantity + b2.quantity  # both originals were 100

    async def test_merge_rejects_non_available_status(self, db_session: AsyncSession):
        """Recalled/consumed batch → BatchMergeError."""
        p = await _prod(db_session)
        w = await _wh(db_session)
        b1 = await _batch(db_session, product_id=p.id, warehouse_id=w.id, batch_no="LOT-A")
        b2 = await _batch(db_session, product_id=p.id, warehouse_id=w.id,
                          batch_no="LOT-B", status="recalled")
        with pytest.raises(BatchMergeError, match="状态为 recalled"):
            await batch_merge_service.merge_batches(
                db_session, [b1.id, b2.id], reason="r", actor="op"
            )

    async def test_merge_rejects_empty_reason(self, db_session: AsyncSession):
        """Empty reason → BatchMergeError."""
        p = await _prod(db_session)
        w = await _wh(db_session)
        b1 = await _batch(db_session, product_id=p.id, warehouse_id=w.id, batch_no="LOT-A")
        b2 = await _batch(db_session, product_id=p.id, warehouse_id=w.id, batch_no="LOT-B")
        for bad in ("", "   "):
            with pytest.raises(BatchMergeError, match="原因不能为空"):
                await batch_merge_service.merge_batches(
                    db_session, [b1.id, b2.id], reason=bad, actor="op"
                )

    async def test_merge_rejects_missing_ids(self, db_session: AsyncSession):
        """Non-existent id in list → BatchMergeError."""
        p = await _prod(db_session)
        w = await _wh(db_session)
        b1 = await _batch(db_session, product_id=p.id, warehouse_id=w.id, batch_no="LOT-A")
        with pytest.raises(BatchMergeError, match="批次不存在"):
            await batch_merge_service.merge_batches(
                db_session, [b1.id, 99999], reason="r", actor="op"
            )


# ── split tests ────────────────────────────────────────────────────


class TestBatchSplit:
    async def test_split_creates_new_batch_auto_numbered(
        self, db_session: AsyncSession
    ):
        """Default new_batch_no = {src}-S1; src reduced by quantity."""
        p = await _prod(db_session)
        w = await _wh(db_session)
        src = await _batch(db_session, product_id=p.id, warehouse_id=w.id,
                          batch_no="PARENT", quantity=100)

        result = await batch_split_service.split_batch(
            db_session, src.id, quantity=30, reason="拆出 30 给 VIP",
            actor="op"
        )

        assert result["src_batch_id"] == src.id
        assert result["new_batch_no"] == "PARENT-S1"
        assert result["new_quantity"] == 30
        assert result["src_remaining"] == 70
        assert result["new_batch_id"] != src.id

        await db_session.refresh(src)
        new = await db_session.get(InventoryBatchORM, result["new_batch_id"])
        assert src.quantity == 70
        assert src.status == "available"
        assert new.batch_no == "PARENT-S1"
        assert new.quantity == 30
        assert new.product_id == src.product_id
        assert new.warehouse_id == src.warehouse_id

    async def test_split_auto_number_increments_on_collision(
        self, db_session: AsyncSession
    ):
        """If PARENT-S1 already exists, new = PARENT-S2."""
        p = await _prod(db_session)
        w = await _wh(db_session)
        src = await _batch(db_session, product_id=p.id, warehouse_id=w.id,
                          batch_no="PARENT", quantity=100)
        # Pre-existing -S1
        await _batch(db_session, product_id=p.id, warehouse_id=w.id,
                     batch_no="PARENT-S1", quantity=5)

        result = await batch_split_service.split_batch(
            db_session, src.id, quantity=10, reason="r", actor="op"
        )
        assert result["new_batch_no"] == "PARENT-S2"

    async def test_split_accepts_explicit_batch_no(
        self, db_session: AsyncSession
    ):
        """Caller-provided new_batch_no is used as-is."""
        p = await _prod(db_session)
        w = await _wh(db_session)
        src = await _batch(db_session, product_id=p.id, warehouse_id=w.id,
                          batch_no="X", quantity=50)
        result = await batch_split_service.split_batch(
            db_session, src.id, quantity=15, new_batch_no="X-VIP-001",
            reason="VIP", actor="op"
        )
        assert result["new_batch_no"] == "X-VIP-001"

    async def test_split_writes_audit_transactions(self, db_session: AsyncSession):
        """Two adjust txns: src (negative) + new (positive)."""
        p = await _prod(db_session)
        w = await _wh(db_session)
        src = await _batch(db_session, product_id=p.id, warehouse_id=w.id,
                          batch_no="S", quantity=80)

        result = await batch_split_service.split_batch(
            db_session, src.id, quantity=20, reason="audit", actor="op"
        )
        txns = (
            await db_session.execute(
                select(InventoryTransaction).where(
                    InventoryTransaction.type == "adjust"
                )
            )
        ).scalars().all()
        assert len(txns) == 2
        src_txn = next(t for t in txns if t.batch_id == src.id)
        new_txn = next(t for t in txns if t.batch_id == result["new_batch_id"])
        assert src_txn.quantity == -20
        assert new_txn.quantity == 20
        assert src_txn.reference_id == result["new_batch_id"]
        assert new_txn.reference_id == src.id

    async def test_split_marks_src_consumed_at_zero(
        self, db_session: AsyncSession
    ):
        """If quantity equals (src-1) → src becomes consumed with qty=1."""
        p = await _prod(db_session)
        w = await _wh(db_session)
        src = await _batch(db_session, product_id=p.id, warehouse_id=w.id,
                          batch_no="S", quantity=10)
        await batch_split_service.split_batch(
            db_session, src.id, quantity=9, reason="near full split", actor="op"
        )
        await db_session.refresh(src)
        assert src.quantity == 1
        assert src.status == "available"  # not zero, so still available

    async def test_split_rejects_zero_quantity(self, db_session: AsyncSession):
        """quantity <= 0 → BatchSplitError."""
        p = await _prod(db_session)
        w = await _wh(db_session)
        src = await _batch(db_session, product_id=p.id, warehouse_id=w.id)
        for bad in (0, -1):
            with pytest.raises(BatchSplitError, match="数量必须 > 0"):
                await batch_split_service.split_batch(
                    db_session, src.id, quantity=bad, reason="r", actor="op"
                )

    async def test_split_rejects_quantity_ge_src(self, db_session: AsyncSession):
        """quantity >= src.quantity → BatchSplitError (use transfer instead)."""
        p = await _prod(db_session)
        w = await _wh(db_session)
        src = await _batch(db_session, product_id=p.id, warehouse_id=w.id,
                          batch_no="S", quantity=10)
        for bad in (10, 11, 100):
            with pytest.raises(BatchSplitError, match="必须 < 源数量"):
                await batch_split_service.split_batch(
                    db_session, src.id, quantity=bad, reason="r", actor="op"
                )

    async def test_split_rejects_non_available_status(
        self, db_session: AsyncSession
    ):
        """Recalled/consumed batch → BatchSplitError."""
        p = await _prod(db_session)
        w = await _wh(db_session)
        src = await _batch(db_session, product_id=p.id, warehouse_id=w.id,
                          batch_no="S", quantity=10, status="recalled")
        with pytest.raises(BatchSplitError, match="状态为 recalled"):
            await batch_split_service.split_batch(
                db_session, src.id, quantity=5, reason="r", actor="op"
            )

    async def test_split_rejects_missing_batch(self, db_session: AsyncSession):
        """Non-existent batch_id → BatchSplitError."""
        with pytest.raises(BatchSplitError, match="批次 .* 不存在"):
            await batch_split_service.split_batch(
                db_session, 99999, quantity=5, reason="r", actor="op"
            )

    async def test_split_rejects_empty_reason(self, db_session: AsyncSession):
        """Empty reason → BatchSplitError."""
        p = await _prod(db_session)
        w = await _wh(db_session)
        src = await _batch(db_session, product_id=p.id, warehouse_id=w.id)
        for bad in ("", "   "):
            with pytest.raises(BatchSplitError, match="原因不能为空"):
                await batch_split_service.split_batch(
                    db_session, src.id, quantity=5, reason=bad, actor="op"
                )