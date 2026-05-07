"""Collaborative-filtering product recommendation using pgvector customer similarity."""

import logging

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.customer import Customer
from app.models.product import Brand, Product
from app.models.sales import SalesOrder, SalesOrderItem
from app.services.ai.agents import EmbeddingService

logger = logging.getLogger(__name__)


async def recommend_products(
    customer_id: int,
    db: AsyncSession,
    top_k: int = 10,
    min_similarity: float = 0.75,
    include_own_history: bool = False,
) -> dict:
    """
    Recommend products via collaborative filtering:
    1. Get target customer embedding
    2. Find similar customers via pgvector
    3. Aggregate products they purchased (that target hasn't)
    4. Rank by: frequency × recency × similarity weight
    """
    target = (
        await db.execute(
            select(Customer).where(Customer.id == customer_id, Customer.deleted_at.is_(None))
        )
    ).scalar_one_or_none()
    if target is None:
        return {"customer_id": customer_id, "recommendations": [], "error": "Customer not found"}

    # Ensure embedding exists
    if target.embedding is None:
        target.embedding = await EmbeddingService.embed_customer({
            "name": target.name,
            "industry": target.industry or "",
            "region": target.region or "",
            "customer_type": target.customer_type or "",
            "level": target.level or "",
            "credit_level": target.credit_level or "",
            "source": target.source or "",
            "notes": target.notes or "",
        })
        await db.flush()

    # Step 1: Find similar customers
    similar = await EmbeddingService.similar_customers(
        target.embedding, db, top_k=20, exclude_id=customer_id
    )
    similar = [s for s in similar if s["similarity"] >= min_similarity]
    if not similar:
        return {"customer_id": customer_id, "recommendations": [], "similar_customers": 0}

    similar_ids = [s["id"] for s in similar]
    similarity_map = {s["id"]: s["similarity"] for s in similar}

    # Step 2: Get products already purchased by target
    target_product_rows = (
        await db.execute(
            select(SalesOrderItem.product_id)
            .join(SalesOrder, SalesOrderItem.order_id == SalesOrder.id)
            .where(
                SalesOrder.customer_id == customer_id,
                SalesOrder.deleted_at.is_(None),
                SalesOrderItem.deleted_at.is_(None),
            )
            .distinct()
        )
    ).all()
    target_product_ids = {r[0] for r in target_product_rows}

    # Step 3: Get products purchased by similar customers
    func.coalesce(
        1.0 / (func.extract("day", func.now() - SalesOrder.created_at) / 30.0 + 1.0),
        0.2,
    )

    product_rows = (
        await db.execute(
            select(
                SalesOrderItem.product_id,
                func.count(SalesOrderItem.id).label("freq"),
                func.max(SalesOrder.created_at).label("last_order"),
                SalesOrder.customer_id,
            )
            .join(SalesOrder, SalesOrderItem.order_id == SalesOrder.id)
            .where(
                SalesOrder.customer_id.in_(similar_ids),
                SalesOrder.deleted_at.is_(None),
                SalesOrderItem.deleted_at.is_(None),
                SalesOrderItem.product_id.notin_(target_product_ids) if not include_own_history else True,
            )
            .group_by(SalesOrderItem.product_id, SalesOrder.customer_id)
        )
    ).all()

    if not product_rows:
        return {
            "customer_id": customer_id,
            "recommendations": [],
            "similar_customers": len(similar_ids),
        }

    # Step 4: Score products
    import datetime as dt

    now = dt.datetime.now(dt.timezone.utc)
    product_scores: dict[int, dict] = {}

    for pid, freq, last_order, sim_cust_id in product_rows:
        if pid not in product_scores:
            product_scores[pid] = {"product_id": pid, "frequency": 0, "recency_days": 9999, "similarity_weight": 0.0}
        entry = product_scores[pid]
        entry["frequency"] += freq
        if last_order:
            days = (now - last_order.replace(tzinfo=dt.timezone.utc)).days
            entry["recency_days"] = min(entry["recency_days"], days)
        entry["similarity_weight"] = max(entry["similarity_weight"], similarity_map.get(sim_cust_id, 0.0))

    for pid, entry in product_scores.items():
        recency_score = max(0, 1.0 - entry["recency_days"] / 365.0)
        entry["score"] = round(
            entry["frequency"] * 0.4 + recency_score * 30 * 0.3 + entry["similarity_weight"] * 30 * 0.3,
            2,
        )

    # Step 5: Get product details
    sorted_products = sorted(product_scores.values(), key=lambda x: x["score"], reverse=True)[:top_k]
    product_ids = [p["product_id"] for p in sorted_products]

    product_details = (
        await db.execute(
            select(Product.id, Product.sku, Product.name, Product.category, Brand.name_cn)
            .outerjoin(Brand, Product.brand_id == Brand.id)
            .where(Product.id.in_(product_ids))
        )
    ).all()
    product_map = {
        p[0]: {"sku": p[1], "name": p[2], "category": p[3], "brand": p[4]} for p in product_details
    }

    recommendations = [
        {
            "product_id": p["product_id"],
            **product_map.get(p["product_id"], {}),
            "score": p["score"],
            "purchase_count": p["frequency"],
            "last_purchase_days_ago": p["recency_days"],
            "recommendation_reason": (
                f"{p['frequency']}个相似客户购买过，最近{p['recency_days']}天前有采购"
                if p["recency_days"] < 9999
                else f"{p['frequency']}个相似客户购买过"
            ),
        }
        for p in sorted_products
    ]

    return {
        "customer_id": customer_id,
        "similar_customers_count": len(similar_ids),
        "recommendations": recommendations,
    }
