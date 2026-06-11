"""Field-level audit log query API (Stage 10 Day 3).

Exposes FieldChangeLog for read-only viewing.

Endpoints:
- GET /audit/field-changes - paginated, filter by table/record/field/actor/time
- GET /audit/field-changes/recent - last N changes (no pagination, fast path)
- GET /audit/field-changes/summary - aggregated counts (per table / per actor)
"""

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.database import get_db
from app.models.audit import FieldChangeLog
from app.schemas.common import ok

router = APIRouter(prefix="/audit", tags=["audit"])


@router.get("/field-changes")
async def list_field_changes(
    table_name: Optional[str] = Query(None, description="Filter by table (e.g. 'customer')"),
    record_id: Optional[int] = Query(None, description="Filter by record id"),
    field_name: Optional[str] = Query(None, description="Filter by field (e.g. 'email')"),
    actor: Optional[str] = Query(None, description="Filter by actor (e.g. 'alice')"),
    days_back: int = Query(30, ge=1, le=365, description="Window in days"),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """Paginated field change log with optional filters.

    Most common use: show audit history of one record, e.g.
      GET /audit/field-changes?table_name=customer&record_id=42
    """
    cutoff = datetime.utcnow() - (datetime.utcnow() - datetime.utcfromtimestamp(0))
    from datetime import timedelta, timezone

    cutoff = datetime.now(timezone.utc) - timedelta(days=days_back)

    conditions = [FieldChangeLog.changed_at >= cutoff]
    if table_name:
        conditions.append(FieldChangeLog.table_name == table_name)
    if record_id is not None:
        conditions.append(FieldChangeLog.record_id == record_id)
    if field_name:
        conditions.append(FieldChangeLog.field_name == field_name)
    if actor:
        conditions.append(FieldChangeLog.actor == actor)

    # Total count for pagination
    total = (await db.scalar(
        select(func.count(FieldChangeLog.id)).where(*conditions)
    )) or 0

    # Page rows
    offset = (page - 1) * page_size
    rows = (await db.execute(
        select(FieldChangeLog)
        .where(*conditions)
        .order_by(FieldChangeLog.changed_at.desc())
        .offset(offset)
        .limit(page_size)
    )).scalars().all()

    items = [
        {
            "id": r.id,
            "table_name": r.table_name,
            "record_id": r.record_id,
            "field_name": r.field_name,
            "old_value": r.old_value,
            "new_value": r.new_value,
            "actor": r.actor,
            "reason": r.reason,
            "changed_at": r.changed_at.isoformat() if r.changed_at else None,
        }
        for r in rows
    ]
    return ok({
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
    })


@router.get("/field-changes/recent")
async def recent_field_changes(
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """Last N changes across all tables. No pagination — fast path for 'recent activity' widget."""
    rows = (await db.execute(
        select(FieldChangeLog)
        .order_by(FieldChangeLog.changed_at.desc())
        .limit(limit)
    )).scalars().all()
    items = [
        {
            "id": r.id,
            "table_name": r.table_name,
            "record_id": r.record_id,
            "field_name": r.field_name,
            "old_value": r.old_value,
            "new_value": r.new_value,
            "actor": r.actor,
            "changed_at": r.changed_at.isoformat() if r.changed_at else None,
        }
        for r in rows
    ]
    return ok({"items": items, "count": len(items)})


@router.get("/field-changes/summary")
async def field_changes_summary(
    days_back: int = Query(30, ge=1, le=365),
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """Aggregated counts — for 'who changed what' dashboard.

    Returns:
        by_table:  { table_name: change_count }
        by_actor:  { actor: change_count }
        by_field:  { table.field: change_count }  (top 20)
    """
    from datetime import timedelta, timezone

    cutoff = datetime.now(timezone.utc) - timedelta(days=days_back)

    # by table
    by_table_rows = (await db.execute(
        select(FieldChangeLog.table_name, func.count(FieldChangeLog.id))
        .where(FieldChangeLog.changed_at >= cutoff)
        .group_by(FieldChangeLog.table_name)
    )).all()
    by_table = {row[0]: row[1] for row in by_table_rows}

    # by actor
    by_actor_rows = (await db.execute(
        select(FieldChangeLog.actor, func.count(FieldChangeLog.id))
        .where(FieldChangeLog.changed_at >= cutoff, FieldChangeLog.actor.is_not(None))
        .group_by(FieldChangeLog.actor)
    )).all()
    by_actor = {row[0]: row[1] for row in by_actor_rows}

    # by (table, field) — top 20
    by_field_rows = (await db.execute(
        select(
            FieldChangeLog.table_name,
            FieldChangeLog.field_name,
            func.count(FieldChangeLog.id).label("cnt"),
        )
        .where(FieldChangeLog.changed_at >= cutoff)
        .group_by(FieldChangeLog.table_name, FieldChangeLog.field_name)
        .order_by(func.count(FieldChangeLog.id).desc())
        .limit(20)
    )).all()
    by_field = [
        {"table": r[0], "field": r[1], "count": r[2]}
        for r in by_field_rows
    ]

    return ok({
        "days_back": days_back,
        "by_table": by_table,
        "by_actor": by_actor,
        "top_fields": by_field,
    })
