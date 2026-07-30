"""User preferences CRUD.

GET    /user-preferences/{scope}        — list a user's prefs for a scope
PUT    /user-preferences/{scope}/{key}  — upsert one pref (idempotent)
DELETE /user-preferences/{scope}/{key}  — soft-delete one pref

All endpoints scope results to the authenticated user; cross-user
reads are not supported. Cascade on user delete is configured at the
table level (FOREIGN KEY ... ON DELETE CASCADE).
"""
from fastapi import APIRouter, Depends
from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.database import get_db
from app.models.user_preferences import UserPreference
from app.schemas.common import fail, ok, APIResponse
from app.schemas.user_preferences import (
    UserPreferenceItem,
    UserPreferenceList,
)

router = APIRouter(prefix="/user-preferences", tags=["user-preferences"])


def _row_to_item(p: UserPreference) -> UserPreferenceItem:
    return UserPreferenceItem(scope=p.scope, key=p.key, value=p.value)


@router.get(
    "/{scope}",
    response_model=APIResponse[UserPreferenceList],
)
async def list_prefs(
    scope: str,
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(get_current_user),
):
    rows = (
        await db.execute(
            select(UserPreference)
            .where(
                UserPreference.user_id == _user["user_id"],
                UserPreference.scope == scope,
                UserPreference.deleted_at.is_(None),
            )
            .order_by(UserPreference.key)
        )
    ).scalars().all()
    return ok(UserPreferenceList(items=[_row_to_item(p) for p in rows]))


@router.put(
    "/{scope}/{key}",
    response_model=APIResponse[UserPreferenceItem],
)
async def upsert_pref(
    scope: str,
    key: str,
    body: UserPreferenceItem,
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(get_current_user),
):
    if body.scope != scope or body.key != key:
        return fail("path scope/key does not match body", 400)
    existing = (
        await db.execute(
            select(UserPreference).where(
                UserPreference.user_id == _user["user_id"],
                UserPreference.scope == scope,
                UserPreference.key == key,
                UserPreference.deleted_at.is_(None),
            )
        )
    ).scalars().first()
    if existing is not None:
        existing.value = body.value
        item = existing
    else:
        item = UserPreference(
            user_id=_user["user_id"],
            scope=scope,
            key=key,
            value=body.value,
        )
        db.add(item)
    try:
        await db.flush()
    except IntegrityError:
        # concurrent upsert race; let the client retry
        return fail("concurrent upsert, retry", 409)
    return ok(_row_to_item(item))


@router.delete(
    "/{scope}/{key}",
    response_model=APIResponse[dict],
)
async def delete_pref(
    scope: str,
    key: str,
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(get_current_user),
):
    # soft-delete via deleted_at; cascade is for hard delete of user
    res = await db.execute(
        delete(UserPreference).where(
            UserPreference.user_id == _user["user_id"],
            UserPreference.scope == scope,
            UserPreference.key == key,
            UserPreference.deleted_at.is_(None),
        )
    )
    if res.rowcount == 0:
        return fail("not found", 404)
    return ok(msg="deleted")
