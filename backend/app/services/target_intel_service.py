"""Target Intelligence Service — AI-driven sales target recommendations, attainment
predictions, and early-warning scans. Backed by real DB queries and structured LLM calls."""

import datetime
import json
import logging

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.customer import Customer
from app.models.finance import SalesTarget
from app.models.sales import Opportunity, SalesOrder
from app.models.user import User
from app.services.ai.client import ai_client
from app.services.ai.prompts import (
    SALES_AGENT_SYSTEM,
    attainment_prediction_prompt,
    target_early_warning_prompt,
    target_recommendation_prompt,
)

logger = logging.getLogger(__name__)

_TODAY = datetime.date.today
_UTC_NOW = datetime.datetime.utcnow


# ---------------------------------------------------------------------------
# Schema definitions for structured AI output
# ---------------------------------------------------------------------------

_RECOMMENDATION_SCHEMA = {
    "recommended_target": "number: suggested target amount",
    "conservative_target": "number: conservative floor",
    "ambitious_target": "number: stretch / aspirational target",
    "confidence": "integer 0-100: confidence in recommendation",
    "growth_rate": "number: suggested growth rate in percentage",
    "key_drivers": ["string: growth driver"],
    "risk_factors": ["string: risks that may prevent attainment"],
    "strategy": ["string: concrete attainment strategies"],
}

_ATTAINMENT_SCHEMA = {
    "predicted_attainment": "number: predicted attainment percentage",
    "predicted_amount": "number: predicted completion amount",
    "gap": "number: projected shortfall (0 if over-achieving)",
    "confidence": "integer 0-100: prediction confidence",
    "trend": "string: 超额 / 达成 / 接近 / 差距大",
    "key_opportunities": ["string: supporting pipeline opportunities"],
    "catch_up_plan": ["string: concrete catch-up steps"],
    "early_warning": "boolean: whether early-warning is needed",
}

_EARLY_WARNING_SCHEMA = {
    "overall_status": "string: 健康 / 关注 / 预警",
    "risk_targets": [
        {
            "user_name": "string",
            "target": "number",
            "actual": "number",
            "attainment_pct": "number",
            "risk_level": "string: 低 / 中 / 高",
            "reason": "string",
        }
    ],
    "top_performers": [
        {"user_name": "string", "attainment_pct": "number", "highlight": "string"}
    ],
    "systemic_issues": ["string: issues affecting team-wide attainment"],
    "recommendations": ["string: management recommendations"],
    "forecast_attainment": "number: projected final attainment percentage",
}


# ---------------------------------------------------------------------------
# Helper queries
# ---------------------------------------------------------------------------


async def _get_user_name(db: AsyncSession, user_id: int) -> str:
    result = await db.execute(select(User.username).where(User.id == user_id))
    row = result.scalar_one_or_none()
    return row or f"用户#{user_id}"


async def _count_active_customers(db: AsyncSession, user_id: int) -> int:
    """Customers with this user as owner and not soft-deleted."""
    result = await db.execute(
        select(func.count(Customer.id)).where(
            Customer.owner == user_id, Customer.deleted_at.is_(None)
        )
    )
    return result.scalar() or 0


# ---------------------------------------------------------------------------
# Function 1: recommend_targets
# ---------------------------------------------------------------------------


