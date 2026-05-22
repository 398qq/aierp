"""Customer-Product Smart Matching — AI recommendations for cross-sell and new product introductions."""

import logging
from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.product import Brand, Product
from app.models.sales import SalesOrder, SalesOrderItem
from app.models.customer import Customer

logger = logging.getLogger(__name__)


async def recommend_products_for_customer(db: AsyncSession, customer_id: int, top_k: int = 5) -> dict:
    """Recommend products a customer should buy but hasn't yet."""

    customer = (await db.execute(
        select(Customer).where(Customer.id == customer_id, Customer.deleted_at.is_(None))
    )).scalar_one_or_none()
    if customer is None:
        raise ValueError("Customer not found")

    # Products this customer has already bought
    bought_pids = set((await db.execute(
        select(func.distinct(SalesOrderItem.product_id))
        .join(SalesOrder, SalesOrderItem.order_id == SalesOrder.id)
        .where(
            SalesOrder.customer_id == customer_id,
            SalesOrder.deleted_at.is_(None),
            SalesOrderItem.deleted_at.is_(None),
        )
    )).scalars().all() or [])

    # Brands and categories the customer buys
    if bought_pids:
        bought_profile = (await db.execute(
            select(
                func.string_agg(func.distinct(Brand.name), ', ').label('brands'),
                func.string_agg(func.distinct(Product.category), ', ').label('cats'),
            )
            .join(Brand, Product.brand_id == Brand.id)
            .where(Product.id.in_(list(bought_pids)), Product.deleted_at.is_(None))
        )).first()
    else:
        bought_profile = ("", "")

    # Find similar customers (bought same products)
    if bought_pids:
        sc_rows = (await db.execute(
            select(
                SalesOrder.customer_id,
                func.count(func.distinct(SalesOrderItem.product_id)).label("shared"),
            )
            .select_from(SalesOrderItem)
            .join(SalesOrder, SalesOrderItem.order_id == SalesOrder.id)
            .where(
                SalesOrderItem.product_id.in_(list(bought_pids)),
                SalesOrder.customer_id != customer_id,
                SalesOrder.deleted_at.is_(None),
                SalesOrderItem.deleted_at.is_(None),
            )
            .group_by(SalesOrder.customer_id)
            .order_by(text("shared DESC"))
            .limit(20)
        )).all()

    # Products bought by similar customers but not by this customer
    if bought_pids:
        sc_product_ids = set(
            (await db.execute(
                select(func.distinct(SalesOrderItem.product_id))
                .select_from(SalesOrderItem)
                .join(SalesOrder, SalesOrderItem.order_id == SalesOrder.id)
                .where(
                    SalesOrder.customer_id.in_([r[0] for r in sc_rows[:10]]),
                    SalesOrder.deleted_at.is_(None),
                    SalesOrderItem.deleted_at.is_(None),
                )
            )).scalars().all() or []
        )
        candidate_pids = list(sc_product_ids - bought_pids)[:10]
    else:
        candidate_pids = []

    candidates = []
    if candidate_pids:
        cand_rows = (await db.execute(
            select(Product.id, Product.name, Product.sku, Product.category, Brand.name, Brand.name_cn,
                   func.count(func.distinct(SalesOrderItem.product_id)).label("times_bought"))
            .outerjoin(Brand, Product.brand_id == Brand.id)
            .join(SalesOrderItem, Product.id == SalesOrderItem.product_id)
            .where(
                Product.id.in_(candidate_pids),
                Product.deleted_at.is_(None),
                SalesOrderItem.deleted_at.is_(None),
            )
            .group_by(Product.id, Brand.name, Brand.name_cn)
            .order_by(text("times_bought DESC"))
            .limit(top_k * 2)
        )).all()

        candidates = [
            {"product_id": r[0], "product_name": f"{r[2] or ''} {r[1]}".strip(),
             "category": r[3], "brand": r[4] or r[5] or "未知",
             "times_bought": r[6]}
            for r in cand_rows
        ]

    # AI reasoning
    customer_profile = (
        f"客户:{customer.name} | 行业:{customer.industry or '未知'} | "
        f"等级:{customer.level or '未知'} | 历史购买品牌:{bought_profile[0] or '无'} | "
        f"历史购买分类:{bought_profile[1] or '无'} | 已购产品数:{len(bought_pids)}"
    )

    candidates_text = (
        "\n".join(
            f"- [{c['brand']}] {c['product_name']} | 分类:{c['category'] or '未知'} | "
            f"被购买{c['times_bought']}次"
            for c in candidates
        ) if candidates else "无候选产品"
    )

    from app.services.ai.client import ai_client
    from app.services.ai.prompts import customer_product_matching_prompt

    schema = {
        "recommendations": [
            {"product_name": "string", "brand": "string", "reason": "string",
             "priority": "string: 高/中/低", "estimated_potential": "string"}
        ],
        "summary": "string, overall recommendation rationale",
        "approach_strategy": "string, how to approach the customer with these recommendations",
    }
    ai_result = await ai_client.chat_structured(
        [{"role": "system", "content": "你是一个电子元器件销售策略专家，擅长基于客户画像推荐产品。"},
         {"role": "user", "content": customer_product_matching_prompt(customer_profile, candidates_text)}],
        schema,
    )
    ai_result["candidates"] = candidates
    ai_result["customer_profile"] = {
        "name": customer.name, "industry": customer.industry, "level": customer.level,
        "bought_brands": bought_profile[0] or "", "bought_categories": bought_profile[1] or "",
        "bought_product_count": len(bought_pids),
    }
    return ai_result


