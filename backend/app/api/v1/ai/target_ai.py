"""Sales target intelligence routes."""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.database import get_db
from app.schemas.common import fail, ok

router = APIRouter(prefix="/ai", tags=["ai"])


@router.post("/targets/recommend/{user_id}")
async def target_recommend(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(get_current_user),
):
    """Recommend sales targets for a user based on historical performance."""
    from app.services.target_intel_service import recommend_targets

    try:
        result = await recommend_targets(db, user_id)
        return ok(result)
    except ValueError as e:
        return fail(str(e), 404)


@router.post("/targets/{target_id}/attainment")
async def target_attainment(
    target_id: int,
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(get_current_user),
):
    """Predict whether a sales target will be attained."""
    from app.services.target_intel_service import predict_attainment

    try:
        result = await predict_attainment(db, target_id)
        return ok(result)
    except ValueError as e:
        return fail(str(e), 404)


@router.post("/targets/early-warning")
async def target_early_warning(
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(get_current_user),
):
    """Scan all active targets and warn users who are falling behind."""
    from app.services.target_intel_service import scan_target_early_warning

    try:
        result = await scan_target_early_warning(db)
        return ok(result)
    except ValueError as e:
        return fail(str(e), 404)
