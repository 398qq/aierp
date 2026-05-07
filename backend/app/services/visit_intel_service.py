"""Visit Intelligence Service — AI-powered visit report, sentiment analysis, and team effectiveness evaluation."""

import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.customer import Customer
from app.models.sales import Opportunity, SalesOrder
from app.models.transaction import Visit
from app.services.ai.client import ai_client
from app.services.ai.prompts import (
    visit_effectiveness_prompt,
    visit_report_prompt,
    visit_sentiment_prompt,
)

logger = logging.getLogger(__name__)


async def generate_visit_report(db: AsyncSession, visit_id: int) -> dict:
    """Generate a structured AI report from a single visit record.

    Queries the Visit joined with Customer for the customer name, then
    calls the AI via visit_report_prompt to produce a structured report
    summarising content, result, key_points, next_plan, and purpose.
    """
    output_schema = {
        "visit_summary": "string: 2-3 sentence summary",
        "key_achievements": "list of strings",
        "customer_sentiment": "string: 积极/中性/消极",
        "engagement_level": "string: 高/中/低",
        "product_interest": "string: assessment of product interest",
        "opportunity_signals": "list of strings",
        "risk_signals": "list of strings",
        "action_items": "list of dicts: {action, priority, deadline}",
        "followup_recommendation": "string",
        "effectiveness_score": "integer 0-100",
    }

    try:
        result = await db.execute(
            select(
                Visit.id,
                Visit.visit_no,
                Visit.title,
                Visit.visit_date,
                Visit.type,
                Visit.status,
                Visit.stage,
                Visit.purpose,
                Visit.main_product,
                Visit.content,
                Visit.result,
                Visit.next_plan,
                Visit.key_points,
                Visit.followup_date,
                Customer.name,
            )
            .join(Customer, Visit.customer_id == Customer.id)
            .where(Visit.id == visit_id, Visit.deleted_at.is_(None))
        )
        row = result.one_or_none()
        if not row:
            return {"error": f"Visit {visit_id} not found"}

        visit_data = {
            "customer_name": row[14] or "未知",
            "visit_date": str(row[3]) if row[3] else "无数据",
            "type": row[4] or "无数据",
            "purpose": row[7] or "无数据",
            "main_product": row[8] or "无数据",
            "content": row[9] or "无内容",
            "result": row[10] or "无结果",
            "key_points": row[12] or "无",
            "next_plan": row[11] or "无",
        }

        messages = [
            {"role": "system", "content": "你是一个销售拜访分析专家。分析拜访记录，生成结构化报告并提供可执行建议。"},
            {"role": "user", "content": visit_report_prompt(visit_data)},
        ]

        return await ai_client.chat_structured(messages, output_schema)

    except Exception as e:
        logger.error(f"generate_visit_report failed for visit {visit_id}: {e}")
        return {"error": f"AI analysis failed: {e}"}


