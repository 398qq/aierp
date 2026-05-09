"""Transaction management API — purchase orders, payments, tickets, visits, samples."""

import logging
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import get_current_user
from app.database import get_db
from app.models.transaction import PurchaseOrder, Payment, Ticket, Visit, Sample
from app.schemas.common import ok

logger = logging.getLogger(__name__)

router = APIRouter(tags=["transactions"])

# --- Purchase Orders ---

po_router = APIRouter(prefix="/purchase-orders")


class POItemCreate(BaseModel):
    product_id: int
    quantity: int = 1
    unit_price: float = 0
    amount: float = 0


class POCreate(BaseModel):
    order_no: str | None = None
    supplier_id: int
    status: str = "draft"
    total_amount: float = 0
    expected_date: str | None = None
    notes: str | None = None
    items: list[POItemCreate] | None = None


@po_router.get("")
async def list_purchase_orders(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    supplier_id: int | None = None,
    status: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(get_current_user),
):
    from app.models.product import Supplier

    base = (
        select(PurchaseOrder.id, PurchaseOrder.order_no, PurchaseOrder.supplier_id,
               Supplier.name, PurchaseOrder.status, PurchaseOrder.total_amount,
               PurchaseOrder.expected_date, PurchaseOrder.notes, PurchaseOrder.created_at)
        .outerjoin(Supplier, PurchaseOrder.supplier_id == Supplier.id)
        .where(PurchaseOrder.deleted_at.is_(None))
    )
    count_base = select(func.count(PurchaseOrder.id)).where(PurchaseOrder.deleted_at.is_(None))

    if supplier_id:
        base = base.where(PurchaseOrder.supplier_id == supplier_id)
        count_base = count_base.where(PurchaseOrder.supplier_id == supplier_id)
    if status:
        base = base.where(PurchaseOrder.status == status)
        count_base = count_base.where(PurchaseOrder.status == status)
    if date_from:
        base = base.where(PurchaseOrder.created_at >= datetime.fromisoformat(date_from))
        count_base = count_base.where(PurchaseOrder.created_at >= datetime.fromisoformat(date_from))
    if date_to:
        base = base.where(PurchaseOrder.created_at <= datetime.fromisoformat(date_to + "T23:59:59"))
        count_base = count_base.where(PurchaseOrder.created_at <= datetime.fromisoformat(date_to + "T23:59:59"))

    total = (await db.execute(count_base)).scalar() or 0
    rows = (await db.execute(
        base.order_by(PurchaseOrder.id.desc()).offset((page - 1) * page_size).limit(page_size)
    )).all()

    return ok({
        "list": [{"id": r[0], "order_no": r[1], "supplier_id": r[2],
                  "supplier_name": r[3] or f"#{r[2]}",
                  "status": r[4], "total_amount": float(r[5]),
                  "expected_date": str(r[6]) if r[6] else None,
                  "notes": r[7], "created_at": str(r[8]) if r[8] else None} for r in rows],
        "total": total, "page": page, "page_size": page_size,
    })


@po_router.post("", status_code=201)
async def create_purchase_order(body: POCreate, db: AsyncSession = Depends(get_db), _user: dict = Depends(get_current_user)):
    from app.models.transaction import PurchaseOrderItem

    data = body.model_dump()
    items_data = data.pop("items", None)
    if data.get("expected_date"):
        data["expected_date"] = datetime.fromisoformat(data["expected_date"])

    if not data.get("order_no"):
        from app.services.sales_service import _gen_no
        data["order_no"] = await _gen_no(db, "PO", PurchaseOrder)

    order = PurchaseOrder(**data)
    db.add(order)
    await db.flush()

    if items_data:
        total = 0.0
        for item in items_data:
            poi = PurchaseOrderItem(order_id=order.id, **item)
            db.add(poi)
            total += item.get("amount", 0) or 0
        order.total_amount = total

    await db.commit()
    await db.refresh(order)
    return ok({"id": order.id, "order_no": order.order_no, "items_count": len(items_data) if items_data else 0})


class POUpdate(BaseModel):
    supplier_id: int | None = None
    expected_date: str | None = None
    notes: str | None = None
    items: list[POItemCreate] | None = None


@po_router.get("/{po_id}")
async def get_purchase_order(
    po_id: int,
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(get_current_user),
):
    from app.models.product import Supplier
    from app.models.transaction import PurchaseOrderItem

    result = await db.execute(
        select(PurchaseOrder)
        .where(PurchaseOrder.id == po_id, PurchaseOrder.deleted_at.is_(None))
        .options(selectinload(PurchaseOrder.items).selectinload(PurchaseOrderItem.product))
    )
    po = result.scalar_one_or_none()
    if po is None:
        raise HTTPException(404, "采购订单不存在")

    supplier_name = None
    if po.supplier_id:
        r = await db.execute(
            select(Supplier.name).where(Supplier.id == po.supplier_id)
        )
        supplier_name = r.scalar()

    return ok({
        "id": po.id,
        "order_no": po.order_no,
        "supplier_id": po.supplier_id,
        "supplier_name": supplier_name or f"#{po.supplier_id}",
        "status": po.status,
        "total_amount": float(po.total_amount),
        "expected_date": str(po.expected_date) if po.expected_date else None,
        "notes": po.notes,
        "created_at": str(po.created_at),
        "updated_at": str(po.updated_at) if po.updated_at else None,
        "items": [{
            "id": i.id,
            "product_id": i.product_id,
            "product_name": i.product.name if i.product else f"#{i.product_id}",
            "product_sku": i.product.sku if i.product and i.product.sku else "",
            "quantity": i.quantity,
            "unit_price": float(i.unit_price),
            "amount": float(i.amount),
        } for i in po.items],
    })


