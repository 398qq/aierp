"""Inventory batch & COGS API — batch traceability and cost accounting.

Endpoints (under /api/v1):
- GET  /inventory/batches               paginated batch list
- GET  /inventory/batches/{id}           single batch detail
- POST /inventory/batches/allocate       pre-flight allocation check
- GET  /inventory/cogs                   COGS / gross margin report
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.database import get_db
from app.schemas.common import fail, ok
from app.services.inventory_batch_service import inventory_batch_service

router = APIRouter(prefix="/inventory", tags=["inventory-batch"])


class AllocateRequest(BaseModel):
    product_id: int
    warehouse_id: int
    quantity: int = Field(gt=0)
    strategy: str = Field(
        default="lowest_cost_first",
        description="分配策略: lowest_cost_first (优先出低价批次) | fifo (先入先出) | fefo (先到期先出)",
    )


# ── Batch list ───────────────────────────────────────────────────────────


@router.get("/batches")
async def list_batches(
    product_id: int | None = Query(None),
    warehouse_id: int | None = Query(None),
    status: str | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(get_current_user),
):
    """Paginated list of inventory batches with product/supplier names."""
    result = await inventory_batch_service.get_batches(
        db,
        product_id=product_id,
        warehouse_id=warehouse_id,
        status=status,
        page=page,
        page_size=page_size,
    )
    return ok(result)


# ── Batch detail ─────────────────────────────────────────────────────────


@router.get("/batches/{batch_id}")
async def get_batch(
    batch_id: int,
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(get_current_user),
):
    """Single batch detail."""
    result = await inventory_batch_service.get_batches(
        db, product_id=None, warehouse_id=None, page=1, page_size=1
    )
    # Filter by ID from full list (single-batch lookup)
    batches = result["list"]
    for b in batches:
        if b["id"] == batch_id:
            return ok(b)
    return fail("Batch not found", 404)


# ── Pre-flight allocation ────────────────────────────────────────────────


@router.post("/batches/allocate")
async def preview_allocation(
    body: AllocateRequest,
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(get_current_user),
):
    """Pre-flight allocation check — shows which batches would be consumed.

    Strategy: lowest_cost_first (默认，优先出价低批次) | fifo | fefo.
    Does NOT commit any deduction. Use before confirming a delivery to
    verify sufficient stock and preview COGS.
    """
    result = await inventory_batch_service.allocate_for_delivery(
        db,
        product_id=body.product_id,
        warehouse_id=body.warehouse_id,
        quantity=body.quantity,
        strategy=body.strategy,
    )
    return ok(
        {
            "strategy": body.strategy,
            "allocations": [
                {
                    "batch_id": a.batch_id,
                    "batch_no": a.batch_no,
                    "quantity": a.quantity,
                    "unit_cost": a.unit_cost,
                    "line_cost": round(a.quantity * a.unit_cost, 2),
                }
                for a in result.allocations
            ],
            "unfilled_qty": result.unfilled_qty,
            "is_fully_allocated": result.is_fully_allocated,
            "total_cost": float(result.total_cost),
            "weighted_unit_cost": float(result.weighted_unit_cost),
        }
    )


# ── Manual Commit ────────────────────────────────────────────────────────


class ManualCommitRequest(BaseModel):
    product_id: int
    warehouse_id: int
    picks: list[dict] = Field(..., description='[{"batch_id": 1, "quantity": 30}, ...]')


@router.post("/batches/commit")
async def commit_allocation(
    body: ManualCommitRequest,
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(get_current_user),
):
    """Manually commit a batch allocation — operator picks exact batches & quantities.

    Validates each pick (batch exists, has stock, belongs to product/warehouse),
    then persists deductions and returns the COGS breakdown.
    """
    try:
        result = await inventory_batch_service.allocate_manual(
            db,
            product_id=body.product_id,
            warehouse_id=body.warehouse_id,
            picks=body.picks,
        )
        total_cogs = await inventory_batch_service.commit_deduction(
            db, result.allocations
        )
        return ok(
            {
                "total_cogs": float(total_cogs),
                "allocations": [
                    {
                        "batch_id": a.batch_id,
                        "batch_no": a.batch_no,
                        "quantity": a.quantity,
                        "unit_cost": a.unit_cost,
                        "line_cost": round(a.quantity * a.unit_cost, 2),
                    }
                    for a in result.allocations
                ],
            }
        )
    except ValueError as e:
        # Stage 17 follow-up: log detail server-side, return generic message
        # to avoid leaking internal state via error strings.
        import logging
        logging.getLogger(__name__).warning(
            "Batch allocation rejected: product=%s warehouse=%s err=%s",
            body.product_id, body.warehouse_id, e,
        )
        return fail("Batch allocation rejected — check inputs and retry", 400)


# ── COGS Report ──────────────────────────────────────────────────────────


@router.get("/cogs")
async def cogs_report(
    start_date: str | None = Query(None, description="YYYY-MM-DD"),
    end_date: str | None = Query(None, description="YYYY-MM-DD"),
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(get_current_user),
):
    """COGS and gross margin report grouped by product.

    Uses actual batch costs recorded on SalesOrderItem.cost_amount.
    """
    result = await inventory_batch_service.get_cogs_report(
        db, start_date=start_date, end_date=end_date
    )
    return ok(result)