async def recommend_targets(db: AsyncSession, user_id: int) -> dict:
    """Recommend monthly / quarterly target for a salesperson.

    Gathers historical SalesTarget rows, actual sales from SalesOrder,
    pipeline Opportunity totals, and customer counts, then calls the LLM
    with ``target_recommendation_prompt``.
    """

    user_name = await _get_user_name(db, user_id)

    # -- Historical SalesTargets (past 12 completed periods, newest first) --
    target_rows = await db.execute(
        select(SalesTarget)
        .where(
            SalesTarget.user_id == user_id,
            SalesTarget.status == "active",
            SalesTarget.deleted_at.is_(None),
        )
        .order_by(SalesTarget.period_start.desc().nullslast())
        .limit(12)
    )
    targets = target_rows.scalars().all()

    last_target = float(targets[0].target_amount) if targets else 0
    last_actual = float(targets[0].actual_amount) if targets else 0
    last_attainment = round(last_actual / last_target * 100, 1) if last_target else 0

    monthly_totals = [float(t.actual_amount) for t in targets if t.actual_amount]
    monthly_avg = (
        round(sum(monthly_totals) / len(monthly_totals), 2) if monthly_totals else 0
    )

    # YoY growth: compare this-year vs last-year same month
    yoy_growth = 0
    if targets:
        six_months = [t for t in targets if t.period_start]
        if len(six_months) >= 2:
            recent = float(six_months[0].actual_amount or 0)
            older = float(six_months[-1].actual_amount or 0)
            if older:
                yoy_growth = round((recent - older) / older * 100, 1)

    # -- Pipeline (open opportunities) --
    pipeline_rows = await db.execute(
        select(func.coalesce(func.sum(Opportunity.amount), 0)).where(
            Opportunity.created_at.isnot(None),
            Opportunity.deleted_at.is_(None),
            Opportunity.stage.notin_(["won", "lost"]),
        )
    )
    pipeline_value = round(float(pipeline_rows.scalar() or 0), 2)

    # Convert won rate from recent opportunities
    won_rows = await db.execute(
        select(
            func.count(Opportunity.id),
            func.count(Opportunity.id).filter(Opportunity.stage == "won"),
        ).where(
            Opportunity.deleted_at.is_(None),
            Opportunity.created_at >= _UTC_NOW() - datetime.timedelta(days=180),
        )
    )
    total_opp, won_opp = won_rows.one()
    conversion_rate = round(won_opp / total_opp * 100, 1) if total_opp else 0

    expected_close = round(pipeline_value * (conversion_rate / 100), 2)

    customer_count = await _count_active_customers(db, user_id)
    active_customers = customer_count  # simplified — could add recent-order filter

    market_growth = 5.0  # placeholder; could pull from external data

    # -- Build prompt data & call AI --
    prompt_data = {
        "user_name": user_name,
        "last_target": last_target,
        "last_actual": last_actual,
        "last_attainment": last_attainment,
        "monthly_avg": monthly_avg,
        "yoy_growth": yoy_growth,
        "pipeline_value": pipeline_value,
        "conversion_rate": conversion_rate,
        "expected_close": expected_close,
        "customer_count": customer_count,
        "active_customers": active_customers,
        "market_growth": market_growth,
    }

    try:
        result = await ai_client.chat_structured(
            [
                {"role": "system", "content": SALES_AGENT_SYSTEM},
                {"role": "user", "content": target_recommendation_prompt(prompt_data)},
            ],
            _RECOMMENDATION_SCHEMA,
        )
        result["_query_data"] = prompt_data
        return result
    except Exception:
        logger.exception("recommend_targets AI call failed")
        return {
            "recommended_target": monthly_avg * 1.1,
            "conservative_target": monthly_avg * 0.9,
            "ambitious_target": monthly_avg * 1.3,
            "confidence": 30,
            "growth_rate": 10.0,
            "key_drivers": [],
            "risk_factors": [],
            "strategy": [],
            "_query_data": prompt_data,
            "_error": "AI analysis unavailable",
        }


# ---------------------------------------------------------------------------
# Function 2: predict_attainment
# ---------------------------------------------------------------------------


