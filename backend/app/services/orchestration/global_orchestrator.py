"""Global 360 orchestrator — aggregates system-wide data across all domains."""

import datetime
import json
import logging

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.customer import Customer
from app.models.finance import Invoice
from app.models.product import Inventory, Product, Supplier
from app.models.sales import SalesOrder, SalesOrderItem
from app.models.transaction import Payment, PurchaseOrder, Ticket
from app.services.ai.client import ai_client
from app.services.ai.prompts import orchestrate_global_prompt
from app.services.orchestration.helpers import _safe_json

logger = logging.getLogger(__name__)


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
        select(func.count(func.distinct(Inventory.product_id)))
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
        select(func.coalesce(func.sum(Invoice.amount), 0))
        .where(
            Invoice.deleted_at.is_(None),
            Invoice.status != "paid",
            Invoice.invoice_date < thirty_days_ago,
        )
    )
    overdue_ar = float(overdue_result.scalar() or 0)

    ap_result = await db.execute(
        select(func.coalesce(func.sum(PurchaseOrder.total_amount), 0))
        .where(
            PurchaseOrder.deleted_at.is_(None),
            PurchaseOrder.status.not_in(["cancelled", "paid"]),
        )
    )
    ap_amount = float(ap_result.scalar() or 0)

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