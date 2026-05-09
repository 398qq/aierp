"""Purchase Order intelligence — optimization, auto-suggestion, risk assessment."""

import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.product import Inventory, Product, Supplier, SupplierProduct
from app.models.transaction import PurchaseOrder, PurchaseOrderItem

logger = logging.getLogger(__name__)


async def optimize_purchase_order(db: AsyncSession, order_id: int) -> dict:
    """AI-powered PO optimization: reviews quantities against stock, recommends supplier splits."""
    from app.services.ai.client import ai_client
    from app.services.ai.prompts import po_optimization_prompt

    # Query PO with supplier
    po = (await db.execute(
        select(PurchaseOrder).where(
            PurchaseOrder.id == order_id, PurchaseOrder.deleted_at.is_(None)
        )
    )).scalar_one_or_none()
    if not po:
        raise ValueError("Purchase order not found")

    supplier = (await db.execute(
        select(Supplier).where(Supplier.id == po.supplier_id, Supplier.deleted_at.is_(None))
    )).scalar_one_or_none()

    # Get items with product info
    item_rows = (await db.execute(
        select(PurchaseOrderItem, Product)
        .join(Product, PurchaseOrderItem.product_id == Product.id)
        .where(
            PurchaseOrderItem.order_id == order_id,
            PurchaseOrderItem.deleted_at.is_(None),
        )
    )).all()

    if not item_rows:
        raise ValueError("Purchase order has no items")

    product_ids = [row.Product.id for row in item_rows]

    items_detail_lines = []
    for item, prod in item_rows:
        items_detail_lines.append(
            f"{prod.name}(SKU:{prod.sku or '无'}): 数量{item.quantity}, "
            f"单价{item.unit_price}, 金额{item.amount}"
        )
    items_detail = "\n".join(items_detail_lines)

    # Get inventory for these products
    inv_rows = (await db.execute(
        select(Inventory, Product)
        .join(Product, Inventory.product_id == Product.id)
        .where(
            Inventory.product_id.in_(product_ids),
            Inventory.deleted_at.is_(None),
        )
    )).all() if product_ids else []

    current_stock = ", ".join(
        [f"{p.name}: {inv.quantity} (安全库存:{inv.safety_stock})"
         for inv, p in inv_rows]
    ) if inv_rows else "无库存数据"

    safety_stock = ", ".join(
        [f"{p.name}: {inv.safety_stock}" for inv, p in inv_rows]
    ) if inv_rows else "无数据"

    # Daily consumption from recent inventory transactions (stock_out, last 30 days)
    now = datetime.now(timezone.utc)
    d30 = now - timedelta(days=30)
    daily_consumption = "无数据"
    if product_ids:
        from app.models.product import InventoryTransaction
        tx_rows = (await db.execute(
            select(
                InventoryTransaction.product_id,
                func.coalesce(func.sum(InventoryTransaction.quantity), 0),
            )
            .where(
                InventoryTransaction.product_id.in_(product_ids),
                InventoryTransaction.type == "stock_out",
                InventoryTransaction.created_at >= d30,
                InventoryTransaction.deleted_at.is_(None),
            )
            .group_by(InventoryTransaction.product_id)
        )).all()
        if tx_rows:
            inv_map = {p.id: p.name for _, p in inv_rows}
            parts = []
            for pid, total_qty in tx_rows:
                product_name = inv_map.get(pid, f"产品#{pid}")
                parts.append(f"{product_name}: 日均{round(float(total_qty) / 30, 1)}")
            daily_consumption = ", ".join(parts)

    # Alternative supplier quotes for the same products (excluding the PO's supplier)
    alt_quote_rows = (await db.execute(
        select(SupplierProduct, Product, Supplier)
        .join(Product, SupplierProduct.product_id == Product.id)
        .join(Supplier, SupplierProduct.supplier_id == Supplier.id)
        .where(
            SupplierProduct.product_id.in_(product_ids),
            SupplierProduct.supplier_id != po.supplier_id,
            SupplierProduct.deleted_at.is_(None),
            Product.deleted_at.is_(None),
            Supplier.deleted_at.is_(None),
        )
        .order_by(SupplierProduct.cost_price.asc())
        .limit(20)
    )).all()

    if alt_quote_rows:
        alt_lines = []
        for sp, prod, sup in alt_quote_rows:
            alt_lines.append(
                f"{sup.name}: {prod.name} 单价{sp.cost_price}, "
                f"交期{sp.lead_time_days or '未知'}天, MOQ{sp.moq or 1}"
            )
        alternative_quotes = "\n".join(alt_lines)
    else:
        alternative_quotes = "无替代报价"

    # Build context for AI
    po_data = {
        "order_no": po.order_no or "无",
        "supplier_name": supplier.name if supplier else "无数据",
        "total_amount": float(po.total_amount or 0),
        "items_detail": items_detail,
        "current_stock": current_stock,
        "safety_stock": safety_stock,
        "daily_consumption": daily_consumption,
        "alternative_quotes": alternative_quotes,
    }

    schema = {
        "optimization_score": "integer 0-100",
        "quantity_advice": [
            {"product_name": "string", "ordered": "integer", "suggested": "integer", "reason": "string"}
        ],
        "supplier_split": [
            {"supplier_name": "string", "product_name": "string", "quantity": "integer",
             "price": "number", "saving": "number"}
        ],
        "timing_advice": "string",
        "risk_flags": ["string"],
        "total_saving_estimate": "number",
    }
    try:
        result = await ai_client.chat_structured(
            [{"role": "system", "content": "你是一个电子元器件采购优化专家。"},
             {"role": "user", "content": po_optimization_prompt(po_data)}],
            schema,
        )
    except ValueError as e:
        logging.getLogger(__name__).warning(f"optimize_purchase_order AI failed: {e}")
        result = {
            "optimization_score": 50,
            "quantity_advice": [],
            "supplier_split": [],
            "timing_advice": "AI分析暂时不可用",
            "risk_flags": [],
            "total_saving_estimate": 0,
        }
    result["context"] = po_data
    return result


