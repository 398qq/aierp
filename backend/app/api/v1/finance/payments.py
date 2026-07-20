"""Finance API — payment bounded context.

Routes for the payment record lifecycle:
- list / stats / get / create / update / delete

Cache invalidation also covers ``reports:predefined:ar`` and
``dashboard:*`` since payment writes change AR aging and KPIs.
"""

import json
import logging
from collections.abc import Mapping

from fastapi import APIRouter, Depends, Query
from fastapi.responses import JSONResponse
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.models.finance import Invoice, PaymentAllocation
from app.models.sales import DeliveryNote, SalesOrder
from app.api.v1.finance._shared import (
    PAYMENTS_LIST_CACHE_TTL,
    PAYMENTS_STATS_CACHE_TTL,
    _payments_cache_key,
)
from app.database import get_db
from app.schemas.common import fail, ok, APIResponse, PageData
from app.schemas.finance import (
    PaymentAllocationRequest,
    PaymentRecordCreate,
    PaymentRecordResponse,
    PaymentRecordUpdate,
    PaymentStats,
)
from app.services import finance_service as svc
from app.domain.states import assert_can_transition_invoice, assert_can_transition_payment
from app.services.state_transition_service import transition_status
from app.services.cache_service import (
    cache_bump_version,
    cache_get_versioned,
    cache_set_versioned,
)

logger = logging.getLogger(__name__)

router = APIRouter(tags=["finance:payment"])


def _serialize_payment(
    pay,
    invoice_map: Mapping[int, str | None],
    order_map: Mapping[int, str | None],
    delivery_note_map: Mapping[int, str | None],
) -> dict:
    return {
        "id": pay.id,
        "sales_order_id": pay.sales_order_id,
        "sales_order_no": order_map.get(pay.sales_order_id),
        "customer_id": pay.customer_id,
        "delivery_note_id": pay.delivery_note_id,
        "delivery_note_no": delivery_note_map.get(pay.delivery_note_id)
        if pay.delivery_note_id
        else None,
        "invoice_id": pay.invoice_id,
        "invoice_no": invoice_map.get(pay.invoice_id) if pay.invoice_id else None,
        "amount": float(pay.amount),
        "payment_date": pay.payment_date.isoformat() if pay.payment_date else None,
        "payment_method": pay.payment_method,
        "status": pay.status,
        "currency": pay.currency,
        "transaction_ref": pay.transaction_ref,
        "bank_account": pay.bank_account,
        "notes": pay.notes,
        "created_at": pay.created_at.isoformat() if pay.created_at else None,
        "updated_at": pay.updated_at.isoformat() if pay.updated_at else None,
    }


async def _load_invoice_no(db: AsyncSession, invoice_id: int | None) -> str | None:
    """Fetch invoice_no for a given invoice_id, or None if not linked."""
    if not invoice_id:
        return None
    result = await db.execute(
        select(Invoice.invoice_no).where(Invoice.id == invoice_id)
    )
    row = result.first()
    return row[0] if row else None


async def _load_order_no(db: AsyncSession, order_id: int | None) -> str | None:
    if not order_id:
        return None
    result = await db.execute(
        select(SalesOrder.order_no).where(SalesOrder.id == order_id)
    )
    row = result.first()
    return row[0] if row else None


async def _load_delivery_note_no(
    db: AsyncSession, delivery_note_id: int | None
) -> str | None:
    if not delivery_note_id:
        return None
    result = await db.execute(
        select(DeliveryNote.delivery_no).where(DeliveryNote.id == delivery_note_id)
    )
    row = result.first()
    return row[0] if row else None


async def _bump_payment_caches() -> None:
    """Bump all caches affected by payment writes."""
    await cache_bump_version("payments:list")
    await cache_bump_version("payments:stats")
    await cache_bump_version("reports:predefined:ar")
    await cache_bump_version("dashboard:overview")
    await cache_bump_version("dashboard:kpi")


