"""Visit intelligence routes."""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.database import get_db
from app.schemas.common import fail, ok

router = APIRouter(prefix="/ai", tags=["ai"])


@router.post("/visits/{visit_id}/report")
async def visit_report(
    visit_id: int,
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(get_current_user),
):
    """Generate an AI summary report for a customer visit."""
    from app.services.visit_intel_service import generate_visit_report

    try:
        result = await generate_visit_report(db, visit_id)
        return ok(result)
    except ValueError as e:
        return fail(str(e), 404)


@router.post("/visits/{visit_id}/sentiment")
async def visit_sentiment(
    visit_id: int,
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(get_current_user),
):
    """Analyze sentiment of a visit report."""
    from app.services.visit_intel_service import analyze_visit_sentiment

    try:
        result = await analyze_visit_sentiment(db, visit_id)
        return ok(result)
    except ValueError as e:
        return fail(str(e), 404)


@router.post("/visits/effectiveness")
async def visit_effectiveness(
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(get_current_user),
):
    """Evaluate the effectiveness of all visits in the past period."""
    from app.services.visit_intel_service import evaluate_visit_effectiveness

    try:
        result = await evaluate_visit_effectiveness(db)
        return ok(result)
    except ValueError as e:
        return fail(str(e), 404)
