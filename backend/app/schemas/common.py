"""Unified API response helpers.

All route handlers MUST use these helpers to produce consistent response
envelopes.  ``ok()`` returns a dict (let FastAPI handle serialisation), and
``fail()`` returns a ``JSONResponse`` so the HTTP status code matches the
error — the frontend axios interceptor can then distinguish success vs error
by status code alone.

Use the ``APIResponse`` and ``ErrorResponse`` models as FastAPI
``response_model`` in route decorators to generate accurate OpenAPI docs::

    from app.schemas.common import APIResponse
    from app.schemas.customer import CustomerResponse

    @router.get("/customers/{id}", response_model=APIResponse[CustomerResponse])
    async def get_customer(...):
        ...
        return ok(customer_data)
"""

from typing import Any, Generic, TypeVar

from pydantic import BaseModel
from starlette.responses import JSONResponse

from app.core.request_context import get_request_id

T = TypeVar("T")


def ok(data: Any = None, msg: str = "success") -> dict:
    """Successful response envelope.

    Returns a plain dict so FastAPI's built-in JSON serialisation (including
    ``jsonable_encoder``) processes complex types.  Status code is determined
    by the route decorator (default 200, or ``status_code=201`` for POST etc).
    """
    return {"code": 0, "msg": msg, "data": data}


def fail(msg: str = "error", code: int = 400) -> JSONResponse:
    """Error response envelope with correct HTTP status code.

    Returns a ``JSONResponse`` instead of a plain dict so that the HTTP
    status code matches ``code`` — the frontend axios interceptor catches
    HTTP 4xx/5xx and routes the response into the error-handling path.
    Every error payload includes ``request_id`` for log correlation.
    """
    return JSONResponse(
        status_code=code,
        content={
            "code": code,
            "msg": msg,
            "data": None,
            "request_id": get_request_id(),
        },
    )


def paginated_ok(items: list[Any], total: int, page: int, page_size: int) -> dict:
    """Paginated success response — wraps ``ok({{list, total, page, page_size}})``."""
    return ok({"list": items, "total": total, "page": page, "page_size": page_size})


class APIResponse(BaseModel, Generic[T]):
    """Success response envelope — mirrors ``ok()``.

    Usage in route decorators::

        @router.get("/products/{id}", response_model=APIResponse[ProductOut])
    """

    code: int = 0
    msg: str = "success"
    data: T | None = None


class ErrorResponse(BaseModel):
    """Error response envelope — mirrors ``fail()``."""

    code: int
    msg: str
    data: None = None
    request_id: str = ""


class PageData(BaseModel, Generic[T]):
    """Schema for paginated ``data`` payloads."""

    list: list[T]
    total: int
    page: int
    page_size: int
    ai: dict[int, dict[str, Any]] | None = None
