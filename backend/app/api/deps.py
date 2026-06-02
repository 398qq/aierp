from fastapi import Cookie, Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.uow import UnitOfWork, get_uow as _get_uow_ctx
from app.core.security import decode_access_token
from app.database import get_db
from app.models.rbac import Role, user_roles_table

security_scheme = HTTPBearer(auto_error=False)
TOKEN_COOKIE_NAME = "aierp_token"


async def get_current_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(security_scheme),
    aierp_token: str | None = Cookie(default=None),
    db: AsyncSession = Depends(get_db),
) -> dict:
    # Prefer Bearer token; fall back to httpOnly cookie
    token = credentials.credentials if credentials else aierp_token
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing token")
    payload = decode_access_token(token)
    if payload is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token")

    # Blacklist check — if token was revoked, treat as expired
    jti = payload.get("jti")
    if jti:
        from app.core.security import is_token_revoked
        if await is_token_revoked(jti):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token has been revoked",
            )

    user_id = int(payload["sub"])
    request.state.user_id = user_id
    request.state.token_jti = jti
    result = await db.execute(
        select(Role.name)
        .join(user_roles_table, user_roles_table.c.role_id == Role.id)
        .where(user_roles_table.c.user_id == user_id, Role.deleted_at.is_(None))
    )
    roles = [row[0] for row in result.fetchall()]
    return {"user_id": user_id, "username": payload["username"], "roles": roles}


async def get_uow() -> UnitOfWork:
    """FastAPI dependency that yields a UnitOfWork.

    The UoW wraps a session and auto-commits on success / auto-rolls back
    on exception. Domain events tracked via `uow.track_event()` are
    dispatched to the event bus after the DB transaction succeeds.
    """
    async with _get_uow_ctx() as uow:
        yield uow
