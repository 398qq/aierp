from fastapi import Cookie, Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import decode_access_token
from app.database import get_db

security_scheme = HTTPBearer(auto_error=False)
TOKEN_COOKIE_NAME = "aierp_token"


async def get_current_user(
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
    return {"user_id": int(payload["sub"]), "username": payload["username"]}
