"""Finance API — payment records and invoices."""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.database import get_db
from app.models.finance import Invoice, PaymentRecord
from app.schemas.common import fail, ok
from app.schemas.finance import (
    InvoiceCreate, InvoiceUpdate,
    PaymentRecordCreate, PaymentRecordUpdate,
)


def _parse_date(value: str | None) -> datetime | None:
    if value:
        return datetime.fromisoformat(value)
    return None


def _serialize_dt(dt: datetime | None) -> str | None:
    return str(dt) if dt else None


# --- Payment Records ---

pay_router = APIRouter(prefix="/sales/payments", tags=["payments"])


def _pay_row(p: PaymentRecord) -> dict:
    return {
        "id": p.id, "sales_order_id": p.sales_order_id, "customer_id": p.customer_id,
        "amount": float(p.amount), "payment_date": _serialize_dt(p.payment_date),
        "payment_method": p.payment_method, "status": p.status,
        "notes": p.notes, "created_at": str(p.created_at),
    }


@pay_router.get("")
async def list_payments(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    customer_id: int | None = None,
    order_id: int | None = None,
    status: str | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(get_current_user),
):
    base = select(PaymentRecord).where(PaymentRecord.deleted_at.is_(None))
    count_base = select(func.count(PaymentRecord.id)).where(PaymentRecord.deleted_at.is_(None))

    if customer_id:
        base = base.where(PaymentRecord.customer_id == customer_id)
        count_base = count_base.where(PaymentRecord.customer_id == customer_id)
    if order_id:
        base = base.where(PaymentRecord.sales_order_id == order_id)
        count_base = count_base.where(PaymentRecord.sales_order_id == order_id)
    if status:
        base = base.where(PaymentRecord.status == status)
        count_base = count_base.where(PaymentRecord.status == status)
    if start_date:
        dt = _parse_date(start_date)
        if dt:
            base = base.where(PaymentRecord.payment_date >= dt)
            count_base = count_base.where(PaymentRecord.payment_date >= dt)
    if end_date:
        dt = _parse_date(end_date)
        if dt:
            base = base.where(PaymentRecord.payment_date <= dt)
            count_base = count_base.where(PaymentRecord.payment_date <= dt)

    total = (await db.execute(count_base)).scalar() or 0
    rows = (await db.execute(
        base.order_by(PaymentRecord.id.desc()).offset((page - 1) * page_size).limit(page_size)
    )).scalars().all()

    return ok({
        "list": [_pay_row(p) for p in rows],
        "total": total, "page": page, "page_size": page_size,
    })


@pay_router.get("/summary")
async def get_payment_summary(db: AsyncSession = Depends(get_db), _user: dict = Depends(get_current_user)):
    received = (await db.execute(
        select(func.coalesce(func.sum(PaymentRecord.amount), 0)).where(
            PaymentRecord.deleted_at.is_(None), PaymentRecord.status == "received"
        )
    )).scalar() or 0

    pending = (await db.execute(
        select(func.coalesce(func.sum(PaymentRecord.amount), 0)).where(
            PaymentRecord.deleted_at.is_(None), PaymentRecord.status == "pending"
        )
    )).scalar() or 0

    overdue = (await db.execute(
        select(func.coalesce(func.sum(PaymentRecord.amount), 0)).where(
            PaymentRecord.deleted_at.is_(None), PaymentRecord.status == "overdue"
        )
    )).scalar() or 0

    return ok({
        "received_total": float(received),
        "pending_total": float(pending),
        "overdue_total": float(overdue),
    })


@pay_router.get("/{payment_id}")
async def get_payment(payment_id: int, db: AsyncSession = Depends(get_db), _user: dict = Depends(get_current_user)):
    result = await db.execute(
        select(PaymentRecord).where(PaymentRecord.id == payment_id, PaymentRecord.deleted_at.is_(None))
    )
    pay = result.scalar_one_or_none()
    if pay is None:
        return fail("Payment not found", 404)
    return ok(_pay_row(pay))


@pay_router.post("", status_code=201)
async def create_payment(body: PaymentRecordCreate, db: AsyncSession = Depends(get_db), _user: dict = Depends(get_current_user)):
    data = body.model_dump()
    if data.get("payment_date"):
        data["payment_date"] = _parse_date(data["payment_date"])
    pay = PaymentRecord(**data)
    db.add(pay)
    await db.flush()
    return ok({"id": pay.id})


@pay_router.put("/{payment_id}")
async def update_payment(payment_id: int, body: PaymentRecordUpdate, db: AsyncSession = Depends(get_db), _user: dict = Depends(get_current_user)):
    result = await db.execute(
        select(PaymentRecord).where(PaymentRecord.id == payment_id, PaymentRecord.deleted_at.is_(None))
    )
    pay = result.scalar_one_or_none()
    if pay is None:
        return fail("Payment not found", 404)
    data = body.model_dump(exclude_unset=True)
    if data.get("payment_date"):
        data["payment_date"] = _parse_date(data["payment_date"])
    for key, val in data.items():
        setattr(pay, key, val)
    await db.flush()
    return ok({"id": pay.id})


