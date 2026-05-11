"""RBAC permission enforcement — FastAPI dependency."""

import json
import logging

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy import and_, or_, select
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

PERM_CACHE_TTL = 60  # seconds — short enough for security, long enough to reduce DB load


async def _check_perm_db(db: AsyncSession, user_id: int, resource: str, action: str) -> bool:
    return await db.scalar(
        select(select(Role.id).where(
            Role.deleted_at.is_(None),
            Role.users.any(and_(User.id == user_id, User.deleted_at.is_(None))),
            or_(
                Role.name == "admin",
                Role.permissions.any(and_(
                    Permission.resource == resource,
                    Permission.action == action,
                    Permission.deleted_at.is_(None),
                )),
            ),
        ).exists())
    )


def require_perm(resource: str, action: str):
    """Factory: returns a FastAPI dependency that checks the given permission.

    Uses a single EXISTS query with JOINs — atomic, no TOCTOU window.
    Admin role (name='admin') grants unrestricted access.
    Result cached in Redis for PERM_CACHE_TTL seconds.
    """

    async def checker(
        request: Request,
        current_user: dict = Depends(get_current_user),
        db: AsyncSession = Depends(get_db),
    ) -> dict:
        user_id = current_user["user_id"]
        cache_key = f"perm:{user_id}:{resource}:{action}"

        # Try Redis cache first
        from app.services.cache_service import cache_get, cache_set
        cached = await cache_get(cache_key)
        if cached is not None:
            if json.loads(cached) is True:
                return current_user
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

        has_perm = await _check_perm_db(db, user_id, resource, action)

        # Cache result (both allow and deny — short TTL prevents stale denials)
        await cache_set(cache_key, json.dumps(has_perm), PERM_CACHE_TTL)

        if not has_perm:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

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
    """Write and commit an audit log entry immediately.

    Commits in its own savepoint so the audit record survives even if the
    caller's outer transaction rolls back. Failures are logged at ERROR level
    for production alerting.
    """
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
        await db.commit()
    except Exception:
        logger.error("Audit log write failed — audit trail integrity compromised", exc_info=True)
