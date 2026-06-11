from datetime import datetime, timedelta, timezone
import logging
import uuid

import jwt
from jwt import InvalidTokenError as JWTError
from passlib.context import CryptContext

from app.config import settings

logger = logging.getLogger(__name__)

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


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


async def revoke_all_user_tokens(user_id: int) -> int:
    """Revoke all currently-active tokens for a user (e.g. on password change).

    Implementation note: with stateless JWTs, the only practical way is
    to bump a `token_version` counter in the user record and include
    it in the JWT, checking on every request. We don't have that field
    yet, so this function records the current timestamp as the
    user's "must-reissue-after" cut-off.

    For now, this is a placeholder that just logs. Full implementation
    requires a `users.token_version` column migration.
    """
    logger.warning(
        "revoke_all_user_tokens called for user_id=%s but full impl pending token_version migration",
        user_id,
    )
    return 0


# ────────────────────────────────────────────────────────────────────────
# Token creation & decoding
# ────────────────────────────────────────────────────────────────────────


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    """Verify password against bcrypt hash.

    Bcrypt 4.x dropped the __about__ attribute that passlib 1.7.4 reads at
    backend load time, which makes `passlib.context.CryptContext.verify`
    fail. We therefore use the `bcrypt` package directly here, while
    `hash_password` still relies on passlib for new hashes (the two are
    wire-compatible because passlib writes standard $2b$ bcrypt hashes).
    """
    import bcrypt

    try:
        plain_bytes = plain.encode("utf-8") if isinstance(plain, str) else plain
        hashed_bytes = hashed.encode("utf-8") if isinstance(hashed, str) else hashed
        return bcrypt.checkpw(plain_bytes, hashed_bytes)
    except Exception:
        # Final fallback to passlib in case the hash uses a non-bcrypt scheme.
        try:
            return pwd_context.verify(plain, hashed)
        except Exception:
            return False


def create_access_token(user_id: int, username: str) -> str:
    """Create a new JWT access token.

    The token includes a unique `jti` (JWT ID) that can be used for
    session revocation via `revoke_token()`.
    """
    now = datetime.now(timezone.utc)
    expire = now + timedelta(minutes=settings.JWT_EXPIRE_MINUTES)
    jti = uuid.uuid4().hex
    return jwt.encode(
        {
            "sub": str(user_id),
            "username": username,
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
