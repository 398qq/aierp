"""Context builders for natural-language ERP queries.

Each builder queries one ERP domain (customers / products / sales / etc.)
and returns a compact Chinese-language summary string suitable for
inclusion in an LLM prompt.

Two flavors per domain:
- Full context  : top-5 detail rows + aggregates (used when the user
                  explicitly asked about that domain).
- Summary only  : single count or total (used as a "what's in this
                  domain" hint when the user asked about something else).

This file holds the SQL. The orchestration layer (service.py) decides
which builders to call and when.
"""

from __future__ import annotations

import json
import logging

from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.customer import Customer
from app.models.finance import Invoice
from app.models.product import Brand, Inventory, Product, Supplier, Warehouse
from app.models.sales import Opportunity, SalesOrder
from app.models.transaction import Payment, PurchaseOrder

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Full-context builders (per domain)
# ---------------------------------------------------------------------------

async def _build_customer_context(db: AsyncSession) -> str:
    total_r = await db.execute(
        select(func.count(Customer.id)).where(Customer.deleted_at.is_(None))
    )
    total = total_r.scalar() or 0

    top_r = await db.execute(
        select(Customer.name, Customer.level, Customer.industry, Customer.last_contacted_at)
        .where(Customer.deleted_at.is_(None))
        .order_by(Customer.last_contacted_at.desc().nullslast())
        .limit(5)
    )
    top = top_r.all()

    level_r = await db.execute(
        select(Customer.level, func.count(Customer.id))
        .where(Customer.deleted_at.is_(None), Customer.level.isnot(None))
        .group_by(Customer.level)
    )
    levels = {r[0]: r[1] for r in level_r.all()}

    recent_r = await db.execute(
        select(func.count(SalesOrder.id)).where(
            SalesOrder.created_at >= text("NOW() - INTERVAL '30 days'"),
            SalesOrder.deleted_at.is_(None),
        )
    )
    recent_orders = recent_r.scalar() or 0

    parts = [f"客户总数：{total}"]
    if levels:
        parts.append(f"等级分布：{json.dumps(levels, ensure_ascii=False)}")
    parts.append(f"近30天订单数：{recent_orders}")
    if top:
        top_str = "；".join(
            f"{r[0]}({r[2] or '未知行业'}, {r[1] or '未知等级'})"
            for r in top
        )
        parts.append(f"最近活跃客户TOP5：{top_str}")
    return "\n".join(parts)


async def _build_product_context(db: AsyncSession) -> str:
    total_r = await db.execute(
        select(func.count(Product.id)).where(Product.deleted_at.is_(None))
    )
    total = total_r.scalar() or 0

    cat_r = await db.execute(
        select(Product.category, func.count(Product.id))
        .where(Product.deleted_at.is_(None), Product.category.isnot(None))
        .group_by(Product.category)
        .order_by(func.count(Product.id).desc())
    )
    cats = {r[0]: r[1] for r in cat_r.all()}

    top_r = await db.execute(
        select(Product.name, Brand.name, Product.category)
        .join(Brand, Product.brand_id == Brand.id, isouter=True)
        .where(Product.deleted_at.is_(None))
        .order_by(Product.updated_at.desc().nullslast())
        .limit(5)
    )
    top = top_r.all()

    brand_r = await db.execute(
        select(func.count(Brand.id)).where(Brand.deleted_at.is_(None))
    )
    brand_count = brand_r.scalar() or 0

    parts = [f"产品总数：{total}", f"品牌数：{brand_count}"]
    if cats:
        cat_str = ", ".join(f"{k}:{v}" for k, v in list(cats.items())[:8])
        parts.append(f"分类分布：{cat_str}")
    if top:
        top_str = "；".join(
            f"{r[0]}({r[1] or '未知品牌'}, {r[2] or '未分类'})" for r in top
        )
        parts.append(f"最近更新产品TOP5：{top_str}")
    return "\n".join(parts)


