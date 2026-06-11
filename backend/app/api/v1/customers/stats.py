import logging
from datetime import datetime, timezone, timedelta

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.permissions import require_perm
from app.database import get_db
from app.models.customer import (
    Customer,
    CustomerFollowUp,
    CustomerLog,
)
from app.models.finance import PaymentRecord
from app.models.sales import Opportunity, SalesOrder
from app.schemas.common import fail, ok

router = APIRouter(prefix="/customers", tags=["customers"])
logger = logging.getLogger(__name__)


def _safe_float(value) -> float:
    try:
        if value is None:
            return 0.0
        return float(value)
    except Exception:
        return 0.0


def _to_utc(dt_value: datetime | None) -> datetime | None:
    if dt_value is None:
        return None
    if dt_value.tzinfo is None:
        return dt_value.replace(tzinfo=timezone.utc)
    return dt_value.astimezone(timezone.utc)


def _days_since(dt_value: datetime | None, now: datetime) -> int:
    value = _to_utc(dt_value)
    if value is None:
        return 999
    return max(0, (now - value).days)


def _rfm_bucket(days_since_contact: int, order_count: int, total_amount: float) -> tuple[int, int, int, str]:
    if days_since_contact <= 30:
        recency = 5
    elif days_since_contact <= 60:
        recency = 4
    elif days_since_contact <= 120:
        recency = 3
    elif days_since_contact <= 180:
        recency = 2
    else:
        recency = 1

    if order_count >= 12:
        frequency = 5
    elif order_count >= 6:
        frequency = 4
    elif order_count >= 3:
        frequency = 3
    elif order_count >= 1:
        frequency = 2
    else:
        frequency = 1

    if total_amount >= 1_000_000:
        monetary = 5
    elif total_amount >= 500_000:
        monetary = 4
    elif total_amount >= 100_000:
        monetary = 3
    elif total_amount >= 20_000:
        monetary = 2
    else:
        monetary = 1

    if recency >= 4 and frequency >= 4 and monetary >= 4:
        tier = "重要价值"
    elif recency >= 3 and (frequency >= 3 or monetary >= 3):
        tier = "重要发展"
    elif recency <= 2 and (frequency >= 3 or monetary >= 3):
        tier = "重要保持"
    elif recency <= 2 and frequency <= 2 and monetary <= 2:
        tier = "流失风险"
    else:
        tier = "一般价值"

    return recency, frequency, monetary, tier


class BatchScoreAIRequest(BaseModel):
    ids: list[int] = Field(default_factory=list)


# --- Dashboard Stats ---


def _health_label(score: float) -> str:
    if score >= 80:
        return "优秀"
    if score >= 60:
        return "良好"
    if score >= 40:
        return "一般"
    return "差"


