"""Notifications API."""


from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.database import get_db
from app.models.finance import Notification
from app.schemas.common import fail, ok
from app.schemas.finance import MarkReadRequest

router = APIRouter(prefix="/notifications", tags=["notifications"])


@router.get("/unread-count")
async def unread_count(db: AsyncSession = Depends(get_db), _user: dict = Depends(get_current_user)):
    count = (await db.execute(
        select(func.count(Notification.id)).where(
            Notification.deleted_at.is_(None),
            Notification.user_id == _user["user_id"],
            not Notification.is_read,
        )
    )).scalar() or 0
    return ok({"count": count})


def _notif_row(n: Notification) -> dict:
    return {
        "id": n.id, "user_id": n.user_id, "type": n.type,
        "title": n.title, "content": n.content, "related_id": n.related_id,
        "is_read": n.is_read, "created_at": str(n.created_at),
    }


@router.get("")
async def list_notifications(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    is_read: bool | None = None,
    type: str | None = None,
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(get_current_user),
):
    user_id = _user["user_id"]
    base = select(Notification).where(Notification.deleted_at.is_(None), Notification.user_id == user_id)
    count_base = select(func.count(Notification.id)).where(Notification.deleted_at.is_(None), Notification.user_id == user_id)

    if is_read is not None:
        base = base.where(Notification.is_read == is_read)
        count_base = count_base.where(Notification.is_read == is_read)
    if type:
        base = base.where(Notification.type == type)
        count_base = count_base.where(Notification.type == type)

    total = (await db.execute(count_base)).scalar() or 0
    rows = (await db.execute(
        base.order_by(Notification.id.desc()).offset((page - 1) * page_size).limit(page_size)
    )).scalars().all()

    unread_count = (await db.execute(
        select(func.count(Notification.id)).where(
            Notification.deleted_at.is_(None), Notification.user_id == user_id, not Notification.is_read
        )
    )).scalar() or 0

    return ok({
        "list": [_notif_row(n) for n in rows],
        "total": total, "page": page, "page_size": page_size,
        "unread_count": unread_count,
    })


@router.post("/mark-read")
async def mark_read(body: MarkReadRequest, db: AsyncSession = Depends(get_db), _user: dict = Depends(get_current_user)):
    user_id = _user["user_id"]

    if body.all:
        result = await db.execute(
            select(Notification).where(
                Notification.deleted_at.is_(None), Notification.user_id == user_id, not Notification.is_read
            )
        )
        rows = result.scalars().all()
    elif body.ids:
        result = await db.execute(
            select(Notification).where(
                Notification.deleted_at.is_(None), Notification.user_id == user_id, Notification.id.in_(body.ids)
            )
        )
        rows = result.scalars().all()
    else:
        return fail("ids or all required")

    for row in rows:
        row.is_read = True
    await db.flush()
    return ok({"marked": len(rows)})
