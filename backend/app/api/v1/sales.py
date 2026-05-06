"""Sales management API — opportunities, quotations, sales orders, delivery notes."""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.database import get_db
from app.models.sales import (
    DeliveryNote, DeliveryNoteItem, Opportunity, Quotation, QuotationItem, SalesOrder, SalesOrderItem,
)
from app.schemas.common import fail, ok
from app.schemas.sales import (
    DeliveryNoteCreate, DeliveryNoteItemCreate, DeliveryNoteItemUpdate, DeliveryNoteUpdate,
    OpportunityCreate, OpportunityUpdate,
    QuotationCreate, QuotationItemCreate, QuotationItemUpdate, QuotationUpdate,
    SalesOrderCreate, SalesOrderItemCreate, SalesOrderItemUpdate, SalesOrderUpdate,
)

router = APIRouter(tags=["sales"])


def _parse_date(value: str | None) -> datetime | None:
    if value:
        return datetime.fromisoformat(value)
    return None


def _serialize_dt(dt: datetime | None) -> str | None:
    return str(dt) if dt else None


# --- Opportunities ---

opp_router = APIRouter(prefix="/opportunities")


def _opp_row(o: Opportunity) -> dict:
    return {
        "id": o.id, "customer_id": o.customer_id, "name": o.name,
        "amount": float(o.amount), "stage": o.stage, "probability": o.probability,
        "expected_close_date": _serialize_dt(o.expected_close_date),
        "actual_close_date": _serialize_dt(o.actual_close_date),
        "notes": o.notes, "created_at": str(o.created_at),
    }


@opp_router.get("")
async def list_opportunities(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    customer_id: int | None = None,
    stage: str | None = None,
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(get_current_user),
):
    base = select(Opportunity).where(Opportunity.deleted_at.is_(None))
    count_base = select(func.count(Opportunity.id)).where(Opportunity.deleted_at.is_(None))

    if customer_id:
        base = base.where(Opportunity.customer_id == customer_id)
        count_base = count_base.where(Opportunity.customer_id == customer_id)
    if stage:
        base = base.where(Opportunity.stage == stage)
        count_base = count_base.where(Opportunity.stage == stage)

    total = (await db.execute(count_base)).scalar() or 0
    rows = (await db.execute(
        base.order_by(Opportunity.id.desc()).offset((page - 1) * page_size).limit(page_size)
    )).scalars().all()

    return ok({
        "list": [_opp_row(o) for o in rows],
        "total": total, "page": page, "page_size": page_size,
    })


@opp_router.get("/{opp_id}")
async def get_opportunity(opp_id: int, db: AsyncSession = Depends(get_db), _user: dict = Depends(get_current_user)):
    result = await db.execute(
        select(Opportunity).where(Opportunity.id == opp_id, Opportunity.deleted_at.is_(None))
    )
    opp = result.scalar_one_or_none()
    if opp is None:
        return fail("Opportunity not found", 404)
    return ok(_opp_row(opp))


@opp_router.post("", status_code=201)
async def create_opportunity(body: OpportunityCreate, db: AsyncSession = Depends(get_db), _user: dict = Depends(get_current_user)):
    data = body.model_dump()
    for date_field in ("expected_close_date", "actual_close_date"):
        if data.get(date_field):
            data[date_field] = _parse_date(data[date_field])
    opp = Opportunity(**data)
    db.add(opp)
    await db.flush()
    return ok({"id": opp.id, "name": opp.name})


@opp_router.put("/{opp_id}")
async def update_opportunity(opp_id: int, body: OpportunityUpdate, db: AsyncSession = Depends(get_db), _user: dict = Depends(get_current_user)):
    result = await db.execute(
        select(Opportunity).where(Opportunity.id == opp_id, Opportunity.deleted_at.is_(None))
    )
    opp = result.scalar_one_or_none()
    if opp is None:
        return fail("Opportunity not found", 404)
    data = body.model_dump(exclude_unset=True)
    for date_field in ("expected_close_date", "actual_close_date"):
        if data.get(date_field):
            data[date_field] = _parse_date(data[date_field])
    for key, val in data.items():
        setattr(opp, key, val)
    await db.flush()
    return ok({"id": opp.id})


