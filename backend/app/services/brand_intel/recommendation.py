"""Brand recommendation engine — collaborative filtering."""

from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.product import Brand, Product
from app.models.sales import SalesOrder, SalesOrderItem
from app.services.ai.client import ai_client
from app.services.ai.prompts import brand_recommendation_prompt
from app.services.brand_intel.context import _brand_context


async def recommend_brands(db: AsyncSession, brand_id: int, top_k: int = 5) -> dict:
    """Collaborative filtering: 'customers who bought this brand also bought...'"""
    ctx = await _brand_context(db, brand_id)

    product_ids = [r[0] for r in (
        await db.execute(
            select(Product.id).where(
                Product.brand_id == brand_id, Product.deleted_at.is_(None)
            )
        )
    ).all()]

    if not product_ids:
        return {"recommendation_summary": "暂无足够数据", "recommended_brands": [], "context": ctx}

    customer_ids = [r[0] for r in (
        await db.execute(
            select(func.distinct(SalesOrder.customer_id))
            .select_from(SalesOrderItem)
            .join(SalesOrder, SalesOrderItem.order_id == SalesOrder.id)
            .where(
                SalesOrderItem.product_id.in_(product_ids),
                SalesOrder.deleted_at.is_(None),
                SalesOrderItem.deleted_at.is_(None),
            )
        )
    ).all()]

    if not customer_ids:
        return {"recommendation_summary": "暂无购买客户，无法生成推荐", "recommended_brands": [], "context": ctx}

    co_purchase_rows = (
        await db.execute(
            select(
                Brand.id, Brand.name, Brand.name_cn, Brand.category,
                func.count(func.distinct(SalesOrder.customer_id)).label('shared_customers'),
                func.count(func.distinct(Product.id)).label('shared_products'),
            )
            .select_from(SalesOrderItem)
            .join(SalesOrder, SalesOrderItem.order_id == SalesOrder.id)
            .join(Product, SalesOrderItem.product_id == Product.id)
            .join(Brand, Product.brand_id == Brand.id)
            .where(
                SalesOrder.customer_id.in_(customer_ids),
                Product.brand_id != brand_id,
                Product.deleted_at.is_(None),
                Brand.deleted_at.is_(None),
                SalesOrder.deleted_at.is_(None),
                SalesOrderItem.deleted_at.is_(None),
            )
            .group_by(Brand.id)
            .order_by(text('shared_customers DESC'))
            .limit(top_k * 3)
        )
    ).all()

    if not co_purchase_rows:
        return {"recommendation_summary": "未发现关联购买品牌", "recommended_brands": [], "context": ctx}

    co_purchase_data = (
        "\n".join(
            f"- {r[1]}{f' ({r[2]})' if r[2] else ''}: {r[4]} 共同客户, {r[5]} 共同产品"
            for r in co_purchase_rows
        )
    )

    candidate_brands = (
        "\n".join(
            f"- {r[1]}{f' ({r[2]})' if r[2] else ''} | 分类: {r[3] or '未知'} | "
            f"客户重叠: {r[4]} | 共同产品数: {r[5]}"
            for r in co_purchase_rows
        )
    )

    rec_data = {
        **ctx,
        "co_purchase_data": co_purchase_data,
        "candidate_brands": candidate_brands,
    }

    schema = {
        "recommendation_summary": "string",
        "recommended_brands": [
            {"brand_name": "string", "overlap_score": "integer 0-100", "reason": "string", "priority": "string: 高/中/低"}
        ],
        "cross_sell_strategies": ["string"],
        "target_industries": ["string"],
        "expected_conversion": "string",
    }
    result = await ai_client.chat_structured(
        [{"role": "system", "content": "你是一个电子元器件销售策略专家，擅长交叉销售和品牌推荐。"},
         {"role": "user", "content": brand_recommendation_prompt(rec_data)}],
        schema,
    )
    result["context"] = rec_data
    result["co_purchase_raw"] = [
        {"id": r[0], "name": r[1], "name_cn": r[2], "category": r[3],
         "shared_customers": r[4], "shared_products": r[5]}
        for r in co_purchase_rows
    ]
    return result