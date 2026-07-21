"""Batch recall service — Stage 18 / Production Batch Management.

Marking a batch as "recalled":
  1. Status → recalled (audit-visible).
  2. Freeze remaining inventory (locked_quantity = quantity).
  3. Surface affected customers / deliveries (reuse BatchTraceabilityService).
  4. Return impact summary so the API caller can trigger notifications.

Notifications are NOT sent automatically by this service — the API layer
coordinates with the existing notification_service to avoid coupling batch
state with delivery channels.
"""

from __future__ import annotations

import logging
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.product import InventoryBatchORM
from app.services.batch_traceability_service import batch_traceability_service

logger = logging.getLogger(__name__)


RECALL_STATUS = "recalled"


class BatchRecallError(Exception):
    """Raised when a recall operation cannot be completed."""


class BatchRecallService:
    """Mark batches as recalled and report downstream impact."""

    async def get_impact(
        self, db: AsyncSession, batch_id: int
    ) -> dict[str, Any] | None:
        """Return customers + deliveries affected by this batch.

        Returns ``None`` if the batch does not exist. Used both as a
        preview-before-recall and as the post-recall report payload.
        """
        trace = await batch_traceability_service.get_traceability(db, batch_id)
        if trace is None:
            return None
        ds = trace["downstream"]
        return {
            "batch": trace["batch"],
            "affected_customers": ds["customers"],
            "deliveries": ds["deliveries"],
            "customer_count": ds["customer_count"],
            "delivery_count": ds["delivery_count"],
            "total_quantity_consumed": ds["total_consumed"],
            "frozen_remaining": trace["batch"]["quantity"],
        }

    async def recall_batch(
        self,
        db: AsyncSession,
        batch_id: int,
        *,
        reason: str,
        actor: str,
    ) -> dict[str, Any]:
        """Mark batch as recalled + freeze remaining inventory.

        Returns the impact payload (same shape as ``get_impact``).
        Raises :class:`BatchRecallError` on validation failures.
        """
        if not reason or not reason.strip():
            raise BatchRecallError("召回原因不能为空")

        batch = await db.get(InventoryBatchORM, batch_id)
        if batch is None:
            raise BatchRecallError(f"批次 {batch_id} 不存在")

        if batch.status == RECALL_STATUS:
            raise BatchRecallError(f"批次 {batch_id} 已处于 recalled 状态")

        previous_status = batch.status
        remaining_qty = batch.quantity

        # 1) status change
        batch.status = RECALL_STATUS
        # 2) freeze remaining inventory (locked = remaining qty)
        # Note: locked_quantity is normally used for "soft reservations" tied
        # to open sales orders. Recall is a hard freeze — we move all
        # remaining stock into locked so future allocations must skip it.
        batch.locked_quantity = max(batch.locked_quantity, remaining_qty)
        db.add(batch)
        await db.flush()

        logger.warning(
            "Batch recalled: id=%s batch_no=%s previous_status=%s "
            "remaining=%s actor=%s reason=%s",
            batch.id,
            batch.batch_no,
            previous_status,
            remaining_qty,
            actor,
            reason,
        )

        # 3) surface downstream impact (reuses traceability work)
        impact = await self.get_impact(db, batch_id)
        assert impact is not None  # we just fetched the batch above
        impact["recall"] = {
            "previous_status": previous_status,
            "reason": reason,
            "actor": actor,
        }
        return impact


# Module-level singleton (matches batch_traceability_service style).
batch_recall_service = BatchRecallService()