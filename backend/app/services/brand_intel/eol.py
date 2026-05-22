"""EOL (End-of-Life) scanning and alternatives."""

import datetime
import logging

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.product import Brand, Inventory, Product
from app.models.sales import SalesOrderItem

logger = logging.getLogger(__name__)


async def scan_eol_alerts(db: AsyncSession, urgency_threshold: str = "warning") -> dict:
    """
    Scan all brands/products for EOL (End-of-Life) and NRND (Not Recommended for New Designs) risks.
    Returns structured alerts with alternative brand recommendations.

    urgency_threshold: filter by minimum severity — info / warning / critical
    """
    severity_order = {"info": 0, "warning": 1, "critical": 2}

    at_risk_brands = (await db.execute(
        select(Brand).where(
            Brand.deleted_at.is_(None),
            Brand.lifecycle_stage.in_(["eol", "nrnd"]),
        )
    )).scalars().all()

    alerts = []

    for brand in at_risk_brands:
        prods = (await db.execute(
            select(Product.id, Product.sku, Product.name)
            .where(Product.brand_id == brand.id, Product.deleted_at.is_(None))
        )).all()

        if not prods:
            continue

        prod_ids = [p.id for p in prods]
        sales_q = (await db.execute(
            select(func.coalesce(func.sum(SalesOrderItem.total_price), 0))
            .where(SalesOrderItem.product_id.in_(prod_ids), SalesOrderItem.deleted_at.is_(None))
        )).scalar() or 0

        alt_brands = (await db.execute(
            select(Brand.id, Brand.name)
            .where(
                Brand.deleted_at.is_(None),
                Brand.category == brand.category,
                Brand.lifecycle_stage == "active",
                Brand.id != brand.id,
            )
            .limit(3)
        )).all()

        alt_names = [b.name for b in alt_brands] if alt_brands else []

        stage_label = "已停产(EOL)" if brand.lifecycle_stage == "eol" else "不推荐新设计(NRND)"
        severity = "critical" if brand.lifecycle_stage == "eol" and float(sales_q) > 0 else "warning"

        alerts.append({
            "brand_id": brand.id,
            "brand_name": brand.name,
            "lifecycle_stage": brand.lifecycle_stage,
            "stage_label": stage_label,
            "severity": severity,
            "affected_products": len(prods),
            "product_list": [f"{p.sku or ''} {p.name}".strip() for p in prods[:10]],
            "sales_exposure": float(sales_q),
            "alternative_brands": alt_names,
            "recommended_action": (
                f"立即为 {len(prods)} 个在售型号寻找替代品牌"
                if alt_names else "需人工评估替代方案"
            ),
        })

    alerts.sort(
        key=lambda a: (
            -severity_order.get(a["severity"], 0),
            -a["sales_exposure"],
        )
    )

    total = len(alerts)
    critical = sum(1 for a in alerts if a["severity"] == "critical")
    warning = sum(1 for a in alerts if a["severity"] == "warning")

    return {
        "scanned_at": datetime.datetime.now().isoformat(),
        "total_alerts": total,
        "critical_count": critical,
        "warning_count": warning,
        "alerts": alerts,
        "summary": (
            f"发现 {total} 个EOL/NRND品牌风险"
            f"（{critical} 紧急，{warning} 关注）"
            if total > 0 else "未发现EOL/NRND风险"
        ),
    }


async def suggest_eol_alternatives(db: AsyncSession, product_id: int) -> dict:
    """
    Given a product that is or might be EOL, suggest alternative products/brands.
    """
    product = (await db.execute(
        select(Product).where(Product.id == product_id)
    )).scalars().first()

    if not product:
        return {"error": "产品不存在"}

    brand = None
    if product.brand_id:
        brand = (await db.execute(
            select(Brand).where(Brand.id == product.brand_id)
        )).scalars().first()

    cond = [Brand.deleted_at.is_(None), Brand.lifecycle_stage == "active"]
    if brand and brand.category:
        cond.append(Brand.category == brand.category)

    active_brands = (await db.execute(
        select(Brand).where(*cond).limit(5)
    )).scalars().all()

    alternatives = []
    for b in active_brands:
        prods = (await db.execute(
            select(Product)
            .where(Product.brand_id == b.id, Product.deleted_at.is_(None))
            .limit(5)
        )).scalars().all()

        for p in prods:
            if p.id == product.id:
                continue
            inv = (await db.execute(
                select(Inventory).where(Inventory.product_id == p.id)
            )).scalars().first()
            if not inv or inv.quantity <= 0:
                continue
            alternatives.append({
                "product_id": p.id,
                "sku": p.sku,
                "name": p.name,
                "brand_id": b.id,
                "brand_name": b.name,
                "stock_qty": inv.quantity if inv else 0,
                "match_reason": f"同品类({b.category or '未知'})替代",
            })

    if not alternatives and brand:
        same_brand_prods = (await db.execute(
            select(Product)
            .where(Product.brand_id == brand.id, Product.deleted_at.is_(None), Product.id != product.id)
            .limit(10)
        )).scalars().all()
        for p in same_brand_prods:
            inv = (await db.execute(
                select(Inventory).where(Inventory.product_id == p.id)
            )).scalars().first()
            if not inv or inv.quantity <= 0:
                continue
            alternatives.append({
                "product_id": p.id,
                "sku": p.sku,
                "name": p.name,
                "brand_id": brand.id,
                "brand_name": brand.name,
                "stock_qty": inv.quantity if inv else 0,
                "match_reason": f"同品牌({brand.name})其他型号",
            })

    return {
        "original": {
            "product_id": product.id,
            "sku": product.sku,
            "name": product.name,
            "brand_name": brand.name if brand else None,
            "lifecycle_stage": brand.lifecycle_stage if brand else None,
        },
        "alternatives": alternatives[:10],
        "count": len(alternatives),
    }
