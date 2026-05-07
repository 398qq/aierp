"""Sales Intelligence Service — AI-powered opportunity scoring, pipeline analysis,
quotation optimization, and cross-sell detection for electronics distribution."""

import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.customer import Customer
from app.models.product import Product
from app.models.sales import Opportunity, Quotation, QuotationItem, SalesOrder, SalesOrderItem
from app.services.ai.client import ai_client
from app.services.ai.prompts import (
    cross_sell_prompt,
    opportunity_score_prompt,
    pipeline_health_prompt,
    quotation_optimize_prompt,
)

logger = logging.getLogger(__name__)

SALES_INTEL_SYSTEM = "你是一个电子元器件分销行业销售策略专家。返回简洁有效的JSON。"


# ---------------------------------------------------------------------------
# 1. score_opportunity — Win probability scoring
# ---------------------------------------------------------------------------


async def score_opportunity(db: AsyncSession, opportunity_id: int) -> dict:
    """AI-powered opportunity scoring: win probability, deal health, competitive position."""
    result = await db.execute(
        select(Opportunity).where(Opportunity.id == opportunity_id, Opportunity.deleted_at.is_(None))
    )
    opp = result.scalar_one_or_none()
    if not opp:
        return {"error": f"机会 #{opportunity_id} 不存在"}

    # Customer context
    cust = None
    if opp.customer_id:
        cust_result = await db.execute(
            select(Customer).where(Customer.id == opp.customer_id, Customer.deleted_at.is_(None))
        )
        cust = cust_result.scalar_one_or_none()

    # Customer order history
    order_count = 0
    total_revenue = 0.0
    if opp.customer_id:
        order_count = (await db.execute(
            select(func.count(SalesOrder.id)).where(
                SalesOrder.customer_id == opp.customer_id,
                SalesOrder.deleted_at.is_(None),
            )
        )).scalar() or 0
        total_revenue = float((await db.execute(
            select(func.coalesce(func.sum(SalesOrder.total_amount), 0)).where(
                SalesOrder.customer_id == opp.customer_id,
                SalesOrder.deleted_at.is_(None),
            )
        )).scalar() or 0)

    # Related quotations (Quotation links to customer, not opportunity)
    quote_count = 0
    if opp.customer_id:
        quote_count = (await db.execute(
            select(func.count(Quotation.id)).where(
                Quotation.customer_id == opp.customer_id,
                Quotation.deleted_at.is_(None),
            )
        )).scalar() or 0

    # Pipeline: other open opportunities for this customer
    other_open = (await db.execute(
        select(func.count(Opportunity.id)).where(
            Opportunity.customer_id == opp.customer_id,
            Opportunity.id != opportunity_id,
            Opportunity.stage.not_in(["won", "lost", "closed"]),
            Opportunity.deleted_at.is_(None),
        )
    )).scalar() or 0

    context_data = {
        "opportunity_name": opp.name,
        "amount": float(opp.amount or 0),
        "stage": opp.stage or "未知",
        "status": opp.stage or "未知",
        "probability": opp.probability or 0,
        "expected_close_date": str(opp.expected_close_date) if opp.expected_close_date else "未知",
        "customer_name": cust.name if cust else "未知",
        "customer_level": cust.level if cust else "未知",
        "customer_industry": cust.industry if cust else "未知",
        "order_count": order_count,
        "total_revenue": total_revenue,
        "quotation_count": quote_count,
        "other_open_opportunities": other_open,
        "days_in_stage": (datetime.now(timezone.utc) - opp.updated_at).days if opp.updated_at else 0,
    }

    output_schema = {
        "win_probability": "integer 0-100",
        "score": "integer 0-100",
        "risk_level": "string: 低/中/高",
        "risk_factors": "list of strings",
        "positive_signals": "list of strings",
        "recommended_actions": "list of strings",
        "next_best_action": "string",
    }

    try:
        ai_result = await ai_client.chat_structured(
            [
                {"role": "system", "content": SALES_INTEL_SYSTEM},
                {"role": "user", "content": opportunity_score_prompt(context_data)},
            ],
            output_schema,
            max_tokens=1024,
        )
        ai_result["context"] = context_data
        return ai_result
    except Exception as e:
        logger.error(f"Opportunity scoring failed #{opportunity_id}: {e}")
        return {
            "win_probability": opp.probability or 50,
            "score": 50,
            "risk_level": "中",
            "risk_factors": [f"AI分析暂时不可用"],
            "positive_signals": [],
            "recommended_actions": [],
            "next_best_action": "请人工评估",
            "context": {"error": str(e)},
        }


# ---------------------------------------------------------------------------
# 2. analyze_pipeline_health — Pipeline health analysis
# ---------------------------------------------------------------------------


