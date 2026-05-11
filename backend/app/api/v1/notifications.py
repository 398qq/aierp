"""Notification API routes — list, unread count, mark read, templates, preferences."""

import datetime

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.permissions import require_perm
from app.database import get_db
from app.models.account import NotificationPreference, NotificationTemplate
from app.schemas.common import fail, ok
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


# ---------------------------------------------------------------------------
# Notification Templates
# ---------------------------------------------------------------------------
@router.get("/notifications/templates")
async def list_templates(
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(require_perm("system", "read")),
):
    result = await db.execute(
        select(NotificationTemplate).where(NotificationTemplate.deleted_at.is_(None)).order_by(NotificationTemplate.code)
    )
    temps = result.scalars().all()
    return ok([{
        "id": t.id, "code": t.code, "name": t.name, "channel": t.channel,
        "event_type": t.event_type, "subject_template": t.subject_template,
        "body_template": t.body_template, "enabled": t.enabled,
    } for t in temps])


class TemplateSave(BaseModel):
    code: str; name: str; channel: str = "in_app"; event_type: str = ""
    subject_template: str = ""; body_template: str; enabled: bool = True


@router.put("/notifications/templates/{template_id}")
async def update_template(template_id: int, body: TemplateSave,
                          db: AsyncSession = Depends(get_db),
                          _user: dict = Depends(require_perm("system", "write"))):
    t = (await db.execute(
        select(NotificationTemplate).where(NotificationTemplate.id == template_id, NotificationTemplate.deleted_at.is_(None))
    )).scalar_one_or_none()
    if not t:
        return fail("模板不存在")
    t.name = body.name; t.channel = body.channel; t.event_type = body.event_type
    t.subject_template = body.subject_template; t.body_template = body.body_template
    t.enabled = body.enabled
    await db.commit()
    return ok(msg="模板更新成功")


# ---------------------------------------------------------------------------
# Notification Preferences (per user)
# ---------------------------------------------------------------------------
@router.get("/notifications/preferences")
async def get_preferences(
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    result = await db.execute(
        select(NotificationPreference).where(
            NotificationPreference.user_id == current_user["user_id"],
            NotificationPreference.deleted_at.is_(None),
        )
    )
    prefs = result.scalars().all()
    return ok([{
        "id": p.id, "event_type": p.event_type, "channel": p.channel, "enabled": p.enabled,
    } for p in prefs])


class PrefSave(BaseModel):
    preferences: list[dict]  # [{event_type, channel, enabled}]


@router.put("/notifications/preferences")
async def save_preferences(
    body: PrefSave,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    # Delete existing preferences
    existing = (await db.execute(
        select(NotificationPreference).where(
            NotificationPreference.user_id == current_user["user_id"],
            NotificationPreference.deleted_at.is_(None),
        )
    )).scalars().all()
    for p in existing:
        p.deleted_at = datetime.datetime.now(datetime.timezone.utc)

    # Insert new
    for pref in body.preferences:
        db.add(NotificationPreference(
            user_id=current_user["user_id"],
            event_type=pref.get("event_type", ""),
            channel=pref.get("channel", "in_app"),
            enabled=pref.get("enabled", True),
        ))

    await db.commit()
    return ok(msg="偏好已保存")
