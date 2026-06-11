"""Pricing routes — benchmark and AI price recommendations."""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.database import get_db
from app.schemas.common import fail, ok

router = APIRouter(prefix="/ai", tags=["ai"])


@router.get("/pricing/benchmark/{product_id}")
async def pricing_benchmark(
    product_id: int,
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(get_current_user),
):
    """Get historical price benchmarks for a product."""
    from app.services.pricing_service import get_pricing_benchmark

    try:
        result = await get_pricing_benchmark(db, product_id)
        return ok(result)
    except ValueError as e:
        return fail(str(e), 404)


@router.post("/pricing/recommend")
async def pricing_recommend(
    product_id: int = Query(...),
    customer_id: int | None = Query(None),
    quantity: int = Query(1, ge=1),
    is_sample: bool = Query(False),
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(get_current_user),
):
    """AI-recommended price for a product considering costs, market, and customer."""
    from app.services.pricing_service import recommend_price

    try:
        result = await recommend_price(db, product_id, customer_id, quantity, is_sample)
        return ok(result)
    except ValueError as e:
        return fail(str(e), 404)