@opp_router.delete("/{opp_id}")
async def delete_opportunity(opp_id: int, db: AsyncSession = Depends(get_db), _user: dict = Depends(get_current_user)):
    result = await db.execute(
        select(Opportunity).where(Opportunity.id == opp_id, Opportunity.deleted_at.is_(None))
    )
    opp = result.scalar_one_or_none()
    if opp is None:
        return fail("Opportunity not found", 404)
    opp.deleted_at = datetime.now(timezone.utc)
    await db.flush()
    return ok(msg="deleted")


# --- Quotations ---

quo_router = APIRouter(prefix="/quotations")


def _quo_row(q: Quotation) -> dict:
    return {
        "id": q.id, "quotation_no": q.quotation_no, "customer_id": q.customer_id,
        "status": q.status, "total_amount": float(q.total_amount),
        "valid_until": _serialize_dt(q.valid_until),
        "notes": q.notes, "created_at": str(q.created_at),
    }


@quo_router.get("")
async def list_quotations(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    customer_id: int | None = None,
    status: str | None = None,
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(get_current_user),
):
    base = select(Quotation).where(Quotation.deleted_at.is_(None))
    count_base = select(func.count(Quotation.id)).where(Quotation.deleted_at.is_(None))

    if customer_id:
        base = base.where(Quotation.customer_id == customer_id)
        count_base = count_base.where(Quotation.customer_id == customer_id)
    if status:
        base = base.where(Quotation.status == status)
        count_base = count_base.where(Quotation.status == status)

    total = (await db.execute(count_base)).scalar() or 0
    rows = (await db.execute(
        base.order_by(Quotation.id.desc()).offset((page - 1) * page_size).limit(page_size)
    )).scalars().all()

    return ok({
        "list": [_quo_row(q) for q in rows],
        "total": total, "page": page, "page_size": page_size,
    })


@quo_router.get("/{quo_id}")
async def get_quotation(quo_id: int, db: AsyncSession = Depends(get_db), _user: dict = Depends(get_current_user)):
    result = await db.execute(
        select(Quotation).where(Quotation.id == quo_id, Quotation.deleted_at.is_(None))
    )
    quo = result.scalar_one_or_none()
    if quo is None:
        return fail("Quotation not found", 404)
    data = _quo_row(quo)
    items_result = await db.execute(
        select(QuotationItem).where(QuotationItem.quotation_id == quo_id, QuotationItem.deleted_at.is_(None))
    )
    data["items"] = [{
        "id": i.id, "quotation_id": i.quotation_id, "product_id": i.product_id,
        "quantity": i.quantity, "unit_price": float(i.unit_price), "amount": float(i.amount),
    } for i in items_result.scalars().all()]
    return ok(data)


@quo_router.post("", status_code=201)
async def create_quotation(body: QuotationCreate, db: AsyncSession = Depends(get_db), _user: dict = Depends(get_current_user)):
    data = body.model_dump()
    if data.get("valid_until"):
        data["valid_until"] = _parse_date(data["valid_until"])
    quo = Quotation(**data)
    db.add(quo)
    await db.flush()
    return ok({"id": quo.id, "quotation_no": quo.quotation_no})


@quo_router.put("/{quo_id}")
async def update_quotation(quo_id: int, body: QuotationUpdate, db: AsyncSession = Depends(get_db), _user: dict = Depends(get_current_user)):
    result = await db.execute(
        select(Quotation).where(Quotation.id == quo_id, Quotation.deleted_at.is_(None))
    )
    quo = result.scalar_one_or_none()
    if quo is None:
        return fail("Quotation not found", 404)
    data = body.model_dump(exclude_unset=True)
    if data.get("valid_until"):
        data["valid_until"] = _parse_date(data["valid_until"])
    for key, val in data.items():
        setattr(quo, key, val)
    await db.flush()
    return ok({"id": quo.id})


