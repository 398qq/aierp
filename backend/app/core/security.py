from datetime import datetime, timedelta, timezone
import logging
import uuid

import bcrypt
import jwt
from jwt import InvalidTokenError as JWTError
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.user import User

logger = logging.getLogger(__name__)

# bcrypt 5 raises ValueError for passwords > 72 bytes; truncate to keep
# parity with bcrypt 4 behavior (silently truncated). UTF-8 boundary is
# best-effort: a half-character at the cut is dropped.
_BCRYPT_MAX_BYTES = 72


def _truncate_bcrypt_secret(password: str) -> bytes:
    if isinstance(password, str):
        raw = password.encode("utf-8")
    else:
        raw = password
    if len(raw) <= _BCRYPT_MAX_BYTES:
        return raw
    truncated = raw[:_BCRYPT_MAX_BYTES]
    # If we cut a multi-byte char mid-sequence, drop trailing partial bytes.
    while truncated and (truncated[-1] & 0xC0) == 0x80:
        truncated = truncated[:-1]
    return truncated


# ────────────────────────────────────────────────────────────────────────
# JWT blacklist — for session revocation
# ────────────────────────────────────────────────────────────────────────

BLACKLIST_KEY_PREFIX = "aierp:jwt_blacklist:"


async def _get_redis():
    try:
        from app.services.cache_service import get_redis

        return await get_redis()
    except Exception:
        return None


async def revoke_token(jti: str, ttl_seconds: int) -> bool:
    """Add a token's JTI to the blacklist with auto-expiry.

    The TTL should equal the token's remaining lifetime so the
    blacklist entry expires exactly when the token would have
    anyway — no memory leak.
    """
    r = await _get_redis()
    if r is None:
        # Fail closed: if Redis is down, treat as not revoked.
        # A stricter deployment could raise here.
        logger.warning("Cannot revoke token: Redis unavailable")
        return False
    try:
        await r.set(f"{BLACKLIST_KEY_PREFIX}{jti}", "1", ex=ttl_seconds)
        return True
    except Exception as exc:
        logger.warning("Revoke failed: %s", exc)
        return False


async def is_token_revoked(jti: str) -> bool:
    """Check whether a token's JTI is in the blacklist.

    Returns False on Redis failure (fail-open for availability).
    """
    if not jti:
        return False
    r = await _get_redis()
    if r is None:
        return False  # Fail open
    try:
        return bool(await r.exists(f"{BLACKLIST_KEY_PREFIX}{jti}"))
    except Exception:
        return False


async def revoke_all_user_tokens(user_id: int, db: AsyncSession | None = None) -> int:
    """Bump ``token_version`` for a user — invalidates all their JWTs.

    Requires a DB session.  Returns the new version number.
    If no session is provided, logs a warning and returns 0 (no-op).
    """
    if db is None:
        logger.warning(
            "revoke_all_user_tokens(user_id=%s) called without db session — no-op",
            user_id,
        )
        return 0

    result = await db.execute(
        update(User)
        .where(User.id == user_id, User.deleted_at.is_(None))
        .values(token_version=User.token_version + 1)
    )
    await db.commit()
    affected = result.rowcount or 0
    if affected:
        # Fetch the new version so the caller knows it
        row = await db.execute(select(User.token_version).where(User.id == user_id))
        new_version = row.scalar() or 0
        logger.info(
            "revoke_all_user_tokens user_id=%s → token_version=%s", user_id, new_version
        )
        return new_version
    return 0


# ────────────────────────────────────────────────────────────────────────
# Token creation & decoding
# ────────────────────────────────────────────────────────────────────────


def _truncate_bcrypt_secret(password: str) -> bytes:
    if isinstance(password, str):
        raw = password.encode("utf-8")
    else:
        raw = password
    if len(raw) <= _BCRYPT_MAX_BYTES:
        return raw
    truncated = raw[:_BCRYPT_MAX_BYTES]
    while truncated and (truncated[-1] & 0xC0) == 0x80:
        truncated = truncated[:-1]
    return truncated


def hash_password(password: str) -> str:
    # bcrypt direct (was: passlib CryptContext — passlib 1.7.4 is incompatible
    # with bcrypt 5 in its internal detect_wrap_bug path, raising ValueError).
    secret = _truncate_bcrypt_secret(password)
    salt = bcrypt.gensalt(rounds=12)
    return bcrypt.hashpw(secret, salt).decode("utf-8")


def _verify_password_sync(plain: str, hashed: str) -> bool:
    """Synchronous bcrypt check (CPU-bound ~200-400ms).

    This is wrapped in `run_in_executor` by `verify_password` so the
    FastAPI event loop is not blocked. Do not call this directly from
    async code paths — use `await verify_password(...)` instead.
    """
    try:
        plain_bytes = _truncate_bcrypt_secret(plain)
        hashed_bytes = hashed.encode("utf-8") if isinstance(hashed, str) else hashed
        return bcrypt.checkpw(plain_bytes, hashed_bytes)
    except Exception:
        return False


async def verify_password(plain: str, hashed: str) -> bool:
    """Async wrapper around bcrypt.checkpw to avoid blocking the event loop.

    Stage 14 load test: synchronous bcrypt was the #1 bottleneck — 20
    concurrent logins serialized at ~200ms each, blowing the 500ms P95
    budget. Running in the default executor (ThreadPoolExecutor) lets
    FastAPI serve other requests while bcrypt hashes.

    Trade-off: threads add slight memory overhead but unlock real
    concurrency. bcrypt is CPU-bound so a process pool would not help.
    """
    import asyncio

    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, _verify_password_sync, plain, hashed)


def create_access_token(user_id: int, username: str, token_version: int = 0) -> str:
    """Create a new JWT access token.

    The token includes a unique `jti` (JWT ID) for individual revocation
    and a `token_version` that can be bumped to revoke *all* tokens for
    a user (e.g. on password change).
    """
    now = datetime.now(timezone.utc)
    expire = now + timedelta(minutes=settings.JWT_EXPIRE_MINUTES)
    jti = uuid.uuid4().hex
    return jwt.encode(
        {
            "sub": str(user_id),
            "username": username,
            "token_version": token_version,
            "iat": now,
            "exp": expire,
            "jti": jti,
        },
        settings.JWT_SECRET,
        algorithm=settings.JWT_ALGORITHM,
    )


def decode_access_token(token: str) -> dict | None:
    """Decode and verify a JWT. Returns the payload or None.

    Note: blacklist check is NOT done here (would require async).
    Callers should use `get_current_user` which performs the full
    decode + revocation check.
    """
    try:
        return jwt.decode(
            token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM]
        )
    except JWTError:
        return None


def get_token_ttl_seconds(payload: dict) -> int:
    """Compute remaining TTL of a token in seconds (for blacklist expiry)."""
    exp = payload.get("exp")
    if not exp:
        return 0
    if isinstance(exp, (int, float)):
        return max(0, int(exp - datetime.now(timezone.utc).timestamp()))
    # Datetime form
    return max(0, int((exp - datetime.now(timezone.utc)).total_seconds()))
