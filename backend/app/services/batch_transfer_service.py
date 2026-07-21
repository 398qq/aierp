"""Batch transfer service — Stage 18 P4 / Production Batch Management.

Move inventory from one warehouse to another while preserving batch lineage:
  - Decrement src batch quantity
  - Increment existing dst batch OR create new one (same batch_no)
  - Write paired stock_out + stock_in InventoryTransaction rows
    (both type='transfer', both carrying batch_id for traceability)

This is the "logical" transfer: the batch number stays the same, so all
traceability / recall / expiry queries continue to work across warehouses.
"""

from __future__ import annotations

import logging
from typing import Any

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.product import InventoryBatchORM, InventoryTransaction, Warehouse

logger = logging.getLogger(__name__)


class BatchTransferError(Exception):
    """Raised when a transfer cannot be completed."""


class BatchTransferService:
    """Move batch inventory between warehouses."""

    async def transfer_batch(
        self,
        db: AsyncSession,
        batch_id: int,
        *,
        dst_warehouse_id: int,
        quantity: int,
        reason: str,
        actor: str,
    ) -> dict[str, Any]:
        """Move ``quantity`` units from src batch to dst warehouse.

        Returns a transfer summary dict. Raises :class:`BatchTransferError`
        on validation failures.

        Args:
            batch_id: source batch id.
            dst_warehouse_id: destination warehouse id.
            quantity: how many units to move (must be > 0 and <= available).
            reason: audit-justified human-readable reason.
            actor: who initiated the transfer.

        Behavior:
          - src.quantity -= quantity (status='consumed' if 0)
          - find-or-create dst batch (same product_id + batch_no)
          - dst.quantity += quantity
          - write paired InventoryTransaction rows (type='transfer')
        """
        if quantity <= 0:
            raise BatchTransferError("调拨数量必须 > 0")
        if not reason or not reason.strip():
            raise BatchTransferError("调拨原因不能为空")

        src = await db.get(InventoryBatchORM, batch_id)
        if src is None:
            raise BatchTransferError(f"批次 {batch_id} 不存在")
        if src.status != "available":
            raise BatchTransferError(
                f"批次 {batch_id} 状态为 {src.status}，不可调拨"
            )

        available = src.quantity - src.locked_quantity
        if quantity > available:
            raise BatchTransferError(
                f"批次 {batch_id} 可用量 {available} 不足，需要 {quantity}"
            )

        if dst_warehouse_id == src.warehouse_id:
            raise BatchTransferError("目标仓库与源仓库相同")

        src_wh = await db.get(Warehouse, src.warehouse_id)
        dst_wh = await db.get(Warehouse, dst_warehouse_id)
        if dst_wh is None:
            raise BatchTransferError(f"目标仓库 {dst_warehouse_id} 不存在")

        # Find-or-create dst batch (same product + batch_no)
        dst_stmt = select(InventoryBatchORM).where(
            and_(
                InventoryBatchORM.product_id == src.product_id,
                InventoryBatchORM.warehouse_id == dst_warehouse_id,
                InventoryBatchORM.batch_no == src.batch_no,
            )
        )
        dst_batch = (await db.execute(dst_stmt)).scalar_one_or_none()
        created_new = dst_batch is None
        if created_new:
            dst_batch = InventoryBatchORM(
                product_id=src.product_id,
                warehouse_id=dst_warehouse_id,
                batch_no=src.batch_no,
                quantity=0,  # set below
                locked_quantity=0,
                unit_cost=src.unit_cost,
                received_date=src.received_date,
                expiry_date=src.expiry_date,
                manufacture_date=src.manufacture_date,
                supplier_id=src.supplier_id,
                status="available",
                rohs_compliant=src.rohs_compliant,
                msl_level=src.msl_level,
                certificate_url=src.certificate_url,
                notes=src.notes,
            )

        # 1) Update src / dst quantities
        src.quantity -= quantity
        if src.quantity == 0:
            src.status = "consumed"
        db.add(src)

        # mypy: after the if/else above, dst_batch is guaranteed non-None
        assert dst_batch is not None
        dst_batch.quantity = (dst_batch.quantity or 0) + quantity
        db.add(dst_batch)

        # mypy: src_wh / dst_wh are guaranteed non-None (FK-validated)
        assert src_wh is not None
        assert dst_wh is not None

        # Flush to populate dst_batch.id for the transaction rows
        await db.flush()

        # 2) Paired transfer transactions (use warehouse names for readability)
        src_txn = InventoryTransaction(
            product_id=src.product_id,
            warehouse_id=src.warehouse_id,
            type="transfer",
            quantity=-quantity,
            reference_type="transfer",
            reference_id=None,
            batch_id=src.id,
            notes=f"调拨到仓库 {dst_wh.name}: {reason}",
        )
        dst_txn = InventoryTransaction(
            product_id=dst_batch.product_id,
            warehouse_id=dst_batch.warehouse_id,
            type="transfer",
            quantity=quantity,
            reference_type="transfer",
            reference_id=None,
            batch_id=dst_batch.id,
            notes=f"从仓库 {src_wh.name} 调拨入: {reason}",
        )
        db.add(src_txn)
        db.add(dst_txn)
        await db.flush()

        logger.warning(
            "Batch transfer: src_batch=%s dst_batch=%s qty=%s actor=%s reason=%s",
            src.id,
            dst_batch.id,
            quantity,
            actor,
            reason,
        )

        return {
            "src_batch_id": src.id,
            "src_warehouse_id": src.warehouse_id,
            "src_remaining": src.quantity,
            "dst_batch_id": dst_batch.id,
            "dst_warehouse_id": dst_batch.warehouse_id,
            "dst_quantity": dst_batch.quantity,
            "quantity_transferred": quantity,
            "new_dst_batch_created": created_new,
            "reason": reason,
            "actor": actor,
            "src_txn_id": src_txn.id,
            "dst_txn_id": dst_txn.id,
        }


# Module-level singleton.
batch_transfer_service = BatchTransferService()