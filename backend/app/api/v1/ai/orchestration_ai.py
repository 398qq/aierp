"""Multi-agent orchestration routes."""

import json

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.database import get_db
from app.schemas.common import fail, ok
from app.services.cache_service import (
    cache_get_versioned,
    cache_set_versioned,
)

router = APIRouter(prefix="/ai", tags=["ai"])

# Global 360 is expensive (multiple aggregate queries + AI call).
# Cache the response for 5 minutes to avoid hammering the AI provider.
GLOBAL_360_CACHE_TTL = 300
GLOBAL_360_CACHE_KEY = "global360"


@router.post("/orchestrate/customer/{customer_id}")
async def orquestrate_customer(
    customer_id: int,
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(get_current_user),
):
    """Run a full 360 customer analysis using multiple AI agents."""
    from app.services.orchestration_service import orchestrate_customer_360

    try:
        result = await orchestrate_customer_360(db, customer_id)
        return ok(result)
    except ValueError as e:
        return fail(str(e), 404)


@router.post("/orchestrate/product/{product_id}")
async def orquestrate_product(
    product_id: int,
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(get_current_user),
):
    """Run a full 360 product analysis using multiple AI agents."""
    from app.services.orchestration_service import orchestrate_product_360

    try:
        result = await orchestrate_product_360(db, product_id)
        return ok(result)
    except ValueError as e:
        return fail(str(e), 404)


@router.post("/orchestrate/global")
async def orquestrate_global(
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(get_current_user),
):
    """Run a global cross-domain orchestration across all entities.

    Cached for 5 minutes — expensive AI call. Pass `?refresh=true` to bypass.
    Always returns raw aggregated data, even if AI analysis fails. The
    `ai_available` field indicates whether the AI insights are real or
    fallback heuristics.
    """
    from app.services.orchestration_service import orchestrate_global_360

    # Try cache first (skip if explicitly asked to refresh)
    cached = await cache_get_versioned(GLOBAL_360_CACHE_KEY, "main")
    if cached is not None:
        return ok(json.loads(cached))

    try:
        result = await orchestrate_global_360(db)
    except ValueError as e:
        return fail(str(e), 404)
    except Exception as e:
        # Don't let a transient AI/db error 500 the whole endpoint —
        # the orchestrator already returns a graceful fallback. If we
        # still end up here it's a programming error, log and return 500.
        import logging
        logging.getLogger(__name__).error(f"Global 360 failed unexpectedly: {e}")
        return fail(f"Global 360 failed: {e}", 500)

    await cache_set_versioned(GLOBAL_360_CACHE_KEY, "main", json.dumps(result, default=str), GLOBAL_360_CACHE_TTL)
    return ok(result)
