"""Multi-domain orchestration — aggregates data across all business domains, then calls AI for cross-domain insights."""

import datetime
import json
import logging

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.customer import Customer
from app.models.finance import Contract, Invoice
from app.models.product import Brand, Inventory, Product, Supplier, SupplierProduct, Warehouse
from app.models.sales import (
    Opportunity,
    SalesOrder,
    SalesOrderItem,
)
from app.models.transaction import Payment, PurchaseOrder, Sample, Ticket, Visit
from app.services.ai.client import ai_client
from app.services.ai.prompts import (
    orchestrate_customer_prompt,
    orchestrate_global_prompt,
    orchestrate_product_prompt,
)

logger = logging.getLogger(__name__)


def _safe_json(obj):
    """Convert objects to JSON-safe dicts, handling datetime etc."""
    if obj is None:
        return None
    if isinstance(obj, (datetime.datetime, datetime.date)):
        return obj.isoformat()
    return str(obj)


async def orchestrate_customer_360(db: AsyncSession, customer_id: int) -> dict:
    """Aggregate all-domain data for a single customer, then invoke AI for cross-domain insights."""

    now = datetime.datetime.now(datetime.timezone.utc)
    three_months_ago = now - datetime.timedelta(days=90)

    # --- 1. Transaction Health: recent sales orders + revenue trend ---
    recent_orders_result = await db.execute(
        select(SalesOrder)
        .where(
            SalesOrder.customer_id == customer_id,
            SalesOrder.deleted_at.is_(None),
            SalesOrder.created_at >= three_months_ago,
        )
        .order_by(SalesOrder.created_at.desc())
        .limit(20)
    )
    recent_orders = recent_orders_result.scalars().all()

    total_orders_result = await db.execute(
        select(func.count(SalesOrder.id), func.coalesce(func.sum(SalesOrder.total_amount), 0))
        .where(
            SalesOrder.customer_id == customer_id,
            SalesOrder.deleted_at.is_(None),
        )
    )
    total_orders_row = total_orders_result.one()

    recent_revenue = sum(float(o.total_amount) for o in recent_orders)
    transaction_health = json.dumps({
        "recent_order_count": len(recent_orders),
        "recent_total_revenue": round(recent_revenue, 2),
        "total_order_count": total_orders_row[0],
        "total_revenue": round(float(total_orders_row[1]), 2),
        "recent_orders": [
            {"order_no": o.order_no, "amount": float(o.total_amount), "status": o.status,
             "created_at": o.created_at.isoformat() if o.created_at else None}
            for o in recent_orders[:5]
        ],
    }, ensure_ascii=False, default=_safe_json)

    # --- 2. Opportunity Pipeline: open opportunities ---
    opps_result = await db.execute(
        select(Opportunity)
        .where(
            Opportunity.customer_id == customer_id,
            Opportunity.deleted_at.is_(None),
            Opportunity.stage.not_in(["won", "lost", "closed"]),
        )
        .order_by(Opportunity.amount.desc())
    )
    open_opps = opps_result.scalars().all()

    opportunity_pipeline = json.dumps({
        "open_count": len(open_opps),
        "total_pipeline_value": round(sum(float(o.amount) for o in open_opps), 2),
        "opportunities": [
            {"name": o.name, "amount": float(o.amount), "stage": o.stage,
             "probability": o.probability,
             "expected_close_date": o.expected_close_date.isoformat() if o.expected_close_date else None}
            for o in open_opps
        ],
    }, ensure_ascii=False, default=_safe_json)

    # --- 3. AR Status: open invoices, total AR, overdue ---
    invoices_result = await db.execute(
        select(Invoice)
        .where(
            Invoice.customer_id == customer_id,
            Invoice.deleted_at.is_(None),
            Invoice.status != "paid",
        )
        .order_by(Invoice.invoice_date.desc().nulls_last())
    )
    open_invoices = invoices_result.scalars().all()

    total_ar = sum(float(inv.amount) for inv in open_invoices)
    overdue_invoices = [inv for inv in open_invoices
                        if inv.invoice_date and inv.invoice_date < now]
    overdue_amount = sum(float(inv.amount) for inv in overdue_invoices)

    ar_status = json.dumps({
        "open_invoice_count": len(open_invoices),
        "total_ar": round(total_ar, 2),
        "overdue_invoice_count": len(overdue_invoices),
        "overdue_amount": round(overdue_amount, 2),
        "invoices": [
            {"invoice_no": inv.invoice_no, "amount": float(inv.amount),
             "invoice_date": inv.invoice_date.isoformat() if inv.invoice_date else None,
             "status": inv.status}
            for inv in open_invoices[:5]
        ],
    }, ensure_ascii=False, default=_safe_json)

    # --- 4. Recent Visits: last 3 ---
    visits_result = await db.execute(
        select(Visit)
        .where(
            Visit.customer_id == customer_id,
            Visit.deleted_at.is_(None),
        )
        .order_by(Visit.visit_date.desc().nulls_last())
        .limit(3)
    )
    recent_visits = visits_result.scalars().all()

    recent_visits_str = json.dumps({
        "count": len(recent_visits),
        "visits": [
            {"title": v.title, "type": v.type, "visit_date": v.visit_date.isoformat() if v.visit_date else None,
             "status": v.status, "purpose": v.purpose, "result": v.result,
             "next_plan": v.next_plan}
            for v in recent_visits
        ],
    }, ensure_ascii=False, default=_safe_json)

    # --- 5. Active Tickets: open tickets ---
    tickets_result = await db.execute(
        select(Ticket)
        .where(
            Ticket.customer_id == customer_id,
            Ticket.deleted_at.is_(None),
            Ticket.status == "open",
        )
        .order_by(Ticket.priority.desc())
    )
    active_tickets = tickets_result.scalars().all()

    active_tickets_str = json.dumps({
        "open_count": len(active_tickets),
        "tickets": [
            {"ticket_no": t.ticket_no, "title": t.title, "priority": t.priority,
             "category": t.category, "created_at": t.created_at.isoformat() if t.created_at else None}
            for t in active_tickets
        ],
    }, ensure_ascii=False, default=_safe_json)

    # --- 6. Contract Status: active contracts ---
    contracts_result = await db.execute(
        select(Contract)
        .where(
            Contract.customer_id == customer_id,
            Contract.deleted_at.is_(None),
            Contract.status.not_in(["cancelled", "expired"]),
        )
        .order_by(Contract.expire_date.desc().nulls_last())
    )
    active_contracts = contracts_result.scalars().all()

    contract_status = json.dumps({
        "active_count": len(active_contracts),
        "contracts": [
            {"contract_no": c.contract_no, "title": c.title, "amount": float(c.amount),
             "status": c.status,
             "signed_date": c.signed_date.isoformat() if c.signed_date else None,
             "expire_date": c.expire_date.isoformat() if c.expire_date else None}
            for c in active_contracts
        ],
    }, ensure_ascii=False, default=_safe_json)

    # --- 7. Sample Status: recent sample requests ---
    samples_result = await db.execute(
        select(Sample)
        .where(
            Sample.customer_id == customer_id,
            Sample.deleted_at.is_(None),
        )
        .order_by(Sample.created_at.desc())
        .limit(10)
    )
    recent_samples = samples_result.scalars().all()

    sample_status = json.dumps({
        "recent_count": len(recent_samples),
        "samples": [
            {"product_id": s.product_id, "quantity": s.quantity, "status": s.status,
             "apply_date": s.apply_date.isoformat() if s.apply_date else None,
             "ship_date": s.ship_date.isoformat() if s.ship_date else None,
             "receive_date": s.receive_date.isoformat() if s.receive_date else None}
            for s in recent_samples[:5]
        ],
    }, ensure_ascii=False, default=_safe_json)

    # --- Get customer basic info ---
    cust_result = await db.execute(
        select(Customer).where(Customer.id == customer_id, Customer.deleted_at.is_(None))
    )
    customer = cust_result.scalar_one_or_none()
    customer_name = customer.name if customer else f"#{customer_id}"
    customer_level = customer.level if customer else "未知"

    # --- Build AI prompt data ---
    ai_input = {
        "name": customer_name,
        "level": customer_level,
        "transaction_health": transaction_health,
        "opportunity_pipeline": opportunity_pipeline,
        "ar_status": ar_status,
        "recent_visits": recent_visits_str,
        "active_tickets": active_tickets_str,
        "contract_status": contract_status,
        "sample_status": sample_status,
    }

    # --- AI Output Schema ---
    output_schema = {
        "customer_360_score": "integer 0-100",
        "health_summary": "string, 2-3 sentence overview",
        "revenue_health": "string, revenue dimension assessment",
        "relationship_health": "string, relationship dimension assessment",
        "risk_health": "string, risk dimension assessment",
        "cross_domain_insights": [
            {"domain": "string", "finding": "string", "impact": "string", "action": "string"}
        ],
        "prioritized_actions": [
            {"action": "string", "domain": "string", "priority": "string",
             "expected_impact": "string"}
        ],
        "opportunity_score": "integer 0-100",
        "risk_score": "integer 0-100",
        "next_best_action": "string",
    }

    ai_insights = {}
    try:
        ai_insights = await ai_client.chat_structured(
            [
                {"role": "system", "content": "你是一个电子元器件ERP系统智能总控。整合分析客户全维度数据。"},
                {"role": "user", "content": orchestrate_customer_prompt(ai_input)},
            ],
            output_schema,
            max_tokens=8192,
        )
    except Exception as e:
        logger.error(f"Customer 360 AI orchestration failed for customer {customer_id}: {e}")
        ai_insights = {
            "customer_360_score": 0,
            "health_summary": "AI分析暂时不可用",
            "revenue_health": "未知",
            "relationship_health": "未知",
            "risk_health": "未知",
            "cross_domain_insights": [],
            "prioritized_actions": [],
            "opportunity_score": 0,
            "risk_score": 0,
            "next_best_action": "",
        }

    return {
        "customer_id": customer_id,
        "customer_name": customer_name,
        "data": {
            "transaction_health": json.loads(transaction_health),
            "opportunity_pipeline": json.loads(opportunity_pipeline),
            "ar_status": json.loads(ar_status),
            "recent_visits": json.loads(recent_visits_str),
            "active_tickets": json.loads(active_tickets_str),
            "contract_status": json.loads(contract_status),
            "sample_status": json.loads(sample_status),
        },
        "insights": ai_insights,
    }


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