@router.get("/{customer_id:int}/stats")
async def customer_stats(
    customer_id: int,
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(require_perm("customers", "read")),
):
    customer = (await db.execute(
        select(Customer).where(
            Customer.id == customer_id,
            Customer.deleted_at.is_(None),
        )
    )).scalar_one_or_none()
    if customer is None:
        return fail("Customer not found", 404)

    now = datetime.now(timezone.utc)
    created_at = _to_utc(customer.created_at) or now
    created_days = max(0, (now - created_at).days)

    order_agg = (await db.execute(
        select(
            func.count(SalesOrder.id),
            func.coalesce(func.sum(SalesOrder.total_amount), 0),
            func.max(func.coalesce(SalesOrder.order_date, SalesOrder.created_at)),
        ).where(
            SalesOrder.customer_id == customer_id,
            SalesOrder.deleted_at.is_(None),
        )
    )).first()

    order_count = int(order_agg[0] or 0) if order_agg else 0
    total_revenue = _safe_float(order_agg[1]) if order_agg else 0.0
    last_order_at = _to_utc(order_agg[2]) if order_agg else None

    paid_total = _safe_float((await db.execute(
        select(func.coalesce(func.sum(PaymentRecord.amount), 0)).where(
            PaymentRecord.customer_id == customer_id,
            PaymentRecord.deleted_at.is_(None),
        )
    )).scalar())
    outstanding = max(0.0, round(total_revenue - paid_total, 2))

    credit_limit = _safe_float(customer.credit_limit)
    credit_usage_pct = round((outstanding / credit_limit) * 100, 1) if credit_limit > 0 else 0.0

    from app.domain.states import CUSTOMER_STATUS_LABELS
    lifecycle = CUSTOMER_STATUS_LABELS.get(customer.status, customer.status or "未知")

    ai_insights = customer.ai_insights if isinstance(customer.ai_insights, dict) else {}
    health_score = _safe_float(ai_insights.get("health_score"))
    health_label = ai_insights.get("health_label")
    if health_score <= 0:
        score = 50.0
        if order_count >= 8:
            score += 20
        elif order_count >= 3:
            score += 12
        elif order_count >= 1:
            score += 6

        if total_revenue >= 500_000:
            score += 15
        elif total_revenue >= 100_000:
            score += 10
        elif total_revenue >= 20_000:
            score += 5

        days_since_contact = _days_since(customer.last_contacted_at, now)
        if days_since_contact <= 30:
            score += 12
        elif days_since_contact <= 90:
            score += 6
        elif days_since_contact >= 365:
            score -= 8

        level = (customer.level or "").upper()
        if level == "A":
            score += 5
        elif level == "B":
            score += 2
        elif level == "D":
            score -= 5

        if credit_usage_pct >= 95:
            score -= 12
        elif credit_usage_pct >= 80:
            score -= 6

        health_score = max(0.0, min(100.0, round(score, 1)))
        health_label = _health_label(health_score)
    else:
        health_score = round(health_score, 1)
        health_label = health_label or _health_label(health_score)

    aging = {"0-30": 0.0, "31-60": 0.0, "61-90": 0.0, "90+": 0.0}
    if outstanding > 0:
        age_days = _days_since(last_order_at, now)
        if age_days <= 30:
            aging["0-30"] = outstanding
        elif age_days <= 60:
            aging["31-60"] = outstanding
        elif age_days <= 90:
            aging["61-90"] = outstanding
        else:
            aging["90+"] = outstanding

    return ok({
        "lifecycle": lifecycle,
        "created_days": created_days,
        "order_count": order_count,
        "total_revenue": round(total_revenue, 2),
        "last_order_date": str(last_order_at) if last_order_at else None,
        "credit_limit": round(credit_limit, 2),
        "outstanding": round(outstanding, 2),
        "paid_total": round(paid_total, 2),
        "credit_usage_pct": credit_usage_pct,
        "aging": aging,
        "health_score": health_score,
        "health_label": health_label,
    })


@router.get("/{customer_id:int}/timeline")
async def customer_timeline(
    customer_id: int,
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(require_perm("customers", "read")),
):
    customer = (await db.execute(
        select(Customer).where(
            Customer.id == customer_id,
            Customer.deleted_at.is_(None),
        )
    )).scalar_one_or_none()
    if customer is None:
        return fail("Customer not found", 404)

    followups = (await db.execute(
        select(CustomerFollowUp).where(
            CustomerFollowUp.customer_id == customer_id,
            CustomerFollowUp.deleted_at.is_(None),
        ).order_by(CustomerFollowUp.created_at.desc()).limit(30)
    )).scalars().all()

    orders = (await db.execute(
        select(SalesOrder).where(
            SalesOrder.customer_id == customer_id,
            SalesOrder.deleted_at.is_(None),
        ).order_by(SalesOrder.created_at.desc()).limit(30)
    )).scalars().all()

    events: list[dict] = []
    if customer.last_contacted_at:
        events.append({
            "id": 2_000_000_000 + customer.id,
            "type": "contact",
            "title": "客户联系记录",
            "detail": "客户最近联系时间已更新",
            "time": str(customer.last_contacted_at),
        })

    for fu in followups:
        event_time = fu.completed_at or fu.planned_at or fu.created_at
        if event_time is None:
            continue
        detail_parts = [part for part in [fu.content, fu.result] if part]
        detail = "；".join(detail_parts) if detail_parts else (fu.status or "跟进记录")
        events.append({
            "id": fu.id,
            "type": "followup",
            "title": f"客户跟进（{fu.method or '记录'}）",
            "detail": detail,
            "time": str(event_time),
        })

    for order in orders:
        event_time = order.order_date or order.created_at
        if event_time is None:
            continue
        amount = _safe_float(order.total_amount)
        events.append({
            "id": 1_000_000_000 + order.id,
            "type": "order",
            "title": f"销售订单 {order.order_no or f'#{order.id}'}",
            "detail": f"金额 ¥{amount:.2f}，状态 {order.status or 'unknown'}",
            "time": str(event_time),
        })

    events.sort(key=lambda item: item["time"], reverse=True)
    return ok(events[:50])

