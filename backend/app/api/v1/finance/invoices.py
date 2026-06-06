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
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.api.v1.finance._shared import (
    INVOICES_LIST_CACHE_TTL,
    _invoices_cache_key,
)
from app.api.v1.sales._serialize import (
    attach_customer_and_quotation,
    attach_sales_order,
    serialize_invoice,
)
from app.database import get_db
from app.models.customer import Customer
from app.models.sales import SalesOrder
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
    raw = await svc.list_invoices(
        db, page=page, page_size=page_size, customer_id=customer_id,
        status=status, sales_order_id=sales_order_id,
        sort_by=sort_by, sort_order=sort_order,
    )
    invoices = list(raw["list"])
    # Eager-load customer + sales_order to avoid N+1 + async lazy loads
    if invoices:
        cust_ids = list({i.customer_id for i in invoices if i.customer_id})
        so_ids = list({i.sales_order_id for i in invoices if i.sales_order_id})
        custs = {c.id: c for c in (await db.execute(select(Customer).where(Customer.id.in_(cust_ids)))).scalars().all()} if cust_ids else {}
        sos = {s.id: s for s in (await db.execute(select(SalesOrder).where(SalesOrder.id.in_(so_ids)))).scalars().all()} if so_ids else {}
        for inv in invoices:
            if (c := custs.get(inv.customer_id)) is not None:
                inv.customer = c
            if (s := sos.get(inv.sales_order_id)) is not None:
                inv.sales_order = s
    serialized_list = [serialize_invoice(i) for i in invoices]
    result = {**raw, "list": serialized_list}
    await cache_set_versioned("invoices:list", cache_key, json.dumps(result),
                                INVOICES_LIST_CACHE_TTL)
    return ok(result)


@router.get("/invoices/{inv_id}")
async def get_invoice(inv_id: int, db: AsyncSession = Depends(get_db), _user: dict = Depends(get_current_user)):
    inv = await svc.get_invoice(db, inv_id)
    if not inv:
        return fail("发票不存在", 404)
    await attach_customer_and_quotation(db, inv, type(inv))
    await attach_sales_order(db, inv, "sales_order_id")
    return ok(serialize_invoice(inv))


@router.post("/invoices")
async def create_invoice(body: InvoiceCreate, db: AsyncSession = Depends(get_db), _user: dict = Depends(get_current_user)):
    inv = await svc.create_invoice(db, body.model_dump())
    await _bump_invoice_caches()
    await attach_customer_and_quotation(db, inv, type(inv))
    await attach_sales_order(db, inv, "sales_order_id")
    return ok(serialize_invoice(inv))


@router.put("/invoices/{inv_id}")
async def update_invoice(inv_id: int, body: InvoiceUpdate, db: AsyncSession = Depends(get_db), _user: dict = Depends(get_current_user)):
    inv = await svc.get_invoice(db, inv_id)
    if not inv:
        return fail("发票不存在", 404)
    inv = await svc.update_invoice(db, inv, body.model_dump(exclude_none=True))
    await _bump_invoice_caches()
    await attach_customer_and_quotation(db, inv, type(inv))
    await attach_sales_order(db, inv, "sales_order_id")
    return ok(serialize_invoice(inv))


@router.delete("/invoices/{inv_id}")
async def delete_invoice(inv_id: int, db: AsyncSession = Depends(get_db), _user: dict = Depends(get_current_user)):
    inv = await svc.get_invoice(db, inv_id)
    if not inv:
        return fail("发票不存在", 404)
    await svc.delete_invoice(db, inv)
    await _bump_invoice_caches()
    return ok({"deleted": inv_id})