async def analyze_visit_sentiment(db: AsyncSession, visit_id: int) -> dict:
    """Analyze customer sentiment by combining current visit with history.

    Fetches the target Visit with its Customer info, then gathers:
    - The last 5 visits for the same customer as a textual summary
    - Purchase trend: order count and total in the last 180 days
    - Relationship duration from Customer.created_at

    All context is fed to visit_sentiment_prompt for AI evaluation.
    """
    output_schema = {
        "overall_sentiment": "string: 满意/中性/不满",
        "sentiment_score": "integer 0-100",
        "key_concerns": "list of strings",
        "satisfaction_indicators": "list of strings",
        "dissatisfaction_signals": "list of strings",
        "relationship_trend": "string: 改善/稳定/恶化",
        "loyalty_risk": "string: 低/中/高",
        "improvement_suggestions": "list of strings",
    }

    try:
        result = await db.execute(
            select(
                Visit.id,
                Visit.visit_no,
                Visit.title,
                Visit.visit_date,
                Visit.type,
                Visit.status,
                Visit.content,
                Visit.result,
                Visit.key_points,
                Visit.next_plan,
                Visit.customer_id,
                Customer.name,
                Customer.level,
                Customer.created_at,
            )
            .join(Customer, Visit.customer_id == Customer.id)
            .where(Visit.id == visit_id, Visit.deleted_at.is_(None))
        )
        row = result.one_or_none()
        if not row:
            return {"error": f"Visit {visit_id} not found"}

        customer_id = row[10]
        customer_name = row[11] or "未知"
        customer_created_at = row[13]

        # Relationship duration in years
        if customer_created_at:
            if customer_created_at.tzinfo is None:
                customer_created_at = customer_created_at.replace(tzinfo=timezone.utc)
            delta = datetime.now(timezone.utc) - customer_created_at
            years = delta.days // 365
            relationship_years = f"{years}年" if years >= 0 else "不足1年"
        else:
            relationship_years = "无数据"

        # Last 5 historical visits for the same customer (exclude current)
        history_result = await db.execute(
            select(
                Visit.visit_date,
                Visit.type,
                Visit.content,
                Visit.result,
                Visit.key_points,
            )
            .where(
                Visit.customer_id == customer_id,
                Visit.id != visit_id,
                Visit.deleted_at.is_(None),
            )
            .order_by(Visit.visit_date.desc())
            .limit(5)
        )
        history_rows = history_result.all()
        visit_history = "\n".join(
            f"- [{h[0]}] {h[1] or '未知类型'}: {h[3] or '无结果'}"
            for h in history_rows
        ) or "无历史拜访"

        # Purchase trend: orders in last 180 days
        since = datetime.now(timezone.utc) - timedelta(days=180)
        order_result = await db.execute(
            select(
                func.count(SalesOrder.id),
                func.coalesce(func.sum(SalesOrder.total_amount), 0),
            )
            .where(
                SalesOrder.customer_id == customer_id,
                SalesOrder.created_at >= since,
                SalesOrder.deleted_at.is_(None),
            )
        )
        order_row = order_result.one()
        order_count = order_row[0]
        order_total = float(order_row[1])
        purchase_trend = (
            f"近180天共{order_count}笔订单，总额{order_total:,.2f}元"
            if order_count else "近180天无订单"
        )

        visit_data = {
            "customer_name": customer_name,
            "content": row[6] or "无",
            "result": row[7] or "无",
            "key_points": row[8] or "无",
            "visit_history": visit_history,
            "relationship_years": relationship_years,
            "purchase_trend": purchase_trend,
        }

        messages = [
            {"role": "system", "content": "你是一个客户交互分析师。通过分析拜访记录、历史互动和采购趋势评估客户情感和关系健康度。"},
            {"role": "user", "content": visit_sentiment_prompt(visit_data)},
        ]

        return await ai_client.chat_structured(messages, output_schema)

    except Exception as e:
        logger.error(f"analyze_visit_sentiment failed for visit {visit_id}: {e}")
        return {"error": f"AI analysis failed: {e}"}


