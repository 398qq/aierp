"""Brand comparison and similarity."""

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.product import Brand, Product
from app.services.ai.client import ai_client
from app.services.ai.prompts import brand_compare_prompt
from app.services.brand_intel.context import _brand_context


async def compare_brands(db: AsyncSession, brand_id_a: int, brand_id_b: int) -> dict:
    """AI-powered brand comparison."""
    ctx_a = await _brand_context(db, brand_id_a)
    ctx_b = await _brand_context(db, brand_id_b)

    prods_a = (await db.execute(
        select(Product.id, Product.category).where(
            Product.brand_id == brand_id_a, Product.deleted_at.is_(None)
        )
    )).all()
    prods_b = (await db.execute(
        select(Product.id, Product.category).where(
            Product.brand_id == brand_id_b, Product.deleted_at.is_(None)
        )
    )).all()

    cats_a = set(p[1] for p in prods_a if p[1])
    cats_b = set(p[1] for p in prods_b if p[1])
    shared_cats = ", ".join(cats_a & cats_b) if cats_a & cats_b else "无"

    overlap = {
        "shared_categories": shared_cats,
        "overlapping_products": 0,
    }

    schema = {
        "comparison_summary": "string",
        "dimension_scores": [
            {"dimension": "string", "a_score": "integer 0-10", "b_score": "integer 0-10", "note": "string"}
        ],
        "switching_feasibility": "string: 容易/中等/困难",
        "switching_notes": ["string"],
        "recommended_strategy": "string: 以A为主/以B为主/双源/视产品而定",
    }
    result = await ai_client.chat_structured(
        [{"role": "system", "content": "你是一个电子元器件供应链策略专家，擅长品牌对比和替代分析。"},
         {"role": "user", "content": brand_compare_prompt(ctx_a, ctx_b, overlap)}],
        schema,
    )
    result["brand_a"] = ctx_a
    result["brand_b"] = ctx_b
    result["overlap"] = overlap
    return result


async def find_similar_brands(db: AsyncSession, brand_id: int, top_k: int = 5) -> list[dict]:
    """Find similar brands based on product category overlap + pgvector embedding fallback."""
    target_cats = (await db.execute(
        select(func.distinct(Product.category)).where(
            Product.brand_id == brand_id, Product.deleted_at.is_(None),
            Product.category.isnot(None),
        )
    )).scalars().all()

    similar = (await db.execute(
        select(
            Brand.id, Brand.name, Brand.name_cn, Brand.category,
            func.count(func.distinct(Product.id)).label("product_count"),
            func.count(func.distinct(Product.category)).label("shared_cats"),
        )
        .join(Product, Brand.id == Product.brand_id)
        .where(
            Brand.id != brand_id,
            Brand.deleted_at.is_(None),
            Product.deleted_at.is_(None),
            Product.category.in_(target_cats),
        )
        .group_by(Brand.id)
        .order_by(func.count(func.distinct(Product.category)).desc())
        .limit(top_k)
    )).all()

    results = [
        {
            "id": r[0], "name": r[1], "name_cn": r[2], "category": r[3],
            "product_count": r[4], "shared_categories": r[5],
        }
        for r in similar
    ]

    if len(results) < top_k:
        brand = (await db.execute(
            select(Brand).where(Brand.id == brand_id, Brand.deleted_at.is_(None))
        )).scalar_one_or_none()
        if brand and brand.embedding:
            vector_candidates = (await db.execute(
                select(Brand).where(
                    Brand.id != brand_id,
                    Brand.deleted_at.is_(None),
                    Brand.embedding.isnot(None),
                )
            )).scalars().all()

            def cosine_similarity(a: list[float], b: list[float]) -> float:
                dot = sum(x * y for x, y in zip(a, b))
                norm_a = sum(x * x for x in a) ** 0.5
                norm_b = sum(y * y for y in b) ** 0.5
                return dot / (norm_a * norm_b) if norm_a and norm_b else 0

            scored = []
            for b in vector_candidates:
                if b.embedding:
                    sim = cosine_similarity(brand.embedding, b.embedding)
                    if sim > 0.7:
                        scored.append((b, sim))

            scored.sort(key=lambda x: -x[1])
            existing_ids = {r["id"] for r in results}
            for b, sim in scored:
                if b.id not in existing_ids:
                    results.append({
                        "id": b.id, "name": b.name, "name_cn": b.name_cn,
                        "category": b.category, "product_count": 0,
                        "shared_categories": 0,
                    })
                    existing_ids.add(b.id)
                if len(results) >= top_k:
                    break

    return results[:top_k]