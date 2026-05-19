"""Supplier AI endpoints — embeddings, similarity, and intelligence."""

import logging

from fastapi import APIRouter, Body, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.database import get_db
from app.schemas.common import fail, ok
from app.services.ai import EmbeddingService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ai", tags=["ai"])


# ============================================================
#  Supplier Embedding Endpoints
# ============================================================


@router.post("/supplier/{supplier_id}/embed")
async def embed_supplier(
    supplier_id: int,
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(get_current_user),
):
    """Embed a single supplier."""
    from app.models.product import Supplier

    supplier = await db.get(Supplier, supplier_id)
    if not supplier:
        return fail("供应商不存在", 404)
    data = {
        "name": supplier.name,
        "product_lines": supplier.product_lines,
        "supplier_type": supplier.supplier_type,
        "region": supplier.region,
        "certifications": supplier.certifications,
        "payment_terms": supplier.payment_terms,
        "financial_rating": supplier.financial_rating,
        "website": supplier.website,
        "notes": supplier.notes,
    }
    try:
        emb = await EmbeddingService.embed_supplier(data)
        supplier.embedding = emb
        await db.commit()
        return ok({"id": supplier_id, "dimensions": len(emb)})
    except Exception as e:
        return fail(f"Embedding failed: {str(e)}", 500)


@router.post("/supplier/embed-all")
async def embed_all_suppliers(
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(get_current_user),
):
    """Batch generate embeddings for all suppliers that lack them."""
    stats = await EmbeddingService.index_all_suppliers(db)
    await db.commit()
    return ok(stats)


@router.get("/supplier/{supplier_id}/similar")
async def similar_suppliers(
    supplier_id: int,
    top_k: int = 10,
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(get_current_user),
):
    """Find similar suppliers via pgvector cosine distance."""
    from app.models.product import Supplier

    supplier = await db.get(Supplier, supplier_id)
    if not supplier:
        return fail("供应商不存在", 404)
    if not supplier.embedding:
        return fail("供应商尚未生成嵌入向量，请先调用 POST /ai/supplier/{id}/embed", 400)
    similar = await EmbeddingService.similar_suppliers(supplier.embedding, db, top_k, exclude_id=supplier_id)
    return ok(similar)


@router.get("/supplier/search")
async def search_suppliers(
    q: str = Query(...),
    top_k: int = 10,
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(get_current_user),
):
    """Natural-language semantic search for suppliers."""
    similar = await EmbeddingService.similar_suppliers_by_text(q, db, top_k)
    return ok(similar)


# ============================================================
#  Supplier Intelligence Routes
# ============================================================


@router.post("/suppliers/compare")
async def compare_suppliers_route(
    supplier_ids: list[int] = Body(...),
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(get_current_user),
):
    """Compare multiple suppliers side by side."""
    from app.services.supplier_intel_service import compare_suppliers

    if len(supplier_ids) < 2:
        return fail("supplier_ids 必须是至少包含2个ID的数组", 400)
    if len(supplier_ids) > 10:
        return fail("supplier_ids 最多支持10个供应商对比", 400)
    if len(set(supplier_ids)) != len(supplier_ids):
        return fail("supplier_ids 不能包含重复ID", 400)
    try:
        result = await compare_suppliers(db, supplier_ids)
        return ok(result)
    except ValueError as e:
        return fail(str(e), 404)
    except Exception as e:
        logger.error(f"compare_suppliers error: {e}")
        return fail("服务内部错误，请稍后重试", 500)


@router.post("/suppliers/{supplier_id}/scorecard")
async def supplier_scorecard(
    supplier_id: int,
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(get_current_user),
):
    """Supplier scorecard — quality, delivery, price, service dimensions."""
    from app.services.supplier_intel_service import get_supplier_scorecard

    try:
        result = await get_supplier_scorecard(db, supplier_id)
        return ok(result)
    except ValueError as e:
        return fail(str(e), 404)
    except Exception as e:
        logger.error(f"get_supplier_scorecard error: {e}")
        return fail("服务内部错误，请稍后重试", 500)


@router.post("/suppliers/{supplier_id}/delay-prediction")
async def supplier_delay_prediction(
    supplier_id: int,
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(get_current_user),
):
    """Predict delivery delay risk for a supplier."""
    from app.services.supplier_intel_service import predict_supplier_delay

    try:
        result = await predict_supplier_delay(db, supplier_id)
        return ok(result)
    except ValueError as e:
        return fail(str(e), 404)
    except Exception as e:
        logger.error(f"predict_supplier_delay error: {e}")
        return fail("服务内部错误，请稍后重试", 500)


@router.post("/suppliers/{supplier_id}/alternatives")
async def supplier_alternatives(
    supplier_id: int,
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(get_current_user),
):
    """Find alternative suppliers for a given supplier."""
    from app.services.supplier_intel_service import get_supplier_alternatives

    try:
        result = await get_supplier_alternatives(db, supplier_id)
        return ok(result)
    except ValueError as e:
        return fail(str(e), 404)
    except Exception as e:
        logger.error(f"get_supplier_alternatives error: {e}")
        return fail("服务内部错误，请稍后重试", 500)


@router.post("/suppliers/{supplier_id}/price-variance")
async def supplier_price_variance(
    supplier_id: int,
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(get_current_user),
):
    """Detect price variance anomalies for a supplier."""
    from app.services.supplier_intel_service import detect_supplier_price_variance

    try:
        result = await detect_supplier_price_variance(db, supplier_id)
        return ok(result)
    except ValueError as e:
        return fail(str(e), 404)
    except Exception as e:
        logger.error(f"detect_supplier_price_variance error: {e}")
        return fail("服务内部错误，请稍后重试", 500)


@router.post("/suppliers/{supplier_id}/360")
async def supplier_360(
    supplier_id: int,
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(get_current_user),
):
    """360-degree view of a supplier — overview, performance, risk, opportunities."""
    from app.services.supplier_intel_service import get_supplier_360

    try:
        result = await get_supplier_360(db, supplier_id)
        return ok(result)
    except ValueError as e:
        return fail(str(e), 404)
    except Exception as e:
        logger.error(f"get_supplier_360 error: {e}")
        return fail("服务内部错误，请稍后重试", 500)


@router.post("/suppliers/{supplier_id}/negotiation")
async def supplier_negotiation(
    supplier_id: int,
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(get_current_user),
):
    """Negotiation intelligence for a supplier — pricing, terms, leverage points."""
    from app.services.supplier_intel_service import get_supplier_negotiation

    try:
        result = await get_supplier_negotiation(db, supplier_id)
        return ok(result)
    except ValueError as e:
        return fail(str(e), 404)
    except Exception as e:
        logger.error(f"get_supplier_negotiation error: {e}")
        return fail("服务内部错误，请稍后重试", 500)