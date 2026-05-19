"""Product AI API endpoints — parse, search, embed, similar, substitutes, intelligence."""

import logging

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.database import get_db
from app.schemas.common import fail, ok
from app.services.ai import EmbeddingService, ProductAgent
from app.services.ai.client import ai_client

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ai", tags=["ai"])


# --- Product AI: Parse, Search, Embed ---


@router.post("/products/parse")
async def ai_parse_product(text: str = Query(...), _user: dict = Depends(get_current_user)):
    """AI parses raw part-number/description text into structured product fields."""
    result = await ProductAgent.parse_product(text)
    return ok(result)


@router.post("/products/parse-bom")
async def ai_parse_bom(text: str = Query(...), _user: dict = Depends(get_current_user)):
    """AI parses a BOM list into structured line items."""
    items = await ProductAgent.parse_bom(text)
    return ok({"items": items, "count": len(items)})


@router.post("/products/search")
async def ai_product_search(
    q: str = Query(...),
    top_k: int = Query(10, le=50),
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(get_current_user),
):
    """Semantic product search via embedding similarity."""
    from app.models.product import Brand, Product

    embedding = await ai_client.embed_single(q)

    result = await db.execute(
        select(
            Product.id,
            Product.sku,
            Product.name,
            Product.category,
            Product.package_type,
            Product.specs,
            Product.unit,
            Product.brand_id,
            Brand.name_cn,
            Brand.name,
            Product.embedding.cosine_distance(embedding).label("distance"),
        )
        .outerjoin(Brand, Product.brand_id == Brand.id)
        .where(Product.deleted_at.is_(None), Product.embedding.isnot(None))
        .order_by(Product.embedding.cosine_distance(embedding))
        .limit(top_k)
    )
    rows = result.all()
    return ok([{
        "id": r[0],
        "sku": r[1],
        "name": r[2],
        "category": r[3],
        "package_type": r[4],
        "specs": r[5],
        "unit": r[6],
        "brand_id": r[7],
        "brand_name": r[8] or r[9],
        "similarity": round(1 - float(r[10]), 4),
    } for r in rows])


@router.post("/products/{product_id}/embed")
async def embed_product(
    product_id: int,
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(get_current_user),
):
    """Generate pgvector embedding for a product."""
    from app.models.product import Brand, Product

    result = await db.execute(
        select(Product).outerjoin(Brand, Product.brand_id == Brand.id)
        .where(Product.id == product_id, Product.deleted_at.is_(None))
    )
    row = result.first()
    if row is None:
        return fail("Product not found", 404)
    p = row[0]
    b = row[1] if len(row) > 1 else None

    embedding = await EmbeddingService.embed_product({
        "part_number": f"{p.sku or ''} {p.name}".strip(),
        "description": p.specs or p.notes or "",
        "brand_name": b.name if b else "",
    })
    p.embedding = embedding
    await db.commit()
    return ok({"product_id": product_id, "dimensions": len(embedding)})


@router.post("/products/embed-all")
async def embed_all_products(db: AsyncSession = Depends(get_db), _user: dict = Depends(get_current_user)):
    """Batch generate embeddings for all products that lack them."""
    from app.models.product import Brand, Product

    result = await db.execute(
        select(Product).where(Product.deleted_at.is_(None), Product.embedding.is_(None))
    )
    products = result.scalars().all()
    indexed, errors = 0, 0
    batch_size = 50

    for i in range(0, len(products), batch_size):
        batch = products[i:i + batch_size]
        texts = []
        for p in batch:
            b_result = await db.execute(select(Brand.name).where(Brand.id == p.brand_id))
            brand_name = b_result.scalar() or ""
            texts.append(
                f"型号：{p.sku or ''} {p.name}，描述：{p.specs or ''}，品牌：{brand_name}"
            )
        try:
            embeddings = await ai_client.embed(texts)
            for p, emb in zip(batch, embeddings):
                p.embedding = emb
            indexed += len(batch)
            await db.flush()
        except Exception:
            errors += len(batch)

    await db.commit()
    return ok({"indexed": indexed, "errors": errors})


