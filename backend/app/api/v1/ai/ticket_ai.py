"""Ticket intelligence routes."""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.database import get_db
from app.schemas.common import fail, ok

router = APIRouter(prefix="/ai", tags=["ai"])


@router.post("/tickets/{ticket_id}/classify")
async def ticket_classify(
    ticket_id: int,
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(get_current_user),
):
    """Classify a ticket by category and priority using AI."""
    from app.services.ticket_intel_service import classify_ticket

    try:
        result = await classify_ticket(db, ticket_id)
        return ok(result)
    except ValueError as e:
        return fail(str(e), 404)


@router.post("/tickets/{ticket_id}/suggest-response")
async def ticket_suggest_response(
    ticket_id: int,
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(get_current_user),
):
    """Suggest a response for a ticket using AI."""
    from app.services.ticket_intel_service import suggest_ticket_response

    try:
        result = await suggest_ticket_response(db, ticket_id)
        return ok(result)
    except ValueError as e:
        return fail(str(e), 404)


@router.post("/tickets/{ticket_id}/predict-resolution")
async def ticket_predict_resolution(
    ticket_id: int,
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(get_current_user),
):
    """Predict how long a ticket will take to resolve."""
    from app.services.ticket_intel_service import predict_ticket_resolution

    try:
        result = await predict_ticket_resolution(db, ticket_id)
        return ok(result)
    except ValueError as e:
        return fail(str(e), 404)


@router.post("/tickets/cluster")
async def ticket_cluster(
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(get_current_user),
):
    """Cluster tickets by topic and similarity to identify systemic issues."""
    from app.services.ticket_intel_service import cluster_tickets

    try:
        result = await cluster_tickets(db)
        return ok(result)
    except ValueError as e:
        return fail(str(e), 404)