async def analyze_pipeline_health(db: AsyncSession) -> dict:
    """AI-powered pipeline health analysis: conversion, velocity, bottleneck detection."""
    now = datetime.now(timezone.utc)
    thirty_days_ago = now - timedelta(days=30)
    ninety_days_ago = now - timedelta(days=90)

    # Open opportunities count and value
    open_opps = (await db.execute(
        select(func.count(Opportunity.id), func.coalesce(func.sum(Opportunity.amount), 0)).where(
            Opportunity.stage.not_in(["won", "lost", "closed"]),
            Opportunity.deleted_at.is_(None),
        )
    )).first()
    total_open = open_opps[0] or 0
    total_value = float(open_opps[1] or 0)

    # Stage distribution
    stage_rows = (await db.execute(
        select(Opportunity.stage, func.count(Opportunity.id), func.coalesce(func.sum(Opportunity.amount), 0))
        .where(Opportunity.stage.not_in(["won", "lost", "closed"]), Opportunity.deleted_at.is_(None))
        .group_by(Opportunity.stage)
    )).all()
    stage_dist = {s or "未知": {"count": c, "value": float(v)} for s, c, v in stage_rows}

    # Won in last 30/90 days
    won_30d = (await db.execute(
        select(func.count(Opportunity.id), func.coalesce(func.sum(Opportunity.amount), 0)).where(
            Opportunity.stage == "won",
            Opportunity.updated_at >= thirty_days_ago,
            Opportunity.deleted_at.is_(None),
        )
    )).first()
    won_90d = (await db.execute(
        select(func.count(Opportunity.id), func.coalesce(func.sum(Opportunity.amount), 0)).where(
            Opportunity.stage == "won",
            Opportunity.updated_at >= ninety_days_ago,
            Opportunity.deleted_at.is_(None),
        )
    )).first()

    # Lost in last 30 days
    lost_30d = (await db.execute(
        select(func.count(Opportunity.id)).where(
            Opportunity.stage == "lost",
            Opportunity.updated_at >= thirty_days_ago,
            Opportunity.deleted_at.is_(None),
        )
    )).scalar() or 0

    # Aging: opportunities stuck > 60 days
    sixty_days_ago = now - timedelta(days=60)
    stuck_count = (await db.execute(
        select(func.count(Opportunity.id)).where(
            Opportunity.stage.not_in(["won", "lost", "closed"]),
            Opportunity.updated_at <= sixty_days_ago,
            Opportunity.deleted_at.is_(None),
        )
    )).scalar() or 0

    # Average deal size
    avg_deal = round(total_value / total_open, 2) if total_open > 0 else 0

    # Win rate
    total_closed = (await db.execute(
        select(func.count(Opportunity.id)).where(
            Opportunity.stage.in_(["won", "lost"]),
            Opportunity.updated_at >= ninety_days_ago,
            Opportunity.deleted_at.is_(None),
        )
    )).scalar() or 1
    win_rate = round((won_90d[0] or 0) / total_closed * 100, 1)

    context_data = {
        "total_open": total_open,
        "total_value": total_value,
        "avg_deal_size": avg_deal,
        "won_30d": won_30d[0] or 0,
        "lost_30d": lost_30d,
        "win_rate_90d": win_rate,
        "stuck_opportunities": stuck_count,
    }

    output_schema = {
        "health_score": "integer 0-100",
        "health_status": "string: 健康/一般/需要关注/严重",
        "pipeline_assessment": "string",
        "bottlenecks": "list of strings",
        "recommendations": "list of strings",
    }

    try:
        ai_result = await ai_client.chat_structured(
            [
                {"role": "system", "content": SALES_INTEL_SYSTEM},
                {"role": "user", "content": pipeline_health_prompt(context_data)},
            ],
            output_schema,
            max_tokens=512,
        )
        ai_result["context"] = context_data
        return ai_result
    except Exception as e:
        logger.error(f"Pipeline health analysis failed: {e}")
        return {
            "health_score": 50,
            "health_status": "一般",
            "pipeline_assessment": f"AI分析暂时不可用",
            "bottlenecks": [],
            "recommendations": [],
            "context": {"error": str(e)},
        }


# ---------------------------------------------------------------------------
# 3. optimize_quotation — Quotation pricing optimization
# ---------------------------------------------------------------------------


