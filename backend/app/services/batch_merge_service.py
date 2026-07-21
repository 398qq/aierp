"""Batch merge service — Stage 18 P5 / Production Batch Management.

Consolidate multiple inventory batches (same product + warehouse) into a
single survivor batch. The oldest batch (lowest id) becomes the survivor;
others are marked status=consumed with quantity=0. All traceability
references to consumed batches remain valid (they keep their ids), and
audit transactions (type=adjust) record the merge.

Note: batches may have different batch_nos (the unique constraint is on
``(product_id, warehouse_id, batch_no)``, so we naturally enforce no
overlap). Survivor's batch_no wins; consumed batches' batch_nos are
preserved in their (now zeroed) rows for historical reference.
"""

from __future__ import annotations

import logging
from datetime import datetime
from decimal import Decimal
from typing import Any, cast

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.product import InventoryBatchORM, InventoryTransaction

logger = logging.getLogger(__name__)


class BatchMergeError(Exception):
    """Raised when a merge cannot be completed."""


class BatchMergeService:
    """Consolidate multiple batches into one."""

    async def merge_batches(
        self,
        db: AsyncSession,
        batch_ids: list[int],
        *,
        reason: str,
        actor: str,
    ) -> dict[str, Any]:
        """Merge ``batch_ids`` into a single survivor batch.

        Rules:
          - At least 2 batches required
          - All must be status='available' and quantity > 0
          - All must share the same product_id and warehouse_id
            (batch_nos may differ — unique constraint prevents same-key
            batches from coexisting anyway)
          - Survivor = lowest id (oldest). Others become status=consumed,
            quantity=0
          - Survivor's quantity = sum of all; unit_cost = weighted average
            by quantity; expiry_date = earliest (most conservative)
          - Audit: one ``adjust`` transaction per consumed batch + one
            ``adjust`` transaction on the survivor (audit marker)
        """
        if not batch_ids or len(batch_ids) < 2:
            raise BatchMergeError("至少需要 2 个批次才能合并")
        if not reason or not reason.strip():
            raise BatchMergeError("合并原因不能为空")
        if len(set(batch_ids)) != len(batch_ids):
            raise BatchMergeError("批次 id 列表中有重复")

        # Fetch all batches in one query
        stmt = select(InventoryBatchORM).where(
            InventoryBatchORM.id.in_(batch_ids)
        )
        batches = list((await db.execute(stmt)).scalars().all())
        if len(batches) != len(batch_ids):
            found_ids = {b.id for b in batches}
            missing = set(batch_ids) - found_ids
            raise BatchMergeError(f"批次不存在: {sorted(missing)}")

        # Cross-batch consistency checks (batch_nos may differ — see docstring)
        product_ids = {b.product_id for b in batches}
        warehouse_ids = {b.warehouse_id for b in batches}
        if len(product_ids) > 1:
            raise BatchMergeError(f"批次产品不一致: {product_ids}")
        if len(warehouse_ids) > 1:
            raise BatchMergeError(f"批次仓库不一致: {warehouse_ids}")
        for b in batches:
            if b.status != "available":
                raise BatchMergeError(
                    f"批次 {b.id} 状态为 {b.status}，不可合并"
                )
            if b.quantity <= 0:
                raise BatchMergeError(f"批次 {b.id} 数量为 0")

        # Pick survivor: lowest id (oldest)
        batches.sort(key=lambda b: b.id)
        survivor = batches[0]
        consumed = batches[1:]

        # Snapshot original qtys BEFORE mutating (needed for audit transactions)
        original_qtys: dict[int, int] = {b.id: int(b.quantity) for b in batches}

        # Compute aggregates
        total_qty = sum(original_qtys.values())
        total_value = sum(
            Decimal(str(original_qtys[b.id])) * Decimal(str(b.unit_cost or 0))
            for b in batches
        )
        weighted_cost = (
            (total_value / Decimal(total_qty)) if total_qty > 0 else Decimal("0")
        ).quantize(Decimal("0.0001"))

        # Use earliest expiry_date (most conservative)
        # mypy: cast to Python datetime so min() accepts the type
        expiry_dates: list[datetime] = [
            cast(datetime, b.expiry_date)
            for b in batches if b.expiry_date is not None
        ]
        earliest_expiry = min(expiry_dates) if expiry_dates else survivor.expiry_date

        # 1) Update survivor
        survivor.quantity = total_qty
        # mypy: unit_cost is float-typed; convert Decimal → float
        survivor.unit_cost = float(weighted_cost)
        if earliest_expiry is not None:
            # mypy: SQLAlchemy DateTime vs Python datetime type mismatch
            # (at runtime they are the same datetime instance)
            survivor.expiry_date = earliest_expiry  # type: ignore[assignment]
        db.add(survivor)

        # 2) Mark consumed batches (snapshot qty first)
        consumed_ids: list[int] = []
        for b in consumed:
            consumed_ids.append(b.id)
            b.status = "consumed"
            b.quantity = 0
            db.add(b)

        await db.flush()

        # 3) Audit transactions (type='adjust')
        # 3a) Outgoing: one per consumed batch, qty = -original_qty
        for b in consumed:
            out_qty = -original_qtys[b.id]
            audit_out = InventoryTransaction(
                product_id=b.product_id,
                warehouse_id=b.warehouse_id,
                type="adjust",
                quantity=out_qty,
                reference_type="batch_merge",
                reference_id=survivor.id,
                batch_id=b.id,
                notes=(
                    f"合并到 batch #{survivor.id}: {reason} "
                    f"(原 qty={original_qtys[b.id]})"
                ),
            )
            db.add(audit_out)

        # 3b) Incoming: survivor audit marker (qty=0, net unchanged)
        audit_in = InventoryTransaction(
            product_id=survivor.product_id,
            warehouse_id=survivor.warehouse_id,
            type="adjust",
            quantity=0,
            reference_type="batch_merge",
            reference_id=survivor.id,
            batch_id=survivor.id,
            notes=(
                f"合并自 batches {consumed_ids}: {reason} "
                f"(total qty={total_qty}, weighted_cost={weighted_cost})"
            ),
        )
        db.add(audit_in)
        await db.flush()

        logger.warning(
            "Batch merge: survivor=%s consumed=%s total_qty=%s actor=%s reason=%s",
            survivor.id, consumed_ids, total_qty, actor, reason,
        )

        return {
            "survivor_batch_id": survivor.id,
            "consumed_batch_ids": consumed_ids,
            "survivor_batch_no": survivor.batch_no,
            "product_id": survivor.product_id,
            "warehouse_id": survivor.warehouse_id,
            "total_quantity": total_qty,
            "weighted_unit_cost": float(weighted_cost),
            "merged_count": len(consumed_ids) + 1,
            "reason": reason,
            "actor": actor,
        }


# Module-level singleton.
batch_merge_service = BatchMergeService()