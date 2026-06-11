"""Purchase order intelligence routes."""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.database import get_db
from app.schemas.common import fail, ok

router = APIRouter(prefix="/ai", tags=["ai"])


@router.post("/purchase-orders/{order_id}/optimize")
async def po_optimize(
    order_id: int,
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(get_current_user),
):
    """Optimize purchase order quantities and supplier allocation."""
    from app.services.po_intel_service import optimize_purchase_order

    try:
        result = await optimize_purchase_order(db, order_id)
        return ok(result)
    except ValueError as e:
        return fail(str(e), 404)


@router.post("/purchase-orders/suggest")
async def po_suggest(
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(get_current_user),
):
    """Suggest new purchase orders based on demand and inventory levels."""
    from app.services.po_intel_service import suggest_purchase_orders

    try:
        result = await suggest_purchase_orders(db)
        return ok(result)
    except ValueError as e:
        return fail(str(e), 404)


@router.post("/purchase-orders/{order_id}/risk")
async def po_risk(
    order_id: int,
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(get_current_user),
):
    """Assess risk for a purchase order (delay, price variance, supply disruption)."""
    from app.services.po_intel_service import assess_po_risk

    try:
        result = await assess_po_risk(db, order_id)
        return ok(result)
    except ValueError as e:
        return fail(str(e), 404)
