"""Multi-agent orchestration routes."""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.database import get_db
from app.schemas.common import fail, ok

router = APIRouter(prefix="/ai", tags=["ai"])


@router.post("/orchestrate/customer/{customer_id}")
async def orchestrate_customer(
    customer_id: int,
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(get_current_user),
):
    """Run a full 360 customer analysis using multiple AI agents."""
    from app.services.orchestration_service import orchestrate_customer_360

    try:
        result = await orchestrate_customer_360(db, customer_id)
        return ok(result)
    except ValueError as e:
        return fail(str(e), 404)


@router.post("/orchestrate/product/{product_id}")
async def orchestrate_product(
    product_id: int,
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(get_current_user),
):
    """Run a full 360 product analysis using multiple AI agents."""
    from app.services.orchestration_service import orchestrate_product_360

    try:
        result = await orchestrate_product_360(db, product_id)
        return ok(result)
    except ValueError as e:
        return fail(str(e), 404)


@router.post("/orchestrate/global")
async def orchestrate_global(
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(get_current_user),
):
    """Run a global cross-domain orchestration across all entities."""
    from app.services.orchestration_service import orchestrate_global_360

    try:
        result = await orchestrate_global_360(db)
        return ok(result)
    except ValueError as e:
        return fail(str(e), 404)