@quo_router.delete("/{quo_id}")
async def delete_quotation(quo_id: int, db: AsyncSession = Depends(get_db), _user: dict = Depends(get_current_user)):
    result = await db.execute(
        select(Quotation).where(Quotation.id == quo_id, Quotation.deleted_at.is_(None))
    )
    quo = result.scalar_one_or_none()
    if quo is None:
        return fail("Quotation not found", 404)
    quo.deleted_at = datetime.now(timezone.utc)
    await db.flush()
    return ok(msg="deleted")


# --- Quotation Items ---

@quo_router.get("/{quo_id}/items")
async def list_quotation_items(quo_id: int, db: AsyncSession = Depends(get_db), _user: dict = Depends(get_current_user)):
    rows = (await db.execute(
        select(QuotationItem).where(
            QuotationItem.quotation_id == quo_id, QuotationItem.deleted_at.is_(None)
        )
    )).scalars().all()
    return ok([{
        "id": i.id, "quotation_id": i.quotation_id, "product_id": i.product_id,
        "quantity": i.quantity, "unit_price": float(i.unit_price), "amount": float(i.amount),
    } for i in rows])


@quo_router.post("/{quo_id}/items", status_code=201)
async def create_quotation_item(quo_id: int, body: QuotationItemCreate, db: AsyncSession = Depends(get_db), _user: dict = Depends(get_current_user)):
    item = QuotationItem(quotation_id=quo_id, **body.model_dump())
    db.add(item)
    await db.flush()
    return ok({"id": item.id, "product_id": item.product_id})


@quo_router.put("/{quo_id}/items/{item_id}")
async def update_quotation_item(quo_id: int, item_id: int, body: QuotationItemUpdate, db: AsyncSession = Depends(get_db), _user: dict = Depends(get_current_user)):
    result = await db.execute(
        select(QuotationItem).where(
            QuotationItem.id == item_id, QuotationItem.quotation_id == quo_id,
            QuotationItem.deleted_at.is_(None),
        )
    )
    item = result.scalar_one_or_none()
    if item is None:
        return fail("Quotation item not found", 404)
    for key, val in body.model_dump(exclude_unset=True).items():
        setattr(item, key, val)
    await db.flush()
    return ok({"id": item.id})


@quo_router.delete("/{quo_id}/items/{item_id}")
async def delete_quotation_item(quo_id: int, item_id: int, db: AsyncSession = Depends(get_db), _user: dict = Depends(get_current_user)):
    result = await db.execute(
        select(QuotationItem).where(
            QuotationItem.id == item_id, QuotationItem.quotation_id == quo_id,
            QuotationItem.deleted_at.is_(None),
        )
    )
    item = result.scalar_one_or_none()
    if item is None:
        return fail("Quotation item not found", 404)
    item.deleted_at = datetime.now(timezone.utc)
    await db.flush()
    return ok(msg="deleted")


# --- Sales Orders ---

so_router = APIRouter(prefix="/sales-orders")


def _so_row(s: SalesOrder) -> dict:
    return {
        "id": s.id, "order_no": s.order_no, "customer_id": s.customer_id,
        "status": s.status, "total_amount": float(s.total_amount),
        "delivery_date": _serialize_dt(s.delivery_date),
        "notes": s.notes, "created_at": str(s.created_at),
    }


@so_router.get("")
async def list_sales_orders(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    customer_id: int | None = None,
    status: str | None = None,
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(get_current_user),
):
    base = select(SalesOrder).where(SalesOrder.deleted_at.is_(None))
    count_base = select(func.count(SalesOrder.id)).where(SalesOrder.deleted_at.is_(None))

    if customer_id:
        base = base.where(SalesOrder.customer_id == customer_id)
        count_base = count_base.where(SalesOrder.customer_id == customer_id)
    if status:
        base = base.where(SalesOrder.status == status)
        count_base = count_base.where(SalesOrder.status == status)

    total = (await db.execute(count_base)).scalar() or 0
    rows = (await db.execute(
        base.order_by(SalesOrder.id.desc()).offset((page - 1) * page_size).limit(page_size)
    )).scalars().all()

    return ok({
        "list": [_so_row(s) for s in rows],
        "total": total, "page": page, "page_size": page_size,
    })


