"""Batch split service — Stage 18 P5 / Production Batch Management.

Split one batch into two. The original is reduced by ``quantity``; a new
batch is created with the same product/warehouse/quality attributes but a
new batch_no. All traceability references to the original remain valid;
the new batch is brand-new and starts with zero downstream history.

Use cases:
  - Different packaging requirements (e.g., re-pack bulk into retail packs)
  - Quality grade separation (e.g., separate pass/fail portions)
  - Customer-specific reservation (split off a portion for a VIP)
"""

from __future__ import annotations

import logging
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.product import InventoryBatchORM, InventoryTransaction

logger = logging.getLogger(__name__)


class BatchSplitError(Exception):
    """Raised when a split cannot be completed."""


class BatchSplitService:
    """Split one batch into two."""

    async def split_batch(
        self,
        db: AsyncSession,
        batch_id: int,
        *,
        quantity: int,
        new_batch_no: str | None = None,
        reason: str,
        actor: str,
    ) -> dict[str, Any]:
        """Split ``quantity`` units from src batch into a new batch.

        Args:
            batch_id: source batch id.
            quantity: how many units to move into the new batch (must be
                > 0 and < src.quantity; equal-to would be a full transfer,
                not a split).
            new_batch_no: optional batch_no for the new batch. If None,
                auto-generated as ``{src.batch_no}-S1`` (or -S2, -S3... if
                that already exists).
            reason: audit-justified human-readable reason.
            actor: who initiated the split.

        Returns:
            Dict with original_batch_id, new_batch_id, quantities, etc.
        """
        if quantity <= 0:
            raise BatchSplitError("拆分数量必须 > 0")
        if not reason or not reason.strip():
            raise BatchSplitError("拆分原因不能为空")

        src = await db.get(InventoryBatchORM, batch_id)
        if src is None:
            raise BatchSplitError(f"批次 {batch_id} 不存在")
        if src.status != "available":
            raise BatchSplitError(
                f"批次 {batch_id} 状态为 {src.status}，不可拆分"
            )
        if quantity >= src.quantity:
            raise BatchSplitError(
                f"拆分数量 {quantity} 必须 < 源数量 {src.quantity}"
            )

        # Auto-generate new_batch_no if not provided
        if not new_batch_no:
            n = 1
            while n <= 999:
                candidate = f"{src.batch_no}-S{n}"
                exists = (
                    await db.execute(
                        select(InventoryBatchORM.id).where(
                            InventoryBatchORM.product_id == src.product_id,
                            InventoryBatchORM.warehouse_id == src.warehouse_id,
                            InventoryBatchORM.batch_no == candidate,
                        )
                    )
                ).scalar_one_or_none()
                if exists is None:
                    new_batch_no = candidate
                    break
                n += 1
            else:
                raise BatchSplitError("自动生成 batch_no 失败：超过 999 次尝试")

        # 1) Decrement source
        src.quantity -= quantity
        if src.quantity == 0:
            src.status = "consumed"
        db.add(src)

        # 2) Create new batch
        new_batch = InventoryBatchORM(
            product_id=src.product_id,
            warehouse_id=src.warehouse_id,
            batch_no=new_batch_no,
            quantity=quantity,
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
        db.add(new_batch)
        await db.flush()  # populate new_batch.id

        # 3) Audit transactions (type='adjust' for both sides)
        src_audit = InventoryTransaction(
            product_id=src.product_id,
            warehouse_id=src.warehouse_id,
            type="adjust",
            quantity=-quantity,
            reference_type="batch_split",
            reference_id=new_batch.id,
            batch_id=src.id,
            notes=(
                f"拆分 {quantity} 到新 batch #{new_batch.id} "
                f"({new_batch.batch_no}): {reason}"
            ),
        )
        new_audit = InventoryTransaction(
            product_id=new_batch.product_id,
            warehouse_id=new_batch.warehouse_id,
            type="adjust",
            quantity=quantity,
            reference_type="batch_split",
            reference_id=src.id,
            batch_id=new_batch.id,
            notes=f"从 batch #{src.id} ({src.batch_no}) 拆分: {reason}",
        )
        db.add(src_audit)
        db.add(new_audit)
        await db.flush()

        logger.warning(
            "Batch split: src=%s new=%s qty=%s actor=%s reason=%s",
            src.id, new_batch.id, quantity, actor, reason,
        )

        return {
            "src_batch_id": src.id,
            "src_warehouse_id": src.warehouse_id,
            "src_remaining": src.quantity,
            "new_batch_id": new_batch.id,
            "new_batch_no": new_batch.batch_no,
            "new_quantity": new_batch.quantity,
            "new_unit_cost": float(new_batch.unit_cost or 0),
            "quantity_split": quantity,
            "reason": reason,
            "actor": actor,
            "src_audit_txn_id": src_audit.id,
            "new_audit_txn_id": new_audit.id,
        }


# Module-level singleton.
batch_split_service = BatchSplitService()