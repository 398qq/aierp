"""Brand risk assessment."""

import datetime
from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.product import Product, SupplierProduct
from app.models.sales import SalesOrder, SalesOrderItem
from app.services.ai.client import ai_client
from app.services.ai.prompts import brand_risk_prompt
from app.services.brand_intel.context import _brand_context


async def assess_brand_risk(db: AsyncSession, brand_id: int) -> dict:
    """AI-powered brand risk assessment across supplier, lifecycle, customer, market dimensions."""
    ctx = await _brand_context(db, brand_id)

    product_ids = [
        r[0]
        for r in (
            await db.execute(
                select(Product.id).where(
                    Product.brand_id == brand_id, Product.deleted_at.is_(None)
                )
            )
        ).all()
    ]

    product_count = len(product_ids)

    if product_ids:
        supplier_counts = (
            await db.execute(
                select(
                    SupplierProduct.product_id,
                    func.count(SupplierProduct.supplier_id).label("sc"),
                )
                .where(
                    SupplierProduct.product_id.in_(product_ids),
                    SupplierProduct.deleted_at.is_(None),
                )
                .group_by(SupplierProduct.product_id)
            )
        ).all()

        single_source_count = sum(1 for r in supplier_counts if r[1] == 1)
        single_source_pct = (
            round(single_source_count / product_count * 100, 1)
            if product_count > 0
            else 0
        )

        supplier_product_counts: dict[int, int] = {}
        if product_ids:
            sp_all = (
                await db.execute(
                    select(SupplierProduct.supplier_id).where(
                        SupplierProduct.product_id.in_(product_ids),
                        SupplierProduct.deleted_at.is_(None),
                    )
                )
            ).all()
            for sp in sp_all:
                supplier_product_counts[sp[0]] = (
                    supplier_product_counts.get(sp[0], 0) + 1
                )

        top_supplier_share = (
            f"{max(supplier_product_counts.values()) / product_count * 100:.0f}%"
            if supplier_product_counts
            else "0%"
        )

        now = datetime.datetime.now(datetime.timezone.utc)
        cust_revenue = (
            await db.execute(
                select(
                    SalesOrder.customer_id,
                    func.sum(SalesOrderItem.total_price).label("rev"),
                )
                .select_from(SalesOrderItem)
                .join(SalesOrder, SalesOrderItem.order_id == SalesOrder.id)
                .where(
                    SalesOrderItem.product_id.in_(product_ids),
                    SalesOrder.status.in_(["confirmed", "delivered", "completed"]),
                    SalesOrder.created_at >= now - datetime.timedelta(days=365),
                    SalesOrder.deleted_at.is_(None),
                    SalesOrderItem.deleted_at.is_(None),
                )
                .group_by(SalesOrder.customer_id)
                .order_by(text("rev DESC"))
            )
        ).all()

        total_rev = sum(float(r[1]) for r in cust_revenue) if cust_revenue else 0
        top1_share = (
            round(float(cust_revenue[0][1]) / total_rev * 100, 1)
            if cust_revenue and total_rev > 0
            else 0
        )
        top3_share = (
            round(sum(float(r[1]) for r in cust_revenue[:3]) / total_rev * 100, 1)
            if cust_revenue and total_rev > 0
            else 0
        )

        brand_cats = [
            r[0]
            for r in (
                await db.execute(
                    select(func.distinct(Product.category)).where(
                        Product.brand_id == brand_id,
                        Product.deleted_at.is_(None),
                        Product.category.isnot(None),
                    )
                )
            ).all()
        ]

        competitor_count = 0
        if brand_cats:
            competitor_count = (
                await db.execute(
                    select(func.count(func.distinct(Product.brand_id))).where(
                        Product.category.in_(brand_cats),
                        Product.brand_id != brand_id,
                        Product.deleted_at.is_(None),
                    )
                )
            ).scalar() or 0
    else:
        single_source_count = 0
        single_source_pct = 0
        top_supplier_share = "0%"
        top1_share = 0
        top3_share = 0
        competitor_count = 0

    risk_data = {
        **ctx,
        "supplier_count": ctx.get("supplier_count", 0),
        "single_source_count": single_source_count,
        "single_source_pct": single_source_pct,
        "top_supplier_share": top_supplier_share,
        "product_count": product_count,
        "eol_count": 0,
        "new_products_6m": 0,
        "active_customers": 0,
        "top_customer_share": top1_share,
        "top3_customer_share": top3_share,
        "competitor_count": competitor_count,
        "substitutable_pct": 0,
    }

    schema = {
        "risk_score": "integer 0-100",
        "risk_level": "string: 低/中/高/严重",
        "supplier_risk": "string",
        "lifecycle_risk": "string",
        "concentration_risk": "string",
        "market_risk": "string",
        "top_risks": ["string"],
        "mitigation_suggestions": ["string"],
    }
    result = await ai_client.chat_structured(
        [
            {"role": "system", "content": "你是一个电子元器件供应链风险管理专家。"},
            {"role": "user", "content": brand_risk_prompt(risk_data)},
        ],
        schema,
    )
    result["context"] = risk_data
    return result
