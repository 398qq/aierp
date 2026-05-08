"""Notification API routes."""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.database import get_db
from app.schemas.finance import MarkReadRequest
from app.services import notification_service as svc

router = APIRouter(tags=["notifications"])


@router.get("/notifications")
async def list_notifications(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    unread_only: bool = Query(False),
    type: str | None = Query(None),
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(get_current_user),
):
    data = await svc.get_notifications(
        db, user_id=_user["user_id"], page=page, page_size=page_size,
        unread_only=unread_only, type=type,
    )
    return {"code": 0, "msg": "success", "data": data}


@router.get("/notifications/unread-count")
async def unread_count(
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(get_current_user),
):
    count = await svc.get_unread_count(db, user_id=_user["user_id"])
    return {"code": 0, "msg": "success", "data": {"count": count}}


@router.post("/notifications/mark-read")
async def mark_read(
    body: MarkReadRequest,
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(get_current_user),
):
    affected = await svc.mark_read(db, user_id=_user["user_id"], ids=body.ids, mark_all=body.all)
    return {"code": 0, "msg": "success", "data": {"affected": affected}}
