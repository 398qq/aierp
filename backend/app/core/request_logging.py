"""Structured request logging middleware."""

import json
import logging
import time
from datetime import datetime, timezone

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app.core.security import decode_access_token

logger = logging.getLogger("app.request")
TOKEN_COOKIE_NAME = "aierp_token"


def _client_ip(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def _extract_user_id(request: Request) -> int | None:
    state_user_id = getattr(getattr(request, "state", None), "user_id", None)
    if state_user_id is not None:
        return state_user_id

    token = None
    auth = request.headers.get("authorization", "")
    if auth.lower().startswith("bearer "):
        token = auth[7:].strip()
    if not token:
        token = request.cookies.get(TOKEN_COOKIE_NAME)
    if not token:
        return None

    payload = decode_access_token(token)
    if payload is None:
        return None
    try:
        return int(payload["sub"])
    except Exception:
        return None


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        started = time.perf_counter()
        status_code = 500

        try:
            response = await call_next(request)
            status_code = response.status_code
            return response
        finally:
            duration_ms = round((time.perf_counter() - started) * 1000, 2)
            request_id = getattr(getattr(request, "state", None), "request_id", "")
            log_data = {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "level": "INFO",
                "request_id": request_id,
                "user_id": _extract_user_id(request),
                "message": "request completed",
                "method": request.method,
                "path": request.url.path,
                "status_code": status_code,
                "duration_ms": duration_ms,
                "client_ip": _client_ip(request),
            }
            logger.info(json.dumps(log_data, ensure_ascii=False))
