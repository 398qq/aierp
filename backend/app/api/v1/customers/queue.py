"""Customers — dashboard queue endpoints (recent activity, overdue, reminders, global).

Operational queues that surface "what should the sales team look at
right now" — separate from the per-customer stats, which are about
one customer at a time.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, Query
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.ai.customer._cleaners import to_utc
from app.core.permissions import require_perm
from app.database import get_db
from app.models.customer import Customer, CustomerFollowUp, CustomerLog
from app.schemas.common import ok

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/customers", tags=["customers"])


@router.get("/recent-activity")
async def recent_activity(
    limit: int = Query(20, le=100),
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(require_perm("customers", "read")),
):
    """Recent customer activity across all customers."""
    logs = (
        await db.execute(
            select(CustomerLog, Customer.name)
            .join(Customer, CustomerLog.customer_id == Customer.id)
            .where(
                CustomerLog.deleted_at.is_(None),
                Customer.deleted_at.is_(None),
            )
            .order_by(CustomerLog.created_at.desc())
            .limit(limit)
        )
    ).all()

    return ok(
        [
            {
                "id": row[0].id,
                "customer_id": row[0].customer_id,
                "customer_name": row[1],
                "action": row[0].action,
                "field_name": row[0].field_name,
                "old_value": row[0].old_value,
                "new_value": row[0].new_value,
                "operator": row[0].operator,
                "summary": row[0].summary,
                "created_at": str(row[0].created_at) if row[0].created_at else None,
            }
            for row in logs
        ]
    )


# --- Overdue Follow-ups (reminders) ---

TERMINAL_FOLLOWUP_STATUSES = ("completed", "cancelled")


@router.get("/overdue-followups")
async def overdue_followups(
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(require_perm("customers", "read")),
):
    now = datetime.now(timezone.utc)
    rows = (
        await db.execute(
            select(CustomerFollowUp, Customer)
            .join(Customer, CustomerFollowUp.customer_id == Customer.id)
            .where(
                CustomerFollowUp.deleted_at.is_(None),
                Customer.deleted_at.is_(None),
                CustomerFollowUp.planned_at < now,
                or_(
                    CustomerFollowUp.status.is_(None),
                    CustomerFollowUp.status.not_in(TERMINAL_FOLLOWUP_STATUSES),
                ),
            )
            .order_by(CustomerFollowUp.planned_at.asc())
            .limit(50)
        )
    ).all()

    result = []
    for fu, cust in rows:
        overdue_days = (now - fu.planned_at.replace(tzinfo=timezone.utc)).days
        result.append(
            {
                "id": fu.id,
                "customer_id": cust.id,
                "customer_name": cust.name,
                "owner": cust.owner,
                "method": fu.method,
                "priority": fu.priority,
                "planned_at": str(fu.planned_at),
                "status": fu.status,
                "content": fu.content,
                "overdue_days": overdue_days,
            }
        )

    result.sort(key=lambda x: -x["overdue_days"])
    return ok({"total": len(result), "items": result})


@router.get("/follow-up-reminders")
async def follow_up_reminders(
    days_ahead: int = Query(default=14, ge=0, le=90),
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(require_perm("customers", "read")),
):
    now = datetime.now(timezone.utc)
    today = now.date()
    window_end = now + timedelta(days=days_ahead)
    rows = (
        await db.execute(
            select(CustomerFollowUp, Customer)
            .join(Customer, CustomerFollowUp.customer_id == Customer.id)
            .where(
                CustomerFollowUp.deleted_at.is_(None),
                Customer.deleted_at.is_(None),
                CustomerFollowUp.planned_at.is_not(None),
                CustomerFollowUp.planned_at <= window_end,
                or_(
                    CustomerFollowUp.status.is_(None),
                    CustomerFollowUp.status.not_in(TERMINAL_FOLLOWUP_STATUSES),
                ),
            )
            .order_by(CustomerFollowUp.planned_at.asc())
            .limit(100)
        )
    ).all()

    items = []
    for fu, cust in rows:
        planned_at = fu.planned_at.replace(tzinfo=timezone.utc)
        planned_date = planned_at.date()
        if planned_date < today:
            due_bucket = "overdue"
            overdue_days = (today - planned_date).days
            days_until = None
        elif planned_date == today:
            due_bucket = "today"
            overdue_days = 0
            days_until = 0
        else:
            due_bucket = "upcoming"
            overdue_days = 0
            days_until = (planned_date - today).days

        items.append(
            {
                "id": fu.id,
                "customer_id": cust.id,
                "customer_name": cust.name,
                "owner": cust.owner,
                "method": fu.method,
                "priority": fu.priority,
                "planned_at": str(fu.planned_at),
                "status": fu.status,
                "content": fu.content,
                "overdue_days": overdue_days,
                "days_until": days_until,
                "due_bucket": due_bucket,
            }
        )

    bucket_order = {"overdue": 0, "today": 1, "upcoming": 2}
    items.sort(key=lambda x: (bucket_order[x["due_bucket"]], x["planned_at"]))
    counts = {
        "overdue": sum(1 for item in items if item["due_bucket"] == "overdue"),
        "today": sum(1 for item in items if item["due_bucket"] == "today"),
        "upcoming": sum(1 for item in items if item["due_bucket"] == "upcoming"),
    }
    return ok({"total": len(items), "counts": counts, "items": items})


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
    now = datetime.now(timezone.utc)
    today = now.date()

    conditions = [
        CustomerFollowUp.deleted_at.is_(None),
        Customer.deleted_at.is_(None),
    ]
    if status:
        conditions.append(CustomerFollowUp.status == status)
    if priority:
        conditions.append(CustomerFollowUp.priority == priority)
    if q and q.strip():
        pattern = f"%{q.strip()}%"
        conditions.append(
            or_(
                Customer.name.ilike(pattern),
                Customer.short_name.ilike(pattern),
                Customer.code.ilike(pattern),
                Customer.contact_person.ilike(pattern),
                CustomerFollowUp.content.ilike(pattern),
                CustomerFollowUp.result.ilike(pattern),
                CustomerFollowUp.assigned_to.ilike(pattern),
            )
        )

    rows = (
        await db.execute(
            select(CustomerFollowUp, Customer)
            .join(Customer, CustomerFollowUp.customer_id == Customer.id)
            .where(*conditions)
            .order_by(
                CustomerFollowUp.planned_at.asc().nulls_last(),
                CustomerFollowUp.created_at.desc(),
            )
        )
    ).all()

    items = []
    for fu, cust in rows:
        planned_at = to_utc(fu.planned_at)
        planned_date = planned_at.date() if planned_at else None
        if fu.status in TERMINAL_FOLLOWUP_STATUSES:
            bucket = "closed"
            overdue_days = 0
            days_until = None
        elif planned_date is None:
            bucket = "unscheduled"
            overdue_days = 0
            days_until = None
        elif planned_date < today and (
            fu.status is None or fu.status not in TERMINAL_FOLLOWUP_STATUSES
        ):
            bucket = "overdue"
            overdue_days = (today - planned_date).days
            days_until = None
        elif planned_date == today and (
            fu.status is None or fu.status not in TERMINAL_FOLLOWUP_STATUSES
        ):
            bucket = "today"
            overdue_days = 0
            days_until = 0
        else:
            bucket = "upcoming"
            overdue_days = 0
            days_until = (planned_date - today).days

        items.append(
            {
                "id": fu.id,
                "customer_id": cust.id,
                "customer_name": cust.name,
                "owner": cust.owner,
                "method": fu.method,
                "priority": fu.priority,
                "planned_at": str(fu.planned_at) if fu.planned_at else None,
                "completed_at": str(fu.completed_at) if fu.completed_at else None,
                "created_at": str(fu.created_at) if fu.created_at else None,
                "status": fu.status,
                "content": fu.content,
                "result": fu.result,
                "assigned_to": fu.assigned_to,
                "overdue_days": overdue_days,
                "days_until": days_until,
                "due_bucket": bucket,
            }
        )

    bucket_order = {
        "overdue": 0,
        "today": 1,
        "upcoming": 2,
        "unscheduled": 3,
        "closed": 4,
    }
    items.sort(
        key=lambda item: (
            bucket_order.get(item["due_bucket"], 9),
            item["planned_at"] or "",
            item["created_at"] or "",
        )
    )
    counts = {
        "all": len(items),
        "overdue": sum(1 for item in items if item["due_bucket"] == "overdue"),
        "today": sum(1 for item in items if item["due_bucket"] == "today"),
        "upcoming": sum(1 for item in items if item["due_bucket"] == "upcoming"),
        "unscheduled": sum(1 for item in items if item["due_bucket"] == "unscheduled"),
        "closed": sum(1 for item in items if item["due_bucket"] == "closed"),
    }
    if due_bucket:
        items = [item for item in items if item["due_bucket"] == due_bucket]
    start = (page - 1) * page_size
    paged = items[start : start + page_size]
    return ok(
        {
            "list": paged,
            "total": len(items),
            "page": page,
            "page_size": page_size,
            "counts": counts,
        }
    )


__all__ = ["router"]