@so_router.get("/{order_id}")
async def get_sales_order(order_id: int, db: AsyncSession = Depends(get_db), _user: dict = Depends(get_current_user)):
    result = await db.execute(
        select(SalesOrder).where(SalesOrder.id == order_id, SalesOrder.deleted_at.is_(None))
    )
    order = result.scalar_one_or_none()
    if order is None:
        return fail("Sales order not found", 404)
    data = _so_row(order)
    items_result = await db.execute(
        select(SalesOrderItem).where(SalesOrderItem.order_id == order_id, SalesOrderItem.deleted_at.is_(None))
    )
    data["items"] = [{
        "id": i.id, "order_id": i.order_id, "product_id": i.product_id,
        "quantity": i.quantity, "unit_price": float(i.unit_price), "amount": float(i.amount),
    } for i in items_result.scalars().all()]
    return ok(data)


@so_router.post("", status_code=201)
async def create_sales_order(body: SalesOrderCreate, db: AsyncSession = Depends(get_db), _user: dict = Depends(get_current_user)):
    data = body.model_dump()
    if data.get("delivery_date"):
        data["delivery_date"] = _parse_date(data["delivery_date"])
    order = SalesOrder(**data)
    db.add(order)
    await db.flush()
    return ok({"id": order.id, "order_no": order.order_no})


@so_router.put("/{order_id}")
async def update_sales_order(order_id: int, body: SalesOrderUpdate, db: AsyncSession = Depends(get_db), _user: dict = Depends(get_current_user)):
    result = await db.execute(
        select(SalesOrder).where(SalesOrder.id == order_id, SalesOrder.deleted_at.is_(None))
    )
    order = result.scalar_one_or_none()
    if order is None:
        return fail("Sales order not found", 404)
    data = body.model_dump(exclude_unset=True)
    if data.get("delivery_date"):
        data["delivery_date"] = _parse_date(data["delivery_date"])
    for key, val in data.items():
        setattr(order, key, val)
    await db.flush()
    return ok({"id": order.id})


@so_router.delete("/{order_id}")
async def delete_sales_order(order_id: int, db: AsyncSession = Depends(get_db), _user: dict = Depends(get_current_user)):
    result = await db.execute(
        select(SalesOrder).where(SalesOrder.id == order_id, SalesOrder.deleted_at.is_(None))
    )
    order = result.scalar_one_or_none()
    if order is None:
        return fail("Sales order not found", 404)
    order.deleted_at = datetime.now(timezone.utc)
    await db.flush()
    return ok(msg="deleted")


# --- Sales Order Items ---

@so_router.get("/{order_id}/items")
async def list_sales_order_items(order_id: int, db: AsyncSession = Depends(get_db), _user: dict = Depends(get_current_user)):
    rows = (await db.execute(
        select(SalesOrderItem).where(
            SalesOrderItem.order_id == order_id, SalesOrderItem.deleted_at.is_(None)
        )
    )).scalars().all()
    return ok([{
        "id": i.id, "order_id": i.order_id, "product_id": i.product_id,
        "quantity": i.quantity, "unit_price": float(i.unit_price), "amount": float(i.amount),
    } for i in rows])


@so_router.post("/{order_id}/items", status_code=201)
async def create_sales_order_item(order_id: int, body: SalesOrderItemCreate, db: AsyncSession = Depends(get_db), _user: dict = Depends(get_current_user)):
    item = SalesOrderItem(order_id=order_id, **body.model_dump())
    db.add(item)
    await db.flush()
    return ok({"id": item.id, "product_id": item.product_id})