async def predict_attainment(db: AsyncSession, target_id: int) -> dict:
    """Predict whether a specific SalesTarget will be achieved.

    Queries the target row, MTD sales from SalesOrder, recent monthly
    averages, and pipeline expected conversion, then calls the LLM via
    ``attainment_prediction_prompt``.
    """

    # -- Load target --
    target = await db.get(SalesTarget, target_id)
    if target is None:
        return {"error": f"SalesTarget #{target_id} not found"}

    target_amount = float(target.target_amount)
    actual_amount = float(target.actual_amount or 0)
    attainment_pct = (
        round(actual_amount / target_amount * 100, 1) if target_amount else 0
    )
    user_name = await _get_user_name(db, target.user_id)

    # -- Remaining days --
    now = _UTC_NOW()
    remaining_days = 0
    if target.period_end:
        remaining_days = max(0, (target.period_end - now).days)

    # -- MTD sales --
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    mtd_result = await db.execute(
        select(func.coalesce(func.sum(SalesOrder.total_amount), 0)).where(
            SalesOrder.created_at >= month_start,
            SalesOrder.status.in_(["confirmed", "delivered", "completed"]),
            SalesOrder.deleted_at.is_(None),
        )
    )
    mtd_amount = round(float(mtd_result.scalar() or 0), 2)

    # -- Recent monthly averages (last 3 completed months) --
    three_months_ago = now - datetime.timedelta(days=90)
    recent_result = await db.execute(
        select(func.coalesce(func.sum(SalesOrder.total_amount), 0)).where(
            SalesOrder.created_at >= three_months_ago,
            SalesOrder.status.in_(["confirmed", "delivered", "completed"]),
            SalesOrder.deleted_at.is_(None),
        )
    )
    recent_total = float(recent_result.scalar() or 0)
    recent_monthly_avg = round(recent_total / 3, 2)

    # MoM growth: compare current MTD / days_elapsed to last month
    mom_growth = 0.0
    prev_month_start = (month_start - datetime.timedelta(days=1)).replace(day=1)
    prev_month_result = await db.execute(
        select(func.coalesce(func.sum(SalesOrder.total_amount), 0)).where(
            SalesOrder.created_at >= prev_month_start,
            SalesOrder.created_at < month_start,
            SalesOrder.status.in_(["confirmed", "delivered", "completed"]),
            SalesOrder.deleted_at.is_(None),
        )
    )
    prev_month = float(prev_month_result.scalar() or 0)
    days_elapsed = max(1, now.day)
    projected_current = (mtd_amount / days_elapsed) * 30 if mtd_amount else 0
    if prev_month:
        mom_growth = round((projected_current - prev_month) / prev_month * 100, 1)

    # -- Pipeline opportunities for this target's user --
    pipeline_rows = await db.execute(
        select(
            Opportunity.name,
            Opportunity.amount,
            Opportunity.stage,
            Opportunity.probability,
        ).where(
            Opportunity.deleted_at.is_(None),
            Opportunity.stage.notin_(["won", "lost"]),
        )
    )
    pipeline_opps = pipeline_rows.all()
    pipeline_opportunities = [
        {"name": r[0], "amount": float(r[1] or 0), "stage": r[2], "probability": r[3]}
        for r in pipeline_opps
    ]
    # Expected conversion = sum(amount * probability)
    expected_conversion = round(
        sum(
            float(o.amount or 0) * (int(o.probability or 0) / 100)
            for o in pipeline_opps
        ),
        2,
    )

    prompt_data = {
        "target_amount": target_amount,
        "actual_amount": actual_amount,
        "attainment_pct": attainment_pct,
        "remaining_days": remaining_days,
        "recent_monthly_avg": recent_monthly_avg,
        "mtd_amount": mtd_amount,
        "mom_growth": mom_growth,
        "pipeline_opportunities": json.dumps(
            pipeline_opportunities, ensure_ascii=False, default=str
        ),
        "expected_conversion": expected_conversion,
    }

    try:
        result = await ai_client.chat_structured(
            [
                {"role": "system", "content": SALES_AGENT_SYSTEM},
                {"role": "user", "content": attainment_prediction_prompt(prompt_data)},
            ],
            _ATTAINMENT_SCHEMA,
        )
        result["_query_data"] = prompt_data
        result["user_name"] = user_name
        return result
    except Exception:
        logger.exception("predict_attainment AI call failed")
        return {
            "predicted_attainment": attainment_pct,
            "predicted_amount": actual_amount + expected_conversion,
            "gap": max(0, target_amount - actual_amount - expected_conversion),
            "confidence": 30,
            "trend": "差距大"
            if attainment_pct < 70
            else "接近"
            if attainment_pct < 95
            else "达成",
            "key_opportunities": [],
            "catch_up_plan": [],
            "early_warning": attainment_pct < 60,
            "_query_data": prompt_data,
            "user_name": user_name,
            "_error": "AI analysis unavailable",
        }


# ---------------------------------------------------------------------------
# Function 3: scan_target_early_warning
# ---------------------------------------------------------------------------


