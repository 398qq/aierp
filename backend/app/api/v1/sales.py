"""Sales management API — opportunities, quotations, sales orders, delivery notes."""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.database import get_db
from app.models.sales import Opportunity, Quotation, QuotationItem, SalesOrder, SalesOrderItem, DeliveryNote, DeliveryNoteItem
from app.schemas.common import fail, ok

router = APIRouter(tags=["sales"])

# --- Opportunities ---

opp_router = APIRouter(prefix="/opportunities")


class OpportunityCreate(BaseModel):
    customer_id: int
    name: str = Field(min_length=1, max_length=255)
    amount: float = 0
    stage: str = "lead"
    probability: int = 10
    expected_close_date: str | None = None
    actual_close_date: str | None = None
    notes: str | None = None


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
        "list": [{"id": o.id, "customer_id": o.customer_id, "name": o.name,
                  "amount": float(o.amount), "stage": o.stage, "probability": o.probability,
                  "expected_close_date": str(o.expected_close_date) if o.expected_close_date else None,
                  "actual_close_date": str(o.actual_close_date) if o.actual_close_date else None,
                  "notes": o.notes, "created_at": str(o.created_at)} for o in rows],
        "total": total, "page": page, "page_size": page_size,
    })


@opp_router.post("", status_code=201)
async def create_opportunity(body: OpportunityCreate, db: AsyncSession = Depends(get_db), _user: dict = Depends(get_current_user)):
    data = body.model_dump()
    for date_field in ("expected_close_date", "actual_close_date"):
        if data.get(date_field):
            data[date_field] = datetime.fromisoformat(data[date_field])
    opp = Opportunity(**data)
    db.add(opp)
    await db.flush()
    return ok({"id": opp.id, "name": opp.name})


# --- Quotations ---

quo_router = APIRouter(prefix="/quotations")


class QuotationCreate(BaseModel):
    quotation_no: str | None = None
    customer_id: int
    status: str = "draft"
    total_amount: float = 0
    valid_until: str | None = None
    notes: str | None = None


@quo_router.get("")
async def list_quotations(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    customer_id: int | None = None,
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(get_current_user),
):
    base = select(Quotation).where(Quotation.deleted_at.is_(None))
    count_base = select(func.count(Quotation.id)).where(Quotation.deleted_at.is_(None))

    if customer_id:
        base = base.where(Quotation.customer_id == customer_id)
        count_base = count_base.where(Quotation.customer_id == customer_id)

    total = (await db.execute(count_base)).scalar() or 0
    rows = (await db.execute(
        base.order_by(Quotation.id.desc()).offset((page - 1) * page_size).limit(page_size)
    )).scalars().all()

    return ok({
        "list": [{"id": q.id, "quotation_no": q.quotation_no, "customer_id": q.customer_id,
                  "status": q.status, "total_amount": float(q.total_amount),
                  "valid_until": str(q.valid_until) if q.valid_until else None,
                  "notes": q.notes, "created_at": str(q.created_at)} for q in rows],
        "total": total, "page": page, "page_size": page_size,
    })


@quo_router.post("", status_code=201)
async def create_quotation(body: QuotationCreate, db: AsyncSession = Depends(get_db), _user: dict = Depends(get_current_user)):
    data = body.model_dump()
    if data.get("valid_until"):
        data["valid_until"] = datetime.fromisoformat(data["valid_until"])
    quo = Quotation(**data)
    db.add(quo)
    await db.flush()
    return ok({"id": quo.id, "quotation_no": quo.quotation_no})


# --- Sales Orders ---

so_router = APIRouter(prefix="/sales-orders")


class SalesOrderCreate(BaseModel):
    order_no: str | None = None
    customer_id: int
    status: str = "pending"
    total_amount: float = 0
    delivery_date: str | None = None
    notes: str | None = None


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
        "list": [{"id": s.id, "order_no": s.order_no, "customer_id": s.customer_id,
                  "status": s.status, "total_amount": float(s.total_amount),
                  "delivery_date": str(s.delivery_date) if s.delivery_date else None,
                  "notes": s.notes, "created_at": str(s.created_at)} for s in rows],
        "total": total, "page": page, "page_size": page_size,
    })


@so_router.post("", status_code=201)
async def create_sales_order(body: SalesOrderCreate, db: AsyncSession = Depends(get_db), _user: dict = Depends(get_current_user)):
    data = body.model_dump()
    if data.get("delivery_date"):
        data["delivery_date"] = datetime.fromisoformat(data["delivery_date"])
    order = SalesOrder(**data)
    db.add(order)
    await db.flush()
    return ok({"id": order.id, "order_no": order.order_no})


# --- Delivery Notes ---

dn_router = APIRouter(prefix="/delivery-notes")


@dn_router.get("")
async def list_delivery_notes(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    sales_order_id: int | None = None,
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(get_current_user),
):
    base = select(DeliveryNote).where(DeliveryNote.deleted_at.is_(None))
    count_base = select(func.count(DeliveryNote.id)).where(DeliveryNote.deleted_at.is_(None))

    if sales_order_id:
        base = base.where(DeliveryNote.sales_order_id == sales_order_id)
        count_base = count_base.where(DeliveryNote.sales_order_id == sales_order_id)

    total = (await db.execute(count_base)).scalar() or 0
    rows = (await db.execute(
        base.order_by(DeliveryNote.id.desc()).offset((page - 1) * page_size).limit(page_size)
    )).scalars().all()

    return ok({
        "list": [{"id": d.id, "note_no": d.note_no, "sales_order_id": d.sales_order_id,
                  "customer_id": d.customer_id, "status": d.status,
                  "delivery_date": str(d.delivery_date) if d.delivery_date else None,
                  "signed_at": str(d.signed_at) if d.signed_at else None,
                  "notes": d.notes, "created_at": str(d.created_at)} for d in rows],
        "total": total, "page": page, "page_size": page_size,
    })