async def orchestrate_global_360(db: AsyncSession) -> dict:
    """Aggregate system-wide data across all domains, then invoke AI for global insights."""

    now = datetime.datetime.now(datetime.timezone.utc)
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    quarter_start_month = ((now.month - 1) // 3) * 3 + 1
    quarter_start = now.replace(month=quarter_start_month, day=1, hour=0, minute=0, second=0, microsecond=0)
    year_start = now.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
    thirty_days_ago = now - datetime.timedelta(days=30)

    # --- 1. Sales Overview: MTD/QTD/YTD revenue, top products/customers ---
    mtd_rev_result = await db.execute(
        select(func.coalesce(func.sum(SalesOrder.total_amount), 0))
        .where(
            SalesOrder.created_at >= month_start,
            SalesOrder.deleted_at.is_(None),
        )
    )
    mtd_revenue = float(mtd_rev_result.scalar() or 0)

    qtd_rev_result = await db.execute(
        select(func.coalesce(func.sum(SalesOrder.total_amount), 0))
        .where(
            SalesOrder.created_at >= quarter_start,
            SalesOrder.deleted_at.is_(None),
        )
    )
    qtd_revenue = float(qtd_rev_result.scalar() or 0)

    ytd_rev_result = await db.execute(
        select(func.coalesce(func.sum(SalesOrder.total_amount), 0))
        .where(
            SalesOrder.created_at >= year_start,
            SalesOrder.deleted_at.is_(None),
        )
    )
    ytd_revenue = float(ytd_rev_result.scalar() or 0)

    # Top products by revenue
    top_products_result = await db.execute(
        select(
            Product.id,
            Product.name,
            Product.sku,
            func.coalesce(func.sum(SalesOrderItem.total_price), 0).label("revenue"),
        )
        .join(SalesOrderItem, SalesOrderItem.product_id == Product.id)
        .join(SalesOrder, SalesOrder.id == SalesOrderItem.order_id)
        .where(
            SalesOrder.created_at >= thirty_days_ago,
            SalesOrder.deleted_at.is_(None),
            SalesOrderItem.deleted_at.is_(None),
            Product.deleted_at.is_(None),
        )
        .group_by(Product.id, Product.name, Product.sku)
        .order_by(func.sum(SalesOrderItem.total_price).desc())
        .limit(5)
    )
    top_products = top_products_result.all()

    # Top customers by revenue
    top_customers_result = await db.execute(
        select(
            Customer.id,
            Customer.name,
            func.coalesce(func.sum(SalesOrder.total_amount), 0).label("revenue"),
        )
        .join(SalesOrder, SalesOrder.customer_id == Customer.id)
        .where(
            SalesOrder.created_at >= thirty_days_ago,
            SalesOrder.deleted_at.is_(None),
            Customer.deleted_at.is_(None),
        )
        .group_by(Customer.id, Customer.name)
        .order_by(func.sum(SalesOrder.total_amount).desc())
        .limit(5)
    )
    top_customers = top_customers_result.all()

    sales_overview = json.dumps({
        "mtd_revenue": round(mtd_revenue, 2),
        "qtd_revenue": round(qtd_revenue, 2),
        "ytd_revenue": round(ytd_revenue, 2),
        "top_products_30d": [
            {"id": r[0], "name": r[1], "sku": r[2], "revenue": round(float(r[3]), 2)}
            for r in top_products
        ],
        "top_customers_30d": [
            {"id": r[0], "name": r[1], "revenue": round(float(r[2]), 2)}
            for r in top_customers
        ],
    }, ensure_ascii=False, default=_safe_json)

    # --- 2. Customer Overview: total, active, new, churning ---
    total_cust_result = await db.execute(
        select(func.count(Customer.id))
        .where(Customer.deleted_at.is_(None))
    )
    total_customers = total_cust_result.scalar() or 0

    new_cust_result = await db.execute(
        select(func.count(Customer.id))
        .where(
            Customer.deleted_at.is_(None),
            Customer.created_at >= thirty_days_ago,
        )
    )
    new_customers = new_cust_result.scalar() or 0

    # Active customers: have orders in last 30 days
    active_cust_result = await db.execute(
        select(func.count(func.distinct(SalesOrder.customer_id)))
        .where(
            SalesOrder.deleted_at.is_(None),
            SalesOrder.created_at >= thirty_days_ago,
        )
    )
    active_customers = active_cust_result.scalar() or 0

    customer_overview = json.dumps({
        "total_customers": total_customers,
        "new_customers_30d": new_customers,
        "active_customers_30d": active_customers,
        "activity_rate_pct": round(active_customers / total_customers * 100, 1) if total_customers else 0,
    }, ensure_ascii=False, default=_safe_json)

    # --- 3. Supply Chain Overview: pending POs, low stock, top suppliers ---
    pending_po_result = await db.execute(
        select(
            func.count(PurchaseOrder.id),
            func.coalesce(func.sum(PurchaseOrder.total_amount), 0),
        )
        .where(
            PurchaseOrder.deleted_at.is_(None),
            PurchaseOrder.status.not_in(["cancelled", "received"]),
        )
    )
    pending_po = pending_po_result.one()

    low_stock_result = await db.execute(
        select(
            func.count(func.distinct(Inventory.product_id)),
        )
        .where(
            Inventory.deleted_at.is_(None),
            Inventory.quantity > 0,
            Inventory.quantity <= Inventory.safety_stock,
        )
    )
    low_stock_count = low_stock_result.scalar() or 0

    out_of_stock_result = await db.execute(
        select(func.count(func.distinct(Inventory.product_id)))
        .where(
            Inventory.deleted_at.is_(None),
            Inventory.quantity <= 0,
        )
    )
    out_of_stock_count = out_of_stock_result.scalar() or 0

    # Top suppliers by purchase volume (30d)
    top_suppliers_result = await db.execute(
        select(
            Supplier.id,
            Supplier.name,
            func.coalesce(func.sum(PurchaseOrder.total_amount), 0).label("total"),
        )
        .join(PurchaseOrder, PurchaseOrder.supplier_id == Supplier.id)
        .where(
            PurchaseOrder.created_at >= thirty_days_ago,
            PurchaseOrder.deleted_at.is_(None),
            Supplier.deleted_at.is_(None),
        )
        .group_by(Supplier.id, Supplier.name)
        .order_by(func.sum(PurchaseOrder.total_amount).desc())
        .limit(5)
    )
    top_suppliers = top_suppliers_result.all()

    supply_chain_overview = json.dumps({
        "pending_po_count": int(pending_po[0]),
        "pending_po_amount": round(float(pending_po[1]), 2),
        "low_stock_product_count": low_stock_count,
        "out_of_stock_product_count": out_of_stock_count,
        "top_suppliers_30d": [
            {"id": r[0], "name": r[1], "total": round(float(r[2]), 2)}
            for r in top_suppliers
        ],
    }, ensure_ascii=False, default=_safe_json)

    # --- 4. Finance Overview: AR, AP ---
    # AR: open invoices (not paid)
    ar_result = await db.execute(
        select(
            func.count(Invoice.id),
            func.coalesce(func.sum(Invoice.amount), 0),
        )
        .where(
            Invoice.deleted_at.is_(None),
            Invoice.status != "paid",
        )
    )
    ar = ar_result.one()

    overdue_result = await db.execute(
        select(
            func.coalesce(func.sum(Invoice.amount), 0),
        )
        .where(
            Invoice.deleted_at.is_(None),
            Invoice.status != "paid",
            Invoice.invoice_date < thirty_days_ago,
        )
    )
    overdue_ar = float(overdue_result.scalar() or 0)

    # AP: pending purchase orders (not yet paid in full) - use POs as proxy
    ap_result = await db.execute(
        select(
            func.coalesce(func.sum(PurchaseOrder.total_amount), 0),
        )
        .where(
            PurchaseOrder.deleted_at.is_(None),
            PurchaseOrder.status.not_in(["cancelled", "paid"]),
        )
    )
    ap_amount = float(ap_result.scalar() or 0)

    # Cash flow: payments received MTD vs payments made
    receipts_mtd_result = await db.execute(
        select(func.coalesce(func.sum(Payment.amount), 0))
        .where(
            Payment.deleted_at.is_(None),
            Payment.type == "receipt",
            Payment.paid_at >= month_start,
        )
    )
    receipts_mtd = float(receipts_mtd_result.scalar() or 0)

    payments_mtd_result = await db.execute(
        select(func.coalesce(func.sum(Payment.amount), 0))
        .where(
            Payment.deleted_at.is_(None),
            Payment.type == "payment",
            Payment.paid_at >= month_start,
        )
    )
    payments_mtd = float(payments_mtd_result.scalar() or 0)

    finance_overview = json.dumps({
        "total_ar": round(float(ar[1]), 2),
        "open_invoice_count": int(ar[0]),
        "overdue_ar": round(overdue_ar, 2),
        "total_ap": round(ap_amount, 2),
        "receipts_mtd": round(receipts_mtd, 2),
        "payments_mtd": round(payments_mtd, 2),
        "net_cash_flow_mtd": round(receipts_mtd - payments_mtd, 2),
    }, ensure_ascii=False, default=_safe_json)

    # --- 5. Ticket Overview: open tickets, avg resolution, hotspots ---
    open_tickets_result = await db.execute(
        select(func.count(Ticket.id))
        .where(
            Ticket.deleted_at.is_(None),
            Ticket.status == "open",
        )
    )
    open_tickets = open_tickets_result.scalar() or 0

    # Avg resolution time for recently resolved tickets
    avg_resolution_result = await db.execute(
        select(
            func.avg(
                func.extract("epoch", Ticket.resolved_at - Ticket.created_at) / 3600
            )
        )
        .where(
            Ticket.deleted_at.is_(None),
            Ticket.status == "resolved",
            Ticket.resolved_at.isnot(None),
            Ticket.resolved_at >= thirty_days_ago,
        )
    )
    avg_resolution_hours = avg_resolution_result.scalar()

    # Hotspot categories
    hotspot_result = await db.execute(
        select(
            Ticket.category,
            func.count(Ticket.id).label("cnt"),
        )
        .where(
            Ticket.deleted_at.is_(None),
            Ticket.status == "open",
        )
        .group_by(Ticket.category)
        .order_by(func.count(Ticket.id).desc())
        .limit(5)
    )
    hotspots = hotspot_result.all()

    ticket_overview = json.dumps({
        "open_tickets": open_tickets,
        "avg_resolution_hours": round(float(avg_resolution_hours), 1) if avg_resolution_hours else None,
        "hotspot_categories": [
            {"category": r[0] or "未分类", "count": int(r[1])}
            for r in hotspots
        ],
    }, ensure_ascii=False, default=_safe_json)

    # --- 6. Anomalies Overview ---
    anomalies_overview = json.dumps({
        "message": "异常检测需通过 /api/v1/watchtower 接口获取完整扫描结果",
    }, ensure_ascii=False)

    # --- Build AI prompt data ---
    ai_input = {
        "sales_overview": sales_overview,
        "customer_overview": customer_overview,
        "supply_chain_overview": supply_chain_overview,
        "finance_overview": finance_overview,
        "ticket_overview": ticket_overview,
        "anomalies_overview": anomalies_overview,
    }

    # --- AI Output Schema ---
    output_schema = {
        "enterprise_health_score": "integer 0-100",
        "executive_summary": "string, 2-3 sentence executive summary",
        "top_opportunities": [
            {"area": "string", "description": "string", "potential_value": "number"}
        ],
        "top_risks": [
            {"area": "string", "description": "string", "severity": "string"}
        ],
        "cross_domain_correlations": [
            {"domains": "string", "finding": "string"}
        ],
        "strategic_recommendations": [
            {"recommendation": "string", "domain": "string", "priority": "string"}
        ],
        "kpi_health": [
            {"kpi": "string", "current": "string", "target": "string", "status": "string"}
        ],
        "focus_areas": ["string"],
    }

    default_insights = {
        "enterprise_health_score": 50,
        "executive_summary": "AI分析暂时不可用",
        "top_opportunities": [],
        "top_risks": [],
        "cross_domain_correlations": [],
        "strategic_recommendations": [],
        "kpi_health": [],
        "focus_areas": [],
    }
    ai_insights = {}
    try:
        ai_insights = await ai_client.chat_structured(
            [
                {"role": "system", "content": "你是一个电子元器件ERP系统智能总控。整合分析企业全局数据。"},
                {"role": "user", "content": orchestrate_global_prompt(ai_input)},
            ],
            output_schema,
            max_tokens=16384,
        )
        # Merge with defaults to ensure all expected keys exist
        for key, default_val in default_insights.items():
            if key not in ai_insights:
                ai_insights[key] = default_val
    except Exception as e:
        logger.error(f"Global 360 AI orchestration failed: {e}")
        ai_insights = default_insights

    return {
        "scanned_at": now.isoformat(),
        **ai_insights,
    }
