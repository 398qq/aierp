"""Products — read paths (list, stats, detail, sales).

Stage 1 refactor: route layer is a thin proxy. All business logic lives in
``app.services.product_service.ProductService``.

Endpoints (all under ``/products`` prefix):
- ``GET /products/stats/summary``  dashboard KPIs
- ``GET /products``                paginated list with filters & sort
- ``GET /products/{id}``           single product detail
- ``GET /products/{id}/sales``     cross-document sales history

Write paths (create / update / delete / batch) live in ``crud.py``;
bulk price import lives in ``pricing.py``.
"""

from __future__ import annotations

import json
import logging

from fastapi import APIRouter, Depends, Query
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.database import get_db
from app.schemas.common import fail, ok
from app.services.cache_service import cache_get_versioned, cache_set_versioned
from app.services.product_service import product_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/products", tags=["products"])


@router.get("/stats/summary")
async def products_stats_summary(
    response: JSONResponse,
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(get_current_user),
):
    """Dashboard KPIs (in-stock / stale / pending completion). Cached 120s."""
    cache_key = "summary"
    cached_payload = await cache_get_versioned("products:stats", cache_key)
    if cached_payload is not None:
        response.headers["X-Cache"] = "HIT"
        return ok(json.loads(cached_payload))
    response.headers["X-Cache"] = "MISS"
    payload = await product_service.get_stats_summary(db)
    await cache_set_versioned(
        "products:stats", cache_key, json.dumps(payload, default=str), ttl=120
    )
    return ok(payload)


@router.get("")
async def list_products(
    response: JSONResponse,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    q: str | None = None,
    category: str | None = None,
    brand_id: int | None = None,
    status: str | None = Query(None, description="draft | active | frozen | inactive"),
    scene: str | None = Query(
        None,
        description="all | in_stock | out_of_stock | low_stock | pending_completion | stale_30d | no_supplier",
    ),
    stock_status: str | None = Query(
        None, description="in_stock | out_of_stock | low_stock"
    ),
    sort: str | None = Query(
        None, description="name_asc | name_desc | created_at_asc | created_at_desc"
    ),
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(get_current_user),
):
    """Paginated product list with filters and sort. Cached for 5 minutes."""
    from app.services.product_service import products_cache_key

    cache_key = products_cache_key(
        page=page,
        page_size=page_size,
        q=q,
        category=category,
        brand_id=brand_id,
        status=status,
        scene=scene,
        stock_status=stock_status,
        sort=sort,
    )
    cached_payload = await cache_get_versioned("products:list", cache_key)
    if cached_payload is not None:
        return JSONResponse(
            content=ok(json.loads(cached_payload)),
            headers={"X-Cache": "HIT", "X-Cache-Key": cache_key},
        )

    response.headers["X-Cache"] = "MISS"
    payload = await product_service.list_products(
        db,
        page=page,
        page_size=page_size,
        q=q,
        category=category,
        brand_id=brand_id,
        status=status,
        scene=scene,
        stock_status=stock_status,
        sort=sort,
    )
    return ok(payload)


@router.get("/{product_id}")
async def get_product(
    product_id: int,
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(get_current_user),
):
    """Single product detail with joined inventory / supplier / sales metrics."""
    payload = await product_service.get_product_detail(db, product_id)
    if payload is None:
        return fail("Product not found", 404)
    return ok(payload)


@router.get("/{product_id}/sales")
async def get_product_sales(
    product_id: int,
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(get_current_user),
):
    """Cross-document sales history (quotations / orders / deliveries)."""
    return ok(await product_service.get_product_sales_history(db, product_id))
