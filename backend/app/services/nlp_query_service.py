"""Natural-language ERP query — the "ask anything" feature.

Processes a free-text question, queries relevant ERP data, and returns an
AI-generated answer with related entities and suggested followups.
"""

import json
import logging
from typing import Any

from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.customer import Customer
from app.models.finance import Invoice
from app.models.product import Brand, Inventory, Product, Supplier, Warehouse
from app.models.sales import Opportunity, SalesOrder
from app.models.transaction import Payment, PurchaseOrder
from app.services.ai.client import ai_client
from app.services.ai.prompts import nlp_query_prompt

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Domain keyword patterns (Chinese + English)
# ---------------------------------------------------------------------------
DOMAIN_PATTERNS: list[tuple[str, list[str]]] = [
    ("customers", ["客户", "customer", "流失", "churn", "跟进", "followup",
                    "信用", "credit", "等级", "level", "联系人", "contact"]),
    ("products",  ["产品", "product", "型号", "part", "sku", "品牌", "brand",
                    "分类", "品类", "category", "封装", "package"]),
    ("sales",     ["销售", "sale", "订单", "order", "商机", "opportunity",
                    "报价", "quotation", "收入", "revenue", "金额", "amount",
                    "交付", "delivery"]),
    ("inventory", ["库存", "inventory", "stock", "采购", "purchase", "po",
                    "短缺", "shortage", "滞销", "slow", "周转", "turnover",
                    "仓库", "warehouse"]),
    ("finance",   ["财务", "finance", "应收", "ar", "应付", "ap", "付款",
                    "payment", "发票", "invoice", "回款", "欠款", "dso",
                    "现金", "cash", "对账", "reconciliation"]),
    ("suppliers", ["供应商", "supplier", "交期", "lead time", "供货",
                    "采购单", "purchase order"]),
]

# ---------------------------------------------------------------------------
# Helpers: domain detection
# ---------------------------------------------------------------------------

def _detect_domains(query: str) -> list[str]:
    """Return a list of domain names mentioned in the query, in order of
    keyword-match count (most hits first)."""
    qlower = query.lower()
    scores: dict[str, int] = {}
    for domain, keywords in DOMAIN_PATTERNS:
        score = sum(1 for kw in keywords if kw.lower() in qlower)
        if score > 0:
            scores[domain] = score
    # Sort by score descending, then alphabetically
    return sorted(scores, key=lambda d: (-scores[d], d))


# ---------------------------------------------------------------------------
# Context builders — each returns a compact string summary
# ---------------------------------------------------------------------------

