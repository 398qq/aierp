"""Brand health dashboard."""

import datetime
from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.product import Inventory, Product, SupplierProduct
from app.models.sales import SalesOrder, SalesOrderItem
from app.services.ai.client import ai_client
from app.services.ai.prompts import brand_health_prompt
from app.services.brand_intel.context import _brand_context


async def get_brand_health(db: AsyncSession, brand_id: int) -> dict:
    """Compute brand health metrics from sales data + AI assessment."""
    ctx = await _brand_context(db, brand_id)

    product_ids = [r[0] for r in (
        await db.execute(
            select(Product.id).where(
                Product.brand_id == brand_id, Product.deleted_at.is_(None)
            )
        )
    ).all()]

    now = datetime.datetime.now(datetime.timezone.utc)
    twelve_months_ago = now - datetime.timedelta(days=365)

    if product_ids:
        monthly_rows = (await db.execute(
            select(
                func.date_trunc('month', SalesOrder.created_at).label('month'),
                func.sum(SalesOrderItem.total_price).label('revenue'),
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

        monthly_revenue = ", ".join(f"{r[0].strftime('%Y-%m')}: ¥{float(r[1]):,.0f}" for r in monthly_rows) if monthly_rows else "无"

        order_stats = (await db.execute(
            select(
                func.count(func.distinct(SalesOrder.id)),
                func.count(func.distinct(SalesOrder.customer_id)),
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
        )).first()

        total_orders = order_stats[0] if order_stats else 0
        active_customers = order_stats[1] if order_stats else 0

        r3m = (await db.execute(
            select(func.sum(SalesOrderItem.total_price))
            .select_from(SalesOrderItem)
            .join(SalesOrder, SalesOrderItem.order_id == SalesOrder.id)
            .where(
                SalesOrderItem.product_id.in_(product_ids),
                SalesOrder.status.in_(['confirmed', 'delivered', 'completed']),
                SalesOrder.created_at >= now - datetime.timedelta(days=90),
                SalesOrder.deleted_at.is_(None),
                SalesOrderItem.deleted_at.is_(None),
            )
        )).scalar() or 0

        r3m_prev = (await db.execute(
            select(func.sum(SalesOrderItem.total_price))
            .select_from(SalesOrderItem)
            .join(SalesOrder, SalesOrderItem.order_id == SalesOrder.id)
            .where(
                SalesOrderItem.product_id.in_(product_ids),
                SalesOrder.status.in_(['confirmed', 'delivered', 'completed']),
                SalesOrder.created_at.between(
                    now - datetime.timedelta(days=180),
                    now - datetime.timedelta(days=90),
                ),
                SalesOrder.deleted_at.is_(None),
                SalesOrderItem.deleted_at.is_(None),
            )
        )).scalar() or 0

        revenue_growth = f"{((float(r3m) - float(r3m_prev)) / float(r3m_prev) * 100):.1f}" if float(r3m_prev) > 0 else "无数据"

        cost_rows = (await db.execute(
            select(func.sum(SupplierProduct.cost_price * SalesOrderItem.quantity))
            .select_from(SalesOrderItem)
            .join(SalesOrder, SalesOrderItem.order_id == SalesOrder.id)
            .join(SupplierProduct, SalesOrderItem.product_id == SupplierProduct.product_id)
            .where(
                SalesOrderItem.product_id.in_(product_ids),
                SalesOrder.status.in_(['confirmed', 'delivered', 'completed']),
                SalesOrder.created_at >= twelve_months_ago,
                SalesOrder.deleted_at.is_(None),
                SalesOrderItem.deleted_at.is_(None),
                SupplierProduct.deleted_at.is_(None),
            )
        )).scalar() or 0

        total_revenue = sum(float(r[1]) for r in monthly_rows) if monthly_rows else 0
        margin_pct = f"{((total_revenue - float(cost_rows)) / total_revenue * 100):.1f}" if total_revenue > 0 else "无数据"

        stock_rows = (await db.execute(
            select(
                func.sum(Inventory.quantity),
                func.count(Inventory.id),
            ).where(
                Inventory.product_id.in_(product_ids),
                Inventory.deleted_at.is_(None),
            )
        )).first()
        total_stock = stock_rows[0] or 0 if stock_rows else 0
    else:
        monthly_revenue = "无"
        total_orders = 0
        active_customers = 0
        revenue_growth = "无数据"
        margin_pct = "无数据"
        total_stock = 0

    health_data = {
        **ctx,
        "monthly_revenue": monthly_revenue,
        "monthly_margin": margin_pct,
        "total_orders": total_orders,
        "active_customers": active_customers,
        "return_rate": "无数据",
        "revenue_growth": revenue_growth,
        "churn_rate": "无数据",
        "total_stock": total_stock,
        "turnover_rate": "无数据",
        "slow_moving_pct": "无数据",
    }

    schema = {
        "overall_health_score": "integer 0-100",
        "health_label": "string: 优秀/良好/一般/需关注/风险",
        "revenue_assessment": "string",
        "margin_assessment": "string",
        "customer_assessment": "string",
        "inventory_assessment": "string",
        "trend_direction": "string: 上升/稳定/下降",
        "risk_signals": ["string"],
        "improvement_suggestions": ["string"],
    }
    result = await ai_client.chat_structured(
        [{"role": "system", "content": "你是一个电子元器件供应链分析专家，擅长品牌经营健康度评估。"},
         {"role": "user", "content": brand_health_prompt(health_data)}],
        schema,
    )
    result["context"] = health_data
    return result