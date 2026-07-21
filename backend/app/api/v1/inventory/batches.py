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
from app.services.batch_traceability_service import batch_traceability_service
from app.services.expiry_alert_service import expiry_alert_service
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


# ── Batch Traceability ─────────────────────────────────────────────────────


@router.get("/batches/{batch_id}/traceability")
async def get_batch_traceability(
    batch_id: int,
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(get_current_user),
):
    """Bidirectional traceability for a single batch.

    Returns upstream (supplier + POs + stock_in records) and downstream
    (delivery notes + sales orders + customers that consumed qty from this
    batch). Requires InventoryTransaction.batch_id to be populated by
    commit_deduction (Stage 18+).
    """
    result = await batch_traceability_service.get_traceability(db, batch_id)
    if result is None:
        return fail("Batch not found", 404)
    return ok(result)


# ── Expiry Alert ─────────────────────────────────────────────────────


@router.get("/batches/expiring")
async def get_expiring_batches(
    buckets: str | None = Query(
        None,
        description=(
            "逗号分隔的 bucket 列表: expired,7d,30d,90d。默认全部。"
        ),
    ),
    warehouse_id: int | None = Query(None),
    limit: int = Query(100, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(get_current_user),
):
    """扫描即将过期 / 已过期的批次,按时间桶分类。

    Buckets:
      - expired  (expiry_date < today)
      - 7d       (within next 7 days)
      - 30d      (within next 8–30 days)
      - 90d      (within next 31–90 days)

    排除 status=consumed/recalled 且 quantity<=0 的批次。
    """
    bucket_list: list[str] | None = None
    if buckets:
        bucket_list = [b.strip() for b in buckets.split(",") if b.strip()]
    try:
        result = await expiry_alert_service.scan(
            db,
            buckets=bucket_list,
            warehouse_id=warehouse_id,
            limit_per_bucket=limit,
        )
    except ValueError as e:
        return fail(str(e), 400)
    total = sum(len(v) for v in result.values())
    return ok({"buckets": result, "total": total})


@router.get("/batches/expiring/summary")
async def get_expiring_summary(
    warehouse_id: int | None = Query(None),
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(get_current_user),
):
    """Dashboard widget 概要 — 每个 bucket 的计数 + total。"""
    summary = await expiry_alert_service.get_summary(
        db, warehouse_id=warehouse_id
    )
    return ok(summary)


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