async def _build_customer_context(db: AsyncSession) -> str:
    # Total count
    total_r = await db.execute(
        select(func.count(Customer.id)).where(Customer.deleted_at.is_(None))
    )
    total = total_r.scalar() or 0

    # Top 5 by recent activity (last_contacted_at)
    top_r = await db.execute(
        select(Customer.name, Customer.level, Customer.industry, Customer.last_contacted_at)
        .where(Customer.deleted_at.is_(None))
        .order_by(Customer.last_contacted_at.desc().nullslast())
        .limit(5)
    )
    top = top_r.all()

    # Level distribution
    level_r = await db.execute(
        select(Customer.level, func.count(Customer.id))
        .where(Customer.deleted_at.is_(None), Customer.level.isnot(None))
        .group_by(Customer.level)
    )
    levels = {r[0]: r[1] for r in level_r.all()}

    # Recent orders count (last 30 days)
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

    # Category distribution
    cat_r = await db.execute(
        select(Product.category, func.count(Product.id))
        .where(Product.deleted_at.is_(None), Product.category.isnot(None))
        .group_by(Product.category)
        .order_by(func.count(Product.id).desc())
    )
    cats = {r[0]: r[1] for r in cat_r.all()}

    # Top 5 products (by recent order items would be ideal, but we use total
    # and brand lookup as a reasonable proxy)
    top_r = await db.execute(
        select(Product.name, Brand.name, Product.category)
        .join(Brand, Product.brand_id == Brand.id, isouter=True)
        .where(Product.deleted_at.is_(None))
        .order_by(Product.updated_at.desc().nullslast())
        .limit(5)
    )
    top = top_r.all()

    # Brand count
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
    # This month revenue
    month_r = await db.execute(
        select(func.coalesce(func.sum(SalesOrder.total_amount), 0))
        .where(
            SalesOrder.created_at >= text("date_trunc('month', NOW())"),
            SalesOrder.deleted_at.is_(None),
        )
    )
    month_revenue = float(month_r.scalar() or 0)

    # Month order count
    month_cnt_r = await db.execute(
        select(func.count(SalesOrder.id))
        .where(
            SalesOrder.created_at >= text("date_trunc('month', NOW())"),
            SalesOrder.deleted_at.is_(None),
        )
    )
    month_orders = month_cnt_r.scalar() or 0

    # Recent 5 orders
    recent_r = await db.execute(
        select(SalesOrder.order_no, SalesOrder.total_amount, SalesOrder.status,
               Customer.name)
        .join(Customer, SalesOrder.customer_id == Customer.id, isouter=True)
        .where(SalesOrder.deleted_at.is_(None))
        .order_by(SalesOrder.created_at.desc())
        .limit(5)
    )
    recent = recent_r.all()

    # Opportunity pipeline
    opp_r = await db.execute(
        select(func.count(Opportunity.id), func.coalesce(func.sum(Opportunity.amount), 0))
        .where(Opportunity.deleted_at.is_(None))
    )
    opp_row = opp_r.one()
    opp_count, opp_value = opp_row[0] or 0, float(opp_row[1] or 0)

    # Order status breakdown
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
    # Total stock value (approximate — we don't have cost per inventory line
    # stored in the inventory table itself, so we count items)
    total_r = await db.execute(
        select(func.count(Inventory.id)).where(Inventory.quantity > 0)
    )
    total_items = total_r.scalar() or 0

    # Low stock items (quantity <= safety_stock)
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

    # Warehouse counts
    wh_r = await db.execute(
        select(Warehouse.name, func.count(Inventory.id))
        .join(Inventory, Warehouse.id == Inventory.warehouse_id, isouter=True)
        .group_by(Warehouse.name)
    )
    warehouses = {r[0]: r[1] for r in wh_r.all()}

    # Pending POs
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
    # AR summary
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

    # Overdue invoices
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

    # Recent payments (transaction.Payment where type == 'receipt')
    recent_pay_r = await db.execute(
        select(Payment.payment_no, Payment.amount, Payment.method, Payment.paid_at,
               Customer.name)
        .join(Customer, Payment.customer_id == Customer.id, isouter=True)
        .where(Payment.type == "receipt", Payment.deleted_at.is_(None))
        .order_by(Payment.paid_at.desc().nullslast())
        .limit(5)
    )
    recent_payments = recent_pay_r.all()

    # AP — payments to suppliers (unpaid)
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

    # Pending POs per supplier
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
# Main entry point
# ---------------------------------------------------------------------------

