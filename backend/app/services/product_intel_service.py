"""Product intelligence — profile, associations, spec normalization, lifecycle, procurement."""

import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.product import Brand, Inventory, Product, Supplier, SupplierProduct
from app.models.sales import SalesOrder, SalesOrderItem

logger = logging.getLogger(__name__)


async def generate_product_profile(db: AsyncSession, product_id: int) -> dict:
    """AI-generated product intelligence card."""
    from app.services.ai.client import ai_client
    from app.services.ai.prompts import product_profile_prompt

    prod_row = (await db.execute(
        select(Product.sku, Product.name, Product.category, Product.package_type,
               Product.specs, Product.notes, Brand.name, Brand.name_cn, Product.brand_id)
        .outerjoin(Brand, Product.brand_id == Brand.id)
        .where(Product.id == product_id, Product.deleted_at.is_(None))
    )).first()
    if prod_row is None:
        raise ValueError("Product not found")

    # Business context
    total_sold = (await db.execute(
        select(func.coalesce(func.sum(SalesOrderItem.quantity), 0))
        .where(SalesOrderItem.product_id == product_id, SalesOrderItem.deleted_at.is_(None))
    )).scalar() or 0

    active_customers = (await db.execute(
        select(func.count(func.distinct(SalesOrder.customer_id)))
        .select_from(SalesOrderItem)
        .join(SalesOrder, SalesOrderItem.order_id == SalesOrder.id)
        .where(SalesOrderItem.product_id == product_id,
               SalesOrderItem.deleted_at.is_(None),
               SalesOrder.deleted_at.is_(None),
               SalesOrder.created_at >= datetime.now(timezone.utc) - timedelta(days=365))
    )).scalar() or 0

    supplier_count = (await db.execute(
        select(func.count(SupplierProduct.id)).where(
            SupplierProduct.product_id == product_id, SupplierProduct.deleted_at.is_(None))
    )).scalar() or 0

    stock_qty = (await db.execute(
        select(func.coalesce(func.sum(Inventory.quantity), 0))
        .where(Inventory.product_id == product_id, Inventory.deleted_at.is_(None))
    )).scalar() or 0

    stock_health = "正常"
    if stock_qty == 0:
        stock_health = "缺货"
    elif supplier_count == 0:
        stock_health = "无供应商"

    context = {
        "part_number": f"{prod_row[0] or ''} {prod_row[1]}".strip(),
        "category": prod_row[2] or "未知",
        "brand": prod_row[6] or prod_row[7] or "未知",
        "package_type": prod_row[3] or "未知",
        "specs": prod_row[4] or "",
        "description": prod_row[5] or "",
        "total_sold": total_sold,
        "active_customers": active_customers,
        "supplier_count": supplier_count,
        "stock_qty": stock_qty,
        "stock_health": stock_health,
    }

    schema = {
        "market_positioning": "string",
        "typical_applications": ["string"],
        "competitor_products": ["string"],
        "target_customers": ["string"],
        "lifecycle_stage": "string",
        "lifecycle_score": "integer 0-100",
        "margin_potential": "string: 高/中/低",
        "demand_stability": "string: 稳定/周期性/波动大",
        "key_selling_points": ["string"],
        "risk_factors": ["string"],
    }
    result = await ai_client.chat_structured(
        [{"role": "system", "content": "你是一个电子元器件产品专家，精通元件市场分析、竞争情报和产品生命周期管理。"},
         {"role": "user", "content": product_profile_prompt(context)}],
        schema,
    )
    result["context"] = context
    return result


async def normalize_specs(db: AsyncSession, product_id: int) -> dict:
    """AI normalizes unstructured spec text into key-value parameters."""
    from app.services.ai.client import ai_client
    from app.services.ai.prompts import spec_normalize_prompt

    prod = (await db.execute(
        select(Product.specs, Product.notes).where(Product.id == product_id, Product.deleted_at.is_(None))
    )).first()
    if prod is None:
        raise ValueError("Product not found")

    raw_text = prod[0] or prod[1] or ""
    if not raw_text.strip():
        return {"parameters": [], "raw": ""}

    schema = {
        "parameters": [
            {"key": "string", "value": "string", "unit": "string | null",
             "display": "string, Chinese display name"}
        ]
    }
    result = await ai_client.chat_structured(
        [{"role": "system", "content": "你是一个电子元器件参数解析专家。精确提取和标准化技术参数。"},
         {"role": "user", "content": spec_normalize_prompt(raw_text)}],
        schema,
    )
    # Persist normalized specs back to product
    import json
    normalized = result.get("parameters", [])
    prod_obj = (await db.execute(
        select(Product).where(Product.id == product_id, Product.deleted_at.is_(None))
    )).scalar_one_or_none()
    if prod_obj and normalized:
        prod_obj.specs = json.dumps({p["key"]: f"{p['value']}{p.get('unit', '')}" for p in normalized}, ensure_ascii=False)
        await db.flush()
    return {"parameters": normalized, "raw": raw_text}


