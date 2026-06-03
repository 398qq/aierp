"""Finance API — payment bounded context.

Routes for the payment record lifecycle:
- list / stats / get / create / update / delete

Cache invalidation also covers ``reports:predefined:ar`` and
``dashboard:*`` since payment writes change AR aging and KPIs.
"""

import json
import logging

from fastapi import APIRouter, Depends, Query
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.api.v1.finance._shared import (
    PAYMENTS_LIST_CACHE_TTL,
    PAYMENTS_STATS_CACHE_TTL,
    _payments_cache_key,
)
from app.database import get_db
from app.schemas.common import fail, ok
from app.schemas.finance import PaymentRecordCreate, PaymentRecordUpdate
from app.services import finance_service as svc
from app.services.cache_service import (
    cache_bump_version,
    cache_get_versioned,
    cache_set_versioned,
)

logger = logging.getLogger(__name__)

router = APIRouter(tags=["finance:payment"])


async def _bump_payment_caches() -> None:
    """Bump all caches affected by payment writes."""
    await cache_bump_version("payments:list")
    await cache_bump_version("payments:stats")
    await cache_bump_version("reports:predefined:ar")
    await cache_bump_version("dashboard:overview")
    await cache_bump_version("dashboard:kpi")


@router.get("/payments")
async def list_payments(
    response: JSONResponse,
    page: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=100),
    customer_id: int | None = None, status: str | None = None,
    sales_order_id: int | None = None, delivery_note_id: int | None = None,
    sort_by: str = "id", sort_order: str = "desc",
    db: AsyncSession = Depends(get_db), _user: dict = Depends(get_current_user),
):
    cache_key = _payments_cache_key(
        page=page, page_size=page_size, customer_id=customer_id,
        status=status, sales_order_id=sales_order_id,
        delivery_note_id=delivery_note_id, sort_by=sort_by, sort_order=sort_order,
    )
    cached_payload = await cache_get_versioned("payments:list", cache_key)
    if cached_payload is not None:
        response.headers["X-Cache"] = "HIT"
        response.headers["X-Cache-Key"] = cache_key
        return ok(json.loads(cached_payload))
    response.headers["X-Cache"] = "MISS"
    result = await svc.list_payments(
        db, page=page, page_size=page_size, customer_id=customer_id,
        status=status, sales_order_id=sales_order_id,
        delivery_note_id=delivery_note_id,
        sort_by=sort_by, sort_order=sort_order,
    )
    await cache_set_versioned("payments:list", cache_key, json.dumps(result, default=str),
                                PAYMENTS_LIST_CACHE_TTL)
    return ok(result)


@router.get("/payments/stats")
async def get_payment_stats(
    response: JSONResponse,
    db: AsyncSession = Depends(get_db), _user: dict = Depends(get_current_user),
):
    cache_key = "payments:stats:global"
    cached_payload = await cache_get_versioned("payments:stats", cache_key)
    if cached_payload is not None:
        response.headers["X-Cache"] = "HIT"
        response.headers["X-Cache-Key"] = cache_key
        return ok(json.loads(cached_payload))
    response.headers["X-Cache"] = "MISS"
    result = await svc.payment_stats(db)
    await cache_set_versioned("payments:stats", cache_key, json.dumps(result, default=str),
                                PAYMENTS_STATS_CACHE_TTL)
    return ok(result)


@router.get("/payments/{pay_id}")
async def get_payment(pay_id: int, db: AsyncSession = Depends(get_db), _user: dict = Depends(get_current_user)):
    pay = await svc.get_payment(db, pay_id)
    if not pay:
        return fail("回款记录不存在", 404)
    return ok(pay)


@router.post("/payments")
async def create_payment(body: PaymentRecordCreate, db: AsyncSession = Depends(get_db), _user: dict = Depends(get_current_user)):
    pay = await svc.create_payment(db, body.model_dump())
    await _bump_payment_caches()
    return ok(pay)


@router.put("/payments/{pay_id}")
async def update_payment(pay_id: int, body: PaymentRecordUpdate, db: AsyncSession = Depends(get_db), _user: dict = Depends(get_current_user)):
    pay = await svc.get_payment(db, pay_id)
    if not pay:
        return fail("回款记录不存在", 404)
    pay = await svc.update_payment(db, pay, body.model_dump(exclude_none=True))
    await _bump_payment_caches()
    return ok(pay)


@router.delete("/payments/{pay_id}")
async def delete_payment(pay_id: int, db: AsyncSession = Depends(get_db), _user: dict = Depends(get_current_user)):
    pay = await svc.get_payment(db, pay_id)
    if not pay:
        return fail("回款记录不存在", 404)
    await svc.delete_payment(db, pay)
    await _bump_payment_caches()
    return ok({"deleted": pay_id})