async def suggest_purchase_orders(db: AsyncSession) -> dict:
    """AI scans all products below safety stock and suggests purchase orders."""
    from app.services.ai.client import ai_client
    from app.services.ai.prompts import po_auto_suggest_prompt

    # Find all products below safety stock
    low_stock_rows = (await db.execute(
        select(Inventory, Product)
        .join(Product, Inventory.product_id == Product.id)
        .where(
            Inventory.quantity < Inventory.safety_stock,
            Inventory.safety_stock > 0,
            Inventory.deleted_at.is_(None),
            Product.deleted_at.is_(None),
        )
        .order_by((Inventory.safety_stock - Inventory.quantity).desc())
        .limit(50)
    )).all()

    if not low_stock_rows:
        return {
            "urgency_level": "低",
            "suggested_pos": [],
            "total_estimated_amount": 0,
            "prioritization": "无产品低于安全库存",
            "inventory_health_score": 100,
            "context": {"low_stock_count": 0},
        }

    low_stock_product_ids = [prod.id for _, prod in low_stock_rows]

    # Stock alerts detail
    stock_alerts_lines = []
    low_stock_items_lines = []
    for inv, prod in low_stock_rows:
        gap = inv.safety_stock - inv.quantity
        stock_alerts_lines.append(
            f"产品: {prod.name}(SKU:{prod.sku or '无'}) | "
            f"当前库存: {inv.quantity} | 安全库存: {inv.safety_stock} | "
            f"缺口: {gap} | 分类: {prod.category or '未知'}"
        )
        low_stock_items_lines.append(
            f"{prod.name}(ID:{prod.id}): 库存{inv.quantity}, "
            f"安全库存{inv.safety_stock}, 缺口{gap}"
        )
    stock_alerts = "\n".join(stock_alerts_lines)
    low_stock_items = "\n".join(low_stock_items_lines)

    # Get supplier quotes for these low-stock products
    supplier_quote_rows = (await db.execute(
        select(SupplierProduct, Product, Supplier)
        .join(Product, SupplierProduct.product_id == Product.id)
        .join(Supplier, SupplierProduct.supplier_id == Supplier.id)
        .where(
            SupplierProduct.product_id.in_(low_stock_product_ids),
            SupplierProduct.cost_price.isnot(None),
            SupplierProduct.deleted_at.is_(None),
            Product.deleted_at.is_(None),
            Supplier.deleted_at.is_(None),
        )
        .order_by(SupplierProduct.is_preferred.desc(), SupplierProduct.cost_price.asc())
        .limit(200)
    )).all()

    if supplier_quote_rows:
        quote_lines = []
        for sp, prod, sup in supplier_quote_rows:
            quote_lines.append(
                f"{sup.name}: {prod.name} 单价{sp.cost_price}, "
                f"交期{sp.lead_time_days or '?'}天, "
                f"MOQ{sp.moq or 1}, SPQ{sp.spq or 1}, "
                f"{'首选' if sp.is_preferred else '普通'}"
            )
        supplier_quotes = "\n".join(quote_lines)
    else:
        supplier_quotes = "无供应商报价"

    # MOQ info summary
    moq_lines = []
    for sp, prod, sup in supplier_quote_rows:
        if sp.moq and sp.moq > 1:
            moq_lines.append(f"{sup.name}/{prod.name}: MOQ={sp.moq}, SPQ={sp.spq or 1}")
    moq_info = "\n".join(moq_lines[:30]) if moq_lines else "无MOQ数据"

    # Purchase frequency: count POs for these products in the last 90 days
    now = datetime.now(timezone.utc)
    d90 = now - timedelta(days=90)
    freq_rows = (await db.execute(
        select(
            Product.name,
            func.count(PurchaseOrderItem.id),
            func.coalesce(func.sum(PurchaseOrderItem.quantity), 0),
        )
        .join(Product, PurchaseOrderItem.product_id == Product.id)
        .where(
            PurchaseOrderItem.product_id.in_(low_stock_product_ids),
            PurchaseOrderItem.created_at >= d90,
            PurchaseOrderItem.deleted_at.is_(None),
            Product.deleted_at.is_(None),
        )
        .group_by(Product.name)
    )).all()

    if freq_rows:
        freq_lines = [
            f"{name}: {cnt}次采购, 合计{qty}件" for name, cnt, qty in freq_rows
        ]
        purchase_frequency = "\n".join(freq_lines)
    else:
        purchase_frequency = "近90天无采购记录"

    po_data = {
        "stock_alerts": stock_alerts,
        "low_stock_items": low_stock_items,
        "purchase_frequency": purchase_frequency,
        "supplier_quotes": supplier_quotes,
        "moq_info": moq_info,
    }

    schema = {
        "urgency_level": "string: 低/中/高/紧急",
        "suggested_pos": [
            {"supplier_name": "string", "product_name": "string", "quantity": "integer",
             "estimated_price": "number", "estimated_amount": "number",
             "urgency": "string", "reason": "string"}
        ],
        "total_estimated_amount": "number",
        "prioritization": "string",
        "inventory_health_score": "integer 0-100",
    }
    try:
        result = await ai_client.chat_structured(
            [{"role": "system", "content": "你是一个电子元器件库存管理专家。"},
             {"role": "user", "content": po_auto_suggest_prompt(po_data)}],
            schema,
        )
    except ValueError as e:
        logging.getLogger(__name__).warning(f"suggest_purchase_orders AI failed: {e}")
        result = {
            "urgency_level": "中",
            "suggested_pos": [],
            "total_estimated_amount": 0,
            "prioritization": "AI分析暂时不可用",
            "inventory_health_score": 50,
        }
    result["context"] = {
        "low_stock_count": len(low_stock_rows),
        "supplier_count": len(set(r[2].id for r in supplier_quote_rows)) if supplier_quote_rows else 0,
    }
    return result


