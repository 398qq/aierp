"""Notification service — CRUD for in-app notifications."""

from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.finance import Notification


async def get_notifications(
    db: AsyncSession, *, user_id: int, page: int = 1, page_size: int = 20,
    unread_only: bool = False, type: str | None = None,
) -> dict:
    base = select(Notification).where(
        Notification.deleted_at.is_(None),
        Notification.user_id == user_id,
    )
    cnt = select(func.count(Notification.id)).where(
        Notification.deleted_at.is_(None),
        Notification.user_id == user_id,
    )
    if unread_only:
        base = base.where(not Notification.is_read)
        cnt = cnt.where(not Notification.is_read)
    if type:
        base = base.where(Notification.type == type)
        cnt = cnt.where(Notification.type == type)
    total = (await db.execute(cnt)).scalar() or 0
    rows = (
        (await db.execute(
            base.order_by(Notification.id.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        ))
        .scalars()
        .all()
    )
    unread = (await db.execute(
        select(func.count(Notification.id)).where(
            Notification.deleted_at.is_(None),
            Notification.user_id == user_id,
            not Notification.is_read,
        )
    )).scalar() or 0
    return {"list": rows, "total": total, "page": page, "page_size": page_size, "unread_count": unread}


async def get_unread_count(db: AsyncSession, *, user_id: int) -> int:
    result = await db.execute(
        select(func.count(Notification.id)).where(
            Notification.deleted_at.is_(None),
            Notification.user_id == user_id,
            not Notification.is_read,
        )
    )
    return result.scalar() or 0


async def mark_read(
    db: AsyncSession, *, user_id: int, ids: list[int] | None = None, all: bool = False,
) -> int:
    stmt = (
        update(Notification)
        .where(
            Notification.deleted_at.is_(None),
            Notification.user_id == user_id,
        )
        .values(is_read=True)
    )
    if not all and ids:
        stmt = stmt.where(Notification.id.in_(ids))
    result = await db.execute(stmt)
    await db.commit()
    return result.rowcount


async def create_notification(
    db: AsyncSession, *,
    user_id: int, type: str = "system", title: str = "",
    content: str | None = None, related_id: int | None = None,
) -> Notification:
    notif = Notification(
        user_id=user_id, type=type, title=title,
        content=content, related_id=related_id,
    )
    db.add(notif)
    await db.commit()
    await db.refresh(notif)
    return notif


async def delete_notification(db: AsyncSession, notif: Notification) -> None:
    notif.deleted_at = datetime.now(timezone.utc)
    await db.commit()


async def delete_old_notifications(db: AsyncSession, *, days: int = 90) -> int:
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    result = await db.execute(
        update(Notification)
        .where(Notification.created_at < cutoff, Notification.deleted_at.is_(None))
        .values(deleted_at=datetime.now(timezone.utc))
    )
    await db.commit()
    return result.rowcount
