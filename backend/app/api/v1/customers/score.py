"""Customers — batch AI scoring endpoint.

Separate from the per-customer read paths because ``batch_score_ai``
runs a multi-second agent loop over hundreds of customers and shares
no logic with the lightweight stats endpoints.
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.api.v1.ai.customer._cleaners import days_since, safe_float, to_utc
from app.api.v1.customers.stats import _rfm_bucket as rfm_bucket
from app.database import get_db
from app.models.customer import Customer, CustomerAIRecommendation, CustomerFollowUp
from app.models.sales import Opportunity, SalesOrder
from app.schemas.common import ok

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/customers", tags=["customers"])

class BatchScoreAIRequest(BaseModel):
    ids: list[int] = Field(default_factory=list)


# --- Dashboard Stats ---

@router.post("/batch-score-ai")
async def batch_score_ai(
    body: BatchScoreAIRequest,
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(get_current_user),
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
            "amount": safe_float(row[2]),
            "last_order_at": to_utc(row[3]),
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
    followup_last_map = {int(row[0]): to_utc(row[1]) for row in latest_followup_rows}

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
            total_amount = safe_float(stats.get("amount"))
            last_order_at = stats.get("last_order_at")
            order_count_90d = int(stats.get("count_90d", 0))

            last_contact_at = to_utc(customer.last_contacted_at) or followup_last_map.get(customer.id)
            days_since_contact = days_since(last_contact_at, now)
            days_since_order = days_since(last_order_at, now)
            open_opportunities = opp_map.get(customer.id, 0)

            recency, frequency, monetary, tier = rfm_bucket(days_since_contact, order_count, total_amount)

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


__all__ = ["router"]