async def get_product_associations(db: AsyncSession, product_id: int, top_k: int = 10) -> dict:
    """Find associated products via collaborative filtering (co-purchase analysis)."""
    datetime.now(timezone.utc) - timedelta(days=90)

    # Find orders containing this product
    order_ids_subq = (
        select(SalesOrderItem.order_id)
        .where(SalesOrderItem.product_id == product_id, SalesOrderItem.deleted_at.is_(None))
        .distinct()
    )

    # Products co-purchased in the same orders
    co_rows = (await db.execute(
        select(
            Product.id, Product.sku, Product.name, Product.category,
            Product.package_type, Brand.name, Brand.name_cn,
            func.count(func.distinct(SalesOrderItem.order_id)).label("co_count"),
            func.sum(SalesOrderItem.quantity).label("co_qty"),
        )
        .join(SalesOrderItem, Product.id == SalesOrderItem.product_id)
        .outerjoin(Brand, Product.brand_id == Brand.id)
        .where(
            SalesOrderItem.order_id.in_(order_ids_subq),
            Product.id != product_id,
            Product.deleted_at.is_(None),
            SalesOrderItem.deleted_at.is_(None),
        )
        .group_by(Product.id, Brand.name, Brand.name_cn)
        .order_by(func.count(func.distinct(SalesOrderItem.order_id)).desc())
        .limit(top_k)
    )).all()

    if not co_rows:
        return {"associations": [], "target_product_id": product_id}

    return {
        "target_product_id": product_id,
        "associations": [
            {
                "product_id": r[0], "sku": r[1], "name": r[2], "category": r[3],
                "package_type": r[4], "brand_name": r[5] or r[6],
                "co_purchase_count": r[7], "co_quantity": int(r[8] or 0),
            }
            for r in co_rows
        ],
    }


async def optimize_procurement(
    db: AsyncSession,
    product_id: int,
    quantity: int,
) -> dict:
    """AI recommends optimal supplier allocation for a given product+quantity."""
    from app.services.ai.client import ai_client
    from app.services.ai.prompts import procurement_optimize_prompt

    prod_row = (await db.execute(
        select(Product.sku, Product.name, Product.category, Brand.name, Brand.name_cn)
        .outerjoin(Brand, Product.brand_id == Brand.id)
        .where(Product.id == product_id, Product.deleted_at.is_(None))
    )).first()
    if prod_row is None:
        raise ValueError("Product not found")

    supplier_rows = (await db.execute(
        select(Supplier.name, SupplierProduct.cost_price, SupplierProduct.lead_time_days,
               SupplierProduct.moq, SupplierProduct.is_preferred)
        .join(SupplierProduct, Supplier.id == SupplierProduct.supplier_id)
        .where(SupplierProduct.product_id == product_id,
               SupplierProduct.deleted_at.is_(None),
               Supplier.deleted_at.is_(None))
        .order_by(SupplierProduct.is_preferred.desc(), SupplierProduct.cost_price.asc())
    )).all()

    stock_qty = (await db.execute(
        select(func.coalesce(func.sum(Inventory.quantity), 0))
        .where(Inventory.product_id == product_id, Inventory.deleted_at.is_(None))
    )).scalar() or 0

    suppliers = [
        {
            "name": r[0], "cost_price": float(r[1]) if r[1] else None,
            "lead_time": r[2], "moq": r[3], "is_preferred": r[4],
        }
        for r in supplier_rows
    ]

    if not suppliers:
        return {"error": "No suppliers linked", "product_id": product_id}

    schema = {
        "recommended_plan": "string",
        "allocations": [
            {"supplier_name": "string", "quantity": "integer", "unit_cost": "number",
             "subtotal": "number", "delivery_days": "integer", "reason": "string"}
        ],
        "total_cost": "number",
        "avg_unit_cost": "number",
        "delivery_risk": "string: 低/中/高",
        "alternative_plan": "string",
        "negotiation_tips": ["string"],
    }
    result = await ai_client.chat_structured(
        [{"role": "system", "content": "你是一个电子元器件供应链采购专家，精通多源采购策略和成本优化。"},
         {"role": "user", "content": procurement_optimize_prompt(
             suppliers,
             {"part_number": f"{prod_row[0] or ''} {prod_row[1]}".strip(),
              "brand": prod_row[3] or prod_row[4] or "未知",
              "stock_qty": stock_qty,
              "market_condition": "正常" if suppliers else "供应紧张"},
             quantity,
         )}],
        schema,
    )
    result["context"] = {
        "product_id": product_id,
        "quantity": quantity,
        "stock_qty": stock_qty,
        "supplier_count": len(suppliers),
    }
    return result