async def assess_po_risk(db: AsyncSession, order_id: int) -> dict:
    """AI performs comprehensive risk assessment on a purchase order."""
    from app.services.ai.client import ai_client
    from app.services.ai.prompts import po_risk_assessment_prompt

    # Query PO with supplier
    po = (await db.execute(
        select(PurchaseOrder).where(
            PurchaseOrder.id == order_id, PurchaseOrder.deleted_at.is_(None)
        )
    )).scalar_one_or_none()
    if not po:
        raise ValueError("Purchase order not found")

    supplier = (await db.execute(
        select(Supplier).where(Supplier.id == po.supplier_id, Supplier.deleted_at.is_(None))
    )).scalar_one_or_none()

    # Get items with product info
    item_rows = (await db.execute(
        select(PurchaseOrderItem, Product)
        .join(Product, PurchaseOrderItem.product_id == Product.id)
        .where(
            PurchaseOrderItem.order_id == order_id,
            PurchaseOrderItem.deleted_at.is_(None),
        )
    )).all()

    if not item_rows:
        raise ValueError("Purchase order has no items")

    [row.Product.id for row in item_rows]

    # --- Supplier history: delay rate ---
    now = datetime.now(timezone.utc)
    d365 = now - timedelta(days=365)

    # Total POs for this supplier in the last 12 months
    total_pos = (await db.execute(
        select(func.count(PurchaseOrder.id))
        .where(
            PurchaseOrder.supplier_id == po.supplier_id,
            PurchaseOrder.id != order_id,
            PurchaseOrder.created_at >= d365,
            PurchaseOrder.deleted_at.is_(None),
        )
    )).scalar() or 0

    # Delayed/overdue POs: status not in terminal completed states AND expected_date past
    delayed_pos = (await db.execute(
        select(func.count(PurchaseOrder.id))
        .where(
            PurchaseOrder.supplier_id == po.supplier_id,
            PurchaseOrder.id != order_id,
            PurchaseOrder.expected_date.isnot(None),
            PurchaseOrder.expected_date < now,
            PurchaseOrder.status.notin_(["received", "completed", "cancelled"]),
            PurchaseOrder.deleted_at.is_(None),
        )
    )).scalar() or 0

    supplier_delay_rate = round((delayed_pos / max(total_pos, 1)) * 100, 1)

    # --- Quality issues from notes ---
    quality_issue_rows = (await db.execute(
        select(PurchaseOrder.notes)
        .where(
            PurchaseOrder.supplier_id == po.supplier_id,
            PurchaseOrder.id != order_id,
            PurchaseOrder.deleted_at.is_(None),
            PurchaseOrder.notes.isnot(None),
        )
        .limit(100)
    )).all()

    quality_keywords = ["质量", "缺陷", "退货", "不良", "损坏", "quality", "defect", "damage", "返工", "NG"]
    quality_issue_count = 0
    quality_notes = []
    for (note,) in quality_issue_rows:
        if note and any(kw in (note or "").lower() for kw in quality_keywords):
            quality_issue_count += 1
            quality_notes.append(note[:100])

    supplier_quality_rate = round(
        (quality_issue_count / max(len(quality_issue_rows), 1)) * 100, 1
    )

    supplier_financial = "未知"
    if supplier and supplier.notes:
        if any(kw in (supplier.notes or "").lower() for kw in ["稳定", "良好", "优质"]):
            supplier_financial = "稳定"
        elif any(kw in (supplier.notes or "").lower() for kw in ["风险", "困难", "预警"]):
            supplier_financial = "需关注"

    # --- Item risks ---
    item_risk_lines = []
    for item, prod in item_rows:
        # Check inventory
        inv = (await db.execute(
            select(func.coalesce(func.sum(Inventory.quantity), 0))
            .where(
                Inventory.product_id == prod.id,
                Inventory.deleted_at.is_(None),
            )
        )).scalar() or 0

        # Check supplier count for this product
        sup_count = (await db.execute(
            select(func.count(SupplierProduct.id))
            .where(
                SupplierProduct.product_id == prod.id,
                SupplierProduct.deleted_at.is_(None),
            )
        )).scalar() or 0

        risk_tags = []
        if sup_count == 0:
            risk_tags.append("无供应商")
        elif sup_count == 1:
            risk_tags.append("单源供应")
        if float(item.amount or 0) > float(po.total_amount or 1) * 0.5:
            risk_tags.append("金额占比高")

        item_risk_lines.append(
            f"{prod.name}: 数量{item.quantity}, 金额{item.amount}, "
            f"当前库存{inv}, 供应商数{sup_count}, "
            f"风险: {'; '.join(risk_tags) if risk_tags else '无明显风险'}"
        )
    item_risks = "\n".join(item_risk_lines)

    # --- Market context ---
    # Aggregate categories from PO items
    categories = list(set(
        prod.category for _, prod in item_rows if prod.category
    ))
    market_supply = "未知"
    market_price_trend = "未知"
    if categories:
        # Check if these categories have many competing suppliers (crude proxy)
        cat_sup_count = (await db.execute(
            select(func.count(func.distinct(SupplierProduct.supplier_id)))
            .join(Product, SupplierProduct.product_id == Product.id)
            .where(
                Product.category.in_(categories),
                SupplierProduct.deleted_at.is_(None),
                Product.deleted_at.is_(None),
            )
        )).scalar() or 0
        if cat_sup_count >= 5:
            market_supply = "供应充足"
        elif cat_sup_count >= 2:
            market_supply = "供应一般"
        else:
            market_supply = "供应紧张"

        # Price trend: compare recent SupplierProduct costs vs older ones
        d90 = now - timedelta(days=90)
        recent_cost = (await db.execute(
            select(func.avg(SupplierProduct.cost_price))
            .join(Product, SupplierProduct.product_id == Product.id)
            .where(
                Product.category.in_(categories),
                SupplierProduct.created_at >= d90,
                SupplierProduct.cost_price.isnot(None),
                SupplierProduct.deleted_at.is_(None),
                Product.deleted_at.is_(None),
            )
        )).scalar()
        older_cost = (await db.execute(
            select(func.avg(SupplierProduct.cost_price))
            .join(Product, SupplierProduct.product_id == Product.id)
            .where(
                Product.category.in_(categories),
                SupplierProduct.created_at < d90,
                SupplierProduct.cost_price.isnot(None),
                SupplierProduct.deleted_at.is_(None),
                Product.deleted_at.is_(None),
            )
        )).scalar()

        if recent_cost and older_cost:
            change_pct = (float(recent_cost) - float(older_cost)) / float(older_cost) * 100
            if change_pct > 5:
                market_price_trend = f"上涨({change_pct:.1f}%)"
            elif change_pct < -5:
                market_price_trend = f"下跌({abs(change_pct):.1f}%)"
            else:
                market_price_trend = "稳定"
        else:
            market_price_trend = "无足够数据"

    po_data = {
        "order_no": po.order_no or "无",
        "supplier_name": supplier.name if supplier else "无数据",
        "total_amount": float(po.total_amount or 0),
        "expected_date": str(po.expected_date)[:10] if po.expected_date else "无数据",
        "supplier_delay_rate": supplier_delay_rate,
        "supplier_quality_rate": supplier_quality_rate,
        "supplier_financial": supplier_financial,
        "item_risks": item_risks,
        "market_supply": market_supply,
        "price_trend": market_price_trend,
    }

    schema = {
        "overall_risk": "string: 低/中/高",
        "risk_score": "integer 0-100",
        "risk_factors": [
            {"factor": "string", "severity": "string", "impact": "string"}
        ],
        "delivery_risk": "string",
        "price_risk": "string",
        "quality_risk": "string",
        "mitigation_plan": ["string"],
        "go_no_go": "string: 执行/暂缓/取消",
    }
    try:
        result = await ai_client.chat_structured(
            [{"role": "system", "content": "你是一个电子元器件采购风控专家。"},
             {"role": "user", "content": po_risk_assessment_prompt(po_data)}],
            schema,
        )
    except ValueError as e:
        logging.getLogger(__name__).warning(f"assess_po_risk AI failed: {e}")
        result = {
            "overall_risk": "中",
            "risk_score": 50,
            "risk_factors": [],
            "delivery_risk": "AI分析暂时不可用",
            "price_risk": "AI分析暂时不可用",
            "quality_risk": "AI分析暂时不可用",
            "mitigation_plan": [],
            "go_no_go": "暂缓",
        }
    result["context"] = {
        "order_id": order_id,
        "supplier_id": po.supplier_id,
        "total_pos_history": total_pos,
        "delayed_pos_count": delayed_pos,
        "quality_issue_count": quality_issue_count,
    }
    return result
