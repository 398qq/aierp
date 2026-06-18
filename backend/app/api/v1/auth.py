from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import JSONResponse
import logging
from pydantic import BaseModel, Field, field_validator
import re
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.security import create_access_token, hash_password, verify_password
from app.database import get_db
from app.schemas.common import ok

router = APIRouter(prefix="/auth", tags=["auth"])
logger = logging.getLogger(__name__)

# Login brute-force protection: dual-key (username + IP) backoff
LOGIN_FAILED_USERNAME_PREFIX = "aierp:login_failed:user:"
LOGIN_FAILED_IP_PREFIX = "aierp:login_failed:ip:"
MAX_FAILED_ATTEMPTS = 5  # lock after 5 failures
BLOCK_DURATION_MINUTES = 15  # block for 15 minutes
IP_BLOCK_THRESHOLD = 20  # Different threshold for IP-based attack
IP_BLOCK_DURATION_MINUTES = 30  # IP blocks last longer (catches botnets)

# --- httpOnly cookie config ---
TOKEN_COOKIE_NAME = "aierp_token"
TOKEN_COOKIE_MAX_AGE = 60 * 60 * 24 * 7  # 7 days in seconds


def _validate_password_complexity(password: str) -> str | None:
    """Enforce password policy: 8+ chars, 3 of {lower, upper, digit, special}.

    Returns None on success, or a human-readable error message.
    """
    if len(password) < 8:
        return "密码至少需要 8 个字符"
    if len(password) > 128:
        return "密码不能超过 128 个字符"
    classes = sum(
        [
            bool(re.search(r"[a-z]", password)),  # lowercase
            bool(re.search(r"[A-Z]", password)),  # uppercase
            bool(re.search(r"\d", password)),  # digit
            bool(
                re.search(r"[!@#$%^&*(),.?\":{}|<>_\-+=\[\]/~`';\\\\]", password)
            ),  # special
        ]
    )
    if classes < 3:
        return "密码必须包含以下 3 类字符：小写字母、大写字母、数字、特殊符号"
    return None


class LoginRequest(BaseModel):
    username: str = Field(min_length=1, max_length=64)
    password: str = Field(min_length=1, max_length=128)


class ChangePasswordRequest(BaseModel):
    current_password: str = Field(min_length=1, max_length=128)
    new_password: str = Field(min_length=8, max_length=128)

    @field_validator("new_password")
    @classmethod
    def _password_complexity(cls, v: str) -> str:
        err = _validate_password_complexity(v)
        if err:
            raise ValueError(err)
        return v


class RegisterRequest(BaseModel):
    """Self-service registration disabled by default; admin creates users via /users."""

    username: str = Field(min_length=3, max_length=64, pattern=r"^[a-zA-Z0-9_.\-]+$")
    password: str = Field(min_length=8, max_length=128)

    @field_validator("password")
    @classmethod
    def _password_complexity(cls, v: str) -> str:
        err = _validate_password_complexity(v)
        if err:
            raise ValueError(err)
        return v


def _username_blocked_key(username: str) -> str:
    return f"{LOGIN_FAILED_USERNAME_PREFIX}{username}"


def _ip_blocked_key(ip: str) -> str:
    return f"{LOGIN_FAILED_IP_PREFIX}{ip}"


async def _get_r():
    try:
        from app.services.cache_service import get_redis

        return await get_redis()
    except Exception:
        return None


def _client_ip(request: Request) -> str:
    """Extract client IP, accounting for X-Forwarded-For when behind a proxy."""
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