async def _build_sales_context(db: AsyncSession) -> str:
    month_r = await db.execute(
        select(func.coalesce(func.sum(SalesOrder.total_amount), 0))
        .where(
            SalesOrder.created_at >= text("date_trunc('month', NOW())"),
            SalesOrder.deleted_at.is_(None),
        )
    )
    month_revenue = float(month_r.scalar() or 0)

    month_cnt_r = await db.execute(
        select(func.count(SalesOrder.id))
        .where(
            SalesOrder.created_at >= text("date_trunc('month', NOW())"),
            SalesOrder.deleted_at.is_(None),
        )
    )
    month_orders = month_cnt_r.scalar() or 0

    recent_r = await db.execute(
        select(SalesOrder.order_no, SalesOrder.total_amount, SalesOrder.status,
               Customer.name)
        .join(Customer, SalesOrder.customer_id == Customer.id, isouter=True)
        .where(SalesOrder.deleted_at.is_(None))
        .order_by(SalesOrder.created_at.desc())
        .limit(5)
    )
    recent = recent_r.all()

    opp_r = await db.execute(
        select(func.count(Opportunity.id), func.coalesce(func.sum(Opportunity.amount), 0))
        .where(Opportunity.deleted_at.is_(None))
    )
    opp_row = opp_r.one()
    opp_count, opp_value = opp_row[0] or 0, float(opp_row[1] or 0)

    status_r = await db.execute(
        select(SalesOrder.status, func.count(SalesOrder.id))
        .where(SalesOrder.deleted_at.is_(None))
        .group_by(SalesOrder.status)
    )
    statuses = {r[0]: r[1] for r in status_r.all()}

    parts = [
        f"本月销售额：{month_revenue:,.2f}",
        f"本月订单数：{month_orders}",
        f"商机数量：{opp_count}，总金额：{opp_value:,.2f}",
    ]
    if statuses:
        parts.append(f"订单状态分布：{json.dumps(statuses, ensure_ascii=False)}")
    if recent:
        recent_str = "；".join(
            f"{r[0] or '-'}({r[2]}, {r[3] or '未知客户'}, ¥{float(r[1] or 0):,.0f})"
            for r in recent
        )
        parts.append(f"最近订单TOP5：{recent_str}")
    return "\n".join(parts)


async def _build_inventory_context(db: AsyncSession) -> str:
    total_r = await db.execute(
        select(func.count(Inventory.id)).where(Inventory.quantity > 0)
    )
    total_items = total_r.scalar() or 0

    low_r = await db.execute(
        select(Product.name, Inventory.quantity, Inventory.safety_stock,
               Warehouse.name)
        .join(Product, Inventory.product_id == Product.id, isouter=True)
        .join(Warehouse, Inventory.warehouse_id == Warehouse.id, isouter=True)
        .where(Inventory.quantity <= Inventory.safety_stock, Inventory.quantity > 0)
        .order_by(Inventory.quantity)
        .limit(5)
    )
    low_stock = low_r.all()

    wh_r = await db.execute(
        select(Warehouse.name, func.count(Inventory.id))
        .join(Inventory, Warehouse.id == Inventory.warehouse_id, isouter=True)
        .group_by(Warehouse.name)
    )
    warehouses = {r[0]: r[1] for r in wh_r.all()}

    po_r = await db.execute(
        select(func.count(PurchaseOrder.id), func.coalesce(func.sum(PurchaseOrder.total_amount), 0))
        .where(PurchaseOrder.status.in_(["draft", "pending", "confirmed"]),
               PurchaseOrder.deleted_at.is_(None))
    )
    po_row = po_r.one()
    pending_pos, po_amount = po_row[0] or 0, float(po_row[1] or 0)

    parts = [f"有库存的产品项数：{total_items}"]
    if warehouses:
        parts.append(f"仓库分布：{json.dumps(warehouses, ensure_ascii=False)}")
    parts.append(f"在途采购单：{pending_pos} 单，总金额：{po_amount:,.2f}")
    if low_stock:
        low_str = "；".join(
            f"{r[0] or '-'}(库存{r[1]}, 安全库存{r[2]}, {r[3] or '未知仓库'})"
            for r in low_stock
        )
        parts.append(f"低库存预警TOP5：{low_str}")
    else:
        parts.append("低库存预警：无")
    return "\n".join(parts)


async def _build_finance_context(db: AsyncSession) -> str:
    ar_r = await db.execute(
        select(
            func.count(Invoice.id),
            func.coalesce(func.sum(Invoice.amount), 0),
        ).where(Invoice.status.notin_(["paid", "cancelled"]),
                Invoice.deleted_at.is_(None))
    )
    ar_row = ar_r.one()
    ar_count = ar_row[0] or 0
    ar_total = float(ar_row[1] or 0)

    overdue_r = await db.execute(
        select(func.count(Invoice.id), func.coalesce(func.sum(Invoice.amount), 0))
        .where(
            Invoice.status == "overdue",
            Invoice.deleted_at.is_(None),
        )
    )
    overdue_row = overdue_r.one()
    overdue_count = overdue_row[0] or 0
    overdue_total = float(overdue_row[1] or 0)

    recent_pay_r = await db.execute(
        select(Payment.payment_no, Payment.amount, Payment.method, Payment.paid_at,
               Customer.name)
        .join(Customer, Payment.customer_id == Customer.id, isouter=True)
        .where(Payment.type == "receipt", Payment.deleted_at.is_(None))
        .order_by(Payment.paid_at.desc().nullslast())
        .limit(5)
    )
    recent_payments = recent_pay_r.all()

    ap_r = await db.execute(
        select(
            func.count(Payment.id),
            func.coalesce(func.sum(Payment.amount), 0),
        ).where(
            Payment.type == "payment",
            Payment.paid_at.is_(None),
            Payment.deleted_at.is_(None),
        )
    )
    ap_row = ap_r.one()
    ap_count = ap_row[0] or 0
    ap_total = float(ap_row[1] or 0)

    parts = [
        f"应收账款：{ar_count} 笔，总额：{ar_total:,.2f}",
        f"已逾期：{overdue_count} 笔，逾期金额：{overdue_total:,.2f}",
        f"应付账款：{ap_count} 笔，总额：{ap_total:,.2f}",
    ]
    if recent_payments:
        pay_str = "；".join(
            f"{r[0] or '-'}({r[4] or '未知客户'}, ¥{float(r[1] or 0):,.0f}, {r[2] or '-'})"
            for r in recent_payments
        )
        parts.append(f"最近回款TOP5：{pay_str}")
    return "\n".join(parts)