@router.get("/stats")
async def customer_dashboard_stats(
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(require_perm("customers", "read")),
):
    async def _agg(field):
        col = getattr(Customer, field)
        r = await db.execute(
            select(col, func.count(Customer.id))
            .where(Customer.deleted_at.is_(None))
            .group_by(col)
        )
        return sorted(
            [{"name": row[0] or "未设置", "value": row[1]} for row in r.all()],
            key=lambda x: -x["value"],
        )

    async def _monthly():
        month_expr = func.date_trunc("month", Customer.created_at)
        r = await db.execute(
            select(month_expr, func.count(Customer.id))
            .where(Customer.deleted_at.is_(None), Customer.created_at.isnot(None))
            .group_by(month_expr)
            .order_by(month_expr.desc())
            .limit(12)
        )
        rows = r.all()
        rows.reverse()
        return [{"month": str(row[0])[:7], "count": row[1]} for row in rows]

    total_r = await db.execute(select(func.count(Customer.id)).where(Customer.deleted_at.is_(None)))
    by_industry = await _agg("industry")
    by_level = await _agg("level")
    by_region = await _agg("region")
    by_source = await _agg("source")
    by_type = await _agg("customer_type")
    monthly = await _monthly()

    return ok({
        "total": total_r.scalar() or 0,
        "by_industry": by_industry,
        "by_level": by_level,
        "by_region": by_region,
        "by_source": by_source,
        "by_type": by_type,
        "monthly": monthly,
    })


