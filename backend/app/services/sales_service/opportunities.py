from __future__ import annotations

import logging
from datetime import datetime, timezone

from app.domain.states import assert_can_transition_opportunity
from app.models.sales import Opportunity
from app.services.sales_service._helpers import _customer_search_ids
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


async def list_opportunities(
    db: AsyncSession,
    *,
    page: int = 1,
    page_size: int = 20,
    customer_id: int | None = None,
    status: str | None = None,
    stage: str | None = None,
    assigned_to: str | None = None,
    q: str | None = None,
    sort_by: str = "id",
    sort_order: str = "desc",
) -> dict:
    base = select(Opportunity).where(Opportunity.deleted_at.is_(None))
    cnt = select(func.count(Opportunity.id)).where(Opportunity.deleted_at.is_(None))

    if customer_id:
        base = base.where(Opportunity.customer_id == customer_id)
        cnt = cnt.where(Opportunity.customer_id == customer_id)
    if status:
        base = base.where(Opportunity.status == status)
        cnt = cnt.where(Opportunity.status == status)
    if stage:
        base = base.where(Opportunity.stage == stage)
        cnt = cnt.where(Opportunity.stage == stage)
    if assigned_to:
        base = base.where(Opportunity.assigned_to == assigned_to)
        cnt = cnt.where(Opportunity.assigned_to == assigned_to)
    if q and q.strip():
        pattern = f"%{q.strip()}%"
        search_filter = or_(
            Opportunity.title.ilike(pattern),
            Opportunity.description.ilike(pattern),
            Opportunity.notes.ilike(pattern),
            Opportunity.source.ilike(pattern),
            Opportunity.assigned_to.ilike(pattern),
            Opportunity.customer_id.in_(_customer_search_ids(q.strip())),
        )
        base = base.where(search_filter)
        cnt = cnt.where(search_filter)

    total = (await db.execute(cnt)).scalar() or 0

    allowed_sorts = {
        "id",
        "title",
        "amount",
        "status",
        "stage",
        "win_probability",
        "expected_close_date",
        "created_at",
        "updated_at",
    }
    sort_by = sort_by if sort_by in allowed_sorts else "id"
    sort_col = getattr(Opportunity, sort_by, Opportunity.id)
    base = base.order_by(sort_col.desc() if sort_order == "desc" else sort_col.asc())
    rows = (
        (await db.execute(base.offset((page - 1) * page_size).limit(page_size)))
        .scalars()
        .all()
    )

    # Resolve customer names in bulk
    from app.models.customer import Customer as CustModel

    cids = [r.customer_id for r in rows if r.customer_id]
    cname_map: dict[int, str] = {}
    if cids:
        cr = await db.execute(
            select(CustModel.id, CustModel.name).where(
                CustModel.id.in_(cids), CustModel.deleted_at.is_(None)
            )
        )
        cname_map = {row[0]: row[1] for row in cr.all()}

    list_data = [_serialize_opportunity(r, cname_map.get(r.customer_id)) for r in rows]
    return {"list": list_data, "total": total, "page": page, "page_size": page_size}


def _serialize_opportunity(opp: Opportunity, customer_name: str | None = None) -> dict:
    return {
        "id": opp.id,
        "title": opp.title,
        "customer_id": opp.customer_id,
        "customer_name": customer_name,
        "amount": float(opp.amount) if opp.amount else None,
        "status": opp.status,
        "stage": opp.stage,
        "win_probability": opp.win_probability,
        "expected_close_date": str(opp.expected_close_date)
        if opp.expected_close_date
        else None,
        "source": opp.source,
        "assigned_to": opp.assigned_to,
        "description": opp.description,
        "notes": opp.notes,
        "created_at": str(opp.created_at) if opp.created_at else None,
        "updated_at": str(opp.updated_at) if opp.updated_at else None,
        "deleted_at": str(opp.deleted_at) if opp.deleted_at else None,
    }


async def get_opportunity(db: AsyncSession, opp_id: int) -> Opportunity | None:
    result = await db.execute(
        select(Opportunity).where(
            Opportunity.id == opp_id, Opportunity.deleted_at.is_(None)
        )
    )
    return result.scalar_one_or_none()


async def create_opportunity(db: AsyncSession, data: dict) -> Opportunity:
    opp = Opportunity(**data)
    db.add(opp)
    await db.flush()

    # Trigger customer state machine transition
    from app.services.customer_state_service import on_first_opportunity

    await on_first_opportunity(db, opp.customer_id)

    await db.commit()
    await db.refresh(opp)
    return opp


async def update_opportunity(
    db: AsyncSession, opp: Opportunity, data: dict
) -> Opportunity:
    if "status" in data and data["status"] != opp.status:
        assert_can_transition_opportunity(opp.status, data["status"])
    for k, v in data.items():
        if v is not None:
            setattr(opp, k, v)
    await db.commit()
    await db.refresh(opp)
    return opp


async def delete_opportunity(db: AsyncSession, opp: Opportunity) -> None:
    opp.deleted_at = datetime.now(timezone.utc)
    await db.commit()


# ============================================================
# Quotation CRUD
