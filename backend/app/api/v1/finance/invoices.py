"""Finance API — invoice bounded context.

Routes for the invoice lifecycle:
- list / get / create / update / delete

Cache invalidation also covers ``finance:reports:pnl`` and
``reports:predefined:ar`` since invoice writes change those aggregates.
"""

import json
import logging

from fastapi import APIRouter, Depends, Query
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.api.v1.finance._shared import (
    INVOICES_LIST_CACHE_TTL,
    _invoices_cache_key,
)
from app.database import get_db
from app.schemas.common import fail, ok
from app.schemas.finance import InvoiceCreate, InvoiceUpdate
from app.services import finance_service as svc
from app.services.cache_service import (
    cache_bump_version,
    cache_get_versioned,
    cache_set_versioned,
)

logger = logging.getLogger(__name__)

router = APIRouter(tags=["finance:invoice"])


async def _bump_invoice_caches() -> None:
    """Bump all caches affected by invoice writes."""
    await cache_bump_version("invoices:list")
    await cache_bump_version("finance:reports:pnl")
    await cache_bump_version("reports:predefined:ar")
    await cache_bump_version("dashboard:overview")
    await cache_bump_version("dashboard:kpi")


@router.get("/invoices")
async def list_invoices(
    response: JSONResponse,
    page: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=100),
    customer_id: int | None = None, status: str | None = None,
    sales_order_id: int | None = None,
    sort_by: str = "id", sort_order: str = "desc",
    db: AsyncSession = Depends(get_db), _user: dict = Depends(get_current_user),
):
    cache_key = _invoices_cache_key(
        page=page, page_size=page_size, customer_id=customer_id,
        status=status, sales_order_id=sales_order_id,
        sort_by=sort_by, sort_order=sort_order,
    )
    cached_payload = await cache_get_versioned("invoices:list", cache_key)
    if cached_payload is not None:
        response.headers["X-Cache"] = "HIT"
        response.headers["X-Cache-Key"] = cache_key
        return ok(json.loads(cached_payload))
    response.headers["X-Cache"] = "MISS"
    result = await svc.list_invoices(
        db, page=page, page_size=page_size, customer_id=customer_id,
        status=status, sales_order_id=sales_order_id,
        sort_by=sort_by, sort_order=sort_order,
    )
    await cache_set_versioned("invoices:list", cache_key, json.dumps(result, default=str),
                                INVOICES_LIST_CACHE_TTL)
    return ok(result)


@router.get("/invoices/{inv_id}")
async def get_invoice(inv_id: int, db: AsyncSession = Depends(get_db), _user: dict = Depends(get_current_user)):
    inv = await svc.get_invoice(db, inv_id)
    if not inv:
        return fail("发票不存在", 404)
    return ok(inv)


@router.post("/invoices")
async def create_invoice(body: InvoiceCreate, db: AsyncSession = Depends(get_db), _user: dict = Depends(get_current_user)):
    inv = await svc.create_invoice(db, body.model_dump())
    await _bump_invoice_caches()
    return ok(inv)


@router.put("/invoices/{inv_id}")
async def update_invoice(inv_id: int, body: InvoiceUpdate, db: AsyncSession = Depends(get_db), _user: dict = Depends(get_current_user)):
    inv = await svc.get_invoice(db, inv_id)
    if not inv:
        return fail("发票不存在", 404)
    inv = await svc.update_invoice(db, inv, body.model_dump(exclude_none=True))
    await _bump_invoice_caches()
    return ok(inv)


@router.delete("/invoices/{inv_id}")
async def delete_invoice(inv_id: int, db: AsyncSession = Depends(get_db), _user: dict = Depends(get_current_user)):
    inv = await svc.get_invoice(db, inv_id)
    if not inv:
        return fail("发票不存在", 404)
    await svc.delete_invoice(db, inv)
    await _bump_invoice_caches()
    return ok({"deleted": inv_id})