@router.get("/ai-stats")
async def customer_ai_stats(
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(require_perm("customers", "read")),
):
    """Customer AI intelligence overview: health score, churn risk, RFM tier distributions, segment overview."""
    now = datetime.now(timezone.utc)
    days_30 = now - timedelta(days=30)

    # Pull required fields once and aggregate in Python to avoid JSON SQL dialect differences.
    from app.domain.states import CUSTOMER_STATUS_LABELS
    customers = (await db.execute(
        select(
            Customer.id,
            Customer.level,
            Customer.status,
            Customer.last_contacted_at,
            Customer.ai_insights,
        ).where(Customer.deleted_at.is_(None))
    )).all()

    total = len(customers)
    ai_computed = 0
    never_contacted = 0
    stale_high_value = 0
    high_churn_count = 0

    rfm_tiers: dict[str, int] = {}
    churn_dist: dict[str, int] = {}
    lifecycle_map: dict[str, int] = {}
    health_scores: list[float] = []

    stale_cutoff = now - timedelta(days=60)

    for _id, level, status, last_contacted_at, ai_insights in customers:
        lifecycle_key = CUSTOMER_STATUS_LABELS.get(status, status or "未设置")
        lifecycle_map[lifecycle_key] = lifecycle_map.get(lifecycle_key, 0) + 1

        if last_contacted_at is None:
            never_contacted += 1

        last_contacted_utc = _to_utc(last_contacted_at)
        if (level or "").upper() == "A" and last_contacted_utc and last_contacted_utc < stale_cutoff:
            stale_high_value += 1

        if not isinstance(ai_insights, dict):
            continue

        ai_computed += 1

        tier = (ai_insights.get("rfm") or {}).get("tier") or "未分析"
        rfm_tiers[tier] = rfm_tiers.get(tier, 0) + 1

        churn = ai_insights.get("churn") or ai_insights.get("churn_risk") or {}
        risk_level = churn.get("risk_level") or "未知"
        churn_dist[risk_level] = churn_dist.get(risk_level, 0) + 1

        risk_score = _safe_float(churn.get("risk_score"))
        if risk_score >= 70:
            high_churn_count += 1

        health_score = _safe_float(ai_insights.get("health_score"))
        if health_score > 0:
            health_scores.append(health_score)

    # Active in last 30d (have orders or follow-ups)
    recent_orders_cus = await db.execute(
        select(SalesOrder.customer_id).where(
            SalesOrder.deleted_at.is_(None),
            SalesOrder.created_at >= days_30,
        ).distinct()
    )
    recent_cus_ids = set(recent_orders_cus.scalars().all())
    followup_cus = await db.execute(
        select(CustomerFollowUp.customer_id).where(
            CustomerFollowUp.deleted_at.is_(None),
            CustomerFollowUp.created_at >= days_30,
        ).distinct()
    )
    recent_cus_ids |= set(followup_cus.scalars().all())
    active_30d = len(recent_cus_ids)

    avg_health = round(sum(health_scores) / len(health_scores), 1) if health_scores else 0

    by_lifecycle = [
        {"stage": stage, "count": count}
        for stage, count in sorted(lifecycle_map.items(), key=lambda item: (-item[1], item[0]))
    ]

    return ok({
        "total": total,
        "ai_computed": ai_computed,
        "ai_coverage_pct": round(ai_computed / total * 100, 1) if total > 0 else 0,
        "rfm_tiers": rfm_tiers,
        "churn_dist": churn_dist,
        "never_contacted": never_contacted,
        "stale_high_value": stale_high_value,
        "active_30d": active_30d,
        "avg_health_score": avg_health,
        "by_lifecycle": by_lifecycle,
        "high_churn_count": high_churn_count,
    })


