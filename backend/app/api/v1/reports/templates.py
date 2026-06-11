"""Reports API — report template bounded context.

Routes for the report template lifecycle:
- list (with all templates ordered by id desc)
- create / update / delete (soft)
"""

import datetime
import json
import logging

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.requests import Request

from app.core.permissions import require_perm
from app.database import get_db
from app.models.report import ReportTemplate
from app.schemas.common import fail, ok
from app.api.v1.reports._shared import (
    TEMPLATES_LIST_CACHE_TTL,
    _templates_cache_key,
)
from app.services.cache_service import (
    cache_bump_version,
    cache_get_versioned,
    cache_set_versioned,
)

logger = logging.getLogger(__name__)

router = APIRouter(tags=["report:template"])


@router.get("/templates")
async def list_templates(
    response: JSONResponse,
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(require_perm("reports", "read")),
):
    cache_key = _templates_cache_key()
    cached_payload = await cache_get_versioned("reports:templates:list", cache_key)
    if cached_payload is not None:
        response.headers["X-Cache"] = "HIT"
        response.headers["X-Cache-Key"] = cache_key
        return ok(json.loads(cached_payload))
    response.headers["X-Cache"] = "MISS"
    result = await db.execute(
        select(ReportTemplate)
        .where(
            ReportTemplate.deleted_at.is_(None),
        )
        .order_by(ReportTemplate.id.desc())
    )
    temps = result.scalars().all()
    payload = [
        {
            "id": t.id,
            "name": t.name,
            "type": t.type,
            "config": t.config,
            "is_public": t.is_public,
            "created_by": t.created_by,
            "created_at": str(t.created_at),
        }
        for t in temps
    ]
    await cache_set_versioned(
        "reports:templates:list",
        cache_key,
        json.dumps(payload, default=str),
        TEMPLATES_LIST_CACHE_TTL,
    )
    return ok(payload)


class TemplateCreate(BaseModel):
    name: str
    type: str
    config: dict = {}
    is_public: bool = False


@router.post("/templates", status_code=201)
async def create_template(
    body: TemplateCreate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_perm("reports", "write")),
):
    t = ReportTemplate(
        name=body.name,
        type=body.type,
        config=body.config,
        created_by=current_user["user_id"],
        is_public=body.is_public,
    )
    db.add(t)
    await db.commit()
    await cache_bump_version("reports:templates:list")
    return ok({"id": t.id}, msg="模板创建成功")


@router.put("/templates/{template_id}")
async def update_template(
    template_id: int,
    body: TemplateCreate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_perm("reports", "write")),
):
    t = (
        await db.execute(
            select(ReportTemplate).where(
                ReportTemplate.id == template_id, ReportTemplate.deleted_at.is_(None)
            )
        )
    ).scalar_one_or_none()
    if not t:
        return fail("模板不存在")
    t.name = body.name
    t.type = body.type
    t.config = body.config
    t.is_public = body.is_public
    await db.commit()
    await cache_bump_version("reports:templates:list")
    return ok(msg="模板更新成功")


@router.delete("/templates/{template_id}")
async def delete_template(
    template_id: int,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_perm("reports", "write")),
):
    t = (
        await db.execute(
            select(ReportTemplate).where(
                ReportTemplate.id == template_id, ReportTemplate.deleted_at.is_(None)
            )
        )
    ).scalar_one_or_none()
    if not t:
        return fail("模板不存在")
    t.deleted_at = datetime.datetime.now(datetime.timezone.utc)
    await db.commit()
    await cache_bump_version("reports:templates:list")
    return ok(msg="模板已删除")
