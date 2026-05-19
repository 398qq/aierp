"""Smart matching routes — customer-product recommendations."""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.database import get_db
from app.schemas.common import fail, ok

router = APIRouter(prefix="/ai", tags=["ai"])


@router.post("/customers/{customer_id}/recommend-products")
async def recommend_products(
    customer_id: int,
    top_k: int = Query(5),
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(get_current_user),
):
    """Recommend products for a customer based on purchase history and embedding similarity."""
    from app.services.matching_service import recommend_products_for_customer

    try:
        result = await recommend_products_for_customer(db, customer_id, top_k)
        return ok(result)
    except ValueError as e:
        return fail(str(e), 404)


@router.post("/products/{product_id}/recommend-customers")
async def recommend_customers(
    product_id: int,
    top_k: int = Query(5),
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(get_current_user),
):
    """Recommend customers for a product based on affinity and embedding similarity."""
    from app.services.matching_service import recommend_customers_for_product

    try:
        result = await recommend_customers_for_product(db, product_id, top_k)
        return ok(result)
    except ValueError as e:
        return fail(str(e), 404)