async def natural_language_query(db: AsyncSession, query: str) -> dict[str, Any]:
    """Process a natural-language query against the ERP system.

    Smart context selection:
    - Fewer than 3 characters → no context (probable test/greeting).
    - Single-domain queries: include that domain's full context + summary
      counts from all other domains.
    - Multi-domain or ambiguous queries: include full context from all
      matched domains + summary from the rest.
    - Complex queries (long, multi-domain): include everything.

    Returns a dict with ``answer``, ``related_entities``,
    ``suggested_followups``, ``actions``, and ``confidence``.
    """

    # ---------- detect domain ----------
    domains = _detect_domains(query)
    all_domains = [d for d, _ in DOMAIN_PATTERNS]

    # ---------- build context ----------
    context: dict[str, str] = {}

    if len(query.strip()) < 3:
        # Trivial query — skip heavy DB work
        pass
    elif len(domains) <= 1:
        # Single-domain: full context for that domain (or general if none
        # detected) plus lightweight summary for the rest
        primary = domains[0] if domains else "general"
        for d in all_domains:
            if d == primary or (primary == "general" and len(query) > 10):
                context[f"{d}_context"] = await _build_context_for(d, db)
            else:
                context[f"{d}_context"] = await _build_summary_context_for(d, db)
    else:
        # Multi-domain: full context for each detected domain, summary for rest
        for d in all_domains:
            if d in domains or len(domains) >= 3:
                context[f"{d}_context"] = await _build_context_for(d, db)
            else:
                context[f"{d}_context"] = await _build_summary_context_for(d, db)

    # ---------- call AI ----------
    output_schema: dict[str, Any] = {
        "answer": "string: 中文自然语言回答，清晰直接",
        "data_summary": "string: 支撑答案的数据摘要，1-2句话",
        "related_entities": (
            "list of dicts: {type: string (customer/product/order/opportunity/"
            "supplier/invoice), id: integer, name: string, relevance: string}"
        ),
        "suggested_followups": "list of strings: 建议追问的问题，2-3条",
        "actions": (
            "list of dicts: {action: string, type: string, entity: string, "
            "urgency: string (高/中/低)} — 如果答案暗示了可执行的操作"
        ),
        "confidence": "integer 0-100: 回答置信度",
    }

    try:
        system_prompt = (
            "你是一个电子元器件分销ERP系统的智能助手。"
            "基于提供的ERP数据上下文，用中文自然语言回答用户问题。"
            "回答应数据驱动、准确、可执行。"
            "如果数据不足以回答，诚实说明并建议如何获取数据。"
        )
        result = await ai_client.chat_structured(
            [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": nlp_query_prompt(query, context)},
            ],
            output_schema,
            temperature=0.3,
        )
        return result
    except Exception as exc:
        logger.exception("NLP query failed")
        return {
            "answer": f"抱歉，查询处理失败：{exc}",
            "data_summary": "",
            "related_entities": [],
            "suggested_followups": [],
            "actions": [],
            "confidence": 0,
        }


# ---------------------------------------------------------------------------
# Internal: context builder dispatchers
# ---------------------------------------------------------------------------

_BUILDERS: dict[str, Any] = {
    "customers":  _build_customer_context,
    "products":   _build_product_context,
    "sales":      _build_sales_context,
    "inventory":  _build_inventory_context,
    "finance":    _build_finance_context,
    "suppliers":  _build_supplier_context,
}


async def _build_context_for(domain: str, db: AsyncSession) -> str:
    builder = _BUILDERS.get(domain)
    if builder is None:
        return "无数据"
    try:
        return await builder(db)
    except Exception as exc:
        logger.warning("Context build failed for %s: %s", domain, exc)
        return f"数据获取失败: {exc}"


async def _build_summary_context_for(domain: str, db: AsyncSession) -> str:
    """Lightweight summary — only counts and totals, no detail rows."""
    try:
        if domain == "customers":
            r = await db.execute(
                select(func.count(Customer.id)).where(Customer.deleted_at.is_(None))
            )
            return f"客户总数：{r.scalar() or 0}"
        elif domain == "products":
            r = await db.execute(
                select(func.count(Product.id)).where(Product.deleted_at.is_(None))
            )
            br = await db.execute(
                select(func.count(Brand.id)).where(Brand.deleted_at.is_(None))
            )
            return f"产品总数：{r.scalar() or 0}，品牌数：{br.scalar() or 0}"
        elif domain == "sales":
            r = await db.execute(
                select(func.coalesce(func.sum(SalesOrder.total_amount), 0))
                .where(
                    SalesOrder.created_at >= text("date_trunc('month', NOW())"),
                    SalesOrder.deleted_at.is_(None),
                )
            )
            return f"本月销售额：{float(r.scalar() or 0):,.2f}"
        elif domain == "inventory":
            r = await db.execute(
                select(func.count(Inventory.id)).where(Inventory.quantity > 0)
            )
            return f"有库存产品项数：{r.scalar() or 0}"
        elif domain == "finance":
            r = await db.execute(
                select(func.coalesce(func.sum(Invoice.amount), 0))
                .where(Invoice.status.notin_(["paid", "cancelled"]),
                       Invoice.deleted_at.is_(None))
            )
            return f"应收账款总额：{float(r.scalar() or 0):,.2f}"
        elif domain == "suppliers":
            r = await db.execute(
                select(func.count(Supplier.id)).where(Supplier.deleted_at.is_(None))
            )
            return f"供应商总数：{r.scalar() or 0}"
        else:
            return "无数据"
    except Exception as exc:
        return f"数据获取失败: {exc}"
