from fastapi import APIRouter, Depends, Query, Request
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.permissions import require_perm, write_audit_log, _invalidate_perm_cache
from app.database import get_db
from app.models.rbac import AuditLog, Permission, Role
from app.models.user import User
from app.schemas.common import fail, ok, paginated_ok

router = APIRouter(prefix="/permissions", tags=["permissions"])


# ---------------------------------------------------------------------------
# Permissions — read-only list
# ---------------------------------------------------------------------------
@router.get("")
async def list_permissions(
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(get_current_user),
):
    result = await db.execute(
        select(Permission)
        .where(Permission.deleted_at.is_(None))
        .order_by(Permission.resource, Permission.action)
    )
    perms = result.scalars().all()
    grouped: dict[str, list[dict]] = {}
    for p in perms:
        grouped.setdefault(p.resource, []).append(
            {
                "id": p.id,
                "resource": p.resource,
                "action": p.action,
                "name": p.name,
                "description": p.description,
            }
        )
    return ok({"groups": grouped, "total": len(perms)})


# ---------------------------------------------------------------------------
# Roles
# ---------------------------------------------------------------------------
@router.get("/roles")
async def list_roles(
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(require_perm("system", "read")),
):
    result = await db.execute(
        select(Role).where(Role.deleted_at.is_(None)).order_by(Role.id)
    )
    roles = result.scalars().all()
    data = []
    for r in roles:
        perm_ids = [p.id for p in r.permissions]
        data.append(
            {
                "id": r.id,
                "name": r.name,
                "description": r.description,
                "permission_ids": perm_ids,
                "user_count": len(r.users) if r.users else 0,
            }
        )
    return ok(data)


class RoleCreate(BaseModel):
    name: str
    description: str = ""
    permission_ids: list[int] = []


@router.post("/roles", status_code=201)
async def create_role(
    body: RoleCreate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_perm("system", "write")),
):
    existing = (
        await db.execute(
            select(Role).where(Role.name == body.name, Role.deleted_at.is_(None))
        )
    ).scalar_one_or_none()
    if existing:
        return fail("角色名已存在")

    role = Role(name=body.name, description=body.description)
    db.add(role)
    await db.flush()

    if body.permission_ids:
        perms = (
            (
                await db.execute(
                    select(Permission).where(
                        Permission.id.in_(body.permission_ids),
                        Permission.deleted_at.is_(None),
                    )
                )
            )
            .scalars()
            .all()
        )
        role.permissions = perms
        await db.flush()

    await db.commit()
    await _invalidate_perm_cache()
    await write_audit_log(
        db,
        current_user["user_id"],
        current_user.get("username", ""),
        "create",
        "role",
        role.id,
        f"创建角色: {role.name}",
        request.client.host if request.client else "",
    )
    return ok({"id": role.id}, msg="角色创建成功")


@router.put("/roles/{role_id}")
async def update_role(
    role_id: int,
    body: RoleCreate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_perm("system", "write")),
):
    role = (
        await db.execute(
            select(Role).where(Role.id == role_id, Role.deleted_at.is_(None))
        )
    ).scalar_one_or_none()
    if not role:
        return fail("角色不存在")

    role.name = body.name
    role.description = body.description
    if body.permission_ids is not None:
        perms = (
            (
                await db.execute(
                    select(Permission).where(
                        Permission.id.in_(body.permission_ids),
                        Permission.deleted_at.is_(None),
                    )
                )
            )
            .scalars()
            .all()
        )
        role.permissions = perms

    await db.commit()
    await _invalidate_perm_cache()
    await write_audit_log(
        db,
        current_user["user_id"],
        current_user.get("username", ""),
        "update",
        "role",
        role.id,
        f"更新角色: {role.name}",
        request.client.host if request.client else "",
    )
    return ok(msg="角色更新成功")


@router.delete("/roles/{role_id}")
async def delete_role(
    role_id: int,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_perm("system", "write")),
):
    role = (
        await db.execute(
            select(Role).where(Role.id == role_id, Role.deleted_at.is_(None))
        )
    ).scalar_one_or_none()
    if not role:
        return fail("角色不存在")
    if role.name == "admin":
        return fail("不能删除 admin 角色")

    from datetime import datetime, timezone

    role.deleted_at = datetime.now(timezone.utc)
    await db.commit()
    await _invalidate_perm_cache()
    await write_audit_log(
        db,
        current_user["user_id"],
        current_user.get("username", ""),
        "delete",
        "role",
        role.id,
        f"删除角色: {role.name}",
        request.client.host if request.client else "",
    )
    return ok(msg="角色已删除")


# ---------------------------------------------------------------------------
# User Roles
# ---------------------------------------------------------------------------
class UserRolesBody(BaseModel):
    role_ids: list[int]


@router.get("/users/{user_id}/roles")
async def get_user_roles(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(get_current_user),
):
    user = (
        await db.execute(
            select(User).where(User.id == user_id, User.deleted_at.is_(None))
        )
    ).scalar_one_or_none()
    if not user:
        return fail("用户不存在")
    return ok(
        {
            "user_id": user_id,
            "role_ids": [r.id for r in user.roles],
            "roles": [{"id": r.id, "name": r.name} for r in user.roles],
        }
    )


@router.put("/users/{user_id}/roles")
async def set_user_roles(
    user_id: int,
    body: UserRolesBody,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_perm("system", "write")),
):
    user = (
        await db.execute(
            select(User).where(User.id == user_id, User.deleted_at.is_(None))
        )
    ).scalar_one_or_none()
    if not user:
        return fail("用户不存在")

    roles = (
        (
            await db.execute(
                select(Role).where(
                    Role.id.in_(body.role_ids), Role.deleted_at.is_(None)
                )
            )
        )
        .scalars()
        .all()
    )
    user.roles = roles
    await db.commit()
    await _invalidate_perm_cache()
    await write_audit_log(
        db,
        current_user["user_id"],
        current_user.get("username", ""),
        "update",
        "user_roles",
        user_id,
        f"设置用户 {user.username} 角色: {[r.name for r in roles]}",
        request.client.host if request.client else "",
    )
    return ok(msg="角色设置成功")


# ---------------------------------------------------------------------------
# Audit Logs
# ---------------------------------------------------------------------------
@router.get("/audit-logs")
async def list_audit_logs(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    resource_type: str | None = None,
    user_id: int | None = None,
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(require_perm("system", "read")),
):
    conditions = []
    if resource_type:
        conditions.append(AuditLog.resource_type == resource_type)
    if user_id:
        conditions.append(AuditLog.user_id == user_id)

    total = (await db.scalar(select(func.count(AuditLog.id)).where(*conditions))) or 0
    result = await db.execute(
        select(AuditLog)
        .where(*conditions)
        .order_by(AuditLog.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    logs = result.scalars().all()
    return paginated_ok(
        [
            {
                "id": log.id,
                "user_id": log.user_id,
                "username": log.username,
                "action": log.action,
                "resource_type": log.resource_type,
                "resource_id": log.resource_id,
                "summary": log.summary,
                "ip_address": log.ip_address,
                "created_at": str(log.created_at),
            }
            for log in logs
        ],
        total,
        page,
        page_size,
    )
