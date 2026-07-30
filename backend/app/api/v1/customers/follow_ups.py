from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import and_, case, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.datetime_utils import to_utc
from app.core.permissions import require_perm
from app.database import get_db
from app.models.customer import Customer, CustomerFollowUp
from app.models.sales import Opportunity
from app.schemas.common import fail, ok
from app.services.cache_service import cache_bump_version

from .crud import FollowUpCreate, FollowUpUpdate

VALID_DUE_BUCKETS = {"overdue", "today", "upcoming", "unscheduled", "closed"}

router = APIRouter(prefix="/customers", tags=["customers"])


@router.get("/{customer_id}/follow-ups")
async def list_followups(
    customer_id: int,
    page: int = Query(1, ge=1, le=10_000, description="1-based page index"),
    page_size: int = Query(20, ge=1, le=100, description="rows per page, max 100"),
    status: Optional[str] = Query(None, max_length=32, description="exact match on status"),
    priority: Optional[str] = Query(None, max_length=32, description="exact match on priority"),
    due_bucket: Optional[str] = Query(
        None, description="overdue|today|upcoming|unscheduled|closed",
    ),
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(require_perm("customers", "read")),
):
    """List customer follow-ups with pagination, filters, and summary counts.

    Response shape:
      {
        "list": [{...follow-up..., "due_bucket": "overdue|..."}],
        "total": <int>,
        "counts": {open, completed, high, overdue, today}
      }

    Bucketing rule (server-side UTC, deterministic):
      - status in {completed, cancelled}            -> "closed"
      - planned_at IS NULL                          -> "unscheduled"
      - planned_at < today_start (UTC midnight)     -> "overdue"
      - today_start <= planned_at < tomorrow_start  -> "today"
      - otherwise                                    -> "upcoming"

    Sort: due_bucket weight (overdue < today < upcoming
    < unscheduled < closed), then earliest of planned_at
    vs created_at (nullslast), then id as tie-breaker.
    """
    if due_bucket is not None and due_bucket not in VALID_DUE_BUCKETS:
        return fail(
            f"due_bucket must be one of {sorted(VALID_DUE_BUCKETS)}", 422,
        )

    now = datetime.now(timezone.utc)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    today_end = today_start + timedelta(days=1)

    status_terminal = CustomerFollowUp.status.in_(["completed", "cancelled"])
    planned_at_null = CustomerFollowUp.planned_at.is_(None)
    planned_before_today = CustomerFollowUp.planned_at < today_start
    planned_today = and_(
        CustomerFollowUp.planned_at >= today_start,
        CustomerFollowUp.planned_at < today_end,
    )

    bucket_expr = case(
        (status_terminal, "closed"),
        (planned_at_null, "unscheduled"),
        (planned_before_today, "overdue"),
        (planned_today, "today"),
        else_="upcoming",
    ).label("bucket")

    bucket_weight_expr = case(
        (status_terminal, 4),
        (planned_at_null, 3),
        (planned_before_today, 0),
        (planned_today, 1),
        else_=2,
    ).label("weight")

    base_filters = (
        CustomerFollowUp.customer_id == customer_id,
        CustomerFollowUp.deleted_at.is_(None),
    )

    def apply_filters(q):
        if status:
            q = q.where(CustomerFollowUp.status == status)
        if priority:
            q = q.where(CustomerFollowUp.priority == priority)
        if due_bucket:
            q = q.where(bucket_expr == due_bucket)
        return q

    main_q = (
        select(CustomerFollowUp, bucket_expr).where(*base_filters)
    )
    main_q = apply_filters(main_q)
    main_q = main_q.order_by(
        bucket_weight_expr.asc(),
        func.coalesce(CustomerFollowUp.planned_at, CustomerFollowUp.created_at).asc(),
        CustomerFollowUp.id.asc(),
    )

    rows = (
        await db.execute(main_q.offset((page - 1) * page_size).limit(page_size))
    ).all()

    total_subq = apply_filters(
        select(CustomerFollowUp.id).where(*base_filters)
    ).subquery()
    total = await db.scalar(select(func.count()).select_from(total_subq)) or 0

    counts_q = select(
        func.coalesce(
            func.sum(
                case(
                    (
                        or_(
                            CustomerFollowUp.status.is_(None),
                            CustomerFollowUp.status.in_(["planned", "in_progress"]),
                        ),
                        1,
                    ),
                    else_=0,
                )
            ),
            0,
        ).label("open"),
        func.coalesce(
            func.sum(case((CustomerFollowUp.status == "completed", 1), else_=0)),
            0,
        ).label("completed"),
        func.coalesce(
            func.sum(case((CustomerFollowUp.priority == "high", 1), else_=0)),
            0,
        ).label("high"),
        func.coalesce(
            func.sum(case((bucket_expr == "overdue", 1), else_=0)),
            0,
        ).label("overdue"),
        func.coalesce(
            func.sum(case((bucket_expr == "today", 1), else_=0)),
            0,
        ).label("today"),
    ).where(*base_filters)
    counts_q = apply_filters(counts_q)
    cnts = (await db.execute(counts_q)).one()

    return ok({
        "list": [
            {
                "id": f.id,
                "opportunity_id": f.opportunity_id,
                "method": f.method,
                "status": f.status,
                "content": f.content,
                "result": f.result,
                "planned_at": str(f.planned_at) if f.planned_at else None,
                "completed_at": str(f.completed_at) if f.completed_at else None,
                "priority": f.priority,
                "assigned_to": f.assigned_to,
                "created_at": str(f.created_at) if f.created_at else None,
                "due_bucket": bucket,
            }
            for (f, bucket) in rows
        ],
        "total": int(total),
        "counts": {
            "open": int(cnts.open),
            "completed": int(cnts.completed),
            "high": int(cnts.high),
            "overdue": int(cnts.overdue),
            "today": int(cnts.today),
        },
    })


