"""Transactions API — visit bounded context.

Sales rep field visits to customers.
"""

import logging
from datetime import datetime

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.database import get_db
from app.models.transaction import Visit
from app.schemas.common import ok

logger = logging.getLogger(__name__)

visit_router = APIRouter(prefix="/visits", tags=["transactions:visit"])


class VisitCreate(BaseModel):
    visit_no: str | None = None
    customer_id: int
    contact_id: int | None = None
    title: str | None = None
    visit_date: str | None = None
    type: str | None = None
    status: str | None = None
    content: str | None = None
    result: str | None = None
    next_plan: str | None = None
    stage: str | None = None
    purpose: str | None = None
    main_product: str | None = None
    key_points: str | None = None
    followup_date: str | None = None


@visit_router.get("")
async def list_visits(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    customer_id: int | None = None,
    type: str | None = None,
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(get_current_user),
):
    base = select(Visit).where(Visit.deleted_at.is_(None))
    count_base = select(func.count(Visit.id)).where(Visit.deleted_at.is_(None))

    if customer_id:
        base = base.where(Visit.customer_id == customer_id)
        count_base = count_base.where(Visit.customer_id == customer_id)
    if type:
        base = base.where(Visit.type == type)
        count_base = count_base.where(Visit.type == type)

    total = (await db.execute(count_base)).scalar() or 0
    rows = (await db.execute(
        base.order_by(Visit.id.desc()).offset((page - 1) * page_size).limit(page_size)
    )).scalars().all()

    return ok({
        "list": [{"id": v.id, "visit_no": v.visit_no, "customer_id": v.customer_id,
                  "title": v.title, "visit_date": str(v.visit_date) if v.visit_date else None,
                  "type": v.type, "status": v.status, "content": v.content,
                  "result": v.result, "next_plan": v.next_plan, "stage": v.stage,
                  "purpose": v.purpose, "main_product": v.main_product,
                  "key_points": v.key_points,
                  "followup_date": str(v.followup_date) if v.followup_date else None,
                  "created_at": str(v.created_at)} for v in rows],
        "total": total, "page": page, "page_size": page_size,
    })


@visit_router.post("", status_code=201)
async def create_visit(body: VisitCreate, db: AsyncSession = Depends(get_db), _user: dict = Depends(get_current_user)):
    data = body.model_dump()
    for date_field in ("visit_date", "followup_date"):
        if data.get(date_field):
            data[date_field] = datetime.fromisoformat(data[date_field])
    visit = Visit(**data)
    db.add(visit)
    await db.flush()
    return ok({"id": visit.id, "title": visit.title})
