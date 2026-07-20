"""Transactions API — sample bounded context.

Sample products sent to customers for evaluation.
"""

import logging
from datetime import datetime, timezone
from typing import Literal

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.database import get_db
from app.domain.shared.errors import NotFoundError
from app.domain.states import assert_can_transition_sample
from app.models.transaction import Sample
from app.schemas.common import ok
from app.services.state_transition_service import transition_status

logger = logging.getLogger(__name__)

sample_router = APIRouter(prefix="/samples", tags=["transactions:sample"])


class SampleCreate(BaseModel):
    customer_id: int
    product_id: int | None = None
    quantity: int = 1
    unit: str | None = None
    apply_date: str | None = None
    shipped_date: str | None = None
    received_date: str | None = None
    status: Literal["pending"] = "pending"
    tracking_no: str | None = None
    approved_by: int | None = None
    sample_result: str | None = None
    notes: str | None = None


class SampleTransition(BaseModel):
    target_status: Literal["shipped", "received", "evaluated", "cancelled"]
    reason: str | None = None


@sample_router.get("")
async def list_samples(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    customer_id: int | None = None,
    status: str | None = None,
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(get_current_user),
):
    base = select(Sample).where(Sample.deleted_at.is_(None))
    count_base = select(func.count(Sample.id)).where(Sample.deleted_at.is_(None))

    if customer_id:
        base = base.where(Sample.customer_id == customer_id)
        count_base = count_base.where(Sample.customer_id == customer_id)
    if status:
        base = base.where(Sample.status == status)
        count_base = count_base.where(Sample.status == status)

    total = (await db.execute(count_base)).scalar() or 0
    rows = (
        (
            await db.execute(
                base.order_by(Sample.id.desc())
                .offset((page - 1) * page_size)
                .limit(page_size)
            )
        )
        .scalars()
        .all()
    )

    return ok(
        {
            "list": [
                {
                    "id": s.id,
                    "customer_id": s.customer_id,
                    "product_id": s.product_id,
                    "quantity": s.quantity,
                    "unit": s.unit,
                    "status": s.status,
                    "tracking_no": s.tracking_no,
                    "approved_by": s.approved_by,
                    "sample_result": s.sample_result,
                    "apply_date": str(s.apply_date) if s.apply_date else None,
                    "shipped_date": str(s.shipped_date) if s.shipped_date else None,
                    "received_date": str(s.received_date) if s.received_date else None,
                    "notes": s.notes,
                    "created_at": str(s.created_at),
                }
                for s in rows
            ],
            "total": total,
            "page": page,
            "page_size": page_size,
        }
    )


@sample_router.post("", status_code=201)
async def create_sample(
    body: SampleCreate,
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(get_current_user),
):
    data = body.model_dump()
    for date_field in ("apply_date", "shipped_date", "received_date"):
        if data.get(date_field):
            data[date_field] = datetime.fromisoformat(data[date_field])
    sample = Sample(**data)
    db.add(sample)
    await db.flush()
    return ok({"id": sample.id, "status": sample.status})


@sample_router.post("/{sample_id}/transition")
async def transition_sample(
    sample_id: int,
    body: SampleTransition,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    sample = await db.get(Sample, sample_id)
    if sample is None or sample.deleted_at is not None:
        raise NotFoundError("样品记录不存在")
    await transition_status(
        db,
        sample,
        body.target_status,
        guard=assert_can_transition_sample,
        aggregate_type="Sample",
        actor=user["user_id"],
        reason=body.reason,
    )
    now = datetime.now(timezone.utc)
    if body.target_status == "shipped" and sample.shipped_date is None:
        sample.shipped_date = now
    elif body.target_status == "received" and sample.received_date is None:
        sample.received_date = now
    await db.commit()
    return ok({"id": sample.id, "status": sample.status})
