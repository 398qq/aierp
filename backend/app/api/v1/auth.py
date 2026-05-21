from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.security import create_access_token, hash_password, verify_password
from app.database import get_db
from app.schemas.common import ok

router = APIRouter(prefix="/auth", tags=["auth"])

# Login brute-force protection: track failed attempts per username in Redis
LOGIN_FAILED_PREFIX = "aierp:login_failed:"
MAX_FAILED_ATTEMPTS = 5          # lock after 5 failures
BLOCK_DURATION_MINUTES = 15      # block for 15 minutes

# --- httpOnly cookie config ---
TOKEN_COOKIE_NAME = "aierp_token"
TOKEN_COOKIE_MAX_AGE = 60 * 60 * 24 * 7  # 7 days in seconds


class LoginRequest(BaseModel):
    username: str
    password: str


class ChangePasswordRequest(BaseModel):
    current_password: str = Field(min_length=1, max_length=128)
    new_password: str = Field(min_length=8, max_length=128)


def _blocked_key(username: str) -> str:
    return f"{LOGIN_FAILED_PREFIX}{username}"


async def _get_r():
    try:
        from app.services.cache_service import get_redis
        return await get_redis()
    except Exception:
        return None


def _client_host(request) -> str:
    """Extract client IP, accounting for X-Forwarded-For when behind a proxy."""
    if request is None:
        return ""
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else ""


@router.post("/login")
async def login(req: LoginRequest, db: AsyncSession = Depends(get_db)):
    from app.models.user import User

    username = req.username.strip().lower()
    r = await _get_r()

    # Check if this username is currently blocked
    if r is not None:
        block_key = _blocked_key(username)
        blocked_count = await r.get(block_key)
        if blocked_count is not None and int(blocked_count) >= MAX_FAILED_ATTEMPTS:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"登录失败次数过多，请在{BLOCK_DURATION_MINUTES}分钟后重试",
            )

    # Authenticate
    result = await db.execute(
        select(User).where(User.username == username, User.deleted_at.is_(None))
    )
    user = result.scalar_one_or_none()

    auth_ok = user is not None and verify_password(req.password, user.password)

    if not auth_ok:
        # Record failed attempt
        if r is not None:
            block_key = _blocked_key(username)
            try:
                pipe = r.pipeline()
                pipe.incr(block_key)
                pipe.expire(block_key, BLOCK_DURATION_MINUTES * 60)
                await pipe.execute()
            except Exception:
                pass  # Redis write failure should not block login
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户名或密码错误",
        )

    # Success — clear failure counter
    if r is not None:
        try:
            await r.delete(_blocked_key(username))
        except Exception:
            pass

    token = create_access_token(user.id, user.username)
    # Set httpOnly cookie — XSS cannot read the token
    response = JSONResponse(content=ok({"token": token, "username": user.username, "role": user.role}))
    response.set_cookie(
        key=TOKEN_COOKIE_NAME,
        value=token,
        max_age=TOKEN_COOKIE_MAX_AGE,
        httponly=True,
        samesite="lax",
        secure=False,  # set True in production behind HTTPS
    )
    return response


@router.get("/me")
async def me(current_user: dict = Depends(get_current_user)):
    return ok(current_user)


@router.post("/change-password")
async def change_password(
    req: ChangePasswordRequest,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    from app.models.user import User

    result = await db.execute(
        select(User).where(User.id == current_user["user_id"], User.deleted_at.is_(None))
    )
    user = result.scalar_one_or_none()
    if user is None or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="用户不可用")

    if not verify_password(req.current_password, user.password):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="当前密码错误")

    if verify_password(req.new_password, user.password):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="新密码不能与当前密码相同")

    user.password = hash_password(req.new_password)
    await db.commit()
    return ok({"changed": True})
