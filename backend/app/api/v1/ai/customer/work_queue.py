"""Customer AI — work queue endpoints.

Generates, lists, and updates the next-best-action queue for the
sales team:

* ``POST /customer/work-queue/generate``           — score customers, build queue
* ``GET  /customer/work-queue``                    — list with paging
* ``POST /customer/recommendation/{id}/status``    — adopt / dismiss
* ``POST /customer/recommendation/{id}/feedback``  — record usefulness
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Any

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.api.v1.ai.customer._cleaners import days_since, safe_float, to_utc
from app.api.v1.ai.customer._scoring import (
    derive_risk_score,
    derive_urgency_score,
    derive_value_score,
    next_action,
)
from app.database import get_db
from app.schemas.common import fail, ok

logger = logging.getLogger(__name__)


router = APIRouter(tags=["ai"])


class WorkQueueGenerateRequest(BaseModel):
    customer_ids: list[int] | None = None
    replace_open: bool = True
    dry_run: bool = False


class WorkQueueStatusRequest(BaseModel):
    status: str = Field(pattern="^(open|in_progress|done|dismissed|superseded)$")
    owner: str | None = None


class WorkQueueFeedbackRequest(BaseModel):
    verdict: str = Field(pattern="^(adopted|rejected|partial)$")
    usefulness: int | None = Field(default=None, ge=1, le=5)
    outcome: str | None = Field(default=None, max_length=50)
    revenue_impact: float | None = None
    cost_impact: float | None = None
    comment: str | None = Field(default=None, max_length=2000)


@router.post("/customer/work-queue/generate")
async def generate_work_queue(
    body: WorkQueueGenerateRequest,
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(get_current_user),
):
    """Generate next-best-action queue for customers."""
    from app.models.customer import (
        Customer,
        CustomerAIRecommendation,
        CustomerAISnapshotDaily,
        CustomerFollowUp,
    )
    from app.models.finance import PaymentRecord
    from app.models.sales import Opportunity, SalesOrder

    now = datetime.now(timezone.utc)
    customer_stmt = select(Customer).where(Customer.deleted_at.is_(None))
    if body.customer_ids:
        customer_stmt = customer_stmt.where(Customer.id.in_(body.customer_ids))
    customers = (await db.execute(customer_stmt)).scalars().all()
    if not customers:
        return ok({"generated": 0, "replaced": 0, "items": []})

    customer_ids = [c.id for c in customers]

    replaced = 0
    if body.replace_open and not body.dry_run:
        open_recs = (
            (
                await db.execute(
                    select(CustomerAIRecommendation).where(
                        CustomerAIRecommendation.customer_id.in_(customer_ids),
                        CustomerAIRecommendation.deleted_at.is_(None),
                        CustomerAIRecommendation.status.in_(["open", "in_progress"]),
                    )
                )
            )
            .scalars()
            .all()
        )
        for rec in open_recs:
            rec.status = "superseded"
            replaced += 1

    orders = (
        (
            await db.execute(
                select(SalesOrder).where(
                    SalesOrder.deleted_at.is_(None),
                    SalesOrder.customer_id.in_(customer_ids),
                )
            )
        )
        .scalars()
        .all()
    )
    opportunities = (
        (
            await db.execute(
                select(Opportunity).where(
                    Opportunity.deleted_at.is_(None),
                    Opportunity.customer_id.in_(customer_ids),
                    Opportunity.stage.in_(
                        ["lead", "qualification", "proposal", "negotiation"]
                    ),
                )
            )
        )
        .scalars()
        .all()
    )
    followups = (
        (
            await db.execute(
                select(CustomerFollowUp).where(
                    CustomerFollowUp.deleted_at.is_(None),
                    CustomerFollowUp.customer_id.in_(customer_ids),
                )
            )
        )
        .scalars()
        .all()
    )
    payments = (
        (
            await db.execute(
                select(PaymentRecord).where(
                    PaymentRecord.deleted_at.is_(None),
                    PaymentRecord.customer_id.in_(customer_ids),
                    PaymentRecord.status != "paid",
                )
            )
        )
        .scalars()
        .all()
    )

    order_map: dict[int, list[Any]] = {}
    for order in orders:
        order_map.setdefault(order.customer_id, []).append(order)

    opp_map: dict[int, int] = {}
    for opp in opportunities:
        opp_map[opp.customer_id] = opp_map.get(opp.customer_id, 0) + 1

    overdue_map: dict[int, int] = {}
    followup_last_map: dict[int, datetime] = {}
    for fu in followups:
        if fu.planned_at and fu.planned_at < now and fu.status != "completed":
            overdue_map[fu.customer_id] = overdue_map.get(fu.customer_id, 0) + 1
        created = to_utc(fu.created_at)
        if created and (
            fu.customer_id not in followup_last_map
            or created > followup_last_map[fu.customer_id]
        ):
            followup_last_map[fu.customer_id] = created

    outstanding_map: dict[int, float] = {}
    for pay in payments:
        outstanding_map[pay.customer_id] = outstanding_map.get(
            pay.customer_id, 0.0
        ) + safe_float(pay.amount)

    created_items: list[dict[str, Any]] = []
    username = _user.get("username")

    for customer in customers:
        cust_orders = order_map.get(customer.id, [])
        latest_order_at = None
        order_count_90d = 0
        order_amount_180d = 0.0

        for order in cust_orders:
            created_at = to_utc(order.created_at)
            if created_at and (latest_order_at is None or created_at > latest_order_at):
                latest_order_at = created_at
            if created_at and created_at >= now - timedelta(days=90):
                order_count_90d += 1
            if created_at and created_at >= now - timedelta(days=180):
                order_amount_180d += safe_float(order.total_amount)

        last_contact_at = to_utc(customer.last_contacted_at) or followup_last_map.get(
            customer.id
        )
        days_since_contact = days_since(last_contact_at, now)
        last_order_days = days_since(latest_order_at, now)

        open_opportunities = opp_map.get(customer.id, 0)
        overdue_followups = overdue_map.get(customer.id, 0)
        outstanding_amount = outstanding_map.get(customer.id, 0.0)
        credit_limit = safe_float(customer.credit_limit)
        outstanding_ratio = (
            0.0 if credit_limit <= 0 else min(2.0, outstanding_amount / credit_limit)
        )

        churn_risk_score = safe_float(
            (customer.ai_insights or {}).get("churn", {}).get("risk_score")
        )
        if churn_risk_score <= 0:
            churn_risk_score = 45.0

        health_score = safe_float((customer.ai_insights or {}).get("health_score"))
        if health_score <= 0:
            health_score = 55.0

        value_score = derive_value_score(
            customer.level, order_amount_180d, customer.credit_level
        )
        risk_score = derive_risk_score(
            churn_risk_score, last_order_days, overdue_followups, outstanding_ratio
        )
        urgency_score = derive_urgency_score(
            days_since_contact, overdue_followups, open_opportunities
        )
        priority_score = round(
            risk_score * 0.45 + value_score * 0.35 + urgency_score * 0.2, 1
        )

        action = next_action(
            customer_name=customer.name,
            overdue_followups=overdue_followups,
            days_since_contact=days_since_contact,
            open_opportunities=open_opportunities,
            outstanding_ratio=outstanding_ratio,
            outstanding_amount=outstanding_amount,
            risk_score=risk_score,
        )
        due_at = now + timedelta(days=int(action["due_days"]))

        snapshot_payload = {
            "customer_id": customer.id,
            "snapshot_date": now,
            "health_score": health_score,
            "churn_risk_score": churn_risk_score,
            "value_score": value_score,
            "urgency_score": urgency_score,
            "recency_days": days_since_contact,
            "frequency_90d": order_count_90d,
            "monetary_180d": round(order_amount_180d, 2),
            "overdue_followups": overdue_followups,
            "open_opportunities": open_opportunities,
            "outstanding_amount": round(outstanding_amount, 2),
            "feature_payload": {
                "last_order_days": last_order_days,
                "outstanding_ratio": round(outstanding_ratio, 3),
                "credit_limit": credit_limit,
            },
        }

        rec_payload = {
            "customer_id": customer.id,
            "model_version": "rule-v1",
            "action_type": action["action_type"],
            "title": action["title"],
            "reason": action["reason"],
            "confidence": float(action["confidence"]),
            "priority_score": priority_score,
            "expected_impact": action["expected_impact"],
            "due_at": due_at,
            "status": "open",
            "owner": username,
            "context_payload": {
                "risk_score": risk_score,
                "value_score": value_score,
                "urgency_score": urgency_score,
                "days_since_contact": days_since_contact,
                "overdue_followups": overdue_followups,
                "open_opportunities": open_opportunities,
                "outstanding_amount": round(outstanding_amount, 2),
                "order_amount_180d": round(order_amount_180d, 2),
            },
        }

        if body.dry_run:
            created_items.append(
                {
                    "customer_id": customer.id,
                    "customer_name": customer.name,
                    **rec_payload,
                    "snapshot": snapshot_payload,
                }
            )
            continue

        snapshot = CustomerAISnapshotDaily(**snapshot_payload)
        db.add(snapshot)
        await db.flush()

        recommendation = CustomerAIRecommendation(
            snapshot_id=snapshot.id, **rec_payload
        )
        db.add(recommendation)
        await db.flush()

        created_items.append(
            {
                "id": recommendation.id,
                "customer_id": customer.id,
                "customer_name": customer.name,
                **rec_payload,
                "snapshot": snapshot_payload,
            }
        )

    created_items.sort(
        key=lambda item: float(item.get("priority_score", 0)), reverse=True
    )
    preview_items = [
        {
            "id": item.get("id"),
            "customer_id": item["customer_id"],
            "customer_name": item["customer_name"],
            "action_type": item["action_type"],
            "title": item["title"],
            "priority_score": item["priority_score"],
            "due_at": str(item["due_at"]) if item.get("due_at") else None,
            "status": item["status"],
        }
        for item in created_items[:20]
    ]
    return ok(
        {
            "generated": len(created_items),
            "replaced": replaced,
            "items": preview_items,
        }
    )


@router.get("/customer/work-queue")
async def get_work_queue(
    status: str = Query("open"),
    owner: str | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(get_current_user),
):
    from app.models.customer import (
        Customer,
        CustomerAIFeedback,
        CustomerAIRecommendation,
        CustomerAISnapshotDaily,
    )

    base = (
        select(
            CustomerAIRecommendation,
            Customer.name,
            Customer.level,
            Customer.industry,
            Customer.owner,
            CustomerAISnapshotDaily,
        )
        .join(Customer, Customer.id == CustomerAIRecommendation.customer_id)
        .outerjoin(
            CustomerAISnapshotDaily,
            CustomerAISnapshotDaily.id == CustomerAIRecommendation.snapshot_id,
        )
        .where(
            CustomerAIRecommendation.deleted_at.is_(None),
            Customer.deleted_at.is_(None),
        )
    )
    count_base = select(func.count(CustomerAIRecommendation.id)).where(
        CustomerAIRecommendation.deleted_at.is_(None)
    )
    if status != "all":
        base = base.where(CustomerAIRecommendation.status == status)
        count_base = count_base.where(CustomerAIRecommendation.status == status)
    if owner:
        base = base.where(CustomerAIRecommendation.owner == owner)
        count_base = count_base.where(CustomerAIRecommendation.owner == owner)

    total = (await db.execute(count_base)).scalar() or 0
    rows = (
        await db.execute(
            base.order_by(
                CustomerAIRecommendation.priority_score.desc(),
                CustomerAIRecommendation.created_at.desc(),
            )
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
    ).all()

    rec_ids = [row[0].id for row in rows]
    feedback_map: dict[int, int] = {}
    if rec_ids:
        fb_rows = (
            await db.execute(
                select(
                    CustomerAIFeedback.recommendation_id,
                    func.count(CustomerAIFeedback.id),
                )
                .where(
                    CustomerAIFeedback.deleted_at.is_(None),
                    CustomerAIFeedback.recommendation_id.in_(rec_ids),
                )
                .group_by(CustomerAIFeedback.recommendation_id)
            )
        ).all()
        feedback_map = {int(r[0]): int(r[1]) for r in fb_rows}

    items: list[dict[str, Any]] = []
    for (
        rec,
        customer_name,
        customer_level,
        customer_industry,
        customer_owner,
        snapshot,
    ) in rows:
        snapshot_payload = {
            "health_score": snapshot.health_score if snapshot else None,
            "churn_risk_score": snapshot.churn_risk_score if snapshot else None,
            "value_score": snapshot.value_score if snapshot else None,
            "urgency_score": snapshot.urgency_score if snapshot else None,
            "recency_days": snapshot.recency_days if snapshot else None,
            "frequency_90d": snapshot.frequency_90d if snapshot else None,
            "monetary_180d": snapshot.monetary_180d if snapshot else None,
            "overdue_followups": snapshot.overdue_followups if snapshot else None,
            "open_opportunities": snapshot.open_opportunities if snapshot else None,
            "outstanding_amount": snapshot.outstanding_amount if snapshot else None,
        }
        items.append(
            {
                "id": rec.id,
                "customer_id": rec.customer_id,
                "customer_name": customer_name,
                "customer_level": customer_level,
                "customer_industry": customer_industry,
                "customer_owner": customer_owner,
                "action_type": rec.action_type,
                "title": rec.title,
                "reason": rec.reason,
                "confidence": rec.confidence,
                "priority_score": rec.priority_score,
                "expected_impact": rec.expected_impact,
                "due_at": str(rec.due_at) if rec.due_at else None,
                "status": rec.status,
                "owner": rec.owner,
                "model_version": rec.model_version,
                "snapshot": snapshot_payload,
                "feedback_count": feedback_map.get(rec.id, 0),
                "created_at": str(rec.created_at) if rec.created_at else None,
            }
        )

    status_rows = (
        await db.execute(
            select(
                CustomerAIRecommendation.status, func.count(CustomerAIRecommendation.id)
            )
            .where(CustomerAIRecommendation.deleted_at.is_(None))
            .group_by(CustomerAIRecommendation.status)
        )
    ).all()
    status_stats = {str(row[0]): int(row[1]) for row in status_rows}

    return ok(
        {
            "list": items,
            "total": total,
            "page": page,
            "page_size": page_size,
            "status_stats": status_stats,
        }
    )


@router.post("/customer/recommendation/{recommendation_id}/status")
async def update_recommendation_status(
    recommendation_id: int,
    body: WorkQueueStatusRequest,
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(get_current_user),
):
    from app.models.customer import CustomerAIAction, CustomerAIRecommendation

    rec = (
        await db.execute(
            select(CustomerAIRecommendation).where(
                CustomerAIRecommendation.id == recommendation_id,
                CustomerAIRecommendation.deleted_at.is_(None),
            )
        )
    ).scalar_one_or_none()
    if rec is None:
        return fail("Recommendation not found", 404)

    rec.status = body.status
    if body.owner:
        rec.owner = body.owner
    elif not rec.owner:
        rec.owner = _user.get("username")

    if body.status == "done":
        action = CustomerAIAction(
            recommendation_id=rec.id,
            customer_id=rec.customer_id,
            action_type=rec.action_type,
            payload=rec.context_payload,
            status="done",
            assignee=rec.owner,
            executed_at=datetime.now(timezone.utc),
            result_summary="Marked done from work queue",
        )
        db.add(action)
    await db.flush()
    return ok({"id": rec.id, "status": rec.status, "owner": rec.owner})


@router.post("/customer/recommendation/{recommendation_id}/feedback")
async def submit_recommendation_feedback(
    recommendation_id: int,
    body: WorkQueueFeedbackRequest,
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(get_current_user),
):
    from app.models.customer import CustomerAIFeedback, CustomerAIRecommendation

    rec = (
        await db.execute(
            select(CustomerAIRecommendation).where(
                CustomerAIRecommendation.id == recommendation_id,
                CustomerAIRecommendation.deleted_at.is_(None),
            )
        )
    ).scalar_one_or_none()
    if rec is None:
        return fail("Recommendation not found", 404)

    feedback = CustomerAIFeedback(
        recommendation_id=rec.id,
        customer_id=rec.customer_id,
        verdict=body.verdict,
        usefulness=body.usefulness,
        outcome=body.outcome,
        revenue_impact=body.revenue_impact,
        cost_impact=body.cost_impact,
        comment=body.comment,
        operator=_user.get("username"),
    )
    db.add(feedback)

    if body.verdict == "adopted":
        rec.status = "done"
    elif body.verdict == "rejected":
        rec.status = "dismissed"
    else:
        rec.status = "in_progress"

    await db.flush()
    return ok({"recommendation_id": rec.id, "status": rec.status})
