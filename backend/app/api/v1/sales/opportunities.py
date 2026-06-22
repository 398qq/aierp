"""Sales API — opportunity bounded context.

Routes for the lead/opportunity lifecycle:
- list / get / create / update / delete
- batch operations (delete, update)

AI enrichment (enrich_opportunity, after_opportunity_save) is delegated
to ``app.services.sales_ai_service`` and ``app.services.sales_ai_pipeline``
respectively. Cache invalidation is the responsibility of the route handler
since cache keys are page-scoped.
"""

import json
import logging

from fastapi import APIRouter, Depends, Query
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.api.v1.sales._shared import (
    OPPORTUNITIES_LIST_CACHE_TTL,
    _opportunities_cache_key,
)
from app.database import get_db
from app.schemas.common import fail, ok, APIResponse, PageData
from app.schemas.sales import (
    OpportunityResponse,
    BatchDeleteRequest,
    OpportunityBatchUpdate,
    OpportunityCreate,
    OpportunityUpdate,
)
from app.services import sales_service as svc
from app.services.cache_service import (
    cache_bump_version,
    cache_get_versioned,
    cache_set_versioned,
)

logger = logging.getLogger(__name__)

router = APIRouter(tags=["sales:opportunity"])


async def _bump_opportunity_caches() -> None:
    """Bump all caches affected by opportunity writes."""
    await cache_bump_version("opportunities:list")
    await cache_bump_version("dashboard:overview")
    await cache_bump_version("dashboard:kpi")


@router.get("/opportunities", response_model=APIResponse[PageData[OpportunityResponse]])
async def list_opportunities(
    response: JSONResponse,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    customer_id: int | None = None,
    status: str | None = None,
    stage: str | None = None,
    assigned_to: str | None = None,
    q: str | None = Query(
        None, description="Search customer, title, owner, source, notes"
    ),
    include_ai: bool = Query(False),
    sort_by: str = "id",
    sort_order: str = "desc",
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(get_current_user),
):
    cache_key = _opportunities_cache_key(
        page=page,
        page_size=page_size,
        customer_id=customer_id,
        status=status,
        stage=stage,
        assigned_to=assigned_to,
        q=q,
        sort_by=sort_by,
        sort_order=sort_order,
    )
    cached_payload = await cache_get_versioned("opportunities:list", cache_key)
    if cached_payload is not None:
        result = json.loads(cached_payload)
        if include_ai and result.get("list"):
            from app.services.sales_ai_service import enrich_opportunity_list

            ai_map = await enrich_opportunity_list(db, result["list"])
            result["ai"] = ai_map
        response.headers["X-Cache"] = "HIT"
        response.headers["X-Cache-Key"] = cache_key
        return ok(result)

    response.headers["X-Cache"] = "MISS"
    result = await svc.list_opportunities(
        db,
        page=page,
        page_size=page_size,
        customer_id=customer_id,
        status=status,
        stage=stage,
        assigned_to=assigned_to,
        q=q,
        sort_by=sort_by,
        sort_order=sort_order,
    )
    if include_ai and result["list"]:
        from app.services.sales_ai_service import enrich_opportunity_list

        ai_map = await enrich_opportunity_list(db, result["list"])
        result["ai"] = ai_map

    serialized = {
        "list": [
            OpportunityResponse.model_validate(o, from_attributes=True).model_dump(mode="json")
            for o in result["list"]
        ],
        **{k: v for k, v in result.items() if k != "list"},
    }
    await cache_set_versioned(
        "opportunities:list",
        cache_key,
        json.dumps(serialized),
        OPPORTUNITIES_LIST_CACHE_TTL,
    )
    return ok(serialized)


@router.get("/opportunities/{opp_id}", response_model=APIResponse[OpportunityResponse])
async def get_opportunity(
    opp_id: int,
    include_ai: bool = Query(False),
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(get_current_user),
):
    opp = await svc.get_opportunity(db, opp_id)
    if not opp:
        return fail("商机不存在", 404)
    if include_ai:
        from app.services.sales_ai_service import enrich_opportunity

        ai_data = await enrich_opportunity(db, opp)

        result = OpportunityResponse.model_validate(
            opp, from_attributes=True
        ).model_dump()
        result["ai"] = ai_data
        return ok(result)
    return ok(
        OpportunityResponse.model_validate(opp, from_attributes=True).model_dump()
    )


@router.post(
    "/opportunities", status_code=201, response_model=APIResponse[OpportunityResponse]
)
async def create_opportunity(
    body: OpportunityCreate,
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(get_current_user),
):
    opp = await svc.create_opportunity(db, body.model_dump())
    from app.services.sales_ai_pipeline import after_opportunity_save

    after_opportunity_save(opp.id)
    await _bump_opportunity_caches()
    return ok(
        OpportunityResponse.model_validate(opp, from_attributes=True).model_dump()
    )


@router.put("/opportunities/{opp_id}", response_model=APIResponse[OpportunityResponse])
async def update_opportunity(
    opp_id: int,
    body: OpportunityUpdate,
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(get_current_user),
):
    opp = await svc.get_opportunity(db, opp_id)
    if not opp:
        return fail("商机不存在", 404)
    opp = await svc.update_opportunity(db, opp, body.model_dump(exclude_none=True))
    from app.services.sales_ai_pipeline import after_opportunity_save

    after_opportunity_save(opp.id)
    await _bump_opportunity_caches()
    return ok(
        OpportunityResponse.model_validate(opp, from_attributes=True).model_dump()
    )


@router.delete("/opportunities/{opp_id}")
async def delete_opportunity(
    opp_id: int,
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(get_current_user),
):
    opp = await svc.get_opportunity(db, opp_id)
    if not opp:
        return fail("商机不存在", 404)
    await svc.delete_opportunity(db, opp)
    await _bump_opportunity_caches()
    return ok({"deleted": opp_id})


@router.post("/opportunities/batch-delete")
async def batch_delete_opportunities(
    body: BatchDeleteRequest,
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(get_current_user),
):
    for oid in body.ids:
        opp = await svc.get_opportunity(db, oid)
        if opp:
            await svc.delete_opportunity(db, opp)
    await _bump_opportunity_caches()
    return ok({"deleted": len(body.ids)})


@router.post("/opportunities/batch-update")
async def batch_update_opportunities(
    body: OpportunityBatchUpdate,
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(get_current_user),
):
    count = 0
    for oid in body.ids:
        opp = await svc.get_opportunity(db, oid)
        if opp:
            updates: dict[str, object] = {}
            if body.stage is not None:
                updates["stage"] = body.stage
            if body.win_probability is not None:
                updates["win_probability"] = body.win_probability
            if updates:
                await svc.update_opportunity(db, opp, updates)
                count += 1
    await _bump_opportunity_caches()
    return ok({"updated": count})
