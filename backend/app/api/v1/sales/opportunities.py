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
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql.elements import ColumnElement

from app.api.deps import get_current_user
from app.api.v1.sales._shared import (
    OPPORTUNITIES_LIST_CACHE_TTL,
    _opportunities_cache_key,
)
from app.database import get_db
from app.models.customer import CustomerFollowUp
from app.schemas.common import fail, ok, APIResponse
from app.schemas.sales import (
    OpportunityResponse,
    BatchDeleteRequest,
    OpportunityBatchUpdate,
    OpportunityCreate,
    OpportunityUpdate,
)
from app.services import sales_service as svc
from app.services.order_business_chain_service import get_opportunity_business_chain
from app.services.cache_service import (
    cache_bump_version,
    cache_get_versioned,
    cache_set_versioned,
)

logger = logging.getLogger(__name__)

router = APIRouter(tags=["sales:opportunity"])


def _audit_actor(user: dict) -> str:
    return str(user.get("username") or user.get("user_id") or "system")


async def _bump_opportunity_caches() -> None:
    """Bump all caches affected by opportunity writes."""
    await cache_bump_version("opportunities:list")
    await cache_bump_version("dashboard:overview")
    await cache_bump_version("dashboard:kpi")


async def _compute_opportunity_counts(
    db: AsyncSession,
    *,
    customer_id: int | None = None,
    status: str | None = None,
    stage: str | None = None,
    assigned_to: str | None = None,
    q: str | None = None,
) -> dict:
    """Aggregate (filter-aware) summary counts.

    Replicates the same filter clauses as the list query so totals match
    the subset the user is viewing. atRisk counts rows where the
    ai_risk_level column equals 'high' (this column is pre-populated by
    the AI scoring background job, so a separate include_ai round-trip
    isn't necessary for the count).
    """
    from app.models.sales import Opportunity
    from sqlalchemy import and_, case, func, or_, select
    from datetime import datetime, timedelta, timezone

    now = datetime.now(timezone.utc)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    in_14d = today_start + timedelta(days=14)

    base_filters: list[ColumnElement[bool]] = [Opportunity.deleted_at.is_(None)]
    if customer_id:
        base_filters.append(Opportunity.customer_id == customer_id)
    if status:
        base_filters.append(Opportunity.status == status)
    if stage:
        base_filters.append(Opportunity.stage == stage)
    if assigned_to:
        base_filters.append(Opportunity.assigned_to == assigned_to)
    if q and q.strip():
        from app.services.sales_service._helpers import _customer_search_ids

        pattern = f"%{q.strip()}%"
        base_filters.append(
            or_(
                Opportunity.title.ilike(pattern),
                Opportunity.description.ilike(pattern),
                Opportunity.notes.ilike(pattern),
                Opportunity.source.ilike(pattern),
                Opportunity.assigned_to.ilike(pattern),
                Opportunity.customer_id.in_(_customer_search_ids(q.strip())),
            )
        )

    counts_q = select(
        func.count(Opportunity.id).label("count"),
        func.coalesce(func.sum(Opportunity.amount), 0).label("amount"),
        func.coalesce(
            func.sum(
                func.coalesce(Opportunity.amount, 0)
                * func.coalesce(Opportunity.win_probability, 0)
                / 100.0
            ),
            0,
        ).label("weighted_amount"),
        func.coalesce(
            func.sum(case((Opportunity.status == "active", 1), else_=0)), 0
        ).label("active"),
        func.coalesce(
            func.sum(
                case(
                    (
                        and_(
                            Opportunity.status == "active",
                            Opportunity.expected_close_date.is_not(None),
                            Opportunity.expected_close_date < today_start,
                        ),
                        1,
                    ),
                    else_=0,
                )
            ),
            0,
        ).label("overdue"),
        func.coalesce(
            func.sum(
                case(
                    (
                        and_(
                            Opportunity.status == "active",
                            Opportunity.expected_close_date.is_not(None),
                            Opportunity.expected_close_date >= today_start,
                            Opportunity.expected_close_date < in_14d,
                        ),
                        1,
                    ),
                    else_=0,
                )
            ),
            0,
        ).label("due_soon"),
        func.coalesce(
            func.sum(case((Opportunity.ai_risk_level == "high", 1), else_=0)), 0
        ).label("at_risk"),
    ).where(*base_filters)
    row = (await db.execute(counts_q)).one()
    mapping = row._mapping
    return {
        "count": int(mapping["count"] or 0),
        "amount": float(mapping["amount"] or 0),
        "weightedAmount": float(mapping["weighted_amount"] or 0),
        "active": int(mapping["active"] or 0),
        "overdue": int(mapping["overdue"] or 0),
        "dueSoon": int(mapping["due_soon"] or 0),
        "atRisk": int(mapping["at_risk"] or 0),
    }