@pay_router.delete("/{payment_id}")
async def delete_payment(payment_id: int, db: AsyncSession = Depends(get_db), _user: dict = Depends(get_current_user)):
    result = await db.execute(
        select(PaymentRecord).where(PaymentRecord.id == payment_id, PaymentRecord.deleted_at.is_(None))
    )
    pay = result.scalar_one_or_none()
    if pay is None:
        return fail("Payment not found", 404)
    pay.deleted_at = datetime.now(timezone.utc)
    await db.flush()
    return ok(msg="deleted")


# --- Invoices ---

inv_router = APIRouter(prefix="/sales/invoices", tags=["invoices"])


def _inv_row(i: Invoice) -> dict:
    return {
        "id": i.id, "invoice_no": i.invoice_no, "sales_order_id": i.sales_order_id,
        "customer_id": i.customer_id, "amount": float(i.amount),
        "tax_amount": float(i.tax_amount), "invoice_date": _serialize_dt(i.invoice_date),
        "invoice_type": i.invoice_type, "status": i.status,
        "notes": i.notes, "created_at": str(i.created_at),
    }


@inv_router.get("")
async def list_invoices(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    customer_id: int | None = None,
    order_id: int | None = None,
    status: str | None = None,
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(get_current_user),
):
    base = select(Invoice).where(Invoice.deleted_at.is_(None))
    count_base = select(func.count(Invoice.id)).where(Invoice.deleted_at.is_(None))

    if customer_id:
        base = base.where(Invoice.customer_id == customer_id)
        count_base = count_base.where(Invoice.customer_id == customer_id)
    if order_id:
        base = base.where(Invoice.sales_order_id == order_id)
        count_base = count_base.where(Invoice.sales_order_id == order_id)
    if status:
        base = base.where(Invoice.status == status)
        count_base = count_base.where(Invoice.status == status)

    total = (await db.execute(count_base)).scalar() or 0
    rows = (await db.execute(
        base.order_by(Invoice.id.desc()).offset((page - 1) * page_size).limit(page_size)
    )).scalars().all()

    return ok({
        "list": [_inv_row(i) for i in rows],
        "total": total, "page": page, "page_size": page_size,
    })


@inv_router.get("/{invoice_id}")
async def get_invoice(invoice_id: int, db: AsyncSession = Depends(get_db), _user: dict = Depends(get_current_user)):
    result = await db.execute(
        select(Invoice).where(Invoice.id == invoice_id, Invoice.deleted_at.is_(None))
    )
    inv = result.scalar_one_or_none()
    if inv is None:
        return fail("Invoice not found", 404)
    return ok(_inv_row(inv))


@inv_router.post("", status_code=201)
async def create_invoice(body: InvoiceCreate, db: AsyncSession = Depends(get_db), _user: dict = Depends(get_current_user)):
    data = body.model_dump()
    if data.get("invoice_date"):
        data["invoice_date"] = _parse_date(data["invoice_date"])
    inv = Invoice(**data)
    db.add(inv)
    await db.flush()
    return ok({"id": inv.id, "invoice_no": inv.invoice_no})


@inv_router.put("/{invoice_id}")
async def update_invoice(invoice_id: int, body: InvoiceUpdate, db: AsyncSession = Depends(get_db), _user: dict = Depends(get_current_user)):
    result = await db.execute(
        select(Invoice).where(Invoice.id == invoice_id, Invoice.deleted_at.is_(None))
    )
    inv = result.scalar_one_or_none()
    if inv is None:
        return fail("Invoice not found", 404)
    data = body.model_dump(exclude_unset=True)
    if data.get("invoice_date"):
        data["invoice_date"] = _parse_date(data["invoice_date"])
    for key, val in data.items():
        setattr(inv, key, val)
    await db.flush()
    return ok({"id": inv.id})


@inv_router.delete("/{invoice_id}")
async def delete_invoice(invoice_id: int, db: AsyncSession = Depends(get_db), _user: dict = Depends(get_current_user)):
    result = await db.execute(
        select(Invoice).where(Invoice.id == invoice_id, Invoice.deleted_at.is_(None))
    )
    inv = result.scalar_one_or_none()
    if inv is None:
        return fail("Invoice not found", 404)
    inv.deleted_at = datetime.now(timezone.utc)
    await db.flush()
    return ok(msg="deleted")


@inv_router.post("/{invoice_id}/issue")
async def issue_invoice(invoice_id: int, db: AsyncSession = Depends(get_db), _user: dict = Depends(get_current_user)):
    result = await db.execute(
        select(Invoice).where(Invoice.id == invoice_id, Invoice.deleted_at.is_(None))
    )
    inv = result.scalar_one_or_none()
    if inv is None:
        return fail("Invoice not found", 404)
    if inv.status != "draft":
        return fail("Only draft invoices can be issued")
    inv.status = "issued"
    inv.invoice_date = datetime.now(timezone.utc)
    await db.flush()
    return ok({"id": inv.id, "status": inv.status})


@inv_router.post("/{invoice_id}/void")
async def void_invoice(invoice_id: int, db: AsyncSession = Depends(get_db), _user: dict = Depends(get_current_user)):
    result = await db.execute(
        select(Invoice).where(Invoice.id == invoice_id, Invoice.deleted_at.is_(None))
    )
    inv = result.scalar_one_or_none()
    if inv is None:
        return fail("Invoice not found", 404)
    inv.status = "void"
    await db.flush()
    return ok({"id": inv.id, "status": inv.status})