@so_router.put("/{order_id}/items/{item_id}")
async def update_sales_order_item(order_id: int, item_id: int, body: SalesOrderItemUpdate, db: AsyncSession = Depends(get_db), _user: dict = Depends(get_current_user)):
    result = await db.execute(
        select(SalesOrderItem).where(
            SalesOrderItem.id == item_id, SalesOrderItem.order_id == order_id,
            SalesOrderItem.deleted_at.is_(None),
        )
    )
    item = result.scalar_one_or_none()
    if item is None:
        return fail("Sales order item not found", 404)
    for key, val in body.model_dump(exclude_unset=True).items():
        setattr(item, key, val)
    await db.flush()
    return ok({"id": item.id})


@so_router.delete("/{order_id}/items/{item_id}")
async def delete_sales_order_item(order_id: int, item_id: int, db: AsyncSession = Depends(get_db), _user: dict = Depends(get_current_user)):
    result = await db.execute(
        select(SalesOrderItem).where(
            SalesOrderItem.id == item_id, SalesOrderItem.order_id == order_id,
            SalesOrderItem.deleted_at.is_(None),
        )
    )
    item = result.scalar_one_or_none()
    if item is None:
        return fail("Sales order item not found", 404)
    item.deleted_at = datetime.now(timezone.utc)
    await db.flush()
    return ok(msg="deleted")


# --- Delivery Notes ---

dn_router = APIRouter(prefix="/delivery-notes")


def _dn_row(d: DeliveryNote) -> dict:
    return {
        "id": d.id, "note_no": d.note_no, "sales_order_id": d.sales_order_id,
        "customer_id": d.customer_id, "status": d.status,
        "delivery_date": _serialize_dt(d.delivery_date),
        "signed_at": _serialize_dt(d.signed_at),
        "notes": d.notes, "created_at": str(d.created_at),
    }


@dn_router.get("")
async def list_delivery_notes(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    sales_order_id: int | None = None,
    status: str | None = None,
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(get_current_user),
):
    base = select(DeliveryNote).where(DeliveryNote.deleted_at.is_(None))
    count_base = select(func.count(DeliveryNote.id)).where(DeliveryNote.deleted_at.is_(None))

    if sales_order_id:
        base = base.where(DeliveryNote.sales_order_id == sales_order_id)
        count_base = count_base.where(DeliveryNote.sales_order_id == sales_order_id)
    if status:
        base = base.where(DeliveryNote.status == status)
        count_base = count_base.where(DeliveryNote.status == status)

    total = (await db.execute(count_base)).scalar() or 0
    rows = (await db.execute(
        base.order_by(DeliveryNote.id.desc()).offset((page - 1) * page_size).limit(page_size)
    )).scalars().all()

    return ok({
        "list": [_dn_row(d) for d in rows],
        "total": total, "page": page, "page_size": page_size,
    })


@dn_router.get("/{note_id}")
async def get_delivery_note(note_id: int, db: AsyncSession = Depends(get_db), _user: dict = Depends(get_current_user)):
    result = await db.execute(
        select(DeliveryNote).where(DeliveryNote.id == note_id, DeliveryNote.deleted_at.is_(None))
    )
    note = result.scalar_one_or_none()
    if note is None:
        return fail("Delivery note not found", 404)
    data = _dn_row(note)
    items_result = await db.execute(
        select(DeliveryNoteItem).where(
            DeliveryNoteItem.delivery_note_id == note_id, DeliveryNoteItem.deleted_at.is_(None)
        )
    )
    data["items"] = [{
        "id": i.id, "delivery_note_id": i.delivery_note_id,
        "product_id": i.product_id, "quantity": i.quantity,
    } for i in items_result.scalars().all()]
    return ok(data)


@dn_router.post("", status_code=201)
async def create_delivery_note(body: DeliveryNoteCreate, db: AsyncSession = Depends(get_db), _user: dict = Depends(get_current_user)):
    data = body.model_dump()
    for date_field in ("delivery_date", "signed_at"):
        if data.get(date_field):
            data[date_field] = _parse_date(data[date_field])
    note = DeliveryNote(**data)
    db.add(note)
    await db.flush()
    return ok({"id": note.id, "note_no": note.note_no})


