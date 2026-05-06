"""Transaction management API — purchase orders, payments, tickets, visits, samples."""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.database import get_db
from app.models.transaction import PurchaseOrder, PurchaseOrderItem, Payment, Ticket, Visit, Sample
from app.schemas.common import fail, ok

router = APIRouter(tags=["transactions"])

# --- Purchase Orders ---

po_router = APIRouter(prefix="/purchase-orders")


class POCreate(BaseModel):
    order_no: str | None = None
    supplier_id: int
    status: str = "draft"
    total_amount: float = 0
    expected_date: str | None = None
    notes: str | None = None


@po_router.get("")
async def list_purchase_orders(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    supplier_id: int | None = None,
    status: str | None = None,
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(get_current_user),
):
    base = select(PurchaseOrder).where(PurchaseOrder.deleted_at.is_(None))
    count_base = select(func.count(PurchaseOrder.id)).where(PurchaseOrder.deleted_at.is_(None))

    if supplier_id:
        base = base.where(PurchaseOrder.supplier_id == supplier_id)
        count_base = count_base.where(PurchaseOrder.supplier_id == supplier_id)
    if status:
        base = base.where(PurchaseOrder.status == status)
        count_base = count_base.where(PurchaseOrder.status == status)

    total = (await db.execute(count_base)).scalar() or 0
    rows = (await db.execute(
        base.order_by(PurchaseOrder.id.desc()).offset((page - 1) * page_size).limit(page_size)
    )).scalars().all()

    return ok({
        "list": [{"id": p.id, "order_no": p.order_no, "supplier_id": p.supplier_id,
                  "status": p.status, "total_amount": float(p.total_amount),
                  "expected_date": str(p.expected_date) if p.expected_date else None,
                  "notes": p.notes, "created_at": str(p.created_at)} for p in rows],
        "total": total, "page": page, "page_size": page_size,
    })


@po_router.post("", status_code=201)
async def create_purchase_order(body: POCreate, db: AsyncSession = Depends(get_db), _user: dict = Depends(get_current_user)):
    data = body.model_dump()
    if data.get("expected_date"):
        data["expected_date"] = datetime.fromisoformat(data["expected_date"])
    order = PurchaseOrder(**data)
    db.add(order)
    await db.flush()
    return ok({"id": order.id, "order_no": order.order_no})


# --- Payments ---

pay_router = APIRouter(prefix="/payments")


class PaymentCreate(BaseModel):
    payment_no: str | None = None
    customer_id: int | None = None
    supplier_id: int | None = None
    type: str = "receipt"
    amount: float
    method: str | None = None
    paid_at: str | None = None
    notes: str | None = None


@pay_router.get("")
async def list_payments(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    type: str | None = None,
    customer_id: int | None = None,
    supplier_id: int | None = None,
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(get_current_user),
):
    base = select(Payment).where(Payment.deleted_at.is_(None))
    count_base = select(func.count(Payment.id)).where(Payment.deleted_at.is_(None))

    if type:
        base = base.where(Payment.type == type)
        count_base = count_base.where(Payment.type == type)
    if customer_id:
        base = base.where(Payment.customer_id == customer_id)
        count_base = count_base.where(Payment.customer_id == customer_id)
    if supplier_id:
        base = base.where(Payment.supplier_id == supplier_id)
        count_base = count_base.where(Payment.supplier_id == supplier_id)

    total = (await db.execute(count_base)).scalar() or 0
    rows = (await db.execute(
        base.order_by(Payment.id.desc()).offset((page - 1) * page_size).limit(page_size)
    )).scalars().all()

    return ok({
        "list": [{"id": p.id, "payment_no": p.payment_no, "customer_id": p.customer_id,
                  "supplier_id": p.supplier_id, "type": p.type, "amount": float(p.amount),
                  "method": p.method, "paid_at": str(p.paid_at) if p.paid_at else None,
                  "notes": p.notes, "created_at": str(p.created_at)} for p in rows],
        "total": total, "page": page, "page_size": page_size,
    })


@pay_router.post("", status_code=201)
async def create_payment(body: PaymentCreate, db: AsyncSession = Depends(get_db), _user: dict = Depends(get_current_user)):
    data = body.model_dump()
    if data.get("paid_at"):
        data["paid_at"] = datetime.fromisoformat(data["paid_at"])
    payment = Payment(**data)
    db.add(payment)
    await db.flush()
    return ok({"id": payment.id, "payment_no": payment.payment_no})


# --- Tickets ---

ticket_router = APIRouter(prefix="/tickets")


class TicketCreate(BaseModel):
    ticket_no: str | None = None
    customer_id: int | None = None
    title: str = Field(min_length=1, max_length=255)
    description: str | None = None
    status: str = "open"
    priority: str = "medium"
    category: str | None = None
    assigned_to: str | None = None
    notes: str | None = None


@ticket_router.get("")
async def list_tickets(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: str | None = None,
    priority: str | None = None,
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(get_current_user),
):
    base = select(Ticket).where(Ticket.deleted_at.is_(None))
    count_base = select(func.count(Ticket.id)).where(Ticket.deleted_at.is_(None))

    if status:
        base = base.where(Ticket.status == status)
        count_base = count_base.where(Ticket.status == status)
    if priority:
        base = base.where(Ticket.priority == priority)
        count_base = count_base.where(Ticket.priority == priority)

    total = (await db.execute(count_base)).scalar() or 0
    rows = (await db.execute(
        base.order_by(Ticket.id.desc()).offset((page - 1) * page_size).limit(page_size)
    )).scalars().all()

    return ok({
        "list": [{"id": t.id, "ticket_no": t.ticket_no, "customer_id": t.customer_id,
                  "title": t.title, "description": t.description, "status": t.status,
                  "priority": t.priority, "category": t.category, "assigned_to": t.assigned_to,
                  "resolved_at": str(t.resolved_at) if t.resolved_at else None,
                  "notes": t.notes, "created_at": str(t.created_at)} for t in rows],
        "total": total, "page": page, "page_size": page_size,
    })


