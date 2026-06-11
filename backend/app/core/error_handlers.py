"""Global exception handlers with unified error response shape."""

import logging

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from starlette.responses import JSONResponse

from app.config import settings
from app.domain.shared.errors import DomainError

logger = logging.getLogger(__name__)


def _request_id(request: Request) -> str | None:
    return getattr(getattr(request, "state", None), "request_id", None)


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(DomainError)
    async def _domain_exception_handler(request: Request, exc: DomainError):
        rid = _request_id(request)
        payload = {
            "code": exc.code,
            "msg": exc.message,
            "data": exc.context or None,
            "request_id": rid,
        }
        return JSONResponse(status_code=exc.http_status, content=payload)

    @app.exception_handler(HTTPException)
    async def _http_exception_handler(request: Request, exc: HTTPException):
        rid = _request_id(request)
        message = exc.detail if isinstance(exc.detail, str) else "Request failed"
        payload = {
            "code": exc.status_code,
            "msg": message,
            "data": None,
            "request_id": rid,
        }
        return JSONResponse(status_code=exc.status_code, content=payload)

    @app.exception_handler(RequestValidationError)
    async def _validation_exception_handler(
        request: Request, exc: RequestValidationError
    ):
        rid = _request_id(request)
        first = exc.errors()[0] if exc.errors() else {}
        location = ".".join(str(x) for x in first.get("loc", []))
        message = first.get("msg", "Request validation failed")
        if location:
            message = f"{location}: {message}"
        payload = {"code": 422, "msg": message, "data": None, "request_id": rid}
        return JSONResponse(status_code=422, content=payload)

    @app.exception_handler(Exception)
    async def _unhandled_exception_handler(request: Request, exc: Exception):
        rid = _request_id(request)
        logger.exception("Unhandled exception rid=%s path=%s", rid, request.url.path)
        message = str(exc) if settings.DEBUG else "Internal server error"
        payload = {"code": -1, "msg": message, "data": None, "request_id": rid}
        return JSONResponse(status_code=500, content=payload)