@router.get("/payments", response_model=APIResponse[PageData[PaymentRecordResponse]])
async def list_payments(
    response: JSONResponse,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    customer_id: int | None = None,
    status: str | None = None,
    sales_order_id: int | None = None,
    delivery_note_id: int | None = None,
    invoice_id: int | None = None,
    sort_by: str = "id",
    sort_order: str = "desc",
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(get_current_user),
):
    cache_key = _payments_cache_key(
        page=page,
        page_size=page_size,
        customer_id=customer_id,
        status=status,
        sales_order_id=sales_order_id,
        delivery_note_id=delivery_note_id,
        invoice_id=invoice_id,
        sort_by=sort_by,
        sort_order=sort_order,
    )
    cached_payload = await cache_get_versioned("payments:list", cache_key)
    if cached_payload is not None:
        response.headers["X-Cache"] = "HIT"
        response.headers["X-Cache-Key"] = cache_key
        return ok(json.loads(cached_payload))
    response.headers["X-Cache"] = "MISS"
    result = await svc.list_payments(
        db,
        page=page,
        page_size=page_size,
        customer_id=customer_id,
        status=status,
        sales_order_id=sales_order_id,
        delivery_note_id=delivery_note_id,
        invoice_id=invoice_id,
        sort_by=sort_by,
        sort_order=sort_order,
    )
    # Eager-load invoice_no for linked invoices
    payments = list(result["list"])
    invoice_ids = [p.invoice_id for p in payments if p.invoice_id]
    invoice_map: dict[int, str] = {}
    if invoice_ids:
        invs = (
            await db.execute(
                select(Invoice.id, Invoice.invoice_no).where(
                    Invoice.id.in_(invoice_ids)
                )
            )
        ).all()
        invoice_map = {inv_id: inv_no or "" for inv_id, inv_no in invs}
    order_ids = list({p.sales_order_id for p in payments if p.sales_order_id})
    order_map: dict[int, str] = {}
    if order_ids:
        orders = (
            await db.execute(
                select(SalesOrder.id, SalesOrder.order_no).where(
                    SalesOrder.id.in_(order_ids)
                )
            )
        ).all()
        order_map = {order_id: order_no or "" for order_id, order_no in orders}
    delivery_note_ids = list(
        {p.delivery_note_id for p in payments if p.delivery_note_id}
    )
    delivery_note_map: dict[int, str] = {}
    if delivery_note_ids:
        delivery_notes = (
            await db.execute(
                select(DeliveryNote.id, DeliveryNote.delivery_no).where(
                    DeliveryNote.id.in_(delivery_note_ids)
                )
            )
        ).all()
        delivery_note_map = {
            note_id: note_no or "" for note_id, note_no in delivery_notes
        }
    serialized = {
        **result,
        "list": [
            _serialize_payment(p, invoice_map, order_map, delivery_note_map)
            for p in payments
        ],
    }
    await cache_set_versioned(
        "payments:list",
        cache_key,
        json.dumps(serialized, default=str),
        PAYMENTS_LIST_CACHE_TTL,
    )
    return ok(serialized)


@router.get("/payments/stats", response_model=APIResponse[PaymentStats])
async def get_payment_stats(
    response: JSONResponse,
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(get_current_user),
):
    cache_key = "payments:stats:global"
    cached_payload = await cache_get_versioned("payments:stats", cache_key)
    if cached_payload is not None:
        response.headers["X-Cache"] = "HIT"
        response.headers["X-Cache-Key"] = cache_key
        return ok(json.loads(cached_payload))
    response.headers["X-Cache"] = "MISS"
    result = await svc.payment_stats(db)
    await cache_set_versioned(
        "payments:stats",
        cache_key,
        json.dumps(result, default=str),
        PAYMENTS_STATS_CACHE_TTL,
    )
    return ok(result)


@router.get("/payments/{pay_id}", response_model=APIResponse[PaymentRecordResponse])
async def get_payment(
    pay_id: int,
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(get_current_user),
):
    pay = await svc.get_payment(db, pay_id)
    if not pay:
        return fail("回款记录不存在", 404)
    invoice_no = await _load_invoice_no(db, pay.invoice_id)
    order_no = await _load_order_no(db, pay.sales_order_id)
    delivery_note_no = await _load_delivery_note_no(db, pay.delivery_note_id)
    return ok(
        _serialize_payment(
            pay,
            {pay.invoice_id: invoice_no} if pay.invoice_id else {},
            {pay.sales_order_id: order_no} if pay.sales_order_id else {},
            {pay.delivery_note_id: delivery_note_no} if pay.delivery_note_id else {},
        )
    )


@router.post("/payments", response_model=APIResponse[PaymentRecordResponse])
async def create_payment(
    body: PaymentRecordCreate,
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(get_current_user),
):
    pay = await svc.create_payment(db, body.model_dump())
    await _bump_payment_caches()
    invoice_no = await _load_invoice_no(db, pay.invoice_id)
    order_no = await _load_order_no(db, pay.sales_order_id)
    delivery_note_no = await _load_delivery_note_no(db, pay.delivery_note_id)
    return ok(
        _serialize_payment(
            pay,
            {pay.invoice_id: invoice_no} if pay.invoice_id else {},
            {pay.sales_order_id: order_no} if pay.sales_order_id else {},
            {pay.delivery_note_id: delivery_note_no} if pay.delivery_note_id else {},
        )
    )


