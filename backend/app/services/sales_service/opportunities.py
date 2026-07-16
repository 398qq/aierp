from __future__ import annotations

import logging
from datetime import datetime, timezone

from app.domain.states import assert_can_transition_opportunity
from app.models.audit import FieldChangeLog, StatusTransitionLog
from app.models.sales import Opportunity
from app.services.sales_service._helpers import _customer_search_ids
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


def _audit_value(value: object) -> str | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.isoformat()
    return str(value)


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

    return {"list": rows, "total": total, "page": page, "page_size": page_size}


async def get_opportunity(db: AsyncSession, opp_id: int) -> Opportunity | None:
    result = await db.execute(
        select(Opportunity).where(
            Opportunity.id == opp_id, Opportunity.deleted_at.is_(None)
        )
    )
    return result.scalar_one_or_none()


async def get_opportunity_audit(db: AsyncSession, opp_id: int) -> dict:
    """Return a unified, newest-first audit trail for one opportunity."""
    transitions = (
        (
            await db.execute(
                select(StatusTransitionLog).where(
                    StatusTransitionLog.aggregate_id == opp_id,
                    StatusTransitionLog.aggregate_type.in_(
                        ("opportunity", "opportunity_stage")
                    ),
                )
            )
        )
        .scalars()
        .all()
    )
    field_changes = (
        (
            await db.execute(
                select(FieldChangeLog).where(
                    FieldChangeLog.table_name == "opportunities",
                    FieldChangeLog.record_id == opp_id,
                    FieldChangeLog.field_name.not_in(("status", "stage")),
                )
            )
        )
        .scalars()
        .all()
    )

    items = [
        {
            "id": f"transition-{row.id}",
            "event_type": "transition",
            "action": row.action,
            "field_name": "stage"
            if row.aggregate_type == "opportunity_stage"
            else "status",
            "before": row.status_before,
            "after": row.status_after,
            "actor": row.actor,
            "reason": row.reason,
            "occurred_at": row.transitioned_at.isoformat(),
        }
        for row in transitions
    ]
    items.extend(
        {
            "id": f"field-{row.id}",
            "event_type": "field_change",
            "action": "field_change",
            "field_name": row.field_name,
            "before": row.old_value,
            "after": row.new_value,
            "actor": row.actor,
            "reason": row.reason,
            "occurred_at": row.changed_at.isoformat(),
        }
        for row in field_changes
    )
    items.sort(key=lambda item: item["occurred_at"], reverse=True)
    return {
        "list": items,
        "total": len(items),
        "transition_count": len(transitions),
        "field_change_count": len(field_changes),
    }


async def create_opportunity(
    db: AsyncSession, data: dict, *, actor: str | None = None
) -> Opportunity:
    opp = Opportunity(**data)
    db.add(opp)
    await db.flush()

    # Trigger customer state machine transition
    from app.services.customer_state_service import on_first_opportunity

    await on_first_opportunity(db, opp.customer_id)

    db.add(
        StatusTransitionLog(
            aggregate_type="opportunity",
            aggregate_id=opp.id,
            aggregate_no=f"OPP-{opp.id:06d}",
            status_before=None,
            status_after=opp.status,
            action="create",
            actor=actor,
            customer_id=opp.customer_id,
        )
    )

    await db.commit()
    await db.refresh(opp)
    return opp


async def update_opportunity(
    db: AsyncSession,
    opp: Opportunity,
    data: dict,
    *,
    actor: str | None = None,
) -> Opportunity:
    changes = {
        key: (getattr(opp, key, None), value)
        for key, value in data.items()
        if value is not None and getattr(opp, key, None) != value
    }
    if "status" in data and data["status"] != opp.status:
        assert_can_transition_opportunity(opp.status, data["status"])
    for k, v in data.items():
        if v is not None:
            setattr(opp, k, v)
    for field_name, (old_value, new_value) in changes.items():
        db.add(
            FieldChangeLog(
                table_name="opportunities",
                record_id=opp.id,
                field_name=field_name,
                old_value=_audit_value(old_value),
                new_value=_audit_value(new_value),
                actor=actor,
            )
        )
    if "status" in changes:
        before, after = changes["status"]
        db.add(
            StatusTransitionLog(
                aggregate_type="opportunity",
                aggregate_id=opp.id,
                aggregate_no=f"OPP-{opp.id:06d}",
                status_before=_audit_value(before),
                status_after=str(after),
                action="status_change",
                actor=actor,
                customer_id=opp.customer_id,
            )
        )
    if "stage" in changes:
        before, after = changes["stage"]
        db.add(
            StatusTransitionLog(
                aggregate_type="opportunity_stage",
                aggregate_id=opp.id,
                aggregate_no=f"OPP-{opp.id:06d}",
                status_before=_audit_value(before),
                status_after=str(after),
                action="stage_change",
                actor=actor,
                customer_id=opp.customer_id,
            )
        )
    await db.commit()
    await db.refresh(opp)
    return opp


async def delete_opportunity(
    db: AsyncSession, opp: Opportunity, *, actor: str | None = None
) -> None:
    deleted_at = datetime.now(timezone.utc)
    opp.deleted_at = deleted_at
    db.add(
        FieldChangeLog(
            table_name="opportunities",
            record_id=opp.id,
            field_name="deleted_at",
            old_value=None,
            new_value=deleted_at.isoformat(),
            actor=actor,
        )
    )
    db.add(
        StatusTransitionLog(
            aggregate_type="opportunity",
            aggregate_id=opp.id,
            aggregate_no=f"OPP-{opp.id:06d}",
            status_before=opp.status,
            status_after="deleted",
            action="delete",
            actor=actor,
            customer_id=opp.customer_id,
        )
    )
    await db.commit()


# ============================================================
# Quotation CRUD
