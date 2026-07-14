"""Inventory batch service — bridges domain allocation/costing logic to DB.

Handles three critical flows:
1. **Receipt → Batch creation** — When goods are received, create InventoryBatchORM
   records with the actual unit_cost from the PO/receipt.
2. **Delivery → Batch deduction + COGS** — When stock is shipped, allocate from
   batches (FIFO/FEFO), deduct quantities, and compute the exact COGS per line.
3. **Cost recalculation** — Recompute Inventory.unit_price (moving average) after
   every receipt.

The domain-layer pure logic lives in:
- ``app/domain/inventory/batch.py`` (FEFO/FIFO allocation)
- ``app/domain/inventory/cost_strategy.py`` (WAC/FIFO/Standard cost)
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import date as date_type, datetime, timezone
from decimal import ROUND_HALF_UP, Decimal
from typing import Any, List, Optional, cast

from sqlalchemy import ColumnElement, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.inventory.batch import (
    BatchAllocation,
    BatchStatus,
    InventoryBatch,
    allocate_fifo_by_received,
    allocate_lowest_cost_first,
)
from app.domain.inventory.cost_strategy import make_cost_strategy
from app.models.product import Inventory as InventoryORM
from app.models.product import InventoryBatchORM

logger = logging.getLogger(__name__)

# ── Application-layer DTOs ────────────────────────────────────────────────


@dataclass
class BatchSummary:
    """Public view of a single inventory batch."""

    id: int
    product_id: int
    warehouse_id: int
    batch_no: str
    quantity: int
    unit_cost: float
    received_date: Optional[str]
    expiry_date: Optional[str]
    status: str
    supplier_name: Optional[str] = None
    product_name: Optional[str] = None


@dataclass
class BatchAllocationResult:
    """Result of allocating n units from inventory for delivery."""

    allocations: List[BatchAllocation]
    unfilled_qty: int

    @property
    def is_fully_allocated(self) -> bool:
        return self.unfilled_qty == 0

    @property
    def total_cost(self) -> Decimal:
        return sum(
            (
                Decimal(str(a.quantity)) * Decimal(str(a.unit_cost))
                for a in self.allocations
            ),
            start=Decimal("0"),
        )

    @property
    def weighted_unit_cost(self) -> Decimal:
        total_qty = self.total_quantity
        if total_qty == 0:
            return Decimal("0")
        return (self.total_cost / Decimal(str(total_qty))).quantize(
            Decimal("0.0001"), rounding=ROUND_HALF_UP
        )

    @property
    def total_quantity(self) -> int:
        return sum(a.quantity for a in self.allocations)


# ── Service ────────────────────────────────────────────────────────────────


class InventoryBatchService:
    """Application service for inventory batch lifecycle."""

    # ── Receipt → Batch Creation ─────────────────────────────────────────

    async def create_batches_from_receipt(
        self,
        db: AsyncSession,
        *,
        product_id: int,
        warehouse_id: int,
        batch_no: str,
        quantity: int,
        unit_cost: float,
        supplier_id: int | None = None,
        received_date: datetime | date_type | None = None,
        expiry_date: datetime | None = None,
        manufacture_date: datetime | None = None,
        rohs_compliant: bool = True,
        msl_level: str | None = None,
        notes: str | None = None,
    ) -> InventoryBatchORM:
        """Create a single inventory batch from a goods receipt line.

        Also updates the aggregate Inventory.unit_price per the product's
        costing method (default: moving weighted average).
        """
        from app.domain.inventory.batch import InventoryBatch as DomainBatch

        # Validate via domain
        received = (
            received_date.date()
            if isinstance(received_date, datetime)
            else (received_date or date_type.today())
        )
        expires = (
            expiry_date.date() if isinstance(expiry_date, datetime) else expiry_date
        )

        domain_batch = DomainBatch(  # noqa: F841 — used for future domain validation
            product_id=product_id,
            warehouse_id=warehouse_id,
            batch_no=batch_no,
            quantity=quantity,
            received_date=received,
            unit_cost=unit_cost,
            supplier_id=supplier_id,
            expiry_date=expires,
            manufacture_date=(
                manufacture_date.date()
                if isinstance(manufacture_date, datetime)
                else manufacture_date
            ),
            rohs_compliant=rohs_compliant,
            notes=notes,
        )
        _ = domain_batch  # explicit placeholder until domain validator is wired

        # Persist to ORM
        orm_batch = InventoryBatchORM(
            product_id=product_id,
            warehouse_id=warehouse_id,
            batch_no=batch_no,
            quantity=quantity,
            unit_cost=unit_cost,
            received_date=received_date or datetime.now(timezone.utc),
            expiry_date=expiry_date,
            manufacture_date=manufacture_date,
            supplier_id=supplier_id,
            status="available",
            rohs_compliant=rohs_compliant,
            msl_level=msl_level,
            notes=notes,
        )
        db.add(orm_batch)

        # Recompute moving average cost on the Inventory aggregate
        await self._recalc_inventory_cost(
            db, product_id, warehouse_id, quantity, unit_cost
        )

        await db.flush()
        logger.info(
            "Batch created: product=%s batch=%s qty=%s cost=%.4f",
            product_id,
            batch_no,
            quantity,
            unit_cost,
        )
        return orm_batch

    # ── Delivery → Batch Deduction + COGS ────────────────────────────────

    async def allocate_for_delivery(
        self,
        db: AsyncSession,
        *,
        product_id: int,
        warehouse_id: int,
        quantity: int,
        strategy: str = "lowest_cost_first",
    ) -> BatchAllocationResult:
        """Allocate `quantity` units from available batches.

        Args:
            strategy: "lowest_cost_first" (default, 优先出低价批次),
                      "fifo" (先入先出), "fefo" (先到期先出)

        Does NOT persist deductions — caller must call `commit_deduction()` after
        confirming the allocation is acceptable (e.g. delivery note is shipped).

        Returns the allocation plan with per-batch cost breakdown for COGS.
        """
        # Load available batches from DB
        orm_batches = (
            (
                await db.execute(
                    select(InventoryBatchORM)
                    .where(
                        InventoryBatchORM.product_id == product_id,
                        InventoryBatchORM.warehouse_id == warehouse_id,
                        InventoryBatchORM.deleted_at.is_(None),
                        InventoryBatchORM.status == "available",
                        InventoryBatchORM.quantity > 0,
                    )
                    .order_by(InventoryBatchORM.received_date.asc())
                )
            )
            .scalars()
            .all()
        )

        if not orm_batches:
            return BatchAllocationResult(allocations=[], unfilled_qty=quantity)

        # Convert to domain batches
        domain_batches = [
            InventoryBatch(
                id=b.id,
                product_id=b.product_id,
                warehouse_id=b.warehouse_id,
                batch_no=b.batch_no,
                quantity=b.quantity,
                received_date=cast(datetime, b.received_date).date()
                if b.received_date
                else date_type.today(),
                unit_cost=float(b.unit_cost),
                status=BatchStatus(b.status) if b.status else BatchStatus.AVAILABLE,
                expiry_date=cast(datetime, b.expiry_date).date()
                if b.expiry_date
                else None,
                supplier_id=b.supplier_id,
            )
            for b in orm_batches
        ]

        # Choose allocation strategy
        if strategy == "fifo":
            result = allocate_fifo_by_received(domain_batches, quantity)
        elif strategy == "fefo":
            from app.domain.inventory.batch import allocate_fefo  # noqa: PLC0415 (per-strategy import keeps domain self-contained)

            result = allocate_fefo(domain_batches, quantity)
        else:
            # Default: lowest cost first — 优先出进价便宜的批次
            result = allocate_lowest_cost_first(domain_batches, quantity)

        return BatchAllocationResult(
            allocations=result.allocations,
            unfilled_qty=result.unfilled_qty,
        )

    async def commit_deduction(
        self,
        db: AsyncSession,
        allocations: List[BatchAllocation],
    ) -> Decimal:
        """Persist batch deductions after delivery is confirmed.

        Updates each batch's quantity and status. Returns total COGS.
        """
        total_cogs = Decimal("0")
        for alloc in allocations:
            if alloc.batch_id is None:
                continue
            # Update batch quantity
            batch = await db.get(InventoryBatchORM, alloc.batch_id)
            if batch is None:
                logger.warning("Batch %s not found during deduction", alloc.batch_id)
                continue
            batch.quantity = max(0, batch.quantity - alloc.quantity)
            if batch.quantity == 0:
                batch.status = "consumed"
            db.add(batch)

            line_cogs = Decimal(str(alloc.quantity)) * Decimal(str(alloc.unit_cost))
            total_cogs += line_cogs

        await db.flush()
        logger.info(
            "Batch deduction committed: %d allocations, total COGS=%.2f",
            len(allocations),
            float(total_cogs),
        )
        return total_cogs.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    # ── Manual Allocation ──────────────────────────────────────────────────

    async def allocate_manual(
        self,
        db: AsyncSession,
        *,
        product_id: int,
        warehouse_id: int,
        picks: list[dict[str, int]],
    ) -> BatchAllocationResult:
        """Manually pick which batches to consume and how many.

        Args:
            picks: [{"batch_id": 1, "quantity": 30}, {"batch_id": 3, "quantity": 20}]

        Validates each batch exists, has sufficient available quantity.
        Does NOT persist — caller must call ``commit_deduction()``.
        """
        if not picks:
            return BatchAllocationResult(allocations=[], unfilled_qty=0)

        allocations: list[BatchAllocation] = []
        for pick in picks:
            batch_id = pick["batch_id"]
            qty = pick["quantity"]
            if qty <= 0:
                continue

            batch = await db.get(InventoryBatchORM, batch_id)
            if batch is None:
                raise ValueError(f"批次 {batch_id} 不存在")
            if batch.product_id != product_id:
                raise ValueError(f"批次 {batch_id} 不属于产品 {product_id}")
            if batch.warehouse_id != warehouse_id:
                raise ValueError(f"批次 {batch_id} 不在仓库 {warehouse_id}")
            if batch.status != "available":
                raise ValueError(f"批次 {batch_id} 状态为 {batch.status}，不可用")
            if batch.quantity < qty:
                raise ValueError(
                    f"批次 {batch_id} 库存不足: 需要 {qty}，可用 {batch.quantity}"
                )

            allocations.append(
                BatchAllocation(
                    batch_id=batch_id,
                    batch_no=batch.batch_no,
                    quantity=qty,
                    unit_cost=float(batch.unit_cost),
                )
            )

        return BatchAllocationResult(allocations=allocations, unfilled_qty=0)

    # ── Cost Recalculation ────────────────────────────────────────────────

    async def _recalc_inventory_cost(
        self,
        db: AsyncSession,
        product_id: int,
        warehouse_id: int,
        incoming_qty: int,
        incoming_unit_cost: float,
    ) -> None:
        """Update Inventory.unit_price using the configured costing method."""
        inv = (
            await db.execute(
                select(InventoryORM).where(
                    InventoryORM.product_id == product_id,
                    InventoryORM.warehouse_id == warehouse_id,
                )
            )
        ).scalar_one_or_none()

        if inv is None:
            return

        method = inv.costing_method or "moving_avg"
        strategy = make_cost_strategy(method)

        new_cost = strategy.compute_new_unit_cost(
            current_qty=Decimal(str(inv.quantity)),
            current_avg_cost=Decimal(str(inv.unit_price or 0)),
            incoming_qty=Decimal(str(incoming_qty)),
            incoming_unit_cost=Decimal(str(incoming_unit_cost)),
        )
        inv.unit_price = float(new_cost)
        db.add(inv)

    # ── Queries ───────────────────────────────────────────────────────────

    async def get_batches(
        self,
        db: AsyncSession,
        *,
        product_id: int | None = None,
        warehouse_id: int | None = None,
        status: str | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> dict[str, Any]:
        """Paginated list of inventory batches with product/supplier names."""
        from app.models.product import Product
        from app.models.product import Supplier

        conditions: list[ColumnElement[bool]] = [
            InventoryBatchORM.deleted_at.is_(None)
        ]
        if product_id:
            conditions.append(InventoryBatchORM.product_id == product_id)
        if warehouse_id:
            conditions.append(InventoryBatchORM.warehouse_id == warehouse_id)
        if status:
            conditions.append(InventoryBatchORM.status == status)
        else:
            conditions.append(InventoryBatchORM.quantity > 0)

        count_q = select(InventoryBatchORM).where(*conditions)
        total = len((await db.execute(count_q)).scalars().all())

        query = (
            select(
                InventoryBatchORM,
                Product.name,
                Supplier.name,
            )
            .outerjoin(Product, InventoryBatchORM.product_id == Product.id)
            .outerjoin(Supplier, InventoryBatchORM.supplier_id == Supplier.id)
            .where(*conditions)
            .order_by(InventoryBatchORM.received_date.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        rows = (await db.execute(query)).all()

        items: List[dict] = []
        for batch, prod_name, supp_name in rows:
            items.append(
                {
                    "id": batch.id,
                    "product_id": batch.product_id,
                    "warehouse_id": batch.warehouse_id,
                    "batch_no": batch.batch_no,
                    "quantity": batch.quantity,
                    "unit_cost": float(batch.unit_cost),
                    "total_value": round(float(batch.unit_cost) * batch.quantity, 2),
                    "received_date": str(batch.received_date)[:10]
                    if batch.received_date
                    else None,
                    "expiry_date": str(batch.expiry_date)[:10]
                    if batch.expiry_date
                    else None,
                    "status": batch.status,
                    "product_name": prod_name,
                    "supplier_name": supp_name,
                }
            )

        return {"list": items, "total": total, "page": page, "page_size": page_size}

    async def get_cogs_report(
        self,
        db: AsyncSession,
        *,
        start_date: str | None = None,
        end_date: str | None = None,
    ) -> dict[str, Any]:
        """Aggregate COGS and gross margin by product over a date range.

        Uses SalesOrderItem.cost_amount for actual COGS and
        SalesOrderItem.total_price for revenue.
        """
        from app.models.sales import SalesOrder, SalesOrderItem

        conditions: list[ColumnElement[bool]] = [
            SalesOrderItem.deleted_at.is_(None),
            SalesOrder.deleted_at.is_(None),
            SalesOrderItem.cost_amount.isnot(None),
        ]
        if start_date:
            conditions.append(SalesOrder.created_at >= start_date)
        if end_date:
            conditions.append(SalesOrder.created_at <= end_date)

        rows = (
            await db.execute(
                select(
                    SalesOrderItem.product_id,
                    SalesOrderItem.product_name,
                    func.sum(SalesOrderItem.quantity).label("total_qty"),
                    func.sum(SalesOrderItem.total_price).label("total_revenue"),
                    func.sum(SalesOrderItem.cost_amount).label("total_cost"),
                )
                .join(SalesOrder, SalesOrderItem.order_id == SalesOrder.id)
                .where(*conditions)
                .group_by(SalesOrderItem.product_id, SalesOrderItem.product_name)
                .order_by(func.sum(SalesOrderItem.total_price).desc())
                .limit(100)
            )
        ).all()

        items: List[dict] = []
        total_revenue = Decimal("0")
        total_cost = Decimal("0")
        for pid, pname, qty, revenue, cost in rows:
            rev = Decimal(str(revenue or 0))
            cos = Decimal(str(cost or 0))
            margin = rev - cos
            margin_pct = round(float(margin / rev * 100), 1) if rev > 0 else 0.0
            items.append(
                {
                    "product_id": pid,
                    "product_name": pname or f"Product #{pid}",
                    "quantity": int(qty or 0),
                    "revenue": float(rev),
                    "cost": float(cos),
                    "margin": float(margin),
                    "margin_pct": margin_pct,
                }
            )
            total_revenue += rev
            total_cost += cos

        total_margin = total_revenue - total_cost
        return {
            "items": items,
            "summary": {
                "total_revenue": float(total_revenue),
                "total_cost": float(total_cost),
                "total_margin": float(total_margin),
                "margin_pct": round(float(total_margin / total_revenue * 100), 1)
                if total_revenue > 0
                else 0.0,
            },
        }


# Module-level singleton
inventory_batch_service = InventoryBatchService()