@ticket_router.post("", status_code=201)
async def create_ticket(body: TicketCreate, db: AsyncSession = Depends(get_db), _user: dict = Depends(get_current_user)):
    ticket = Ticket(**body.model_dump())
    db.add(ticket)
    await db.flush()
    return ok({"id": ticket.id, "title": ticket.title})


# --- Visits ---

visit_router = APIRouter(prefix="/visits")


class VisitCreate(BaseModel):
    visit_no: str | None = None
    customer_id: int
    contact_id: int | None = None
    title: str | None = None
    visit_date: str | None = None
    type: str | None = None
    status: str | None = None
    content: str | None = None
    result: str | None = None
    next_plan: str | None = None
    stage: str | None = None
    purpose: str | None = None
    main_product: str | None = None
    key_points: str | None = None
    followup_date: str | None = None


@visit_router.get("")
async def list_visits(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    customer_id: int | None = None,
    type: str | None = None,
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(get_current_user),
):
    base = select(Visit).where(Visit.deleted_at.is_(None))
    count_base = select(func.count(Visit.id)).where(Visit.deleted_at.is_(None))

    if customer_id:
        base = base.where(Visit.customer_id == customer_id)
        count_base = count_base.where(Visit.customer_id == customer_id)
    if type:
        base = base.where(Visit.type == type)
        count_base = count_base.where(Visit.type == type)

    total = (await db.execute(count_base)).scalar() or 0
    rows = (await db.execute(
        base.order_by(Visit.id.desc()).offset((page - 1) * page_size).limit(page_size)
    )).scalars().all()

    return ok({
        "list": [{"id": v.id, "visit_no": v.visit_no, "customer_id": v.customer_id,
                  "title": v.title, "visit_date": str(v.visit_date) if v.visit_date else None,
                  "type": v.type, "status": v.status, "content": v.content,
                  "result": v.result, "next_plan": v.next_plan, "stage": v.stage,
                  "purpose": v.purpose, "main_product": v.main_product,
                  "key_points": v.key_points,
                  "followup_date": str(v.followup_date) if v.followup_date else None,
                  "created_at": str(v.created_at)} for v in rows],
        "total": total, "page": page, "page_size": page_size,
    })


@visit_router.post("", status_code=201)
async def create_visit(body: VisitCreate, db: AsyncSession = Depends(get_db), _user: dict = Depends(get_current_user)):
    data = body.model_dump()
    for date_field in ("visit_date", "followup_date"):
        if data.get(date_field):
            data[date_field] = datetime.fromisoformat(data[date_field])
    visit = Visit(**data)
    db.add(visit)
    await db.flush()
    return ok({"id": visit.id, "title": visit.title})


# --- Samples ---

sample_router = APIRouter(prefix="/samples")


class SampleCreate(BaseModel):
    customer_id: int
    product_id: int | None = None
    quantity: int = 1
    unit: str | None = None
    apply_date: str | None = None
    ship_date: str | None = None
    receive_date: str | None = None
    status: str = "requested"
    tracking_number: str | None = None
    notes: str | None = None


@sample_router.get("")
async def list_samples(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    customer_id: int | None = None,
    status: str | None = None,
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(get_current_user),
):
    base = select(Sample).where(Sample.deleted_at.is_(None))
    count_base = select(func.count(Sample.id)).where(Sample.deleted_at.is_(None))

    if customer_id:
        base = base.where(Sample.customer_id == customer_id)
        count_base = count_base.where(Sample.customer_id == customer_id)
    if status:
        base = base.where(Sample.status == status)
        count_base = count_base.where(Sample.status == status)

    total = (await db.execute(count_base)).scalar() or 0
    rows = (await db.execute(
        base.order_by(Sample.id.desc()).offset((page - 1) * page_size).limit(page_size)
    )).scalars().all()

    return ok({
        "list": [{"id": s.id, "customer_id": s.customer_id, "product_id": s.product_id,
                  "quantity": s.quantity, "unit": s.unit,
                  "apply_date": str(s.apply_date) if s.apply_date else None,
                  "ship_date": str(s.ship_date) if s.ship_date else None,
                  "receive_date": str(s.receive_date) if s.receive_date else None,
                  "status": s.status, "tracking_number": s.tracking_number,
                  "notes": s.notes, "created_at": str(s.created_at)} for s in rows],
        "total": total, "page": page, "page_size": page_size,
    })


@sample_router.post("", status_code=201)
async def create_sample(body: SampleCreate, db: AsyncSession = Depends(get_db), _user: dict = Depends(get_current_user)):
    data = body.model_dump()
    for date_field in ("apply_date", "ship_date", "receive_date"):
        if data.get(date_field):
            data[date_field] = datetime.fromisoformat(data[date_field])
    sample = Sample(**data)
    db.add(sample)
    await db.flush()
    return ok({"id": sample.id, "status": sample.status})
