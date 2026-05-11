"""RBAC permission enforcement — FastAPI dependency."""

import json
import logging

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.database import get_db
from app.models.rbac import AuditLog, Permission, Role
from app.models.user import User

logger = logging.getLogger(__name__)

# Resource registry — modules register their resources here
RESOURCES: dict[str, str] = {
    "customers": "客户管理",
    "products": "产品管理",
    "sales": "销售管理",
    "purchases": "采购管理",
    "finance": "财务管理",
    "inventory": "库存管理",
    "reports": "报表管理",
    "system": "系统管理",
}


def require_perm(resource: str, action: str):
    """Factory: returns a FastAPI dependency that checks the given permission."""

    async def checker(
        request: Request,
        current_user: dict = Depends(get_current_user),
        db: AsyncSession = Depends(get_db),
    ) -> dict:
        user_id = current_user["user_id"]
        username = current_user.get("username", "")

        # Admin bypass — role string check for backward compat
        user = (await db.execute(
            select(User.role).where(User.id == user_id)
        )).scalar_one_or_none()
        if user == "admin":
            return current_user

        # Check permission via RBAC roles
        perm = (await db.execute(
            select(Permission.id).where(
                Permission.resource == resource,
                Permission.action == action,
                Permission.deleted_at.is_(None),
            )
        )).scalar_one_or_none()
        if perm is None:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=f"未知权限: {resource}:{action}")

        has_perm = (await db.execute(
            select(Role.id).where(
                Role.deleted_at.is_(None),
                Role.id.in_(
                    select(Role.id).join(Role.permissions).where(
                        Permission.id == perm,
                    )
                ),
                Role.id.in_(
                    select(Role.id).join(Role.users).where(User.id == user_id)
                ),
            )
        )).scalar_one_or_none()

        if not has_perm:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=f"权限不足: {resource}:{action}")

        return current_user

    return checker


async def write_audit_log(
    db: AsyncSession,
    user_id: int,
    username: str,
    action: str,
    resource_type: str,
    resource_id: int | None,
    summary: str = "",
    ip_address: str = "",
):
    """Write an audit log entry. Fire-and-forget — errors are logged but not raised."""
    try:
        log_entry = AuditLog(
            user_id=user_id,
            username=username,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            summary=summary[:500] if summary else "",
            ip_address=ip_address[:50] if ip_address else "",
        )
        db.add(log_entry)
        await db.flush()
    except Exception:
        logger.exception("Failed to write audit log")