@router.get("/opportunities")
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
    kanban: bool = Query(
        False,
        description=(
            "Board mode: bypass pagination and cap at 200 records on "
            "page 1 so all six stages are visible without slicing"
        ),
    ),
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(get_current_user),
):
    """List opportunities with pagination + filter.

    When `kanban=true`, page is forced to 1 and page_size to 200 — the
    Response shape includes a top-level `counts` block aggregating the
    same filter set (count / amount / weightedAmount / active /
    overdue / dueSoon / atRisk). AI-enrichment metadata is in `ai` when
    include_ai=true and there are rows; otherwise null.
    """
    if kanban:
        page = 1
        page_size = 200

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
        kanban=kanban,
    )
    cached_payload = await cache_get_versioned("opportunities:list", cache_key)
    if cached_payload is not None:
        result = json.loads(cached_payload)
        if include_ai and result.get("list"):
            from app.services.sales_ai_service import enrich_opportunity_list

            result["ai"] = await enrich_opportunity_list(db, result["list"])
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

    counts = await _compute_opportunity_counts(
        db,
        customer_id=customer_id,
        status=status,
        stage=stage,
        assigned_to=assigned_to,
        q=q,
    )

    ai_map: dict[int, dict] | None = None
    if include_ai and result["list"]:
        from app.services.sales_ai_service import enrich_opportunity_list

        ai_map = await enrich_opportunity_list(db, result["list"])

    serialized = {
        "list": [
            OpportunityResponse.model_validate(o, from_attributes=True).model_dump(
                mode="json"
            )
            for o in result["list"]
        ],
        "total": result["total"],
        "page": result["page"],
        "page_size": result["page_size"],
        "counts": counts,
        "ai": ai_map,
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


@router.get("/opportunities/{opp_id}/follow-ups")
async def list_opportunity_followups(
    opp_id: int,
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(get_current_user),
):
    opportunity = await svc.get_opportunity(db, opp_id)
    if not opportunity:
        return fail("商机不存在", 404)
    rows = (
        (
            await db.execute(
                select(CustomerFollowUp)
                .where(
                    CustomerFollowUp.opportunity_id == opp_id,
                    CustomerFollowUp.deleted_at.is_(None),
                )
                .order_by(
                    CustomerFollowUp.planned_at.asc().nulls_last(),
                    CustomerFollowUp.created_at.desc(),
                )
            )
        )
        .scalars()
        .all()
    )
    return ok(
        [
            {
                "id": row.id,
                "opportunity_id": row.opportunity_id,
                "method": row.method,
                "status": row.status,
                "content": row.content,
                "result": row.result,
                "planned_at": row.planned_at.isoformat() if row.planned_at else None,
                "completed_at": row.completed_at.isoformat()
                if row.completed_at
                else None,
                "priority": row.priority,
                "assigned_to": row.assigned_to,
                "created_at": row.created_at.isoformat() if row.created_at else None,
            }
            for row in rows
        ]
    )


@router.get("/opportunities/{opp_id}/business-chain")
async def opportunity_business_chain(
    opp_id: int,
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(get_current_user),
):
    result = await get_opportunity_business_chain(db, opp_id)
    if result is None:
        return fail("商机不存在", 404)
    return ok(result)


@router.get("/opportunities/{opp_id}/audit")
async def opportunity_audit(
    opp_id: int,
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(get_current_user),
):
    opportunity = await svc.get_opportunity(db, opp_id)
    if not opportunity:
        return fail("商机不存在", 404)
    return ok(await svc.get_opportunity_audit(db, opp_id))


@router.post(
    "/opportunities", status_code=201, response_model=APIResponse[OpportunityResponse]
)
async def create_opportunity(
    body: OpportunityCreate,
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(get_current_user),
):
    opp = await svc.create_opportunity(db, body.model_dump(), actor=_audit_actor(_user))
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
    opp = await svc.update_opportunity(
        db,
        opp,
        body.model_dump(exclude_none=True),
        actor=_audit_actor(_user),
    )
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
    await svc.delete_opportunity(db, opp, actor=_audit_actor(_user))
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
            await svc.delete_opportunity(db, opp, actor=_audit_actor(_user))
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
                await svc.update_opportunity(
                    db, opp, updates, actor=_audit_actor(_user)
                )
                count += 1
    await _bump_opportunity_caches()
    return ok({"updated": count})
