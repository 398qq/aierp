"""Smart Quotation Assistant — AI-driven pricing, cross-sell, risk check, win-probability."""

import logging
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.product import Brand, Inventory, Product, SupplierProduct
from app.models.sales import SalesOrder, SalesOrderItem
from app.models.customer import Customer

logger = logging.getLogger(__name__)


async def quote_assist(
    db: AsyncSession,
    customer_id: int,
    items: list[dict],  # [{product_id, quantity}]
) -> dict:
    """For a quotation being built, return AI pricing, cross-sell, risk, and win-probability."""

    customer = (await db.execute(
        select(Customer).where(Customer.id == customer_id, Customer.deleted_at.is_(None))
    )).scalar_one_or_none()
    if customer is None:
        raise ValueError("Customer not found")

    customer_info = {
        "name": customer.name,
        "level": customer.level or "未知",
        "industry": customer.industry or "未知",
        "lifecycle": customer.lifecycle or "未知",
        "credit_limit": customer.credit_limit or 0,
    }

    # Enrich each line item with product info, pricing, risk
    product_ids = [it["product_id"] for it in items]

    # Product details
    product_rows = (await db.execute(
        select(Product.id, Product.sku, Product.name, Product.category,
               Brand.name, Brand.name_cn)
        .outerjoin(Brand, Product.brand_id == Brand.id)
        .where(Product.id.in_(product_ids), Product.deleted_at.is_(None))
    )).all()
    product_map = {
        r[0]: {"sku": r[1], "name": r[2], "category": r[3], "brand": r[4] or r[5] or "未知"}
        for r in product_rows
    }

    # Inventory
    stock_rows = (await db.execute(
        select(Inventory.product_id, func.coalesce(func.sum(Inventory.quantity), 0))
        .where(Inventory.product_id.in_(product_ids), Inventory.deleted_at.is_(None))
        .group_by(Inventory.product_id)
    )).all()
    stock_map = {r[0]: r[1] for r in stock_rows}

    # Supplier coverage per product
    sp_rows = (await db.execute(
        select(SupplierProduct.product_id,
               func.count(SupplierProduct.supplier_id).label("sc"),
               func.min(SupplierProduct.cost_price).label("min_cost"))
        .where(SupplierProduct.product_id.in_(product_ids),
               SupplierProduct.deleted_at.is_(None))
        .group_by(SupplierProduct.product_id)
    )).all()
    sp_map = {r[0]: {"supplier_count": r[1], "min_cost": float(r[2]) if r[2] else None} for r in sp_rows}

    # Customer historical prices per product (last 12 months)
    hist_map = {}
    for pid in product_ids:
        hist = (await db.execute(
            select(SalesOrderItem.unit_price)
            .join(SalesOrder, SalesOrderItem.order_id == SalesOrder.id)
            .where(
                SalesOrderItem.product_id == pid,
                SalesOrder.customer_id == customer_id,
                SalesOrder.status.in_(['confirmed', 'delivered', 'completed']),
                SalesOrder.deleted_at.is_(None),
                SalesOrderItem.deleted_at.is_(None),
            )
            .order_by(SalesOrder.created_at.desc())
            .limit(5)
        )).all()
        hist_map[pid] = [float(r[0]) for r in hist if r[0]]

    # Build enriched items
    enriched_items = []
    for it in items:
        pid = it["product_id"]
        qty = it.get("quantity", 1)
        prod = product_map.get(pid, {})
        sp = sp_map.get(pid, {})
        stock = stock_map.get(pid, 0)
        hist_prices = hist_map.get(pid, [])

        # Risk flags
        risks = []
        if sp.get("supplier_count", 0) == 0:
            risks.append("无供应商")
        elif sp.get("supplier_count", 0) == 1:
            risks.append("单源供应")
        if stock < qty:
            risks.append(f"库存不足({stock}<{qty})")

        enriched_items.append({
            "product_id": pid,
            "product_name": f"{prod.get('sku', '')} {prod.get('name', '')}".strip() or f"#{pid}",
            "brand": prod.get("brand", "未知"),
            "category": prod.get("category", "未知"),
            "quantity": qty,
            "stock_qty": stock,
            "supplier_count": sp.get("supplier_count", 0),
            "min_cost": sp.get("min_cost"),
            "historical_prices": hist_prices,
            "risk_flags": risks,
        })

    # Customer total order stats
    order_stats = (await db.execute(
        select(
            func.count(SalesOrder.id).label("total_orders"),
            func.coalesce(func.sum(SalesOrder.total_amount), 0).label("total_revenue"),
        ).where(
            SalesOrder.customer_id == customer_id,
            SalesOrder.status.in_(['confirmed', 'delivered', 'completed']),
            SalesOrder.deleted_at.is_(None),
        )
    )).first()

    customer_info["total_orders"] = order_stats[0] if order_stats else 0
    customer_info["total_revenue"] = round(float(order_stats[1]), 2) if order_stats and order_stats[1] else 0

    # Build AI context
    items_text = "\n".join(
        f"- [{it['brand']}] {it['product_name']} | 数量:{it['quantity']} | "
        f"库存:{it['stock_qty']} | 供应商:{it['supplier_count']}家 | "
        f"最低成本:{f'¥{it["min_cost"]:.4f}' if it['min_cost'] else '未知'} | "
        f"历史成交价:{[f'¥{p:.2f}' for p in it['historical_prices'][:3]] or '无'} | "
        f"风险:{', '.join(it['risk_flags']) if it['risk_flags'] else '无'}"
        for it in enriched_items
    )

    customer_text = (
        f"客户:{customer_info['name']} | 等级:{customer_info['level']} | "
        f"行业:{customer_info['industry']} | 生命周期:{customer_info['lifecycle']} | "
        f"历史订单{customer_info['total_orders']}笔 "
        f"累计交易¥{customer_info['total_revenue']:,.0f}"
    )

    from app.services.ai.client import ai_client
    from app.services.ai.prompts import quote_assist_prompt

    schema = {
        "win_probability": "integer 0-100",
        "win_probability_reason": "string, brief reason for probability",
        "pricing_recommendations": [
            {"product_name": "string", "recommended_price": "number", "price_range_low": "number",
             "price_range_high": "number", "margin_pct": "number", "rationale": "string"}
        ],
        "cross_sell_suggestions": [
            {"brand_name": "string", "product_name": "string", "reason": "string",
             "estimated_value": "number"}
        ],
        "risk_summary": "string, overall risk assessment",
        "negotiation_tips": ["string"],
    }
    result = await ai_client.chat_structured(
        [{"role": "system", "content": "你是一个电子元器件销售策略专家，精通报价策略、交叉销售和交易风险评估。"},
         {"role": "user", "content": quote_assist_prompt(customer_text, items_text)}],
        schema,
    )
    result["customer_info"] = customer_info
    result["enriched_items"] = enriched_items
    return result