async def _build_supplier_context(db: AsyncSession) -> str:
    total_r = await db.execute(
        select(func.count(Supplier.id)).where(Supplier.deleted_at.is_(None))
    )
    total = total_r.scalar() or 0

    top_r = await db.execute(
        select(Supplier.name, Supplier.product_lines, Supplier.contact_person)
        .where(Supplier.deleted_at.is_(None))
        .order_by(Supplier.updated_at.desc().nullslast())
        .limit(5)
    )
    top = top_r.all()

    po_r = await db.execute(
        select(Supplier.name, func.count(PurchaseOrder.id),
               func.coalesce(func.sum(PurchaseOrder.total_amount), 0))
        .join(PurchaseOrder, Supplier.id == PurchaseOrder.supplier_id, isouter=True)
        .where(PurchaseOrder.status.in_(["draft", "pending", "confirmed"]),
               PurchaseOrder.deleted_at.is_(None))
        .group_by(Supplier.name)
        .order_by(func.count(PurchaseOrder.id).desc())
        .limit(5)
    )
    pending = po_r.all()

    parts = [f"供应商总数：{total}"]
    if top:
        top_str = "；".join(
            f"{r[0]}({r[1] or '未标注产品线'}, 联系人:{r[2] or '无'})"
            for r in top
        )
        parts.append(f"最近更新供应商TOP5：{top_str}")
    if pending:
        po_str = "；".join(
            f"{r[0]}：{r[1]}笔(¥{float(r[2] or 0):,.0f})"
            for r in pending
        )
        parts.append(f"在途采购按供应商：{po_str}")
    else:
        parts.append("在途采购：无")
    return "\n".join(parts)


# ---------------------------------------------------------------------------
# Builder registry — used by the orchestration layer to dispatch by name
# ---------------------------------------------------------------------------

_BUILDERS = {
    "customers":  _build_customer_context,
    "products":   _build_product_context,
    "sales":      _build_sales_context,
    "inventory":  _build_inventory_context,
    "finance":    _build_finance_context,
    "suppliers":  _build_supplier_context,
}


async def build_full_context(domain: str, db: AsyncSession) -> str:
    """Dispatch to the full-context builder for `domain`."""
    builder = _BUILDERS.get(domain)
    if builder is None:
        return "无数据"
    try:
        return await builder(db)
    except Exception as exc:
        logger.warning("Context build failed for %s: %s", domain, exc)
        return f"数据获取失败: {exc}"


async def build_summary_context(domain: str, db: AsyncSession) -> str:
    """Lightweight per-domain summary — only counts and totals, no detail rows."""
    try:
        if domain == "customers":
            r = await db.execute(
                select(func.count(Customer.id)).where(Customer.deleted_at.is_(None))
            )
            return f"客户总数：{r.scalar() or 0}"
        if domain == "products":
            r = await db.execute(
                select(func.count(Product.id)).where(Product.deleted_at.is_(None))
            )
            br = await db.execute(
                select(func.count(Brand.id)).where(Brand.deleted_at.is_(None))
            )
            return f"产品总数：{r.scalar() or 0}，品牌数：{br.scalar() or 0}"
        if domain == "sales":
            r = await db.execute(
                select(func.coalesce(func.sum(SalesOrder.total_amount), 0))
                .where(
                    SalesOrder.created_at >= text("date_trunc('month', NOW())"),
                    SalesOrder.deleted_at.is_(None),
                )
            )
            return f"本月销售额：{float(r.scalar() or 0):,.2f}"
        if domain == "inventory":
            r = await db.execute(
                select(func.count(Inventory.id)).where(Inventory.quantity > 0)
            )
            return f"有库存产品项数：{r.scalar() or 0}"
        if domain == "finance":
            r = await db.execute(
                select(func.coalesce(func.sum(Invoice.amount), 0))
                .where(Invoice.status.notin_(["paid", "cancelled"]),
                       Invoice.deleted_at.is_(None))
            )
            return f"应收账款总额：{float(r.scalar() or 0):,.2f}"
        if domain == "suppliers":
            r = await db.execute(
                select(func.count(Supplier.id)).where(Supplier.deleted_at.is_(None))
            )
            return f"供应商总数：{r.scalar() or 0}"
        return "无数据"
    except Exception as exc:
        return f"数据获取失败: {exc}"