async def evaluate_visit_effectiveness(db: AsyncSession) -> dict:
    """Evaluate visit-team effectiveness across the last 30 days.

    Queries the database for:
    - Total visits, visits per salesperson (grouped by Customer.owner)
    - Distinct customers visited
    - High-value (level A/B) customer coverage
    - Unvisited customer count
    - Opportunities created within 7 days after a visit
    - Revenue from visited customers

    Feeds the aggregated data into visit_effectiveness_prompt and
    returns AI-generated insights together with raw statistics under _stats.
    """
    output_schema = {
        "effectiveness_score": "integer 0-100",
        "coverage_assessment": "string (1-2 sentences)",
        "productivity_assessment": "string (1-2 sentences)",
        "high_performers": "list of strings",
        "gaps": "list of strings",
        "optimization_suggestions": "list of strings (3 items)",
        "visit_frequency_recommendation": "string",
    }

    try:
        now = datetime.now(timezone.utc)
        thirty_days_ago = now - timedelta(days=30)

        # 1. Total visits
        total_result = await db.execute(
            select(func.count(Visit.id))
            .where(Visit.visit_date >= thirty_days_ago, Visit.deleted_at.is_(None))
        )
        total_visits = total_result.scalar() or 0

        # 2. Visits per person (grouped by Customer.owner)
        per_person_result = await db.execute(
            select(
                Customer.owner,
                func.count(Visit.id),
            )
            .join(Customer, Visit.customer_id == Customer.id)
            .where(Visit.visit_date >= thirty_days_ago, Visit.deleted_at.is_(None))
            .group_by(Customer.owner)
        )
        per_person_rows = per_person_result.all()
        unique_persons = len([r for r in per_person_rows if r[0]])
        visits_per_person = round(total_visits / unique_persons, 1) if unique_persons else 0

        # 3. Distinct customers visited
        visited_customers_result = await db.execute(
            select(func.count(func.distinct(Visit.customer_id)))
            .where(Visit.visit_date >= thirty_days_ago, Visit.deleted_at.is_(None))
        )
        visited_customers = visited_customers_result.scalar() or 0

        # 4. High-value customer coverage (level A or B)
        high_value_total_result = await db.execute(
            select(func.count(Customer.id))
            .where(Customer.level.in_(["A", "B"]), Customer.deleted_at.is_(None))
        )
        high_value_total = high_value_total_result.scalar() or 0

        high_value_visited_result = await db.execute(
            select(func.count(func.distinct(Visit.customer_id)))
            .where(
                Visit.visit_date >= thirty_days_ago,
                Visit.deleted_at.is_(None),
            )
            .where(
                Visit.customer_id.in_(
                    select(Customer.id).where(
                        Customer.level.in_(["A", "B"]),
                        Customer.deleted_at.is_(None),
                    )
                )
            )
        )
        high_value_visited = high_value_visited_result.scalar() or 0
        high_value_coverage = round(high_value_visited / high_value_total * 100, 1) if high_value_total else 0

        # 5. Unvisited customers (no visit in past 30 days)
        unvisited_result = await db.execute(
            select(func.count(Customer.id))
            .where(
                Customer.deleted_at.is_(None),
                Customer.id.notin_(
                    select(Visit.customer_id).where(
                        Visit.visit_date >= thirty_days_ago,
                        Visit.deleted_at.is_(None),
                    )
                ),
            )
        )
        unvisited_count = unvisited_result.scalar() or 0

        # 6. Opportunities created within 7 days after a visit
        opp_after_visit_result = await db.execute(
            select(func.count(Opportunity.id))
            .where(
                Opportunity.deleted_at.is_(None),
                Opportunity.id.in_(
                    select(Opportunity.id)
                    .join(Visit, Opportunity.customer_id == Visit.customer_id)
                    .where(
                        Visit.visit_date >= thirty_days_ago,
                        Visit.deleted_at.is_(None),
                        Opportunity.created_at > Visit.visit_date,
                        Opportunity.created_at <= Visit.visit_date + text("interval '7 days'"),
                    )
                ),
            )
        )
        new_opps_after_visit = opp_after_visit_result.scalar() or 0

        opp_conversion_rate = round(new_opps_after_visit / total_visits * 100, 1) if total_visits else 0

        # 7. Revenue from visited customers (sales orders in last 30 days)
        revenue_result = await db.execute(
            select(func.coalesce(func.sum(SalesOrder.total_amount), 0))
            .where(
                SalesOrder.created_at >= thirty_days_ago,
                SalesOrder.deleted_at.is_(None),
                SalesOrder.customer_id.in_(
                    select(func.distinct(Visit.customer_id))
                    .where(Visit.visit_date >= thirty_days_ago, Visit.deleted_at.is_(None))
                ),
            )
        )
        revenue_after_visit = float(revenue_result.scalar() or 0)

        # 8. Average visit interval (days between visits per customer)
        avg_visit_interval = (
            round(30 / (total_visits / visited_customers), 1)
            if visited_customers and total_visits else 30
        )

        summary_data = {
            "total_visits": total_visits,
            "visits_per_person": visits_per_person,
            "opp_conversion_rate": opp_conversion_rate,
            "avg_visit_interval": avg_visit_interval,
            "visited_customers": visited_customers,
            "high_value_coverage": high_value_coverage,
            "unvisited_count": unvisited_count,
            "new_opps_after_visit": new_opps_after_visit,
            "revenue_after_visit": revenue_after_visit,
            "avg_visit_cost": "无数据",
        }

        messages = [
            {"role": "system", "content": "你是一个销售效率分析专家。分析销售团队拜访数据，评估效率、覆盖面和产出，给出优化建议。"},
            {"role": "user", "content": visit_effectiveness_prompt(summary_data)},
        ]

        ai_result = await ai_client.chat_structured(messages, output_schema)
        ai_result["_stats"] = summary_data
        return ai_result

    except Exception as e:
        logger.error(f"evaluate_visit_effectiveness failed: {e}")
        return {"error": f"AI analysis failed: {e}", "_stats": {}}
