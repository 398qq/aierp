from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.security import hash_password
from app.database import get_db
from app.models.user import User
from app.schemas.common import ok, fail
from app.schemas.user import UserResponse, UserCreate, UserUpdate

router = APIRouter(prefix="/users", tags=["users"])


def _user_row(u: User) -> dict:
    return {
        "id": u.id,
        "username": u.username,
        "role": u.role,
        "created_at": str(u.created_at) if u.created_at else None,
        "is_active": u.deleted_at is None,
    }


# --- List ---
class PaginatedUsers(BaseModel):
    list: list[dict]
    total: int
    page: int
    page_size: int


@router.get("")
async def list_users(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=200),
    q: str | None = None,
    role: str | None = None,
    is_active: bool | None = None,
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(get_current_user),
):
    base = select(User)
    count_base = select(func.count(User.id))

    # Filter non-deleted
    base = base.where(User.deleted_at.is_(None))
    count_base = count_base.where(User.deleted_at.is_(None))

    if q:
        like = f"%{q}%"
        filt = User.username.ilike(like)
        base = base.where(filt)
        count_base = count_base.where(filt)

    if role:
        base = base.where(User.role == role)
        count_base = count_base.where(User.role == role)

    if is_active is not None:
        if is_active:
            base = base.where(User.deleted_at.is_(None))
            count_base = count_base.where(User.deleted_at.is_(None))
        else:
            base = base.where(User.deleted_at.isnot(None))
            count_base = count_base.where(User.deleted_at.isnot(None))

    total = (await db.execute(count_base)).scalar() or 0

    rows = (await db.execute(
        base.order_by(User.id.desc()).offset((page - 1) * page_size).limit(page_size)
    )).scalars().all()

    return ok({
        "list": [_user_row(u) for u in rows],
        "total": total,
        "page": page,
        "page_size": page_size,
    })


# --- Detail ---
@router.get("/{user_id}")
async def get_user(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(get_current_user),
):
    row = (await db.execute(
        select(User).where(User.id == user_id, User.deleted_at.is_(None))
    )).scalar_one_or_none()

    if not row:
        return fail("用户不存在", 404)

    return ok(_user_row(row))


# --- Create ---
@router.post("")
async def create_user(
    body: UserCreate,
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(get_current_user),
):
    # Check duplicate username
    existing = (await db.execute(
        select(User).where(User.username == body.username, User.deleted_at.is_(None))
    )).scalar_one_or_none()

    if existing:
        return fail("用户名已存在", 400)

    hashed = hash_password(body.password)
    user = User(username=body.username, password=hashed, role=body.role)
    db.add(user)
    await db.flush()
    await db.refresh(user)

    return ok(_user_row(user))


# --- Update ---
@router.put("/{user_id}")
async def update_user(
    user_id: int,
    body: UserUpdate,
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(get_current_user),
):
    row = (await db.execute(
        select(User).where(User.id == user_id, User.deleted_at.is_(None))
    )).scalar_one_or_none()

    if not row:
        return fail("用户不存在", 404)

    if body.role is not None:
        row.role = body.role

    if body.password is not None:
        row.password = hash_password(body.password)

    await db.flush()
    await db.refresh(row)

    return ok(_user_row(row))


# --- Soft Delete ---
@router.delete("/{user_id}")
async def delete_user(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(get_current_user),
):
    row = (await db.execute(
        select(User).where(User.id == user_id, User.deleted_at.is_(None))
    )).scalar_one_or_none()

    if not row:
        return fail("用户不存在", 404)

    row.deleted_at = datetime.now(timezone.utc)
    await db.flush()

    return ok({"id": user_id})
