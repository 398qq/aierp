"""Inventory AI endpoints."""
import logging

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.database import get_db
from app.schemas.common import fail, ok
from app.services.ai import InventoryAgent

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ai", tags=["ai"])


@router.post("/inventory/analyze")
async def analyze_inventory(
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(get_current_user),
):
    """Analyze inventory levels and generate insights against safety stock."""
    from app.models.product import Inventory, Product

    items = (
        await db.execute(
            select(
                Product.name,
                Inventory.quantity,
                Inventory.safety_stock,
            )
            .select_from(Inventory)
            .join(Product, Inventory.product_id == Product.id)
            .where(
                Inventory.deleted_at.is_(None),
                Product.deleted_at.is_(None),
            )
        )
    ).all()

    if not items:
        return fail("No inventory data found", 404)

    inventory_data = [
        {
            "product_name": r[0],
            "current_stock": r[1] or 0,
            "safety_stock": r[2] or 0,
        }
        for r in items
    ]
    analysis = await InventoryAgent.analyze(inventory_data)
    return ok(analysis)


@router.get("/inventory/demand-forecast")
async def demand_forecast(
    category: str | None = Query(None),
    top_k: int = Query(20, le=100),
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(get_current_user),
):
    """Enhanced demand forecasting with seasonality, trend, and lead-time detection."""
    from app.services.inventory_service import forecast_demand

    try:
        result = await forecast_demand(db, category=category, top_k=top_k)
        return ok(result)
    except Exception as e:
        return fail(f"Demand forecast failed: {str(e)}", 500)