@po_router.put("/{po_id}")
async def update_purchase_order(
    po_id: int,
    body: POUpdate,
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(get_current_user),
):
    from app.models.transaction import PurchaseOrderItem

    result = await db.execute(
        select(PurchaseOrder)
        .where(PurchaseOrder.id == po_id, PurchaseOrder.deleted_at.is_(None))
        .options(selectinload(PurchaseOrder.items))
    )
    po = result.scalar_one_or_none()
    if po is None:
        raise HTTPException(404, "采购订单不存在")
    if po.status != "draft":
        raise HTTPException(400, "只能编辑草稿状态的采购订单")

    data = body.model_dump(exclude_none=True)
    items_data = data.pop("items", None)

    if "supplier_id" in data:
        po.supplier_id = data["supplier_id"]
    if "expected_date" in data and data["expected_date"]:
        po.expected_date = datetime.fromisoformat(data["expected_date"])
    if "notes" in data:
        po.notes = data["notes"]

    if items_data is not None:
        for item in po.items:
            await db.delete(item)
        total = 0.0
        for item in items_data:
            poi = PurchaseOrderItem(order_id=po.id, **item)
            db.add(poi)
            total += item.get("amount", 0) or 0
        po.total_amount = total

    await db.commit()
    await db.refresh(po)
    return ok({"id": po.id, "order_no": po.order_no, "msg": "更新成功"})


@po_router.delete("/{po_id}")
async def delete_purchase_order(
    po_id: int,
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(get_current_user),
):
    result = await db.execute(
        select(PurchaseOrder)
        .where(PurchaseOrder.id == po_id, PurchaseOrder.deleted_at.is_(None))
    )
    po = result.scalar_one_or_none()
    if po is None:
        raise HTTPException(404, "采购订单不存在")
    if po.status != "draft":
        raise HTTPException(400, "只能删除草稿状态的采购订单")

    po.deleted_at = datetime.utcnow()
    await db.commit()
    return ok({"id": po.id, "msg": "删除成功"})


class POReceive(BaseModel):
    warehouse_id: int = 1


@po_router.post("/{po_id}/receive")
async def receive_purchase_order(
    po_id: int,
    body: POReceive = POReceive(),
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(get_current_user),
):
    from app.services.inventory_service import receive_po_item

    result = await db.execute(
        select(PurchaseOrder)
        .where(PurchaseOrder.id == po_id, PurchaseOrder.deleted_at.is_(None))
        .options(selectinload(PurchaseOrder.items))
    )
    po = result.scalar_one_or_none()
    if po is None:
        raise HTTPException(404, "采购订单不存在")
    if po.status == "received":
        raise HTTPException(400, "采购订单已收货")

    received_items = []
    for item in po.items:
        if item.product_id and item.quantity > 0:
            try:
                r = await receive_po_item(db, item.product_id, body.warehouse_id, item.quantity, po.id)
                received_items.append(r)
            except Exception as e:
                logger.error("PO receive failed PO#%s product#%s: %s", po.id, item.product_id, e)

    po.status = "received"
    await db.commit()

    return ok({
        "po_id": po.id,
        "order_no": po.order_no,
        "status": po.status,
        "items_received": len(received_items),
        "details": received_items,
    })


class RestockItem(BaseModel):
    product_id: int
    quantity: int


class PORestockCreate(BaseModel):
    supplier_id: int
    items: list[RestockItem] = Field(min_length=1, max_length=50)
    notes: str | None = None


@po_router.post("/from-restock", status_code=201)
async def create_po_from_restock(
    body: PORestockCreate,
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(get_current_user),
):
    """One-click restock: create a purchase order from restock suggestions."""
    from app.services.sales_service import _gen_no
    from app.models.transaction import PurchaseOrderItem

    # Validate supplier exists
    from app.models.product import Supplier
    supplier = (await db.execute(
        select(Supplier).where(Supplier.id == body.supplier_id, Supplier.deleted_at.is_(None))
    )).scalar_one_or_none()
    if supplier is None:
        raise HTTPException(404, "供应商不存在")

    # Generate PO number
    po_no = await _gen_no(db, "PO", PurchaseOrder)

    po = PurchaseOrder(
        order_no=po_no,
        supplier_id=body.supplier_id,
        status="draft",
        total_amount=0,
        notes=body.notes or "AI补货建议自动生成",
    )
    db.add(po)
    await db.flush()

    created = 0
    skipped = 0
    for item in body.items:
        if item.quantity <= 0:
            skipped += 1
            continue
        poi = PurchaseOrderItem(
            order_id=po.id,
            product_id=item.product_id,
            quantity=item.quantity,
            unit_price=0,
            amount=0,
        )
        db.add(poi)
        created += 1

    await db.commit()
    await db.refresh(po)

    return ok({
        "po_id": po.id,
        "order_no": po.order_no,
        "supplier_id": body.supplier_id,
        "items_created": created,
        "items_skipped": skipped,
    })


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
