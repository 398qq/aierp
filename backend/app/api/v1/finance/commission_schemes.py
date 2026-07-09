"""API routes for 013 commission scheme configuration."""

import logging

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.database import get_db
from app.schemas.common import APIResponse, PageData, fail, ok
from app.schemas.commission_scheme import (
    MySchemeResponse,
    SchemeCreate,
    SchemeResponse,
    SchemeSimulateRequest,
    SchemeUpdate,
)
from app.services import commission_scheme_service as svc

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/commission-schemes", tags=["finance:commission-scheme"])


def _full_scheme(scheme) -> dict:
    """Serialize a scheme with tiers and assignments."""
    return {
        "id": scheme.id,
        "name": scheme.name,
        "description": scheme.description,
        "version_no": scheme.version_no,
        "status": scheme.status,
        "effective_from": str(scheme.effective_from),
        "effective_to": str(scheme.effective_to) if scheme.effective_to else None,
        "is_default": scheme.is_default,
        "created_by": scheme.created_by,
        "created_at": str(scheme.created_at) if scheme.created_at else None,
        "updated_at": str(scheme.updated_at) if scheme.updated_at else None,
        "tiers": [
            {
                "id": t.id,
                "scheme_id": t.scheme_id,
                "tier_no": t.tier_no,
                "metric_type": t.metric_type,
                "low_amount": float(t.low_amount) if t.low_amount else 0,
                "high_amount": float(t.high_amount) if t.high_amount else None,
                "rate": float(t.rate),
                "cap_amount": float(t.cap_amount) if t.cap_amount else 0,
                "floor_amount": float(t.floor_amount) if t.floor_amount else 0,
                "product_category": t.product_category,
                "customer_level": t.customer_level,
            }
            for t in (scheme.tiers or [])
            if not t.deleted_at
        ],
        "assignments": [
            {
                "id": a.id,
                "scheme_id": a.scheme_id,
                "assignee_type": a.assignee_type,
                "assignee_id": a.assignee_id,
            }
            for a in (scheme.assignments or [])
            if not a.deleted_at
        ],
    }


@router.get("", response_model=APIResponse[PageData[SchemeResponse]])
async def list_schemes(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: str | None = None,
    q: str | None = None,
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(get_current_user),
):
    result = await svc.list_schemes(
        db, status=status, q=q, page=page, page_size=page_size
    )
    return ok(result)


@router.get("/my-scheme", response_model=APIResponse[MySchemeResponse])
async def get_my_scheme(
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    scheme = await svc.get_my_scheme(db, current_user["user_id"])
    if not scheme:
        return ok(None, msg="当前没有生效方案，使用默认 3% 比例")
    return ok(scheme)


@router.get("/{scheme_id}", response_model=APIResponse[SchemeResponse])
async def get_scheme(
    scheme_id: int,
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(get_current_user),
):
    try:
        scheme = await svc.get_scheme(db, scheme_id)
    except svc.NotFoundError as e:
        return fail(str(e), 404)
    return ok(_full_scheme(scheme))


@router.post("", status_code=201, response_model=APIResponse[SchemeResponse])
async def create_scheme(
    body: SchemeCreate,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    try:
        scheme = await svc.create_scheme(db, body.model_dump(), current_user["user_id"])
    except svc.ConflictError as e:
        return fail(str(e), 409)
    except svc.ValidationError as e:
        return fail(str(e), 422)
    return ok(_full_scheme(scheme))


@router.put("/{scheme_id}", response_model=APIResponse[SchemeResponse])
async def update_scheme(
    scheme_id: int,
    body: SchemeUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    try:
        scheme = await svc.update_scheme(
            db, scheme_id, body.model_dump(exclude_none=True), current_user["user_id"]
        )
    except svc.NotFoundError as e:
        return fail(str(e), 404)
    except (svc.BusinessRuleViolation, svc.ValidationError) as e:
        return fail(str(e), 422)
    except svc.ConflictError as e:
        return fail(str(e), 409)
    return ok(_full_scheme(scheme))


@router.delete("/{scheme_id}")
async def delete_scheme(
    scheme_id: int,
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(get_current_user),
):
    try:
        await svc.delete_scheme(db, scheme_id)
    except svc.NotFoundError as e:
        return fail(str(e), 404)
    except svc.ConflictError as e:
        return fail(str(e), 409)
    return ok(None, msg="方案已删除")


@router.post("/{scheme_id}/activate", response_model=APIResponse[SchemeResponse])
async def activate_scheme(
    scheme_id: int,
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(get_current_user),
):
    try:
        scheme = await svc.activate_scheme(db, scheme_id)
    except svc.NotFoundError as e:
        return fail(str(e), 404)
    except svc.BusinessRuleViolation as e:
        return fail(str(e), 422)
    return ok(_full_scheme(scheme))


@router.post("/{scheme_id}/deactivate", response_model=APIResponse[SchemeResponse])
async def deactivate_scheme(
    scheme_id: int,
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(get_current_user),
):
    try:
        scheme = await svc.deactivate_scheme(db, scheme_id)
    except svc.NotFoundError as e:
        return fail(str(e), 404)
    except svc.BusinessRuleViolation as e:
        return fail(str(e), 422)
    return ok(_full_scheme(scheme))


@router.put("/{scheme_id}/assign")
async def assign_scheme(
    scheme_id: int,
    body: list[dict],
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(get_current_user),
):
    try:
        scheme = await svc.assign_scheme(db, scheme_id, body)
    except svc.NotFoundError as e:
        return fail(str(e), 404)
    except svc.ConflictError as e:
        return fail(str(e), 409)
    return ok(_full_scheme(scheme))


@router.delete("/{scheme_id}/assign/{assignment_id}")
async def unassign_scheme(
    scheme_id: int,
    assignment_id: int,
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(get_current_user),
):
    try:
        scheme = await svc.unassign_scheme(db, scheme_id, assignment_id)
    except svc.NotFoundError as e:
        return fail(str(e), 404)
    return ok(_full_scheme(scheme))


@router.post("/simulate")
async def simulate_scheme(
    body: SchemeSimulateRequest,
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(get_current_user),
):
    try:
        result = await svc.simulate_scheme(
            db, body.scheme_id, body.period_from, body.period_to, body.user_ids
        )
    except svc.NotFoundError as e:
        return fail(str(e), 404)
    return ok(result)


@router.get("/{scheme_id}/versions")
async def list_versions(
    scheme_id: int,
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(get_current_user),
):
    versions = await svc.list_versions(db, scheme_id)
    return ok(
        [
            {
                "id": v.id,
                "scheme_id": v.scheme_id,
                "version_no": v.version_no,
                "changed_by": v.changed_by,
                "changed_at": str(v.changed_at) if v.changed_at else None,
            }
            for v in versions
        ]
    )