@router.post("/batch-score-ai")
async def batch_score_ai(
    body: BatchScoreAIRequest,
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(require_perm("customers", "write")),
):
    """Generate/refresh lightweight AI insights for customers (compat route for frontend dashboard)."""
    now = datetime.now(timezone.utc)
    d90 = now - timedelta(days=90)

    customer_stmt = select(Customer).where(Customer.deleted_at.is_(None))
    if body.ids:
        customer_stmt = customer_stmt.where(Customer.id.in_(body.ids))
    customers = (await db.execute(customer_stmt)).scalars().all()

    if not customers:
        return ok({"scored": 0, "errors": 0, "total": 0})

    customer_ids = [c.id for c in customers]

    order_rows = (await db.execute(
        select(
            SalesOrder.customer_id,
            func.count(SalesOrder.id),
            func.coalesce(func.sum(SalesOrder.total_amount), 0),
            func.max(SalesOrder.created_at),
            func.count(SalesOrder.id).filter(SalesOrder.created_at >= d90),
        )
        .where(
            SalesOrder.deleted_at.is_(None),
            SalesOrder.customer_id.in_(customer_ids),
        )
        .group_by(SalesOrder.customer_id)
    )).all()
    order_map = {
        int(row[0]): {
            "count": int(row[1] or 0),
            "amount": _safe_float(row[2]),
            "last_order_at": _to_utc(row[3]),
            "count_90d": int(row[4] or 0),
        }
        for row in order_rows
    }

    latest_followup_rows = (await db.execute(
        select(CustomerFollowUp.customer_id, func.max(CustomerFollowUp.created_at))
        .where(
            CustomerFollowUp.deleted_at.is_(None),
            CustomerFollowUp.customer_id.in_(customer_ids),
        )
        .group_by(CustomerFollowUp.customer_id)
    )).all()
    followup_last_map = {int(row[0]): _to_utc(row[1]) for row in latest_followup_rows}

    opp_rows = (await db.execute(
        select(Opportunity.customer_id, func.count(Opportunity.id))
        .where(
            Opportunity.deleted_at.is_(None),
            Opportunity.customer_id.in_(customer_ids),
            Opportunity.stage.in_(["lead", "qualification", "proposal", "negotiation"]),
        )
        .group_by(Opportunity.customer_id)
    )).all()
    opp_map = {int(row[0]): int(row[1] or 0) for row in opp_rows}

    scored = 0
    errors = 0

    for customer in customers:
        try:
            stats = order_map.get(customer.id, {})
            order_count = int(stats.get("count", 0))
            total_amount = _safe_float(stats.get("amount"))
            last_order_at = stats.get("last_order_at")
            order_count_90d = int(stats.get("count_90d", 0))

            last_contact_at = _to_utc(customer.last_contacted_at) or followup_last_map.get(customer.id)
            days_since_contact = _days_since(last_contact_at, now)
            days_since_order = _days_since(last_order_at, now)
            open_opportunities = opp_map.get(customer.id, 0)

            recency, frequency, monetary, tier = _rfm_bucket(days_since_contact, order_count, total_amount)

            level_bonus = {"A": 12.0, "B": 6.0, "C": 0.0, "D": -6.0}.get((customer.level or "").upper(), 0.0)
            contact_term = max(0.0, min(30.0, (120 - days_since_contact) * 0.25))
            order_term = max(0.0, min(24.0, order_count_90d * 4.0))
            health_score = max(0.0, min(100.0, round(46.0 + level_bonus + contact_term + order_term, 1)))

            if health_score >= 80:
                health_label = "健康"
            elif health_score >= 60:
                health_label = "关注"
            else:
                health_label = "风险"

            order_risk = min(100.0, days_since_order / 120.0 * 100.0)
            contact_risk = min(100.0, days_since_contact / 120.0 * 100.0)
            opp_risk = 0.0 if open_opportunities > 0 else 10.0
            churn_risk = max(0.0, min(100.0, round(order_risk * 0.55 + contact_risk * 0.35 + opp_risk, 1)))

            if churn_risk >= 70:
                risk_level = "高"
            elif churn_risk >= 40:
                risk_level = "中"
            else:
                risk_level = "低"

            churn_payload = {
                "risk_score": churn_risk,
                "risk_level": risk_level,
                "days_since_contact": days_since_contact,
                "days_since_order": days_since_order,
                "open_opportunities": open_opportunities,
            }

            merged_insights = dict(customer.ai_insights) if isinstance(customer.ai_insights, dict) else {}
            merged_insights.update({
                "updated_at": now.isoformat(),
                "health_score": health_score,
                "health_label": health_label,
                "rfm": {
                    "recency": recency,
                    "frequency": frequency,
                    "monetary": monetary,
                    "tier": tier,
                },
                # Keep both keys for backward compatibility.
                "churn": churn_payload,
                "churn_risk": churn_payload,
            })
            customer.ai_insights = merged_insights
            scored += 1
        except Exception as exc:
            errors += 1
            logger.warning("batch-score-ai failed for customer_id=%s: %s", customer.id, exc)

    await db.flush()
    return ok({"scored": scored, "errors": errors, "total": len(customers)})


@router.get("/recent-activity")
async def recent_activity(
    limit: int = Query(20, le=100),
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(require_perm("customers", "read")),
):
    """Recent customer activity across all customers."""
    logs = (await db.execute(
        select(CustomerLog, Customer.name).join(
            Customer, CustomerLog.customer_id == Customer.id
        ).where(
            CustomerLog.deleted_at.is_(None),
            Customer.deleted_at.is_(None),
        ).order_by(CustomerLog.created_at.desc()).limit(limit)
    )).all()

    return ok([{
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
    } for row in logs])


