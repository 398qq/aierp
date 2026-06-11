"""Customer stats / dashboard / AI / follow-up routes.

Stage 1 refactor: route layer is a thin proxy. All business logic lives in
``app.services.customer_stats_service.CustomerStatsService``.

Endpoints (all under ``/customers`` prefix):
- ``GET /{customer_id:int}/stats``        single-customer aggregate
- ``GET /{customer_id:int}/timeline``     unified timeline (contact/follow-up/order)
- ``GET /stats``                          dashboard group-by stats
- ``GET /ai-stats``                       AI intelligence overview
- ``POST /batch-score-ai``                bulk AI insight refresh
- ``GET /recent-activity``                tail customer logs
- ``GET /overdue-followups``              planned-but-past follow-ups
- ``GET /follow-up-reminders``            upcoming + today + overdue reminders
- ``GET /follow-ups-global``              paged follow-up explorer
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.permissions import require_perm
from app.database import get_db
from app.schemas.common import fail, ok
from app.services.customer_stats_service import customer_stats_service

router = APIRouter(prefix="/customers", tags=["customers"])
logger = logging.getLogger(__name__)


class BatchScoreAIRequest(BaseModel):
    ids: list[int] = Field(default_factory=list)


@router.get("/{customer_id:int}/stats")
async def customer_stats(
    customer_id: int,
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(require_perm("customers", "read")),
):
    """Single-customer aggregate (lifecycle, RFM, health, aging)."""
    payload = await customer_stats_service.get_customer_stats(db, customer_id)
    if payload is None:
        return fail("Customer not found", 404)
    payload["last_order_date"] = (
        str(payload["last_order_date"]) if payload["last_order_date"] else None
    )
    return ok(payload)


@router.get("/{customer_id:int}/timeline")
async def customer_timeline(
    customer_id: int,
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(require_perm("customers", "read")),
):
    """Unified timeline (contact / follow-up / order events)."""
    events = await customer_stats_service.get_customer_timeline(db, customer_id)
    if events is None:
        return fail("Customer not found", 404)
    return ok(events)


@router.get("/stats")
async def customer_dashboard_stats(
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(require_perm("customers", "read")),
):
    """Dashboard group-by stats (industry/level/region/source/type + monthly)."""
    return ok(await customer_stats_service.get_dashboard_stats(db))


@router.get("/ai-stats")
async def customer_ai_stats(
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(require_perm("customers", "read")),
):
    """AI intelligence overview (health, churn, RFM, lifecycle)."""
    return ok(await customer_stats_service.get_ai_stats(db))


@router.post("/batch-score-ai")
async def batch_score_ai(
    body: BatchScoreAIRequest,
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(require_perm("customers", "write")),
):
    """Refresh lightweight AI insights (RFM / health / churn) in bulk."""
    return ok(await customer_stats_service.batch_score_ai(db, body.ids))


@router.get("/recent-activity")
async def recent_activity(
    limit: int = Query(20, le=100),
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(require_perm("customers", "read")),
):
    """Tail customer log entries across all customers."""
    return ok(await customer_stats_service.get_recent_activity(db, limit=limit))


@router.get("/overdue-followups")
async def overdue_followups(
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(require_perm("customers", "read")),
):
    """Overdue follow-ups (planned_at < now and not terminal)."""
    return ok(await customer_stats_service.get_overdue_followups(db))


@router.get("/follow-up-reminders")
async def follow_up_reminders(
    days_ahead: int = Query(default=14, ge=0, le=90),
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(require_perm("customers", "read")),
):
    """Upcoming + today + overdue reminders within a window."""
    return ok(
        await customer_stats_service.get_follow_up_reminders(db, days_ahead=days_ahead)
    )


@router.get("/follow-ups-global")
async def global_follow_ups(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    status: str | None = Query(default=None),
    priority: str | None = Query(default=None),
    due_bucket: str | None = Query(default=None),
    q: str | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(require_perm("customers", "read")),
):
    """Paged follow-up explorer with status/priority/due-bucket/q filters."""
    return ok(
        await customer_stats_service.get_global_follow_ups(
            db,
            page=page,
            page_size=page_size,
            status=status,
            priority=priority,
            due_bucket=due_bucket,
            q=q,
        )
    )
