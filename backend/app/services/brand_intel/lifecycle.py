"""Brand lifecycle prediction and price trends."""

import datetime
from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.product import Product, SupplierProduct
from app.models.sales import SalesOrder, SalesOrderItem
from app.services.ai.client import ai_client
from app.services.ai.prompts import brand_lifecycle_prompt, brand_price_trends_prompt
from app.services.brand_intel.context import _brand_context


async def predict_brand_lifecycle(db: AsyncSession, brand_id: int) -> dict:
    """AI predicts brand lifecycle stage based on product, sales, and supplier trends."""
    ctx = await _brand_context(db, brand_id)

    now = datetime.datetime.now(datetime.timezone.utc)
    twelve_months_ago = now - datetime.timedelta(days=365)
    six_mo_ago = now - datetime.timedelta(days=180)

    prod_rows = (await db.execute(
        select(Product.id, Product.created_at).where(
            Product.brand_id == brand_id, Product.deleted_at.is_(None)
        )
    )).all()

    product_ids = [r[0] for r in prod_rows]
    new_6m = sum(1 for r in prod_rows if r[1] and r[1] >= six_mo_ago)

    revenue_growth = "无数据"
    if product_ids:
        rev_12m = (await db.execute(
            select(func.coalesce(func.sum(SalesOrderItem.total_price), 0))
            .select_from(SalesOrderItem)
            .join(SalesOrder, SalesOrderItem.order_id == SalesOrder.id)
            .where(
                SalesOrderItem.product_id.in_(product_ids),
                SalesOrder.status.in_(['confirmed', 'delivered', 'completed']),
                SalesOrder.created_at >= twelve_months_ago,
                SalesOrder.deleted_at.is_(None),
                SalesOrderItem.deleted_at.is_(None),
            )
        )).scalar() or 0

        rev_prev = (await db.execute(
            select(func.coalesce(func.sum(SalesOrderItem.total_price), 0))
            .select_from(SalesOrderItem)
            .join(SalesOrder, SalesOrderItem.order_id == SalesOrder.id)
            .where(
                SalesOrderItem.product_id.in_(product_ids),
                SalesOrder.status.in_(['confirmed', 'delivered', 'completed']),
                SalesOrder.created_at.between(
                    now - datetime.timedelta(days=730),
                    twelve_months_ago,
                ),
                SalesOrder.deleted_at.is_(None),
                SalesOrderItem.deleted_at.is_(None),
            )
        )).scalar() or 0

        revenue_growth = f"{((float(rev_12m) - float(rev_prev)) / float(rev_prev) * 100):.1f}" if float(rev_prev) > 0 else "无历史数据"

    lc_data = {
        **ctx,
        "new_products_6m": new_6m,
        "eol_pct": 0,
        "revenue_growth_12m": revenue_growth,
        "customer_growth_12m": "无数据",
        "supplier_trend": "无数据",
        "product_intro_rhythm": f"近6月{new_6m}新品" if new_6m > 0 else "近期无新品推出",
    }

    schema = {
        "lifecycle_stage": "string: 导入期/成长期/成熟期/衰退期",
        "stage_confidence": "integer 0-100",
        "stage_evidence": ["string"],
        "strategic_advice": "string",
        "next_12m_outlook": "string",
        "key_actions": ["string"],
        "risk_signals": ["string"],
    }
    result = await ai_client.chat_structured(
        [{"role": "system", "content": "你是一个电子元器件产品生命周期管理专家，擅长判断品牌所处阶段并给出战略建议。"},
         {"role": "user", "content": brand_lifecycle_prompt(lc_data)}],
        schema,
    )
    result["context"] = lc_data
    return result


async def get_brand_price_trends(db: AsyncSession, brand_id: int) -> dict:
    """Analyze brand price trends over 12 months with margin and competitiveness assessment."""
    ctx = await _brand_context(db, brand_id)

    now = datetime.datetime.now(datetime.timezone.utc)
    twelve_months_ago = now - datetime.timedelta(days=365)

    product_ids = [r[0] for r in (
        await db.execute(
            select(Product.id).where(
                Product.brand_id == brand_id, Product.deleted_at.is_(None)
            )
        )
    ).all()]

    monthly_avg_price = "无销售数据"
    monthly_margin = "无数据"
    current_avg = "无数据"
    price_12m_ago = "无数据"
    price_change_pct = "无数据"
    cost_trend = "无数据"

    if product_ids:
        price_rows = (await db.execute(
            select(
                func.date_trunc('month', SalesOrder.created_at).label('month'),
                func.avg(SalesOrderItem.unit_price).label('avg_price'),
            )
            .select_from(SalesOrderItem)
            .join(SalesOrder, SalesOrderItem.order_id == SalesOrder.id)
            .where(
                SalesOrderItem.product_id.in_(product_ids),
                SalesOrder.status.in_(['confirmed', 'delivered', 'completed']),
                SalesOrder.created_at >= twelve_months_ago,
                SalesOrder.deleted_at.is_(None),
                SalesOrderItem.deleted_at.is_(None),
            )
            .group_by(text('month'))
            .order_by(text('month'))
        )).all()

        if price_rows:
            monthly_avg_price = ", ".join(
                f"{r[0].strftime('%Y-%m')}: ¥{float(r[1]):.2f}" for r in price_rows
            )
            current_avg = f"¥{float(price_rows[-1][1]):.4f}"
            if len(price_rows) > 1:
                price_12m_ago = f"¥{float(price_rows[0][1]):.4f}"
                delta = (float(price_rows[-1][1]) - float(price_rows[0][1])) / float(price_rows[0][1]) * 100
                price_change_pct = f"{delta:.1f}"

        cost_rows = (await db.execute(
            select(
                func.date_trunc('month', SupplierProduct.created_at).label('month'),
                func.avg(SupplierProduct.cost_price).label('avg_cost'),
            )
            .where(
                SupplierProduct.product_id.in_(product_ids),
                SupplierProduct.cost_price.isnot(None),
                SupplierProduct.created_at >= twelve_months_ago,
                SupplierProduct.deleted_at.is_(None),
            )
            .group_by(text('month'))
            .order_by(text('month'))
        )).all()

        if cost_rows:
            cost_trend = ", ".join(
                f"{r[0].strftime('%Y-%m')}: ¥{float(r[1]):.4f}" for r in cost_rows
            )

    trend_data = {
        **ctx,
        "monthly_avg_price": monthly_avg_price,
        "monthly_margin": monthly_margin,
        "current_avg_price": current_avg,
        "price_12m_ago": price_12m_ago,
        "price_change_pct": price_change_pct,
        "market_benchmark": "暂无市场基准数据",
        "cost_trend": cost_trend,
    }

    schema = {
        "price_trend": "string: 上涨/稳定/下降",
        "trend_score": "integer 0-100",
        "margin_assessment": "string",
        "competitiveness": "string",
        "pricing_issues": ["string"],
        "optimization_suggestions": ["string"],
        "opportunity_alert": "string | null",
    }
    result = await ai_client.chat_structured(
        [{"role": "system", "content": "你是一个电子元器件定价策略专家，擅长价格趋势分析和定价优化。"},
         {"role": "user", "content": brand_price_trends_prompt(trend_data)}],
        schema,
    )
    result["context"] = trend_data
    return result