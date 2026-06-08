from __future__ import annotations

import logging
from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.finance import SalesTarget


logger = logging.getLogger(__name__)


async def list_targets(db: AsyncSession, page: int = 1, page_size: int = 20, status: str | None = None) -> dict:
    offset = (page - 1) * page_size
    conditions = [SalesTarget.deleted_at.is_(None)]
    if status:
        conditions.append(SalesTarget.status == status)
    total = (await db.execute(select(func.count()).where(*conditions))).scalar() or 0
    rows = (await db.execute(
        select(SalesTarget).where(*conditions).order_by(SalesTarget.id.desc()).offset(offset).limit(page_size)
    )).scalars().all()
    return {"list": rows, "total": total, "page": page, "page_size": page_size}

async def get_target(db: AsyncSession, target_id: int) -> SalesTarget | None:
    result = await db.execute(
        select(SalesTarget).where(SalesTarget.id == target_id, SalesTarget.deleted_at.is_(None))
    )
    return result.scalar_one_or_none()

async def create_target(db: AsyncSession, data: dict) -> SalesTarget:
    data = {k: v for k, v in data.items() if v is not None}
    target = SalesTarget(**data)
    db.add(target)
    await db.commit()
    await db.refresh(target)
    return target

async def update_target(db: AsyncSession, target: SalesTarget, data: dict) -> SalesTarget:
    for k, v in data.items():
        setattr(target, k, v)
    await db.commit()
    await db.refresh(target)
    return target

async def delete_target(db: AsyncSession, target: SalesTarget):
    target.deleted_at = datetime.now(timezone.utc)
    await db.commit()

async def get_target_summary(db: AsyncSession) -> list:
    rows = (await db.execute(
        select(SalesTarget).where(SalesTarget.deleted_at.is_(None))
    )).scalars().all()
    return [{"id": r.id, "period": r.period, "target_amount": r.target_amount, "target_orders": r.target_orders, "user_id": r.user_id} for r in rows]

async def get_target_stats(db: AsyncSession) -> dict:
    rows = (await db.execute(
        select(SalesTarget).where(SalesTarget.deleted_at.is_(None))
    )).scalars().all()
    total_target = sum(float(r.target_amount or 0) for r in rows)
    total_actual = sum(float(r.actual_amount or 0) for r in rows)
    achievement_pct = round(total_actual / total_target * 100, 1) if total_target else 0
    completed = sum(1 for r in rows if r.status == "completed")
    return {
        "total_target": total_target,
        "total_actual": total_actual,
        "achievement_pct": achievement_pct,
        "count": len(rows),
        "completed": completed,
    }