@router.post("/login")
async def login(
    req: LoginRequest, request: Request, db: AsyncSession = Depends(get_db)
):
    from app.models.user import User

    username = req.username.strip().lower()
    client_ip = _client_ip(request)
    r = await _get_r()

    # Block 1: per-username lockout (5 failures / 15min)
    # Block 2: per-IP lockout (20 failures / 30min) — catches credential-stuffing
    if r is not None:
        try:
            for key, threshold, block_min, label in [
                (
                    _username_blocked_key(username),
                    MAX_FAILED_ATTEMPTS,
                    BLOCK_DURATION_MINUTES,
                    "用户名",
                ),
                (
                    _ip_blocked_key(client_ip),
                    IP_BLOCK_THRESHOLD,
                    IP_BLOCK_DURATION_MINUTES,
                    "IP",
                ),
            ]:
                count = await r.get(key)
                if count is not None and int(count) >= threshold:
                    raise HTTPException(
                        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                        detail=f"该{label}登录失败次数过多，请在 {block_min} 分钟后重试",
                        headers={"Retry-After": str(block_min * 60)},
                    )
        except HTTPException:
            raise
        except Exception as exc:
            logger.warning("Login rate-limit check unavailable: %s", exc)
            r = None

    # Authenticate
    result = await db.execute(
        select(User).where(User.username == username, User.deleted_at.is_(None))
    )
    user = result.scalar_one_or_none()

    auth_ok = user is not None and await verify_password(req.password, user.password)

    if not auth_ok:
        # Record failed attempt under BOTH username and IP keys
        if r is not None:
            try:
                pipe = r.pipeline()
                pipe.incr(_username_blocked_key(username))
                pipe.expire(
                    _username_blocked_key(username), BLOCK_DURATION_MINUTES * 60
                )
                pipe.incr(_ip_blocked_key(client_ip))
                pipe.expire(_ip_blocked_key(client_ip), IP_BLOCK_DURATION_MINUTES * 60)
                await pipe.execute()
            except Exception:
                pass
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户名或密码错误",
        )

    # Success — clear both failure counters
    if r is not None:
        try:
            await r.delete(_username_blocked_key(username))
            await r.delete(_ip_blocked_key(client_ip))
        except Exception:
            pass

    # Active-user check
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="账户已停用")

    token = create_access_token(
        user.id, user.username, token_version=user.token_version or 0
    )
    response = JSONResponse(
        content=ok({"token": token, "username": user.username, "role": user.role})
    )
    response.set_cookie(
        key=TOKEN_COOKIE_NAME,
        value=token,
        max_age=TOKEN_COOKIE_MAX_AGE,
        httponly=True,
        samesite="lax",
        secure=False,
    )
    return response


@router.get("/me")
async def me(current_user: dict = Depends(get_current_user)):
    return ok(current_user)


@router.post("/logout")
async def logout(
    request: Request,
    current_user: dict = Depends(get_current_user),
):
    """Revoke the current JWT by adding its JTI to the blacklist.

    The blacklist entry expires automatically when the token would
    have expired, so the blacklist stays small.
    """
    from app.core.security import get_token_ttl_seconds, revoke_token

    jti = getattr(request.state, "token_jti", None)
    if not jti:
        return ok({"revoked": False, "reason": "no_jti_in_token"})

    # Find the token from Authorization header to read its payload
    token = request.headers.get("authorization", "")
    if token.lower().startswith("bearer "):
        token = token[7:].strip()
    if not token:
        # Try cookie
        token = request.cookies.get(TOKEN_COOKIE_NAME) or ""

    from app.core.security import decode_access_token

    payload = decode_access_token(token) if token else None
    ttl = get_token_ttl_seconds(payload) if payload else 60

    revoked = await revoke_token(jti, ttl_seconds=ttl)

    response = JSONResponse(content=ok({"revoked": revoked}))
    # Clear the cookie too
    response.delete_cookie(TOKEN_COOKIE_NAME)
    return response


@router.post("/change-password")
async def change_password(
    req: ChangePasswordRequest,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    from app.models.user import User

    result = await db.execute(
        select(User).where(
            User.id == current_user["user_id"], User.deleted_at.is_(None)
        )
    )
    user = result.scalar_one_or_none()
    if user is None or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="用户不可用"
        )

    if not await verify_password(req.current_password, user.password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="当前密码错误"
        )

    if await verify_password(req.new_password, user.password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="新密码不能与当前密码相同"
        )

    user.password = hash_password(req.new_password)
    await db.commit()
    return ok({"changed": True})