async def optimize_quotation(db: AsyncSession, quotation_id: int) -> dict:
    """AI-powered quotation optimization: pricing suggestions, discount analysis,
    win probability at different price points."""
    result = await db.execute(
        select(Quotation).where(Quotation.id == quotation_id, Quotation.deleted_at.is_(None))
    )
    quote = result.scalar_one_or_none()
    if not quote:
        return {"error": f"报价单 #{quotation_id} 不存在"}

    # Items
    items_result = await db.execute(
        select(QuotationItem).where(QuotationItem.quotation_id == quotation_id, QuotationItem.deleted_at.is_(None))
    )
    items = items_result.scalars().all()

    items_data = []
    total_price = 0.0
    for item in items:
        price = float(item.unit_price or 0)
        items_data.append({
            "product_id": item.product_id,
            "quantity": item.quantity,
            "unit_price": price,
            "amount": float(item.amount or 0),
        })
        total_price += price * item.quantity

    # Customer info if available
    cust_name = "未知"
    cust_level = "未知"
    if quote.customer_id:
        cust_result = await db.execute(
            select(Customer).where(Customer.id == quote.customer_id, Customer.deleted_at.is_(None))
        )
        cust = cust_result.scalar_one_or_none()
        if cust:
            cust_name = cust.name
            cust_level = cust.level or "未知"

    context_data = {
        "quotation_no": quote.quotation_no or f"Q-{quote.id}",
        "customer_name": cust_name,
        "customer_level": cust_level,
        "total_amount": float(quote.total_amount or total_price),
        "items": str(items_data),
        "status": quote.status or "draft",
    }

    output_schema = {
        "optimal_total": "number: 建议总价",
        "discount_room": "number: 可让利空间(%)",
        "win_probability_current": "integer: 当前价格赢单概率",
        "win_probability_optimal": "integer: 优化后赢单概率",
        "pricing_strategy": "string: 定价策略建议",
        "item_adjustments": "list of dicts: {product_name: string, current_price: number, suggested_price: number, reason: string}",
        "negotiation_guardrails": "string: 谈判底线建议",
    }

    try:
        ai_result = await ai_client.chat_structured(
            [
                {"role": "system", "content": SALES_INTEL_SYSTEM},
                {"role": "user", "content": quotation_optimize_prompt(context_data)},
            ],
            output_schema,
            max_tokens=1024,
        )
        ai_result["context"] = context_data
        return ai_result
    except Exception as e:
        logger.error(f"Quotation optimization failed #{quotation_id}: {e}")
        return {
            "optimal_total": total_price,
            "discount_room": 5,
            "win_probability_current": 50,
            "win_probability_optimal": 60,
            "pricing_strategy": f"AI分析暂时不可用",
            "item_adjustments": [],
            "negotiation_guardrails": "",
            "context": {"error": str(e)},
        }


# ---------------------------------------------------------------------------
# 4. detect_cross_sell — Cross-sell/upsell detection
# ---------------------------------------------------------------------------


async def detect_cross_sell(db: AsyncSession, customer_id: int) -> dict:
    """AI-powered cross-sell and upsell detection for a customer based on
    purchase history and product associations."""
    cust_result = await db.execute(
        select(Customer).where(Customer.id == customer_id, Customer.deleted_at.is_(None))
    )
    cust = cust_result.scalar_one_or_none()
    if not cust:
        return {"error": f"客户 #{customer_id} 不存在"}

    # Products already purchased
    purchased_products = (await db.execute(
        select(Product.id, Product.name, Product.category, func.sum(SalesOrderItem.quantity).label("qty"))
        .join(SalesOrderItem, SalesOrderItem.product_id == Product.id)
        .join(SalesOrder, SalesOrder.id == SalesOrderItem.order_id)
        .where(SalesOrder.customer_id == customer_id, SalesOrder.deleted_at.is_(None))
        .group_by(Product.id)
        .order_by(func.sum(SalesOrderItem.quantity).desc())
        .limit(20)
    )).all()

    purchased_names = [f"{p.name}({p.category or '未分类'})" for p in purchased_products]
    purchased_categories = list(set(p.category for p in purchased_products if p.category))

    # Products in open quotations
    open_quote_items = (await db.execute(
        select(Product.name, Product.category)
        .join(QuotationItem, QuotationItem.product_id == Product.id)
        .join(Quotation, Quotation.id == QuotationItem.quotation_id)
        .where(Quotation.customer_id == customer_id, Quotation.status.not_in(["won", "lost"]),
               Quotation.deleted_at.is_(None))
        .limit(10)
    )).all()

    context_data = {
        "customer_name": cust.name,
        "customer_industry": cust.industry or "未知",
        "customer_level": cust.level or "未知",
        "purchased_products": ", ".join(purchased_names[:10]) if purchased_names else "无历史购买",
        "purchased_categories": ", ".join(purchased_categories) if purchased_categories else "无数据",
        "open_quotation_products": ", ".join([f"{n}({c or '未知'})" for n, c in open_quote_items]) if open_quote_items else "无",
    }

    output_schema = {
        "cross_sell_opportunities": "list of dicts: {category: string, suggestion: string, reasoning: string, estimated_value: number}",
        "upsell_opportunities": "list of dicts: {current_product: string, upgrade_suggestion: string, reason: string}",
        "bundle_suggestions": "list of strings",
        "total_estimated_value": "number",
        "priority_recommendation": "string",
    }

    try:
        ai_result = await ai_client.chat_structured(
            [
                {"role": "system", "content": SALES_INTEL_SYSTEM},
                {"role": "user", "content": cross_sell_prompt(context_data)},
            ],
            output_schema,
            max_tokens=1024,
        )
        ai_result["context"] = context_data
        return ai_result
    except Exception as e:
        logger.error(f"Cross-sell detection failed for customer #{customer_id}: {e}")
        return {
            "cross_sell_opportunities": [],
            "upsell_opportunities": [],
            "bundle_suggestions": [],
            "total_estimated_value": 0,
            "priority_recommendation": f"AI分析暂时不可用",
            "context": {"error": str(e)},
        }
