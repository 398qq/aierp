"""Finance API — sales target bounded context.

Routes for the sales target lifecycle:
- list / stats / get / create / update / delete
"""

import json
import logging

from fastapi import APIRouter, Depends, Query
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.api.v1.finance._shared import (
    TARGETS_LIST_CACHE_TTL,
    TARGETS_STATS_CACHE_TTL,
    _targets_cache_key,
)
from app.database import get_db
from app.schemas.common import fail, ok
from app.schemas.finance import SalesTargetCreate, SalesTargetUpdate
from app.services.cache_service import (
    cache_bump_version,
    cache_get_versioned,
    cache_set_versioned,
)

logger = logging.getLogger(__name__)

router = APIRouter(tags=["finance:target"])


async def _bump_target_caches() -> None:
    """Bump all caches affected by target writes."""
    await cache_bump_version("targets:list")
    await cache_bump_version("targets:stats")


@router.get("/targets")
async def list_targets(
    response: JSONResponse,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    user_id: int | None = None,
    status: str | None = None,
    target_type: str | None = None,
    sort_by: str = "id",
    sort_order: str = "desc",
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(get_current_user),
):
    cache_key = _targets_cache_key(
        page=page,
        page_size=page_size,
        user_id=user_id,
        status=status,
        target_type=target_type,
        sort_by=sort_by,
        sort_order=sort_order,
    )
    cached_payload = await cache_get_versioned("targets:list", cache_key)
    if cached_payload is not None:
        response.headers["X-Cache"] = "HIT"
        response.headers["X-Cache-Key"] = cache_key
        return ok(json.loads(cached_payload))
    response.headers["X-Cache"] = "MISS"
    from app.services.finance_service import list_targets as svc_list

    result = await svc_list(
        db,
        page=page,
        page_size=page_size,
        user_id=user_id,
        status=status,
        target_type=target_type,
        sort_by=sort_by,
        sort_order=sort_order,
    )
    await cache_set_versioned(
        "targets:list",
        cache_key,
        json.dumps(result, default=str),
        TARGETS_LIST_CACHE_TTL,
    )
    return ok(result)


@router.get("/targets/stats")
async def get_target_stats(
    response: JSONResponse,
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(get_current_user),
):
    cache_key = "targets:stats:global"
    cached_payload = await cache_get_versioned("targets:stats", cache_key)
    if cached_payload is not None:
        response.headers["X-Cache"] = "HIT"
        response.headers["X-Cache-Key"] = cache_key
        return ok(json.loads(cached_payload))
    response.headers["X-Cache"] = "MISS"
    from app.services.finance_service import target_stats

    result = await target_stats(db)
    await cache_set_versioned(
        "targets:stats",
        cache_key,
        json.dumps(result, default=str),
        TARGETS_STATS_CACHE_TTL,
    )
    return ok(result)


@router.get("/targets/{target_id}")
async def get_target(
    target_id: int,
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(get_current_user),
):
    from app.services.finance_service import get_target as svc_get

    t = await svc_get(db, target_id)
    if not t:
        return fail("目标不存在", 404)
    return ok(t)


@router.post("/targets")
async def create_target(
    body: SalesTargetCreate,
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(get_current_user),
):
    from app.services.finance_service import create_target as svc_create

    t = await svc_create(db, body.model_dump())
    await _bump_target_caches()
    return ok(t)


@router.put("/targets/{target_id}")
async def update_target(
    target_id: int,
    body: SalesTargetUpdate,
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(get_current_user),
):
    from app.services.finance_service import (
        get_target as svc_get,
        update_target as svc_update,
    )

    t = await svc_get(db, target_id)
    if not t:
        return fail("目标不存在", 404)
    t = await svc_update(db, t, body.model_dump(exclude_none=True))
    await _bump_target_caches()
    return ok(t)


@router.delete("/targets/{target_id}")
async def delete_target(
    target_id: int,
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(get_current_user),
):
    from app.services.finance_service import (
        get_target as svc_get,
        delete_target as svc_del,
    )

    t = await svc_get(db, target_id)
    if not t:
        return fail("目标不存在", 404)
    await svc_del(db, t)
    await _bump_target_caches()
    return ok({"deleted": target_id})
