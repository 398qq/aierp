"""Brand AI endpoints."""
import logging

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.database import get_db
from app.schemas.common import fail, ok

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ai", tags=["ai"])


# --- Brand Intelligence ---


@router.post("/brands/{brand_id}/profile")
async def brand_profile(
    brand_id: int,
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(get_current_user),
):
    """Generate brand profile."""
    from app.services.brand_intel_service import generate_brand_profile

    try:
        result = await generate_brand_profile(db, brand_id)
        return ok(result)
    except ValueError as e:
        return fail(str(e), 404)


@router.post("/brands/{brand_id}/portfolio")
async def brand_portfolio(
    brand_id: int,
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(get_current_user),
):
    """Analyze brand portfolio."""
    from app.services.brand_intel_service import analyze_brand_portfolio

    try:
        result = await analyze_brand_portfolio(db, brand_id)
        return ok(result)
    except ValueError as e:
        return fail(str(e), 404)


@router.get("/brands/{brand_id}/similar")
async def similar_brands(
    brand_id: int,
    top_k: int = 5,
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(get_current_user),
):
    """Find similar brands."""
    from app.services.brand_intel_service import find_similar_brands

    result = await find_similar_brands(db, brand_id, top_k)
    return ok(result)


@router.post("/brands/compare")
async def compare_brands(
    brand_a: int = Query(...),
    brand_b: int = Query(...),
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(get_current_user),
):
    """Compare two brands."""
    from app.services.brand_intel_service import compare_brands

    try:
        result = await compare_brands(db, brand_a, brand_b)
        return ok(result)
    except ValueError as e:
        return fail(str(e), 404)


@router.post("/brands/import")
async def import_brand(
    text: str = Query(...),
    auto_create: bool = Query(False),
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(get_current_user),
):
    """Import brand from text."""
    from app.services.brand_intel_service import import_brand_from_text

    try:
        result = await import_brand_from_text(db, text, auto_create)
        return ok(result)
    except ValueError as e:
        return fail(f"AI 解析失败: {str(e)}", 503)


@router.post("/brands/{brand_id}/health")
async def brand_health(
    brand_id: int,
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(get_current_user),
):
    """Brand health assessment."""
    from app.services.brand_intel_service import get_brand_health

    try:
        result = await get_brand_health(db, brand_id)
        return ok(result)
    except ValueError as e:
        return fail(str(e), 404)


@router.post("/brands/{brand_id}/risk")
async def brand_risk(
    brand_id: int,
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(get_current_user),
):
    """Brand risk assessment."""
    from app.services.brand_intel_service import assess_brand_risk

    try:
        result = await assess_brand_risk(db, brand_id)
        return ok(result)
    except ValueError as e:
        return fail(str(e), 404)


@router.post("/brands/{brand_id}/supplier-matrix")
async def brand_supplier_matrix(
    brand_id: int,
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(get_current_user),
):
    """Brand supplier matrix."""
    from app.services.brand_intel_service import get_brand_supplier_matrix

    try:
        result = await get_brand_supplier_matrix(db, brand_id)
        return ok(result)
    except ValueError as e:
        return fail(str(e), 404)


@router.post("/brands/{brand_id}/recommendations")
async def brand_recommendations(
    brand_id: int,
    top_k: int = Query(5),
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(get_current_user),
):
    """Brand recommendations."""
    from app.services.brand_intel_service import recommend_brands

    try:
        result = await recommend_brands(db, brand_id, top_k)
        return ok(result)
    except ValueError as e:
        return fail(str(e), 404)


# --- Brand Performance ---


@router.post("/brands/{brand_id}/product-performance")
async def brand_product_performance(
    brand_id: int,
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(get_current_user),
):
    """Brand product performance."""
    from app.services.brand_intel_service import get_brand_product_performance

    try:
        result = await get_brand_product_performance(db, brand_id)
        return ok(result)
    except ValueError as e:
        return fail(str(e), 404)


@router.post("/brands/{brand_id}/customer-penetration")
async def brand_customer_penetration(
    brand_id: int,
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(get_current_user),
):
    """Brand customer penetration."""
    from app.services.brand_intel_service import get_brand_customer_penetration

    try:
        result = await get_brand_customer_penetration(db, brand_id)
        return ok(result)
    except ValueError as e:
        return fail(str(e), 404)


@router.post("/brands/{brand_id}/lifecycle")
async def brand_lifecycle(
    brand_id: int,
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(get_current_user),
):
    """Brand lifecycle prediction."""
    from app.services.brand_intel_service import predict_brand_lifecycle

    try:
        result = await predict_brand_lifecycle(db, brand_id)
        return ok(result)
    except ValueError as e:
        return fail(str(e), 404)


@router.post("/brands/{brand_id}/price-trends")
async def brand_price_trends(
    brand_id: int,
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(get_current_user),
):
    """Brand price trends."""
    from app.services.brand_intel_service import get_brand_price_trends

    try:
        result = await get_brand_price_trends(db, brand_id)
        return ok(result)
    except ValueError as e:
        return fail(str(e), 404)


@router.post("/brands/{brand_id}/auto-complete")
async def brand_auto_complete(
    brand_id: int,
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(get_current_user),
):
    """Auto-complete brand info."""
    from app.services.brand_intel_service import auto_complete_brand

    try:
        result = await auto_complete_brand(db, brand_id)
        return ok(result)
    except ValueError as e:
        return fail(str(e), 404)


@router.get("/brands/eol-alerts")
async def brand_eol_alerts(
    urgency: str = Query("warning", description="最低紧急度: info / warning / critical"),
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(get_current_user),
):
    """Scan all brands for EOL/NRND risks."""
    from app.services.brand_intel_service import scan_eol_alerts

    result = await scan_eol_alerts(db, urgency_threshold=urgency)
    return ok(result)


@router.get("/products/{product_id}/eol-alternatives")
async def product_eol_alternatives(
    product_id: int,
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(get_current_user),
):
    """Get EOL alternatives for a product."""
    from app.services.brand_intel_service import suggest_eol_alternatives

    result = await suggest_eol_alternatives(db, product_id)
    if "error" in result:
        return fail(result["error"], 404)
    return ok(result)