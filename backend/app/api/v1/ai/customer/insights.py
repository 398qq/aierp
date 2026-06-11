"""Customer AI — analytical insights endpoints.

Heavier read paths that aggregate data across customers, orders,
follow-ups, payments, opportunities, and quotations to produce
operational recommendations:

* ``POST /customer/{id}/rfm``            — Recency / Frequency / Monetary
* ``POST /customer/{id}/churn-risk``     — churn probability + drivers
* ``POST /customer/{id}/followup-suggestion`` — next follow-up suggestion
* ``POST /customer/{id}/analyze-followups``   — sentiment / topic / action items
* ``GET  /customer/{id}/summary``        — one-shot AI summary view
* ``POST /alert/{id}/enrich``            — alert enrichment
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.api.v1.ai.customer._cleaners import safe_float
from app.database import get_db
from app.schemas.common import fail, ok
from app.services.ai import CustomerAgent
from app.services.customer_service import calc_health

logger = logging.getLogger(__name__)


router = APIRouter(tags=["ai"])


@router.post("/customer/{customer_id}/rfm")
async def analyze_rfm(
    customer_id: int,
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(get_current_user),
):
    """RFM analysis for a customer (Recency, Frequency, Monetary)."""
    from app.models.customer import Customer, CustomerFollowUp
    from app.models.sales import SalesOrder

    result = await db.execute(
        select(Customer).where(
            Customer.id == customer_id, Customer.deleted_at.is_(None)
        )
    )
    customer = result.scalar_one_or_none()
    if customer is None:
        return fail("Customer not found", 404)

    if customer.ai_insights and customer.ai_insights.get("rfm"):
        return ok(customer.ai_insights["rfm"])

    order_stats = (
        await db.execute(
            select(
                func.count(SalesOrder.id),
                func.coalesce(func.sum(SalesOrder.total_amount), 0),
                func.max(SalesOrder.created_at),
            ).where(
                SalesOrder.customer_id == customer_id, SalesOrder.deleted_at.is_(None)
            )
        )
    ).first()

    last_fu = (
        await db.execute(
            select(CustomerFollowUp)
            .where(
                CustomerFollowUp.customer_id == customer_id,
                CustomerFollowUp.deleted_at.is_(None),
            )
            .order_by(CustomerFollowUp.created_at.desc())
            .limit(1)
        )
    ).scalar_one_or_none()

    data = {
        "name": customer.name,
        "industry": customer.industry or "",
        "total_orders": order_stats[0] or 0,
        "total_revenue": float(order_stats[1]) if order_stats[1] else 0,
        "last_order_date": str(order_stats[2]) if order_stats[2] else None,
        "last_contacted_at": str(customer.last_contacted_at)
        if customer.last_contacted_at
        else None,
        "last_followup": str(last_fu.planned_at)
        if last_fu and last_fu.planned_at
        else None,
    }
    analysis = await CustomerAgent.rfm_analysis(data)
    return ok(analysis)


@router.post("/customer/{customer_id}/churn-risk")
async def analyze_churn(
    customer_id: int,
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(get_current_user),
):
    """Churn risk analysis for a customer."""
    from app.models.customer import Customer, CustomerFollowUp
    from app.models.finance import PaymentRecord
    from app.models.sales import Opportunity, Quotation, SalesOrder

    result = await db.execute(
        select(Customer).where(
            Customer.id == customer_id, Customer.deleted_at.is_(None)
        )
    )
    customer = result.scalar_one_or_none()
    if customer is None:
        return fail("Customer not found", 404)

    if customer.ai_insights and customer.ai_insights.get("churn"):
        return ok(customer.ai_insights["churn"])

    now = datetime.now(timezone.utc)
    d90 = now - timedelta(days=90)
    d180 = now - timedelta(days=180)

    order_stats = (
        await db.execute(
            select(
                func.count(SalesOrder.id),
                func.coalesce(func.sum(SalesOrder.total_amount), 0),
                func.max(SalesOrder.created_at),
                func.count(SalesOrder.id).filter(SalesOrder.created_at >= d90),
                func.count(SalesOrder.id).filter(SalesOrder.created_at >= d180),
            ).where(
                SalesOrder.customer_id == customer_id, SalesOrder.deleted_at.is_(None)
            )
        )
    ).first()

    active_opps = (
        await db.execute(
            select(func.count(Opportunity.id)).where(
                Opportunity.customer_id == customer_id,
                Opportunity.deleted_at.is_(None),
                Opportunity.stage.in_(
                    ["lead", "qualification", "proposal", "negotiation"]
                ),
            )
        )
    ).scalar() or 0

    active_quotations = (
        await db.execute(
            select(func.count(Quotation.id)).where(
                Quotation.customer_id == customer_id,
                Quotation.deleted_at.is_(None),
                Quotation.status.in_(["draft", "sent"]),
            )
        )
    ).scalar() or 0

    credit_util = "无数据"
    if customer.credit_limit and customer.credit_limit > 0:
        outstanding = (
            await db.execute(
                select(func.coalesce(func.sum(PaymentRecord.amount), 0)).where(
                    PaymentRecord.customer_id == customer_id,
                    PaymentRecord.deleted_at.is_(None),
                    PaymentRecord.status != "paid",
                )
            )
        ).scalar() or 0
        credit_util = f"{min(100, round(float(outstanding) / float(customer.credit_limit) * 100))}%"

    ar_overdue_days = 0
    thirty_days_ago = now - timedelta(days=30)
    oldest_unpaid = (
        await db.execute(
            select(PaymentRecord)
            .where(
                PaymentRecord.customer_id == customer_id,
                PaymentRecord.deleted_at.is_(None),
                PaymentRecord.status != "paid",
                PaymentRecord.created_at < thirty_days_ago,
            )
            .order_by(PaymentRecord.created_at.asc())
            .limit(1)
        )
    ).scalar_one_or_none()
    if oldest_unpaid and oldest_unpaid.created_at:
        ar_overdue_days = (
            now - oldest_unpaid.created_at.replace(tzinfo=timezone.utc)
        ).days

    payments_for_health = (
        (
            await db.execute(
                select(PaymentRecord).where(
                    PaymentRecord.customer_id == customer_id,
                    PaymentRecord.deleted_at.is_(None),
                )
            )
        )
        .scalars()
        .all()
    )
    orders_for_health = (
        (
            await db.execute(
                select(SalesOrder).where(
                    SalesOrder.customer_id == customer_id,
                    SalesOrder.deleted_at.is_(None),
                )
            )
        )
        .scalars()
        .all()
    )
    health_score, health_label = calc_health(
        customer, list(orders_for_health), list(payments_for_health), now
    )

    orders_90d = order_stats[3] or 0
    orders_180d = order_stats[4] or 0
    orders_before = (orders_180d or 0) - (orders_90d or 0)
    order_trend = "稳定"
    if orders_90d > 0 and orders_before > 0:
        if orders_90d > orders_before * 1.3:
            order_trend = "增长"
        elif orders_90d < orders_before * 0.7:
            order_trend = "下降"

    last_fu = (
        await db.execute(
            select(CustomerFollowUp)
            .where(
                CustomerFollowUp.customer_id == customer_id,
                CustomerFollowUp.deleted_at.is_(None),
            )
            .order_by(CustomerFollowUp.created_at.desc())
            .limit(1)
        )
    ).scalar_one_or_none()

    data = {
        "name": customer.name,
        "industry": customer.industry or "",
        "level": customer.level or "",
        "lifecycle": customer.lifecycle or "未知",
        "total_orders": order_stats[0] or 0,
        "total_revenue": float(order_stats[1]) if order_stats[1] else 0,
        "last_order_date": str(order_stats[2]) if order_stats[2] else None,
        "orders_last_90d": orders_90d,
        "orders_last_180d": orders_180d,
        "order_trend": order_trend,
        "last_followup_date": str(last_fu.planned_at)
        if last_fu and last_fu.planned_at
        else None,
        "last_contacted_at": str(customer.last_contacted_at)
        if customer.last_contacted_at
        else None,
        "active_opportunities": active_opps,
        "active_quotations": active_quotations,
        "credit_utilization": credit_util,
        "ar_overdue_days": ar_overdue_days,
        "health_score": health_score,
        "health_label": health_label,
    }
    analysis = await CustomerAgent.churn_risk(data)
    return ok(analysis)


@router.post("/customer/{customer_id}/followup-suggestion")
async def suggest_followup(
    customer_id: int,
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(get_current_user),
):
    """AI-generated follow-up suggestion for a customer."""
    from app.models.customer import Customer, CustomerFollowUp

    result = await db.execute(
        select(Customer).where(
            Customer.id == customer_id, Customer.deleted_at.is_(None)
        )
    )
    customer = result.scalar_one_or_none()
    if customer is None:
        return fail("Customer not found", 404)

    last_fu = (
        await db.execute(
            select(CustomerFollowUp)
            .where(
                CustomerFollowUp.customer_id == customer_id,
                CustomerFollowUp.deleted_at.is_(None),
            )
            .order_by(CustomerFollowUp.created_at.desc())
            .limit(1)
        )
    ).scalar_one_or_none()

    data = {
        "name": customer.name,
        "industry": customer.industry or "",
        "notes": customer.notes or "",
        "level": customer.level or "",
        "last_followup_content": last_fu.content if last_fu else None,
        "last_followup_date": str(last_fu.planned_at)
        if last_fu and last_fu.planned_at
        else None,
    }
    suggestion = await CustomerAgent.followup_suggestion(data)
    return ok(suggestion)


@router.post("/customer/{customer_id}/analyze-followups")
async def analyze_followups(
    customer_id: int,
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(get_current_user),
):
    """Semantic analysis of follow-up history: sentiment, topics, action items, risk signals."""
    from app.models.customer import Customer, CustomerFollowUp

    result = await db.execute(
        select(Customer).where(
            Customer.id == customer_id, Customer.deleted_at.is_(None)
        )
    )
    customer = result.scalar_one_or_none()
    if customer is None:
        return fail("Customer not found", 404)

    followups = (
        (
            await db.execute(
                select(CustomerFollowUp)
                .where(
                    CustomerFollowUp.customer_id == customer_id,
                    CustomerFollowUp.deleted_at.is_(None),
                )
                .order_by(CustomerFollowUp.created_at.desc())
                .limit(20)
            )
        )
        .scalars()
        .all()
    )

    analysis = await CustomerAgent.analyze_followups(
        [
            {"method": f.method, "content": f.content, "result": f.result}
            for f in followups
        ],
        customer_name=customer.name,
    )
    return ok(analysis)


@router.get("/customer/{customer_id}/summary")
async def customer_ai_summary(
    customer_id: int,
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(get_current_user),
):
    """Compact AI summary: customer + latest snapshot + next best actions."""
    from app.models.customer import (
        Customer,
        CustomerAIRecommendation,
        CustomerAISnapshotDaily,
    )

    customer = (
        await db.execute(
            select(Customer).where(
                Customer.id == customer_id, Customer.deleted_at.is_(None)
            )
        )
    ).scalar_one_or_none()
    if customer is None:
        return fail("Customer not found", 404)

    latest_snapshot = (
        await db.execute(
            select(CustomerAISnapshotDaily)
            .where(
                CustomerAISnapshotDaily.customer_id == customer_id,
                CustomerAISnapshotDaily.deleted_at.is_(None),
            )
            .order_by(CustomerAISnapshotDaily.snapshot_date.desc())
            .limit(1)
        )
    ).scalar_one_or_none()

    next_actions = (
        (
            await db.execute(
                select(CustomerAIRecommendation)
                .where(
                    CustomerAIRecommendation.customer_id == customer_id,
                    CustomerAIRecommendation.deleted_at.is_(None),
                    CustomerAIRecommendation.status.in_(["open", "in_progress"]),
                )
                .order_by(CustomerAIRecommendation.priority_score.desc())
                .limit(5)
            )
        )
        .scalars()
        .all()
    )

    return ok(
        {
            "customer": {
                "id": customer.id,
                "name": customer.name,
                "level": customer.level,
                "industry": customer.industry,
                "owner": customer.owner,
                "health_score": safe_float(
                    (customer.ai_insights or {}).get("health_score")
                )
                or None,
                "health_label": (customer.ai_insights or {}).get("health_label"),
                "last_contacted_at": str(customer.last_contacted_at)
                if customer.last_contacted_at
                else None,
            },
            "snapshot": {
                "snapshot_date": str(latest_snapshot.snapshot_date)
                if latest_snapshot
                else None,
                "health_score": latest_snapshot.health_score
                if latest_snapshot
                else None,
                "churn_risk_score": latest_snapshot.churn_risk_score
                if latest_snapshot
                else None,
                "value_score": latest_snapshot.value_score if latest_snapshot else None,
                "urgency_score": latest_snapshot.urgency_score
                if latest_snapshot
                else None,
                "overdue_followups": latest_snapshot.overdue_followups
                if latest_snapshot
                else None,
                "open_opportunities": latest_snapshot.open_opportunities
                if latest_snapshot
                else None,
                "outstanding_amount": latest_snapshot.outstanding_amount
                if latest_snapshot
                else None,
            },
            "next_actions": [
                {
                    "id": rec.id,
                    "action_type": rec.action_type,
                    "title": rec.title,
                    "reason": rec.reason,
                    "priority_score": rec.priority_score,
                    "status": rec.status,
                    "due_at": str(rec.due_at) if rec.due_at else None,
                }
                for rec in next_actions
            ],
        }
    )


@router.post("/alert/{event_id}/enrich")
async def enrich_alert(
    event_id: int,
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(get_current_user),
):
    """Generate AI action suggestions for a specific alert event."""
    from app.models.customer import AlertEvent, Customer

    event_result = await db.execute(select(AlertEvent).where(AlertEvent.id == event_id))
    event = event_result.scalar_one_or_none()
    if event is None:
        return fail("Alert event not found", 404)

    cust_result = await db.execute(
        select(Customer).where(
            Customer.id == event.customer_id, Customer.deleted_at.is_(None)
        )
    )
    customer = cust_result.scalar_one_or_none()

    ctx = {
        "rule_type": event.rule_type,
        "rule_name": event.rule_name,
        "severity": event.severity,
        "message": event.message,
        "customer_name": customer.name if customer else "未知",
        "industry": customer.industry or "" if customer else "",
        "level": customer.level or "" if customer else "",
        "last_contact": str(customer.last_contacted_at)
        if customer and customer.last_contacted_at
        else "无",
    }
    enrichment = await CustomerAgent.enrich_alert(ctx)
    return ok(enrichment)
