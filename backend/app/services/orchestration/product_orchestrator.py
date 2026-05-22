"""Product 360 orchestrator — aggregates all-domain data for a single product."""

import datetime
import json
import logging

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.customer import Customer
from app.models.product import Brand, Inventory, Product, Supplier, SupplierProduct, Warehouse
from app.models.sales import SalesOrder, SalesOrderItem
from app.models.transaction import Ticket
from app.services.ai.client import ai_client
from app.services.ai.prompts import orchestrate_product_prompt
from app.services.orchestration.helpers import _safe_json

logger = logging.getLogger(__name__)


async def orchestrate_product_360(db: AsyncSession, product_id: int) -> dict:
    """Aggregate all-domain data for a single product, then invoke AI for cross-domain insights."""

    now = datetime.datetime.now(datetime.timezone.utc)
    six_months_ago = now - datetime.timedelta(days=180)

    # --- Get product basic info ---
    prod_result = await db.execute(
        select(Product, Brand.name)
        .outerjoin(Brand, Product.brand_id == Brand.id)
        .where(Product.id == product_id, Product.deleted_at.is_(None))
    )
    prod_row = prod_result.one_or_none()
    if not prod_row:
        return {"product_id": product_id, "error": "Product not found"}

    product, brand_name = prod_row
    product_name = product.name or f"SKU:{product.sku}"
    product_category = product.category or "未知"

    # --- 1. Sales Performance: recent sales, revenue, trend ---
    sales_items_result = await db.execute(
        select(
            func.count(SalesOrderItem.id).label("line_count"),
            func.coalesce(func.sum(SalesOrderItem.total_price), 0).label("total_revenue"),
            func.coalesce(func.sum(SalesOrderItem.quantity), 0).label("total_qty"),
        )
        .join(SalesOrder, SalesOrderItem.order_id == SalesOrder.id)
        .where(
            SalesOrderItem.product_id == product_id,
            SalesOrderItem.deleted_at.is_(None),
            SalesOrder.deleted_at.is_(None),
        )
    )
    sales_totals = sales_items_result.one()

    recent_sales_result = await db.execute(
        select(
            func.count(SalesOrderItem.id).label("line_count"),
            func.coalesce(func.sum(SalesOrderItem.total_price), 0).label("revenue"),
            func.coalesce(func.sum(SalesOrderItem.quantity), 0).label("qty"),
        )
        .join(SalesOrder, SalesOrderItem.order_id == SalesOrder.id)
        .where(
            SalesOrderItem.product_id == product_id,
            SalesOrderItem.deleted_at.is_(None),
            SalesOrder.deleted_at.is_(None),
            SalesOrder.created_at >= six_months_ago,
        )
    )
    recent_sales = recent_sales_result.one()

    # Distinct customers who bought this product
    customer_count_result = await db.execute(
        select(func.count(func.distinct(SalesOrder.customer_id)))
        .join(SalesOrderItem, SalesOrderItem.order_id == SalesOrder.id)
        .where(
            SalesOrderItem.product_id == product_id,
            SalesOrderItem.deleted_at.is_(None),
            SalesOrder.deleted_at.is_(None),
        )
    )
    distinct_customers = customer_count_result.scalar() or 0

    sales_performance = json.dumps({
        "total_sold_quantity": int(sales_totals[2]),
        "total_revenue": round(float(sales_totals[1]), 2),
        "total_order_lines": int(sales_totals[0]),
        "recent_6m_sold_quantity": int(recent_sales[2]),
        "recent_6m_revenue": round(float(recent_sales[1]), 2),
        "recent_6m_order_lines": int(recent_sales[0]),
        "distinct_customers": distinct_customers,
    }, ensure_ascii=False, default=_safe_json)

    # --- 2. Inventory Status: current stock across warehouses ---
    inv_result = await db.execute(
        select(
            Warehouse.name.label("warehouse_name"),
            func.coalesce(func.sum(Inventory.quantity), 0).label("qty"),
            func.coalesce(func.sum(Inventory.safety_stock), 0).label("safety"),
        )
        .join(Warehouse, Inventory.warehouse_id == Warehouse.id)
        .where(
            Inventory.product_id == product_id,
            Inventory.deleted_at.is_(None),
            Warehouse.deleted_at.is_(None),
        )
        .group_by(Warehouse.id, Warehouse.name)
    )
    warehouse_stocks = inv_result.all()

    total_stock = sum(int(r[1]) for r in warehouse_stocks)
    inventory_status = json.dumps({
        "total_stock": total_stock,
        "warehouses": [
            {"warehouse": r[0], "quantity": int(r[1]), "safety_stock": int(r[2])}
            for r in warehouse_stocks
        ],
    }, ensure_ascii=False, default=_safe_json)

    # --- 3. Supplier Status: suppliers with pricing ---
    supplier_result = await db.execute(
        select(
            Supplier.id,
            Supplier.name,
            SupplierProduct.cost_price,
            SupplierProduct.lead_time_days,
            SupplierProduct.moq,
            SupplierProduct.is_preferred,
        )
        .join(SupplierProduct, Supplier.id == SupplierProduct.supplier_id)
        .where(
            SupplierProduct.product_id == product_id,
            SupplierProduct.deleted_at.is_(None),
            Supplier.deleted_at.is_(None),
        )
        .order_by(SupplierProduct.is_preferred.desc(), SupplierProduct.cost_price.asc().nulls_last())
    )
    suppliers = supplier_result.all()

    supplier_status = json.dumps({
        "supplier_count": len(suppliers),
        "preferred_count": sum(1 for s in suppliers if s[5]),
        "suppliers": [
            {"id": s[0], "name": s[1], "cost_price": float(s[2]) if s[2] else None,
             "lead_time_days": s[3], "moq": s[4], "is_preferred": s[5]}
            for s in suppliers
        ],
    }, ensure_ascii=False, default=_safe_json)

    # --- 4. Customer Coverage: which customers buy it ---
    top_customers_result = await db.execute(
        select(
            Customer.id,
            Customer.name,
            func.coalesce(func.sum(SalesOrderItem.total_price), 0).label("total_amount"),
            func.count(func.distinct(SalesOrder.id)).label("order_count"),
        )
        .join(SalesOrder, SalesOrder.customer_id == Customer.id)
        .join(SalesOrderItem, SalesOrderItem.order_id == SalesOrder.id)
        .where(
            SalesOrderItem.product_id == product_id,
            SalesOrderItem.deleted_at.is_(None),
            SalesOrder.deleted_at.is_(None),
            Customer.deleted_at.is_(None),
        )
        .group_by(Customer.id, Customer.name)
        .order_by(func.sum(SalesOrderItem.total_price).desc())
        .limit(10)
    )
    top_customers = top_customers_result.all()

    customer_coverage = json.dumps({
        "distinct_customers": distinct_customers,
        "top_customers": [
            {"id": r[0], "name": r[1], "total_amount": round(float(r[2]), 2),
             "order_count": int(r[3])}
            for r in top_customers
        ],
    }, ensure_ascii=False, default=_safe_json)

    # --- 5. Quality Issues: tickets mentioning this product ---
    tickets_result = await db.execute(
        select(Ticket)
        .where(
            Ticket.deleted_at.is_(None),
            Ticket.title.ilike(f"%{product_name}%"),
        )
        .order_by(Ticket.created_at.desc())
        .limit(10)
    )
    related_tickets = tickets_result.scalars().all()

    quality_issues = json.dumps({
        "ticket_count": len(related_tickets),
        "tickets": [
            {"ticket_no": t.ticket_no, "title": t.title, "status": t.status,
             "priority": t.priority, "category": t.category,
             "created_at": t.created_at.isoformat() if t.created_at else None}
            for t in related_tickets[:5]
        ],
    }, ensure_ascii=False, default=_safe_json)

    # --- 6. Lifecycle Status: NPD date, age ---
    product_age_days = (now - product.created_at.replace(tzinfo=datetime.timezone.utc)).days if product.created_at else 0
    lifecycle_status = json.dumps({
        "product_age_days": product_age_days,
        "product_age_months": round(product_age_days / 30, 1),
        "created_at": product.created_at.isoformat() if product.created_at else None,
        "category": product_category,
    }, ensure_ascii=False, default=_safe_json)

    # --- Build AI prompt data ---
    ai_input = {
        "name": product_name,
        "brand_name": brand_name or "未知",
        "category": product_category,
        "sales_performance": sales_performance,
        "inventory_status": inventory_status,
        "supplier_status": supplier_status,
        "customer_coverage": customer_coverage,
        "quality_issues": quality_issues,
        "lifecycle_status": lifecycle_status,
    }

    # --- AI Output Schema ---
    output_schema = {
        "product_360_score": "integer 0-100",
        "health_summary": "string, 2-3 sentence overview",
        "commercial_health": "string, commercial dimension assessment",
        "supply_health": "string, supply chain dimension assessment",
        "quality_health": "string, quality dimension assessment",
        "cross_domain_insights": [
            {"domain": "string", "finding": "string", "impact": "string", "action": "string"}
        ],
        "prioritized_actions": [
            {"action": "string", "domain": "string", "priority": "string",
             "expected_impact": "string"}
        ],
        "growth_potential": "string: 高/中/低",
        "risk_flags": ["string"],
        "next_best_action": "string",
    }

    ai_insights = {}
    try:
        ai_insights = await ai_client.chat_structured(
            [
                {"role": "system", "content": "你是一个电子元器件ERP系统智能总控。整合分析产品全维度数据。"},
                {"role": "user", "content": orchestrate_product_prompt(ai_input)},
            ],
            output_schema,
            max_tokens=8192,
        )
    except Exception as e:
        logger.error(f"Product 360 AI orchestration failed for product {product_id}: {e}")
        ai_insights = {
            "product_360_score": 0,
            "health_summary": "AI分析暂时不可用",
            "commercial_health": "未知",
            "supply_health": "未知",
            "quality_health": "未知",
            "cross_domain_insights": [],
            "prioritized_actions": [],
            "growth_potential": "未知",
            "risk_flags": [],
            "next_best_action": "",
        }

    return {
        "product_id": product_id,
        "product_name": product_name,
        "brand_name": brand_name or "未知",
        "data": {
            "sales_performance": json.loads(sales_performance),
            "inventory_status": json.loads(inventory_status),
            "supplier_status": json.loads(supplier_status),
            "customer_coverage": json.loads(customer_coverage),
            "quality_issues": json.loads(quality_issues),
            "lifecycle_status": json.loads(lifecycle_status),
        },
        "insights": ai_insights,
    }