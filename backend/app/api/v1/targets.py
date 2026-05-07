"""Sales targets API — KPI tracking."""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.database import get_db
from app.models.finance import SalesTarget
from app.schemas.common import fail, ok
from app.schemas.finance import SalesTargetCreate, SalesTargetUpdate

router = APIRouter(prefix="/sales/targets", tags=["sales-targets"])


def _parse_date(value: str | None) -> datetime | None:
    if value:
        return datetime.fromisoformat(value)
    return None


def _serialize_dt(dt: datetime | None) -> str | None:
    return str(dt) if dt else None


def _target_row(t: SalesTarget) -> dict:
    return {
        "id": t.id, "user_id": t.user_id, "target_amount": float(t.target_amount),
        "target_type": t.target_type, "actual_amount": float(t.actual_amount),
        "period_start": _serialize_dt(t.period_start), "period_end": _serialize_dt(t.period_end),
        "status": t.status, "created_at": str(t.created_at),
    }


@router.get("")
async def list_targets(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    user_id: int | None = None,
    target_type: str | None = None,
    status: str | None = None,
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(get_current_user),
):
    base = select(SalesTarget).where(SalesTarget.deleted_at.is_(None))
    count_base = select(func.count(SalesTarget.id)).where(SalesTarget.deleted_at.is_(None))

    if user_id:
        base = base.where(SalesTarget.user_id == user_id)
        count_base = count_base.where(SalesTarget.user_id == user_id)
    if target_type:
        base = base.where(SalesTarget.target_type == target_type)
        count_base = count_base.where(SalesTarget.target_type == target_type)
    if status:
        base = base.where(SalesTarget.status == status)
        count_base = count_base.where(SalesTarget.status == status)

    total = (await db.execute(count_base)).scalar() or 0
    rows = (await db.execute(
        base.order_by(SalesTarget.id.desc()).offset((page - 1) * page_size).limit(page_size)
    )).scalars().all()

    return ok({
        "list": [_target_row(t) for t in rows],
        "total": total, "page": page, "page_size": page_size,
    })


@router.get("/summary")
async def get_target_summary(db: AsyncSession = Depends(get_db), _user: dict = Depends(get_current_user)):
    rows = (await db.execute(
        select(SalesTarget).where(SalesTarget.deleted_at.is_(None)).order_by(SalesTarget.period_start.desc())
    )).scalars().all()

    items = []
    for t in rows:
        completion = round(float(t.actual_amount) / float(t.target_amount) * 100, 1) if float(t.target_amount) > 0 else 0
        items.append({
            "id": t.id, "user_id": t.user_id, "target_type": t.target_type,
            "target_amount": float(t.target_amount), "actual_amount": float(t.actual_amount),
            "completion_rate": completion, "status": t.status,
            "period_start": _serialize_dt(t.period_start), "period_end": _serialize_dt(t.period_end),
        })

    total_target = sum(t["target_amount"] for t in items)
    total_actual = sum(t["actual_amount"] for t in items)
    overall_rate = round(total_actual / total_target * 100, 1) if total_target > 0 else 0

    return ok({
        "items": items,
        "total_target": total_target,
        "total_actual": total_actual,
        "overall_completion_rate": overall_rate,
    })


@router.get("/{target_id}")
async def get_target(target_id: int, db: AsyncSession = Depends(get_db), _user: dict = Depends(get_current_user)):
    result = await db.execute(
        select(SalesTarget).where(SalesTarget.id == target_id, SalesTarget.deleted_at.is_(None))
    )
    target = result.scalar_one_or_none()
    if target is None:
        return fail("Target not found", 404)
    return ok(_target_row(target))


@router.post("", status_code=201)
async def create_target(body: SalesTargetCreate, db: AsyncSession = Depends(get_db), _user: dict = Depends(get_current_user)):
    data = body.model_dump()
    for field in ("period_start", "period_end"):
        if data.get(field):
            data[field] = _parse_date(data[field])
    target = SalesTarget(**data)
    db.add(target)
    await db.flush()
    return ok({"id": target.id})


@router.put("/{target_id}")
async def update_target(target_id: int, body: SalesTargetUpdate, db: AsyncSession = Depends(get_db), _user: dict = Depends(get_current_user)):
    result = await db.execute(
        select(SalesTarget).where(SalesTarget.id == target_id, SalesTarget.deleted_at.is_(None))
    )
    target = result.scalar_one_or_none()
    if target is None:
        return fail("Target not found", 404)
    data = body.model_dump(exclude_unset=True)
    for field in ("period_start", "period_end"):
        if data.get(field):
            data[field] = _parse_date(data[field])
    for key, val in data.items():
        setattr(target, key, val)
    await db.flush()
    return ok({"id": target.id})


@router.delete("/{target_id}")
async def delete_target(target_id: int, db: AsyncSession = Depends(get_db), _user: dict = Depends(get_current_user)):
    result = await db.execute(
        select(SalesTarget).where(SalesTarget.id == target_id, SalesTarget.deleted_at.is_(None))
    )
    target = result.scalar_one_or_none()
    if target is None:
        return fail("Target not found", 404)
    target.deleted_at = datetime.now(timezone.utc)
    await db.flush()
    return ok(msg="deleted")
