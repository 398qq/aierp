"""Request context middleware and helpers."""

from contextvars import ContextVar
from uuid import uuid4

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

_request_id_ctx: ContextVar[str] = ContextVar("request_id", default="")


def get_request_id() -> str:
    return _request_id_ctx.get() or ""


class RequestContextMiddleware(BaseHTTPMiddleware):
    """Attach request_id to context + request.state and echo in response header."""

    async def dispatch(self, request: Request, call_next) -> Response:
        incoming = request.headers.get("X-Request-ID")
        request_id = incoming.strip() if incoming else f"req_{uuid4().hex[:16]}"
        token = _request_id_ctx.set(request_id)
        request.state.request_id = request_id

        try:
            response = await call_next(request)
        finally:
            _request_id_ctx.reset(token)

        response.headers["X-Request-ID"] = request_id
        return response