async def recommend_customers_for_product(db: AsyncSession, product_id: int, top_k: int = 5) -> dict:
    """Given a product, find customers most likely to buy it."""

    prod = (await db.execute(
        select(Product.id, Product.name, Product.sku, Product.category, Brand.name, Brand.name_cn)
        .outerjoin(Brand, Product.brand_id == Brand.id)
        .where(Product.id == product_id, Product.deleted_at.is_(None))
    )).first()

    if prod is None:
        raise ValueError("Product not found")

    product_name = f"{prod[2] or ''} {prod[1]}".strip()
    product_brand = prod[4] or prod[5] or "未知"
    product_category = prod[3] or "未知"

    # Customers who bought this product
    existing_customer_ids = set((await db.execute(
        select(func.distinct(SalesOrder.customer_id))
        .join(SalesOrder, SalesOrderItem.order_id == SalesOrder.id)
        .where(
            SalesOrderItem.product_id == product_id,
            SalesOrder.deleted_at.is_(None),
            SalesOrderItem.deleted_at.is_(None),
        )
    )).scalars().all() or [])

    # Customers who bought from the same brand or category but not this product
    if Product.brand_id.__class__.__name__ == "InstrumentedAttribute":
        pass  # We know it's a Column, skip reflection

    # Find customers who bought same brand
    brand_customers = (await db.execute(
        select(func.distinct(SalesOrder.customer_id))
        .select_from(SalesOrderItem)
        .join(SalesOrder, SalesOrderItem.order_id == SalesOrder.id)
        .join(Product, SalesOrderItem.product_id == Product.id)
        .where(
            Product.brand_id == prod[0],  # Use the brand association from the product
            SalesOrder.deleted_at.is_(None),
            SalesOrderItem.deleted_at.is_(None),
            Product.deleted_at.is_(None),
        )
    )).scalars().all() or []

    # Actually need to find the brand_id first
    brand_id_row = (await db.execute(
        select(Product.brand_id).where(Product.id == product_id)
    )).scalar_one_or_none()

    if brand_id_row:
        brand_customers = (await db.execute(
            select(func.distinct(SalesOrder.customer_id))
            .select_from(SalesOrderItem)
            .join(SalesOrder, SalesOrderItem.order_id == SalesOrder.id)
            .join(Product, SalesOrderItem.product_id == Product.id)
            .where(
                Product.brand_id == brand_id_row,
                SalesOrder.deleted_at.is_(None),
                SalesOrderItem.deleted_at.is_(None),
                Product.deleted_at.is_(None),
            )
        )).scalars().all() or []
    else:
        brand_customers = []

    target_ids = list(set(brand_customers) - existing_customer_ids)[:20]
    if len(target_ids) < top_k:
        # Supplement with customers in same category
        cat_customers = (await db.execute(
            select(func.distinct(SalesOrder.customer_id))
            .select_from(SalesOrderItem)
            .join(SalesOrder, SalesOrderItem.order_id == SalesOrder.id)
            .join(Product, SalesOrderItem.product_id == Product.id)
            .where(
                Product.category == product_category,
                SalesOrder.deleted_at.is_(None),
                SalesOrderItem.deleted_at.is_(None),
                Product.deleted_at.is_(None),
            )
        )).scalars().all() or []
        extra = [c for c in cat_customers if c not in existing_customer_ids and c not in target_ids]
        target_ids = target_ids + extra[:top_k * 2 - len(target_ids)]

    candidates = []
    if target_ids:
        cand_rows = (await db.execute(
            select(
                Customer.id, Customer.name, Customer.industry, Customer.level,
                func.count(SalesOrder.id).label("total_orders"),
                func.coalesce(func.sum(SalesOrder.total_amount), 0).label("total_revenue"),
            )
            .outerjoin(SalesOrder, Customer.id == SalesOrder.customer_id)
            .where(
                Customer.id.in_(target_ids),
                Customer.deleted_at.is_(None),
            )
            .group_by(Customer.id)
            .order_by(text("total_orders DESC"))
            .limit(top_k * 2)
        )).all()

        candidates = [
            {"customer_id": r[0], "name": r[1], "industry": r[2] or "未知",
             "level": r[3] or "未知", "total_orders": r[4], "total_revenue": round(float(r[5]), 2)}
            for r in cand_rows
        ]

    product_profile = (
        f"产品:{product_name} | 品牌:{product_brand} | 分类:{product_category} | "
        f"现有客户数:{len(existing_customer_ids)}"
    )

    candidates_text = (
        "\n".join(
            f"- {c['name']} | 行业:{c['industry']} | 等级:{c['level']} | "
            f"历史{c['total_orders']}单 ¥{c['total_revenue']:,.0f}"
            for c in candidates
        ) if candidates else "无候选客户"
    )

    from app.services.ai.client import ai_client
    from app.services.ai.prompts import product_customer_matching_prompt

    schema = {
        "recommendations": [
            {"customer_name": "string", "reason": "string", "priority": "string: 高/中/低",
             "estimated_potential": "string"}
        ],
        "summary": "string",
        "outreach_strategy": "string",
    }
    ai_result = await ai_client.chat_structured(
        [{"role": "system", "content": "你是一个电子元器件销售策略专家，擅长将新产品匹配给最可能采购的客户。"},
         {"role": "user", "content": product_customer_matching_prompt(product_profile, candidates_text)}],
        schema,
    )
    ai_result["candidates"] = candidates
    ai_result["product_profile"] = {
        "name": product_name, "brand": product_brand, "category": product_category,
        "existing_customers": len(existing_customer_ids),
    }
    return ai_result