@router.post("/{customer_id}/follow-ups", status_code=201)
async def create_followup(
    customer_id: int,
    body: FollowUpCreate,
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(require_perm("customers", "write")),
):
    try:
        data = body.model_dump()
        if data.get("opportunity_id") is not None:
            opportunity = await db.scalar(
                select(Opportunity).where(
                    Opportunity.id == data["opportunity_id"],
                    Opportunity.customer_id == customer_id,
                    Opportunity.deleted_at.is_(None),
                )
            )
            if opportunity is None:
                return fail("商机不存在或不属于当前客户", 400)
        for date_field in ("planned_at", "completed_at"):
            if data.get(date_field):
                data[date_field] = to_utc(datetime.fromisoformat(data[date_field]))
        if data.get("completed_at") and not data.get("status"):
            data["status"] = "completed"
        if data.get("status") != "completed":
            data["completed_at"] = None
        followup = CustomerFollowUp(customer_id=customer_id, **data)
        db.add(followup)
        with db.no_autoflush:
            result = await db.execute(
                select(Customer).where(Customer.id == customer_id)
            )
            cust = result.scalar_one_or_none()
            if cust:
                cust.last_contacted_at = datetime.now(timezone.utc)
                # Trigger customer state machine transition (inactive/churned -> active)
                from app.services.customer_state_service import on_re_engage

                await on_re_engage(db, customer_id)
            await db.flush()
            followup_id = followup.id
        await cache_bump_version("customers:list")
        await cache_bump_version("dashboard:overview")
        await cache_bump_version("dashboard:kpi")
        return ok({"id": followup_id})
    except Exception as e:
        import traceback

        traceback.print_exc()
        return fail(str(e), 500)


@router.put("/{customer_id}/follow-ups/{followup_id}")
async def update_followup(
    customer_id: int,
    followup_id: int,
    body: FollowUpUpdate,
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(require_perm("customers", "write")),
):
    result = await db.execute(
        select(CustomerFollowUp).where(
            CustomerFollowUp.id == followup_id,
            CustomerFollowUp.customer_id == customer_id,
            CustomerFollowUp.deleted_at.is_(None),
        )
    )
    followup = result.scalar_one_or_none()
    if followup is None:
        return fail("Follow-up not found", 404)
    data = body.model_dump(exclude_unset=True)
    if data.get("opportunity_id") is not None:
        opportunity = await db.scalar(
            select(Opportunity).where(
                Opportunity.id == data["opportunity_id"],
                Opportunity.customer_id == customer_id,
                Opportunity.deleted_at.is_(None),
            )
        )
        if opportunity is None:
            return fail("商机不存在或不属于当前客户", 400)
    for date_field in ("planned_at", "completed_at"):
        if date_field in data and data.get(date_field) is None:
            del data[date_field]
        elif data.get(date_field):
            data[date_field] = to_utc(datetime.fromisoformat(data[date_field]))
    if data.get("completed_at") and not data.get("status"):
        data["status"] = "completed"
    for key, val in data.items():
        setattr(followup, key, val)
    if any(key in data for key in ("content", "result", "completed_at")):
        customer = await db.scalar(
            select(Customer).where(
                Customer.id == customer_id,
                Customer.deleted_at.is_(None),
            )
        )
        if customer:
            customer.last_contacted_at = datetime.now(timezone.utc)
    await db.flush()
    await cache_bump_version("customers:list")
    await cache_bump_version("dashboard:overview")
    await cache_bump_version("dashboard:kpi")
    return ok({"id": followup.id})


@router.delete("/{customer_id}/follow-ups/{followup_id}")
async def delete_followup(
    customer_id: int,
    followup_id: int,
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(require_perm("customers", "delete")),
):
    result = await db.execute(
        select(CustomerFollowUp).where(
            CustomerFollowUp.id == followup_id,
            CustomerFollowUp.customer_id == customer_id,
            CustomerFollowUp.deleted_at.is_(None),
        )
    )
    followup = result.scalar_one_or_none()
    if followup is None:
        return fail("Follow-up not found", 404)
    followup.deleted_at = datetime.now(timezone.utc)
    await db.flush()
    await cache_bump_version("customers:list")
    return ok(msg="deleted")