@dn_router.put("/{note_id}")
async def update_delivery_note(note_id: int, body: DeliveryNoteUpdate, db: AsyncSession = Depends(get_db), _user: dict = Depends(get_current_user)):
    result = await db.execute(
        select(DeliveryNote).where(DeliveryNote.id == note_id, DeliveryNote.deleted_at.is_(None))
    )
    note = result.scalar_one_or_none()
    if note is None:
        return fail("Delivery note not found", 404)
    data = body.model_dump(exclude_unset=True)
    for date_field in ("delivery_date", "signed_at"):
        if data.get(date_field):
            data[date_field] = _parse_date(data[date_field])
    for key, val in data.items():
        setattr(note, key, val)
    await db.flush()
    return ok({"id": note.id})


@dn_router.delete("/{note_id}")
async def delete_delivery_note(note_id: int, db: AsyncSession = Depends(get_db), _user: dict = Depends(get_current_user)):
    result = await db.execute(
        select(DeliveryNote).where(DeliveryNote.id == note_id, DeliveryNote.deleted_at.is_(None))
    )
    note = result.scalar_one_or_none()
    if note is None:
        return fail("Delivery note not found", 404)
    note.deleted_at = datetime.now(timezone.utc)
    await db.flush()
    return ok(msg="deleted")


# --- Delivery Note Items ---

@dn_router.get("/{note_id}/items")
async def list_delivery_note_items(note_id: int, db: AsyncSession = Depends(get_db), _user: dict = Depends(get_current_user)):
    rows = (await db.execute(
        select(DeliveryNoteItem).where(
            DeliveryNoteItem.delivery_note_id == note_id, DeliveryNoteItem.deleted_at.is_(None)
        )
    )).scalars().all()
    return ok([{
        "id": i.id, "delivery_note_id": i.delivery_note_id,
        "product_id": i.product_id, "quantity": i.quantity,
    } for i in rows])


@dn_router.post("/{note_id}/items", status_code=201)
async def create_delivery_note_item(note_id: int, body: DeliveryNoteItemCreate, db: AsyncSession = Depends(get_db), _user: dict = Depends(get_current_user)):
    item = DeliveryNoteItem(delivery_note_id=note_id, **body.model_dump())
    db.add(item)
    await db.flush()
    return ok({"id": item.id, "product_id": item.product_id})


@dn_router.put("/{note_id}/items/{item_id}")
async def update_delivery_note_item(note_id: int, item_id: int, body: DeliveryNoteItemUpdate, db: AsyncSession = Depends(get_db), _user: dict = Depends(get_current_user)):
    result = await db.execute(
        select(DeliveryNoteItem).where(
            DeliveryNoteItem.id == item_id, DeliveryNoteItem.delivery_note_id == note_id,
            DeliveryNoteItem.deleted_at.is_(None),
        )
    )
    item = result.scalar_one_or_none()
    if item is None:
        return fail("Delivery note item not found", 404)
    for key, val in body.model_dump(exclude_unset=True).items():
        setattr(item, key, val)
    await db.flush()
    return ok({"id": item.id})


@dn_router.delete("/{note_id}/items/{item_id}")
async def delete_delivery_note_item(note_id: int, item_id: int, db: AsyncSession = Depends(get_db), _user: dict = Depends(get_current_user)):
    result = await db.execute(
        select(DeliveryNoteItem).where(
            DeliveryNoteItem.id == item_id, DeliveryNoteItem.delivery_note_id == note_id,
            DeliveryNoteItem.deleted_at.is_(None),
        )
    )
    item = result.scalar_one_or_none()
    if item is None:
        return fail("Delivery note item not found", 404)
    item.deleted_at = datetime.now(timezone.utc)
    await db.flush()
    return ok(msg="deleted")