async def analyze_lifecycle(db: AsyncSession, product_id: int) -> dict:
    """AI evaluates product lifecycle stage and EOL/NRND risk."""
    from app.services.ai.client import ai_client
    from app.services.ai.prompts import lifecycle_warning_prompt

    prod_row = (await db.execute(
        select(Product.sku, Product.name, Product.category, Brand.name, Brand.name_cn,
               Product.created_at)
        .outerjoin(Brand, Product.brand_id == Brand.id)
        .where(Product.id == product_id, Product.deleted_at.is_(None))
    )).first()
    if prod_row is None:
        raise ValueError("Product not found")

    now = datetime.now(timezone.utc)
    d3m = now - timedelta(days=90)
    d6m = now - timedelta(days=180)

    # Sales trends
    sales_6m = (await db.execute(
        select(func.coalesce(func.sum(SalesOrderItem.quantity), 0))
        .where(SalesOrderItem.product_id == product_id,
               SalesOrderItem.deleted_at.is_(None),
               SalesOrderItem.created_at >= d6m)
    )).scalar() or 0

    sales_3m = (await db.execute(
        select(func.coalesce(func.sum(SalesOrderItem.quantity), 0))
        .where(SalesOrderItem.product_id == product_id,
               SalesOrderItem.deleted_at.is_(None),
               SalesOrderItem.created_at >= d3m)
    )).scalar() or 0

    sales_before_3m = sales_6m - sales_3m
    trend_6m = "增长" if sales_3m > sales_before_3m * 1.2 else "下降" if sales_3m < sales_before_3m * 0.7 else "稳定"
    trend_3m_desc = f"近3月:{sales_3m} vs 前3月:{sales_before_3m}({trend_6m})"

    # Supplier trends
    supplier_count = (await db.execute(
        select(func.count(SupplierProduct.id)).where(
            SupplierProduct.product_id == product_id, SupplierProduct.deleted_at.is_(None))
    )).scalar() or 0

    active_6m = (await db.execute(
        select(func.count(SupplierProduct.id)).where(
            SupplierProduct.product_id == product_id,
            SupplierProduct.deleted_at.is_(None),
            SupplierProduct.created_at >= d6m)
    )).scalar() or 0

    supplier_trend = "稳定"
    if active_6m == 0 and supplier_count > 0:
        supplier_trend = "收缩中"
    elif active_6m > 0:
        supplier_trend = "活跃"

    # Price trend from supplier costs
    cost_rows = (await db.execute(
        select(SupplierProduct.cost_price)
        .where(SupplierProduct.product_id == product_id,
               SupplierProduct.deleted_at.is_(None),
               SupplierProduct.cost_price.isnot(None))
        .order_by(SupplierProduct.created_at.desc())
        .limit(10)
    )).all()
    price_trend = "无数据"
    if len(cost_rows) >= 3:
        recent_avg = sum(float(r[0]) for r in cost_rows[:3]) / 3
        older_avg = sum(float(r[0]) for r in cost_rows[3:]) / max(len(cost_rows) - 3, 1)
        if recent_avg > older_avg * 1.1:
            price_trend = "上涨"
        elif recent_avg < older_avg * 0.9:
            price_trend = "下跌"
        else:
            price_trend = "稳定"

    context = {
        "part_number": f"{prod_row[0] or ''} {prod_row[1]}".strip(),
        "brand": prod_row[3] or prod_row[4] or "未知",
        "category": prod_row[2] or "未知",
        "introduced_at": str(prod_row[5])[:10] if prod_row[5] else "未知",
        "sales_trend_6m": f"总销量:{sales_6m}",
        "sales_trend_3m": trend_3m_desc,
        "supplier_trend": supplier_trend,
        "lead_time_trend": "无数据",
        "price_trend": price_trend,
    }

    schema = {
        "lifecycle_stage": "string: 活跃/成熟/NRND/EOL",
        "stage_confidence": "integer 0-100",
        "warning_signals": ["string"],
        "eol_risk_score": "integer 0-100",
        "eol_estimated_months": "integer | null",
        "stock_strategy": "string: 不备/备3个月/备6个月/紧急备货",
        "suggested_quantity": "integer",
        "migration_path": "string | null",
        "urgency": "string: 紧急/建议关注/正常",
    }
    result = await ai_client.chat_structured(
        [{"role": "system", "content": "你是一个电子元器件生命周期管理专家，精通产品EOL预测和备货策略。"},
         {"role": "user", "content": lifecycle_warning_prompt(context)}],
        schema,
    )
    result["context"] = context
    return result
