"""Redis-backed rate limiting middleware using sliding window.

Add to main.py:
    from app.core.rate_limit import RateLimitMiddleware
    app.add_middleware(RateLimitMiddleware)

Override the default 100 req/min per-IP limit via env vars
(e.g. for performance testing or staging):
    AIERP_RATE_LIMIT_CALLS=10000   AIERP_RATE_LIMIT_WINDOW=60
"""

import logging
import os
import time

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response, JSONResponse

logger = logging.getLogger(__name__)


def _env_int(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None or not raw.strip():
        return default
    try:
        value = int(raw)
    except ValueError:
        logger.warning(
            "rate_limit: non-integer %s=%r, using default %s", name, raw, default
        )
        return default
    if value <= 0:
        logger.warning(
            "rate_limit: %s=%r must be positive, using default %s", name, raw, default
        )
        return default
    return value


# Global config — overridable via env vars
# Stage 15 Day 0: default raised 100 → 300 to fit 10-15 concurrent sales reps
# (each rep issues 20-30 req/min naturally). Override per-env for load tests
# via AIERP_RATE_LIMIT_CALLS=10000.
RATE_LIMIT_CALLS = _env_int("AIERP_RATE_LIMIT_CALLS", 300)
RATE_LIMIT_WINDOW = _env_int("AIERP_RATE_LIMIT_WINDOW", 60)
RATE_LIMIT_KEY_PREFIX = "aierp:rl:"


async def _get_redis():
    try:
        from app.services.cache_service import get_redis

        return await get_redis()
    except Exception:
        return None


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Per-IP sliding-window rate limiter backed by Redis.

    Ignores the health endpoint and returns 429 with Retry-After when
    the limit is exceeded. Degrades gracefully if Redis is unavailable.
    """

    async def dispatch(self, request: Request, call_next) -> Response:
        # Skip health checks, metrics, and non-API paths
        path = request.url.path
        if (
            path == "/health"
            or path.startswith("/health/")
            or path == "/metrics"
            or path.startswith("/metrics/")
            or path in ("/docs", "/openapi.json", "/redoc")
            or path.startswith("/api/v1/auth")
        ):
            return await call_next(request)

        client_ip = self._client_ip(request)
        # Stage 19 P2 #1: prefer per-user key when authenticated; fall back to
        # per-IP. Authenticated abusers behind a shared NAT no longer bypass.
        user_key = self._user_id(request)
        if user_key is not None:
            key = f"{RATE_LIMIT_KEY_PREFIX}u:{user_key}"
        else:
            key = f"{RATE_LIMIT_KEY_PREFIX}ip:{client_ip}"

        r = await _get_redis()
        if r is None:
            # Redis unavailable — allow requests (fail-open for availability)
            return await call_next(request)

        try:
            now = time.time()
            window_start = now - RATE_LIMIT_WINDOW

            pipe = r.pipeline()
            # Remove old entries outside the window
            pipe.zremrangebyscore(key, 0, window_start)
            # Count requests in current window
            pipe.zcard(key)
            # Add this request with current timestamp as score
            pipe.zadd(key, {str(now): now})
            # Set TTL on the key
            pipe.expire(key, RATE_LIMIT_WINDOW + 1)
            results = await pipe.execute()
            current_count = results[1]

            if current_count >= RATE_LIMIT_CALLS:
                retry_after = int(RATE_LIMIT_WINDOW - (now - window_start))
                request_id = getattr(
                    getattr(request, "state", None), "request_id", None
                )
                return JSONResponse(
                    status_code=429,
                    content={
                        "code": 429,
                        "msg": f"请求过于频繁，请 {retry_after} 秒后重试",
                        "data": None,
                        "request_id": request_id,
                    },
                    headers={"Retry-After": str(max(retry_after, 1))},
                )

            return await call_next(request)
        except Exception:
            # Redis error — fail open
            logger.warning("Rate limiter Redis error, allowing request")
            return await call_next(request)

    @staticmethod
    def _client_ip(request: Request) -> str:
        forwarded = request.headers.get("x-forwarded-for")
        if forwarded:
            return forwarded.split(",")[0].strip()
        return request.client.host if request.client else "unknown"

    @staticmethod
    def _user_id(request: Request) -> int | None:
        """Return authenticated user id from request.state (set by get_current_user).

        Cheap path: look at ``request.state.user_id``. Returns None for
        unauthenticated requests, so the middleware falls back to per-IP.
        """
        state = getattr(request, "state", None)
        if state is None:
            return None
        uid = getattr(state, "user_id", None)
        if isinstance(uid, int):
            return uid
        return None