@router.get("/products/{product_id}/similar")
async def similar_products(
    product_id: int,
    top_k: int = 10,
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(get_current_user),
):
    """Find similar products via pgvector cosine distance."""
    from app.models.product import Brand, Product

    prod = (await db.execute(
        select(Product).where(Product.id == product_id, Product.deleted_at.is_(None))
    )).scalar_one_or_none()
    if prod is None:
        return fail("Product not found", 404)
    if prod.embedding is None:
        return fail("Product has no embedding yet", 400)

    result = await db.execute(
        select(
            Product.id,
            Product.sku,
            Product.name,
            Product.category,
            Product.package_type,
            Product.unit,
            Brand.name_cn,
            Brand.name,
            Product.embedding.cosine_distance(prod.embedding).label("distance"),
        )
        .outerjoin(Brand, Product.brand_id == Brand.id)
        .where(Product.deleted_at.is_(None), Product.id != product_id, Product.embedding.isnot(None))
        .order_by(Product.embedding.cosine_distance(prod.embedding))
        .limit(top_k)
    )
    rows = result.all()
    return ok([{
        "id": r[0],
        "sku": r[1],
        "name": r[2],
        "category": r[3],
        "package_type": r[4],
        "unit": r[5],
        "brand_name": r[6] or r[7],
        "similarity": round(1 - float(r[8]), 4),
    } for r in rows])


@router.get("/products/{product_id}/substitutes")
async def product_substitutes(
    product_id: int,
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(get_current_user),
):
    """AI-recommended substitute parts for a product."""
    from app.models.product import Brand, Product

    prod = (await db.execute(
        select(Product).outerjoin(Brand, Product.brand_id == Brand.id)
        .where(Product.id == product_id, Product.deleted_at.is_(None))
    )).first()
    if prod is None:
        return fail("Product not found", 404)

    product_info = {
        "part_number": f"{prod[0].sku or ''} {prod[0].name}".strip(),
        "description": prod[0].specs or prod[0].notes or "",
        "category": prod[0].category or "",
        "specs": prod[0].specs or "",
        "brand": f"{prod[3] or ''} {prod[2] or ''}".strip(),
    }
    result = await ProductAgent.suggest_substitutes(product_info)
    return ok(result)


# --- Product Intelligence ---


@router.post("/products/{product_id}/profile")
async def product_profile(
    product_id: int,
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(get_current_user),
):
    """AI generates a full product intelligence profile."""
    from app.services.product_intel_service import generate_product_profile

    try:
        result = await generate_product_profile(db, product_id)
        return ok(result)
    except ValueError as e:
        return fail(str(e), 404)


@router.post("/products/{product_id}/normalize-specs")
async def normalize_product_specs(
    product_id: int,
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(get_current_user),
):
    """AI normalizes unstructured spec text into key-value parameters."""
    from app.services.product_intel_service import normalize_specs

    try:
        result = await normalize_specs(db, product_id)
        return ok(result)
    except ValueError as e:
        return fail(str(e), 404)


@router.get("/products/{product_id}/associations")
async def product_associations(
    product_id: int,
    top_k: int = 10,
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(get_current_user),
):
    """Find co-purchased/associated products via collaborative filtering."""
    from app.services.product_intel_service import get_product_associations

    result = await get_product_associations(db, product_id, top_k)
    return ok(result)


@router.post("/products/{product_id}/procurement-optimize")
async def procurement_optimize(
    product_id: int,
    quantity: int = Query(..., ge=1),
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(get_current_user),
):
    """AI recommends optimal multi-source procurement allocation."""
    from app.services.product_intel_service import optimize_procurement

    try:
        result = await optimize_procurement(db, product_id, quantity)
        return ok(result)
    except ValueError as e:
        return fail(str(e), 404)


@router.post("/products/{product_id}/lifecycle")
async def analyze_product_lifecycle(
    product_id: int,
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(get_current_user),
):
    """AI evaluates product lifecycle stage and EOL/NRND risks."""
    from app.services.product_intel_service import analyze_lifecycle

    try:
        result = await analyze_lifecycle(db, product_id)
        return ok(result)
    except ValueError as e:
        return fail(str(e), 404)