@router.put("/payments/{pay_id}/allocations")
async def replace_payment_allocations(
    pay_id: int,
    body: PaymentAllocationRequest,
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(get_current_user),
):
    """Allocate one receipt across one or more invoices atomically."""
    pay = await svc.get_payment(db, pay_id)
    if not pay:
        return fail("回款记录不存在", 404)

    invoice_ids = [item.invoice_id for item in body.allocations]
    if len(invoice_ids) != len(set(invoice_ids)):
        return fail("同一张发票不能重复核销", 400)
    requested_total = round(sum(item.amount for item in body.allocations), 6)
    if requested_total > float(pay.amount or 0) + 0.000001:
        return fail("核销金额不能超过本次回款金额", 400)

    invoices = list(
        (
            await db.scalars(
                select(Invoice).where(
                    Invoice.id.in_(invoice_ids), Invoice.deleted_at.is_(None)
                )
            )
        ).all()
    )
    invoice_map = {item.id: item for item in invoices}
    if len(invoice_map) != len(invoice_ids):
        return fail("存在无效发票", 400)
    if any(item.customer_id != pay.customer_id for item in invoices):
        return fail("回款只能核销同一客户的发票", 400)

    current = list(
        (
            await db.scalars(
                select(PaymentAllocation).where(
                    PaymentAllocation.payment_id == pay_id,
                    PaymentAllocation.deleted_at.is_(None),
                )
            )
        ).all()
    )
    for item in current:
        await db.delete(item)
    await db.flush()

    for requested in body.allocations:
        invoice = invoice_map[requested.invoice_id]
        allocated_elsewhere = float(
            await db.scalar(
                select(func.coalesce(func.sum(PaymentAllocation.amount), 0)).where(
                    PaymentAllocation.invoice_id == invoice.id,
                    PaymentAllocation.deleted_at.is_(None),
                )
            )
            or 0
        )
        if allocated_elsewhere + requested.amount > float(invoice.amount) + 0.000001:
            return fail(f"发票 {invoice.invoice_no or invoice.id} 核销金额超出发票金额", 400)
        db.add(
            PaymentAllocation(
                payment_id=pay.id,
                invoice_id=invoice.id,
                sales_order_id=invoice.sales_order_id,
                amount=requested.amount,
            )
        )

    await db.flush()
    for invoice in invoices:
        allocated = float(
            await db.scalar(
                select(func.coalesce(func.sum(PaymentAllocation.amount), 0)).where(
                    PaymentAllocation.invoice_id == invoice.id,
                    PaymentAllocation.deleted_at.is_(None),
                )
            )
            or 0
        )
        if allocated >= float(invoice.amount) - 0.000001:
            await transition_status(
                db,
                invoice,
                "paid",
                guard=assert_can_transition_invoice,
                aggregate_type="Invoice",
                actor=_user["user_id"],
                action="allocate_payment",
            )

    target_status = (
        "completed"
        if requested_total >= float(pay.amount) - 0.000001
        else "partial"
    )
    await transition_status(
        db,
        pay,
        target_status,
        guard=assert_can_transition_payment,
        aggregate_type="PaymentRecord",
        actor=_user["user_id"],
        action="allocate_payment",
    )
    await _bump_payment_caches()
    await cache_bump_version("invoices:list")
    return ok(
        {
            "payment_id": pay.id,
            "allocated_amount": round(requested_total, 2),
            "unallocated_amount": max(round(float(pay.amount) - requested_total, 2), 0),
            "status": pay.status,
        }
    )


@router.put("/payments/{pay_id}", response_model=APIResponse[PaymentRecordResponse])
async def update_payment(
    pay_id: int,
    body: PaymentRecordUpdate,
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(get_current_user),
):
    pay = await svc.get_payment(db, pay_id)
    if not pay:
        return fail("回款记录不存在", 404)
    pay = await svc.update_payment(
        db,
        pay,
        body.model_dump(exclude_none=True),
        actor=_user["user_id"],
    )
    await _bump_payment_caches()
    invoice_no = await _load_invoice_no(db, pay.invoice_id)
    order_no = await _load_order_no(db, pay.sales_order_id)
    delivery_note_no = await _load_delivery_note_no(db, pay.delivery_note_id)
    return ok(
        _serialize_payment(
            pay,
            {pay.invoice_id: invoice_no} if pay.invoice_id else {},
            {pay.sales_order_id: order_no} if pay.sales_order_id else {},
            {pay.delivery_note_id: delivery_note_no} if pay.delivery_note_id else {},
        )
    )


@router.delete("/payments/{pay_id}")
async def delete_payment(
    pay_id: int,
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(get_current_user),
):
    pay = await svc.get_payment(db, pay_id)
    if not pay:
        return fail("回款记录不存在", 404)
    await svc.delete_payment(db, pay)
    await _bump_payment_caches()
    return ok({"deleted": pay_id})