# --- Overdue Follow-ups (reminders) ---

TERMINAL_FOLLOWUP_STATUSES = ("completed", "cancelled")

@router.get("/overdue-followups")
async def overdue_followups(
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(require_perm("customers", "read")),
):
    now = datetime.now(timezone.utc)
    rows = (await db.execute(
        select(CustomerFollowUp, Customer).join(Customer, CustomerFollowUp.customer_id == Customer.id).where(
            CustomerFollowUp.deleted_at.is_(None),
            Customer.deleted_at.is_(None),
            CustomerFollowUp.planned_at < now,
            or_(
                CustomerFollowUp.status.is_(None),
                CustomerFollowUp.status.not_in(TERMINAL_FOLLOWUP_STATUSES),
            ),
        ).order_by(CustomerFollowUp.planned_at.asc()).limit(50)
    )).all()

    result = []
    for fu, cust in rows:
        overdue_days = (now - fu.planned_at.replace(tzinfo=timezone.utc)).days
        result.append({
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
        })

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
    rows = (await db.execute(
        select(CustomerFollowUp, Customer).join(Customer, CustomerFollowUp.customer_id == Customer.id).where(
            CustomerFollowUp.deleted_at.is_(None),
            Customer.deleted_at.is_(None),
            CustomerFollowUp.planned_at.is_not(None),
            CustomerFollowUp.planned_at <= window_end,
            or_(
                CustomerFollowUp.status.is_(None),
                CustomerFollowUp.status.not_in(TERMINAL_FOLLOWUP_STATUSES),
            ),
        ).order_by(CustomerFollowUp.planned_at.asc()).limit(100)
    )).all()

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

        items.append({
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
        })

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
        conditions.append(or_(
            Customer.name.ilike(pattern),
            Customer.short_name.ilike(pattern),
            Customer.code.ilike(pattern),
            Customer.contact_person.ilike(pattern),
            CustomerFollowUp.content.ilike(pattern),
            CustomerFollowUp.result.ilike(pattern),
            CustomerFollowUp.assigned_to.ilike(pattern),
        ))

    rows = (await db.execute(
        select(CustomerFollowUp, Customer)
        .join(Customer, CustomerFollowUp.customer_id == Customer.id)
        .where(*conditions)
        .order_by(CustomerFollowUp.planned_at.asc().nulls_last(), CustomerFollowUp.created_at.desc())
    )).all()

    items = []
    for fu, cust in rows:
        planned_at = _to_utc(fu.planned_at)
        planned_date = planned_at.date() if planned_at else None
        if fu.status in TERMINAL_FOLLOWUP_STATUSES:
            bucket = "closed"
            overdue_days = 0
            days_until = None
        elif planned_date is None:
            bucket = "unscheduled"
            overdue_days = 0
            days_until = None
        elif planned_date < today and (fu.status is None or fu.status not in TERMINAL_FOLLOWUP_STATUSES):
            bucket = "overdue"
            overdue_days = (today - planned_date).days
            days_until = None
        elif planned_date == today and (fu.status is None or fu.status not in TERMINAL_FOLLOWUP_STATUSES):
            bucket = "today"
            overdue_days = 0
            days_until = 0
        else:
            bucket = "upcoming"
            overdue_days = 0
            days_until = (planned_date - today).days

        items.append({
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
        })

    bucket_order = {"overdue": 0, "today": 1, "upcoming": 2, "unscheduled": 3, "closed": 4}
    items.sort(key=lambda item: (bucket_order.get(item["due_bucket"], 9), item["planned_at"] or "", item["created_at"] or ""))
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
    paged = items[start:start + page_size]
    return ok({"list": paged, "total": len(items), "page": page, "page_size": page_size, "counts": counts})
