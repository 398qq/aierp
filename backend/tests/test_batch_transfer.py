"""Batch transfer service tests — Stage 18 P4.

Verifies the inter-warehouse batch transfer:
  - Decrement src / increment-or-create dst
  - Write paired transfer transactions
  - Validation: qty > 0, non-empty reason, dst != src, dst exists,
    sufficient available (quantity - locked_quantity)
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
from app.services.batch_transfer_service import (
    BatchTransferError,
    batch_transfer_service,
)

pytestmark = pytest.mark.asyncio


# ── helpers ─────────────────────────────────────────────────────────


async def _make_warehouse(
    db: AsyncSession, name: str = "源仓", location: str = "深圳"
) -> Warehouse:
    wh = Warehouse(name=name, location=location)
    db.add(wh)
    await db.flush()
    return wh


async def _make_product(db: AsyncSession) -> Product:
    p = Product(name="调拨测试产品", sku="TRANSFER-001", unit="PCS")
    db.add(p)
    await db.flush()
    return p


async def _make_batch(
    db: AsyncSession,
    *,
    product_id: int,
    warehouse_id: int,
    quantity: int = 100,
    locked_quantity: int = 0,
    status: str = "available",
) -> InventoryBatchORM:
    batch = InventoryBatchORM(
        product_id=product_id,
        warehouse_id=warehouse_id,
        batch_no=f"T-{uuid.uuid4().hex[:8]}",
        quantity=quantity,
        locked_quantity=locked_quantity,
        unit_cost=Decimal("10.0"),
        status=status,
    )
    db.add(batch)
    await db.flush()
    return batch


async def _get_transactions(
    db: AsyncSession, *, batch_id: int, type_: str = "transfer"
) -> list[InventoryTransaction]:
    stmt = (
        select(InventoryTransaction)
        .where(InventoryTransaction.batch_id == batch_id)
        .where(InventoryTransaction.type == type_)
        .order_by(InventoryTransaction.id.asc())
    )
    return list((await db.execute(stmt)).scalars().all())


# ── tests ───────────────────────────────────────────────────────────


class TestBatchTransfer:
    async def test_transfer_creates_new_dst_batch(self, db_session: AsyncSession):
        """Transfer to a warehouse with no existing batch → new dst row created."""
        product = await _make_product(db_session)
        src_wh = await _make_warehouse(db_session, "深圳仓", "深圳")
        dst_wh = await _make_warehouse(db_session, "上海仓", "上海")
        src = await _make_batch(
            db_session, product_id=product.id, warehouse_id=src_wh.id, quantity=100
        )

        result = await batch_transfer_service.transfer_batch(
            db_session, src.id,
            dst_warehouse_id=dst_wh.id,
            quantity=30, reason="调拨到上海仓", actor="warehouse-mgr",
        )

        assert result["src_remaining"] == 70
        assert result["dst_quantity"] == 30
        assert result["new_dst_batch_created"] is True
        assert result["quantity_transferred"] == 30
        assert result["src_warehouse_id"] == src_wh.id
        assert result["dst_warehouse_id"] == dst_wh.id

        # Verify src row
        await db_session.refresh(src)
        assert src.quantity == 70
        assert src.status == "available"

        # Verify dst row was created
        assert result["dst_batch_id"] != src.id
        dst_batch = await db_session.get(InventoryBatchORM, result["dst_batch_id"])
        assert dst_batch is not None
        assert dst_batch.batch_no == src.batch_no
        assert dst_batch.warehouse_id == dst_wh.id
        assert dst_batch.quantity == 30
        assert dst_batch.unit_cost == src.unit_cost

    async def test_transfer_appends_to_existing_dst_batch(
        self, db_session: AsyncSession
    ):
        """If dst already has a batch with same batch_no, quantity is added."""
        product = await _make_product(db_session)
        src_wh = await _make_warehouse(db_session, "深圳仓", "深圳")
        dst_wh = await _make_warehouse(db_session, "上海仓", "上海")
        src = await _make_batch(
            db_session, product_id=product.id, warehouse_id=src_wh.id, quantity=50
        )
        # Pre-existing dst batch with same batch_no, qty 20
        existing_dst = await _make_batch(
            db_session, product_id=product.id, warehouse_id=dst_wh.id,
            quantity=20, status="available",
        )
        # Rename dst batch to have same batch_no as src
        existing_dst.batch_no = src.batch_no
        await db_session.flush()

        result = await batch_transfer_service.transfer_batch(
            db_session, src.id,
            dst_warehouse_id=dst_wh.id,
            quantity=10, reason="追加库存", actor="m",
        )

        assert result["new_dst_batch_created"] is False
        assert result["dst_batch_id"] == existing_dst.id
        assert result["dst_quantity"] == 30  # 20 + 10

    async def test_transfer_writes_paired_transactions(
        self, db_session: AsyncSession
    ):
        """One stock_out at src, one stock_in at dst, both type=transfer, same batch_id."""
        product = await _make_product(db_session)
        src_wh = await _make_warehouse(db_session, "A仓", "A地")
        dst_wh = await _make_warehouse(db_session, "B仓", "B地")
        src = await _make_batch(
            db_session, product_id=product.id, warehouse_id=src_wh.id, quantity=80
        )

        result = await batch_transfer_service.transfer_batch(
            db_session, src.id,
            dst_warehouse_id=dst_wh.id,
            quantity=25, reason="test", actor="tester",
        )

        # src transaction
        src_txns = await _get_transactions(
            db_session, batch_id=src.id, type_="transfer"
        )
        assert len(src_txns) == 1
        assert src_txns[0].warehouse_id == src_wh.id
        assert src_txns[0].quantity == -25  # negative = out

        # dst transaction (pointing to the newly created dst batch)
        dst_txns = await _get_transactions(
            db_session, batch_id=result["dst_batch_id"], type_="transfer"
        )
        assert len(dst_txns) == 1
        assert dst_txns[0].warehouse_id == dst_wh.id
        assert dst_txns[0].quantity == 25  # positive = in

        # Notes cross-reference
        assert "B仓" in src_txns[0].notes
        assert "A仓" in dst_txns[0].notes

    async def test_transfer_marks_src_consumed_when_qty_zero(
        self, db_session: AsyncSession
    ):
        """Transferring all available qty → src.status='consumed'."""
        product = await _make_product(db_session)
        src_wh = await _make_warehouse(db_session, "A仓", "A地")
        dst_wh = await _make_warehouse(db_session, "B仓", "B地")
        src = await _make_batch(
            db_session, product_id=product.id, warehouse_id=src_wh.id, quantity=10
        )

        await batch_transfer_service.transfer_batch(
            db_session, src.id,
            dst_warehouse_id=dst_wh.id,
            quantity=10, reason="全调", actor="m",
        )

        await db_session.refresh(src)
        assert src.quantity == 0
        assert src.status == "consumed"

    async def test_transfer_rejects_zero_or_negative_qty(
        self, db_session: AsyncSession
    ):
        """quantity <= 0 → BatchTransferError."""
        product = await _make_product(db_session)
        src_wh = await _make_warehouse(db_session, "A仓", "A地")
        dst_wh = await _make_warehouse(db_session, "B仓", "B地")
        src = await _make_batch(
            db_session, product_id=product.id, warehouse_id=src_wh.id, quantity=10
        )

        for bad_qty in (0, -1, -100):
            with pytest.raises(BatchTransferError, match="数量必须 > 0"):
                await batch_transfer_service.transfer_batch(
                    db_session, src.id,
                    dst_warehouse_id=dst_wh.id,
                    quantity=bad_qty, reason="r", actor="m",
                )

    async def test_transfer_rejects_empty_reason(self, db_session: AsyncSession):
        """Empty / whitespace reason → BatchTransferError."""
        product = await _make_product(db_session)
        src_wh = await _make_warehouse(db_session, "A仓", "A地")
        dst_wh = await _make_warehouse(db_session, "B仓", "B地")
        src = await _make_batch(
            db_session, product_id=product.id, warehouse_id=src_wh.id, quantity=10
        )
        for bad in ("", "   ", "\t\n"):
            with pytest.raises(BatchTransferError, match="原因不能为空"):
                await batch_transfer_service.transfer_batch(
                    db_session, src.id,
                    dst_warehouse_id=dst_wh.id,
                    quantity=5, reason=bad, actor="m",
                )

    async def test_transfer_rejects_same_warehouse(self, db_session: AsyncSession):
        """dst_warehouse_id == src.warehouse_id → BatchTransferError."""
        product = await _make_product(db_session)
        wh = await _make_warehouse(db_session, "A仓", "A地")
        src = await _make_batch(
            db_session, product_id=product.id, warehouse_id=wh.id, quantity=10
        )
        with pytest.raises(BatchTransferError, match="源仓库相同"):
            await batch_transfer_service.transfer_batch(
                db_session, src.id,
                dst_warehouse_id=wh.id, quantity=5, reason="r", actor="m",
            )

    async def test_transfer_rejects_unknown_dst_warehouse(
        self, db_session: AsyncSession
    ):
        """dst_warehouse_id not in warehouses → BatchTransferError."""
        product = await _make_product(db_session)
        wh = await _make_warehouse(db_session, "A仓", "A地")
        src = await _make_batch(
            db_session, product_id=product.id, warehouse_id=wh.id, quantity=10
        )
        with pytest.raises(BatchTransferError, match="目标仓库 .* 不存在"):
            await batch_transfer_service.transfer_batch(
                db_session, src.id,
                dst_warehouse_id=99999, quantity=5, reason="r", actor="m",
            )

    async def test_transfer_rejects_unknown_batch(self, db_session: AsyncSession):
        """batch_id not in inventory_batches → BatchTransferError."""
        wh = await _make_warehouse(db_session, "A仓", "A地")
        with pytest.raises(BatchTransferError, match="批次 .* 不存在"):
            await batch_transfer_service.transfer_batch(
                db_session, 99999,
                dst_warehouse_id=wh.id, quantity=5, reason="r", actor="m",
            )

    async def test_transfer_rejects_insufficient_available(
        self, db_session: AsyncSession
    ):
        """quantity > quantity - locked_quantity → BatchTransferError."""
        product = await _make_product(db_session)
        src_wh = await _make_warehouse(db_session, "A仓", "A地")
        dst_wh = await _make_warehouse(db_session, "B仓", "B地")
        src = await _make_batch(
            db_session, product_id=product.id, warehouse_id=src_wh.id,
            quantity=10, locked_quantity=7,  # available = 3
        )
        with pytest.raises(BatchTransferError, match="可用量 .* 不足"):
            await batch_transfer_service.transfer_batch(
                db_session, src.id,
                dst_warehouse_id=dst_wh.id, quantity=5, reason="r", actor="m",
            )
        # available exactly = 3 should pass
        result = await batch_transfer_service.transfer_batch(
            db_session, src.id,
            dst_warehouse_id=dst_wh.id, quantity=3, reason="r", actor="m",
        )
        assert result["quantity_transferred"] == 3

    async def test_transfer_rejects_non_available_status(
        self, db_session: AsyncSession
    ):
        """status in (consumed, recalled, …) → BatchTransferError."""
        product = await _make_product(db_session)
        src_wh = await _make_warehouse(db_session, "A仓", "A地")
        dst_wh = await _make_warehouse(db_session, "B仓", "B地")
        src = await _make_batch(
            db_session, product_id=product.id, warehouse_id=src_wh.id,
            quantity=10, status="recalled",
        )
        with pytest.raises(BatchTransferError, match="状态为 recalled"):
            await batch_transfer_service.transfer_batch(
                db_session, src.id,
                dst_warehouse_id=dst_wh.id, quantity=5, reason="r", actor="m",
            )