async def scan_target_early_warning(db: AsyncSession) -> dict:
    """Scan all active SalesTargets and generate an early-warning dashboard.

    Queries every currently-active target, computes overall company
    attainment vs time progress, and calls the LLM via
    ``target_early_warning_prompt``.
    """

    now = _UTC_NOW()

    # -- All active targets with user info --
    target_rows = await db.execute(
        select(
            SalesTarget.id,
            SalesTarget.user_id,
            SalesTarget.target_amount,
            SalesTarget.actual_amount,
            SalesTarget.period_start,
            SalesTarget.period_end,
            SalesTarget.target_type,
            User.username,
        )
        .join(User, User.id == SalesTarget.user_id)
        .where(
            SalesTarget.status == "active",
            SalesTarget.deleted_at.is_(None),
        )
    )
    rows = target_rows.all()

    if not rows:
        return {
            "overall_status": "健康",
            "risk_targets": [],
            "top_performers": [],
            "systemic_issues": ["暂无活跃销售目标"],
            "recommendations": ["请设置销售目标后再进行预警分析"],
            "forecast_attainment": 0,
        }

    # -- Build per-user summary --
    user_summaries: list[dict] = []
    company_target = 0.0
    company_actual = 0.0

    for r in rows:
        t_id, u_id, t_amt, a_amt, p_start, p_end, t_type, username = r
        amt = float(a_amt or 0)
        tgt = float(t_amt or 0)
        pct = round(amt / tgt * 100, 1) if tgt else 0
        company_target += tgt
        company_actual += amt
        user_summaries.append(
            {
                "id": t_id,
                "user_id": u_id,
                "user_name": username,
                "target": tgt,
                "actual": amt,
                "attainment_pct": pct,
                "target_type": t_type,
                "period_start": p_start.isoformat() if p_start else None,
                "period_end": p_end.isoformat() if p_end else None,
            }
        )

    overall_attainment = (
        round(company_actual / company_target * 100, 1) if company_target else 0
    )

    # Time progress: compute average elapsed fraction across all targets
    time_progress = 0.0
    periods_with_dates = 0
    for r in rows:
        p_start, p_end = r[4], r[5]
        if p_start and p_end:
            total_dur = (p_end - p_start).total_seconds()
            elapsed = (now - p_start).total_seconds()
            if total_dur > 0:
                time_progress += min(1.0, max(0.0, elapsed / total_dur))
                periods_with_dates += 1
    if periods_with_dates:
        time_progress = round(time_progress / periods_with_dates * 100, 1)

    targets_summary = json.dumps(user_summaries, ensure_ascii=False)

    prompt_data = {
        "targets_summary": targets_summary,
        "company_target": round(company_target, 2),
        "company_actual": round(company_actual, 2),
        "overall_attainment": overall_attainment,
        "time_progress": time_progress,
    }

    try:
        result = await ai_client.chat_structured(
            [
                {"role": "system", "content": SALES_AGENT_SYSTEM},
                {"role": "user", "content": target_early_warning_prompt(prompt_data)},
            ],
            _EARLY_WARNING_SCHEMA,
        )
        result["_query_data"] = prompt_data
        result["_user_summaries"] = user_summaries
        return result
    except Exception:
        logger.exception("scan_target_early_warning AI call failed")
        # Fallback: simple rule-based scan
        risk_targets = [
            {
                "user_name": u["user_name"],
                "target": u["target"],
                "actual": u["actual"],
                "attainment_pct": u["attainment_pct"],
                "risk_level": "高"
                if u["attainment_pct"] < 60
                else "中"
                if u["attainment_pct"] < 80
                else "低",
                "reason": f"达成率仅{u['attainment_pct']}%，时间进度{time_progress}%",
            }
            for u in user_summaries
            if u["attainment_pct"] < 80
        ]
        top_performers = [
            {
                "user_name": u["user_name"],
                "attainment_pct": u["attainment_pct"],
                "highlight": "超额完成",
            }
            for u in user_summaries
            if u["attainment_pct"] >= 100
        ]
        return {
            "overall_status": "预警"
            if overall_attainment < time_progress * 0.8
            else "关注"
            if overall_attainment < time_progress
            else "健康",
            "risk_targets": risk_targets,
            "top_performers": top_performers,
            "systemic_issues": [],
            "recommendations": [],
            "forecast_attainment": overall_attainment,
            "_query_data": prompt_data,
            "_user_summaries": user_summaries,
            "_error": "AI analysis unavailable",
        }
