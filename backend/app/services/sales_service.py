"""Sales CRUD service — opportunities, quotations, orders, delivery notes."""

import logging
from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.product import Warehouse
from app.models.sales import (
    DeliveryNote,
    DeliveryNoteItem,
    Opportunity,
    Quotation,
    QuotationItem,
    SalesOrder,
    SalesOrderItem,
)
from app.models.finance import SalesTarget

logger = logging.getLogger(__name__)


# ============================================================
# Document Number Generation
# ============================================================

_NO_COLUMN_MAP = {
    "QT": "quotation_no",
    "SO": "order_no",
    "DN": "delivery_no",
    "PO": "order_no",
}


async def _gen_no(db: AsyncSession, prefix: str, model) -> str:
    now = datetime.now(timezone.utc)
    date_part = now.strftime("%Y%m%d")
    col_name = _NO_COLUMN_MAP.get(prefix, list(model.__table__.columns.keys())[1])
    col = getattr(model, col_name)
    result = await db.execute(
        select(func.count()).where(col.like(f"{prefix}{date_part}%"))
    )
    seq = (result.scalar() or 0) + 1
    return f"{prefix}{date_part}{seq:04d}"


# ============================================================
# Opportunity CRUD
# ============================================================

async def list_opportunities(
    db: AsyncSession, *, page: int = 1, page_size: int = 20,
    customer_id: int | None = None, status: str | None = None,
    stage: str | None = None, assigned_to: str | None = None,
    sort_by: str = "id", sort_order: str = "desc",
) -> dict:
    base = select(Opportunity).where(Opportunity.deleted_at.is_(None))
    cnt = select(func.count(Opportunity.id)).where(Opportunity.deleted_at.is_(None))

    if customer_id:
        base = base.where(Opportunity.customer_id == customer_id)
        cnt = cnt.where(Opportunity.customer_id == customer_id)
    if status:
        base = base.where(Opportunity.status == status)
        cnt = cnt.where(Opportunity.status == status)
    if stage:
        base = base.where(Opportunity.stage == stage)
        cnt = cnt.where(Opportunity.stage == stage)
    if assigned_to:
        base = base.where(Opportunity.assigned_to == assigned_to)
        cnt = cnt.where(Opportunity.assigned_to == assigned_to)

    total = (await db.execute(cnt)).scalar() or 0

    allowed_sorts = {"id", "title", "amount", "status", "stage", "win_probability", "expected_close_date", "created_at", "updated_at"}
    sort_by = sort_by if sort_by in allowed_sorts else "id"
    sort_col = getattr(Opportunity, sort_by, Opportunity.id)
    base = base.order_by(sort_col.desc() if sort_order == "desc" else sort_col.asc())
    rows = (await db.execute(base.offset((page - 1) * page_size).limit(page_size))).scalars().all()

    return {"list": rows, "total": total, "page": page, "page_size": page_size}


async def get_opportunity(db: AsyncSession, opp_id: int) -> Opportunity | None:
    result = await db.execute(
        select(Opportunity).where(Opportunity.id == opp_id, Opportunity.deleted_at.is_(None))
    )
    return result.scalar_one_or_none()


async def create_opportunity(db: AsyncSession, data: dict) -> Opportunity:
    opp = Opportunity(**data)
    db.add(opp)
    await db.commit()
    await db.refresh(opp)
    return opp


async def update_opportunity(db: AsyncSession, opp: Opportunity, data: dict) -> Opportunity:
    for k, v in data.items():
        if v is not None:
            setattr(opp, k, v)
    await db.commit()
    await db.refresh(opp)
    return opp


async def delete_opportunity(db: AsyncSession, opp: Opportunity) -> None:
    opp.deleted_at = datetime.now(timezone.utc)
    await db.commit()


# ============================================================
# Quotation CRUD
# ============================================================

async def list_quotations(
    db: AsyncSession, *, page: int = 1, page_size: int = 20,
    customer_id: int | None = None, status: str | None = None,
    sort_by: str = "id", sort_order: str = "desc",
) -> dict:
    base = select(Quotation).where(Quotation.deleted_at.is_(None))
    cnt = select(func.count(Quotation.id)).where(Quotation.deleted_at.is_(None))

    if customer_id:
        base = base.where(Quotation.customer_id == customer_id)
        cnt = cnt.where(Quotation.customer_id == customer_id)
    if status:
        base = base.where(Quotation.status == status)
        cnt = cnt.where(Quotation.status == status)

    total = (await db.execute(cnt)).scalar() or 0

    allowed_sorts = {"id", "quotation_no", "total_amount", "status", "created_at", "updated_at"}
    sort_by = sort_by if sort_by in allowed_sorts else "id"
    sort_col = getattr(Quotation, sort_by, Quotation.id)
    base = base.order_by(sort_col.desc() if sort_order == "desc" else sort_col.asc())
    rows = (await db.execute(base.offset((page - 1) * page_size).limit(page_size))).scalars().all()

    return {"list": rows, "total": total, "page": page, "page_size": page_size}


async def get_quotation(db: AsyncSession, quote_id: int) -> Quotation | None:
    result = await db.execute(
        select(Quotation).where(Quotation.id == quote_id, Quotation.deleted_at.is_(None))
    )
    return result.scalar_one_or_none()


async def create_quotation(db: AsyncSession, data: dict, items_data: list[dict] | None = None) -> Quotation:
    if not data.get("quotation_no"):
        data["quotation_no"] = await _gen_no(db, "QT", Quotation)
    quote = Quotation(**{k: v for k, v in data.items() if k != "items"})
    db.add(quote)
    await db.flush()

    if items_data:
        for item in items_data:
            qi = QuotationItem(quotation_id=quote.id, **item)
            db.add(qi)

    await db.commit()
    await db.refresh(quote)
    return quote


async def update_quotation(db: AsyncSession, quote: Quotation, data: dict) -> Quotation:
    for k, v in data.items():
        if v is not None and k != "items":
            setattr(quote, k, v)
    await db.commit()
    await db.refresh(quote)
    return quote


async def delete_quotation(db: AsyncSession, quote: Quotation) -> None:
    quote.deleted_at = datetime.now(timezone.utc)
    await db.commit()


# ============================================================
# Sales Order CRUD
# ============================================================

async def list_sales_orders(
    db: AsyncSession, *, page: int = 1, page_size: int = 20,
    customer_id: int | None = None, status: str | None = None,
    sort_by: str = "id", sort_order: str = "desc",
) -> dict:
    base = select(SalesOrder).where(SalesOrder.deleted_at.is_(None))
    cnt = select(func.count(SalesOrder.id)).where(SalesOrder.deleted_at.is_(None))

    if customer_id:
        base = base.where(SalesOrder.customer_id == customer_id)
        cnt = cnt.where(SalesOrder.customer_id == customer_id)
    if status:
        base = base.where(SalesOrder.status == status)
        cnt = cnt.where(SalesOrder.status == status)

    total = (await db.execute(cnt)).scalar() or 0

    allowed_sorts = {"id", "order_no", "total_amount", "status", "order_date", "delivery_date", "created_at", "updated_at"}
    sort_by = sort_by if sort_by in allowed_sorts else "id"
    sort_col = getattr(SalesOrder, sort_by, SalesOrder.id)
    base = base.order_by(sort_col.desc() if sort_order == "desc" else sort_col.asc())
    rows = (await db.execute(base.offset((page - 1) * page_size).limit(page_size))).scalars().all()

    return {"list": rows, "total": total, "page": page, "page_size": page_size}


async def get_sales_order(db: AsyncSession, order_id: int) -> SalesOrder | None:
    result = await db.execute(
        select(SalesOrder).where(SalesOrder.id == order_id, SalesOrder.deleted_at.is_(None))
    )
    return result.scalar_one_or_none()


async def create_sales_order(db: AsyncSession, data: dict, items_data: list[dict] | None = None) -> SalesOrder:
    if not data.get("order_no"):
        data["order_no"] = await _gen_no(db, "SO", SalesOrder)
    if not data.get("order_date"):
        data["order_date"] = datetime.now(timezone.utc)
    order = SalesOrder(**{k: v for k, v in data.items() if k != "items"})
    db.add(order)
    await db.flush()

    if items_data:
        for item in items_data:
            soi = SalesOrderItem(order_id=order.id, **item)
            db.add(soi)

    await db.commit()
    await db.refresh(order)
    return order


async def update_sales_order(db: AsyncSession, order: SalesOrder, data: dict) -> SalesOrder:
    old_status = order.status
    for k, v in data.items():
        if v is not None and k != "items":
            setattr(order, k, v)
    await db.commit()
    await db.refresh(order)

    new_status = data.get("status")
    if new_status and new_status == "confirmed" and old_status != new_status:
        await _auto_lock_sales_order(db, order)

    return order


async def delete_sales_order(db: AsyncSession, order: SalesOrder) -> None:
    order.deleted_at = datetime.now(timezone.utc)
    await db.commit()


# ============================================================
# Delivery Note CRUD
# ============================================================

async def list_delivery_notes(
    db: AsyncSession, *, page: int = 1, page_size: int = 20,
    customer_id: int | None = None, status: str | None = None,
    sales_order_id: int | None = None,
    sort_by: str = "id", sort_order: str = "desc",
) -> dict:
    base = select(DeliveryNote).where(DeliveryNote.deleted_at.is_(None))
    cnt = select(func.count(DeliveryNote.id)).where(DeliveryNote.deleted_at.is_(None))

    if customer_id:
        base = base.where(DeliveryNote.customer_id == customer_id)
        cnt = cnt.where(DeliveryNote.customer_id == customer_id)
    if status:
        base = base.where(DeliveryNote.status == status)
        cnt = cnt.where(DeliveryNote.status == status)
    if sales_order_id:
        base = base.where(DeliveryNote.sales_order_id == sales_order_id)
        cnt = cnt.where(DeliveryNote.sales_order_id == sales_order_id)

    total = (await db.execute(cnt)).scalar() or 0

    allowed_sorts = {"id", "delivery_no", "status", "delivery_date", "received_date", "created_at", "updated_at"}
    sort_by = sort_by if sort_by in allowed_sorts else "id"
    sort_col = getattr(DeliveryNote, sort_by, DeliveryNote.id)
    base = base.order_by(sort_col.desc() if sort_order == "desc" else sort_col.asc())
    rows = (await db.execute(base.offset((page - 1) * page_size).limit(page_size))).scalars().all()

    return {"list": rows, "total": total, "page": page, "page_size": page_size}


async def get_delivery_note(db: AsyncSession, note_id: int) -> DeliveryNote | None:
    result = await db.execute(
        select(DeliveryNote).where(DeliveryNote.id == note_id, DeliveryNote.deleted_at.is_(None))
    )
    return result.scalar_one_or_none()


async def create_delivery_note(db: AsyncSession, data: dict, items_data: list[dict] | None = None) -> DeliveryNote:
    if not data.get("delivery_no"):
        data["delivery_no"] = await _gen_no(db, "DN", DeliveryNote)
    note = DeliveryNote(**{k: v for k, v in data.items() if k != "items"})
    db.add(note)
    await db.flush()

    if items_data:
        for item in items_data:
            dni = DeliveryNoteItem(delivery_note_id=note.id, **item)
            db.add(dni)

    await db.commit()
    await db.refresh(note)
    return note


async def update_delivery_note(db: AsyncSession, note: DeliveryNote, data: dict) -> DeliveryNote:
    old_status = note.status
    for k, v in data.items():
        if v is not None and k != "items":
            setattr(note, k, v)
    await db.commit()
    await db.refresh(note)

    # Auto-deduct inventory when status changes to shipped/completed
    new_status = data.get("status")
    if new_status and new_status in ("shipped", "completed") and old_status != new_status:
        await _auto_deduct_delivery(db, note)

    return note


async def _auto_deduct_delivery(db: AsyncSession, note: DeliveryNote) -> None:
    """Auto-deduct inventory for each item when a delivery note is shipped/completed."""
    from app.services.inventory_service import deduct_for_delivery

    result = await db.execute(select(Warehouse.id).limit(1))
    warehouse_id = result.scalar() or 1

    for item in note.items:
        if item.product_id and item.quantity > 0:
            try:
                await deduct_for_delivery(db, item.product_id, warehouse_id, item.quantity, note.id)
            except Exception as e:
                logger.error("Auto-deduct failed DN#%s product#%s: %s", note.id, item.product_id, e)


async def _auto_lock_sales_order(db: AsyncSession, order: SalesOrder) -> None:
    """Auto-lock inventory for each item when a sales order is confirmed."""
    from app.services.inventory_service import lock_for_sales_order

    result = await db.execute(select(Warehouse.id).limit(1))
    warehouse_id = result.scalar() or 1

    for item in order.items:
        if item.product_id and item.quantity > 0:
            try:
                await lock_for_sales_order(db, item.product_id, warehouse_id, item.quantity, order.id)
            except Exception as e:
                logger.error("Auto-lock failed SO#%s product#%s: %s", order.id, item.product_id, e)


async def delete_delivery_note(db: AsyncSession, note: DeliveryNote) -> None:
    note.deleted_at = datetime.now(timezone.utc)
    await db.commit()


# ============================================================
# Flow Conversions
# ============================================================

async def convert_quotation_to_order(db: AsyncSession, quote: Quotation) -> SalesOrder:
    order_no = await _gen_no(db, "SO", SalesOrder)
    order = SalesOrder(
        order_no=order_no,
        customer_id=quote.customer_id,
        quotation_id=quote.id,
        total_amount=quote.total_amount,
        status="pending",
        order_date=datetime.now(timezone.utc),
    )
    db.add(order)
    await db.flush()

    for qi in quote.items:
        soi = SalesOrderItem(
            order_id=order.id,
            product_id=qi.product_id,
            product_name=qi.product_name,
            quantity=qi.quantity,
            unit_price=qi.unit_price,
            total_price=qi.total_price,
        )
        db.add(soi)

    quote.status = "won"
    await db.commit()
    await db.refresh(order)
    return order


async def convert_order_to_delivery(db: AsyncSession, order: SalesOrder) -> DeliveryNote | None:
    existing = await db.execute(
        select(func.count()).where(DeliveryNote.sales_order_id == order.id, DeliveryNote.deleted_at.is_(None))
    )
    existing_count = existing.scalar() or 0
    if existing_count > 0:
        return None
    delivery_no = await _gen_no(db, "DN", DeliveryNote)
    note = DeliveryNote(
        delivery_no=delivery_no,
        sales_order_id=order.id,
        customer_id=order.customer_id,
        status="pending",
    )
    db.add(note)
    await db.flush()

    for soi in order.items:
        dni = DeliveryNoteItem(
            delivery_note_id=note.id,
            product_id=soi.product_id,
            product_name=soi.product_name,
            quantity=soi.quantity,
        )
        db.add(dni)

    await db.commit()
    await db.refresh(note)
    return note


# ============================================================
# Sales Targets
# ============================================================

async def list_targets(db: AsyncSession, page: int = 1, page_size: int = 20) -> dict:
    offset = (page - 1) * page_size
    total = (await db.execute(select(func.count()).where(SalesTarget.deleted_at.is_(None)))).scalar() or 0
    rows = (await db.execute(
        select(SalesTarget).where(SalesTarget.deleted_at.is_(None)).order_by(SalesTarget.id.desc()).offset(offset).limit(page_size)
    )).scalars().all()
    return {"list": rows, "total": total, "page": page, "page_size": page_size}


async def get_target(db: AsyncSession, target_id: int) -> SalesTarget | None:
    result = await db.execute(
        select(SalesTarget).where(SalesTarget.id == target_id, SalesTarget.deleted_at.is_(None))
    )
    return result.scalar_one_or_none()


async def create_target(db: AsyncSession, data: dict) -> SalesTarget:
    target = SalesTarget(**data)
    db.add(target)
    await db.commit()
    await db.refresh(target)
    return target


async def update_target(db: AsyncSession, target: SalesTarget, data: dict) -> SalesTarget:
    for k, v in data.items():
        setattr(target, k, v)
    await db.commit()
    await db.refresh(target)
    return target


async def delete_target(db: AsyncSession, target: SalesTarget):
    from datetime import datetime, timezone
    target.deleted_at = datetime.now(timezone.utc)
    await db.commit()


async def get_target_summary(db: AsyncSession) -> list:
    rows = (await db.execute(
        select(SalesTarget).where(SalesTarget.deleted_at.is_(None))
    )).scalars().all()
    return [{"id": r.id, "period": r.period, "target_amount": r.target_amount, "target_orders": r.target_orders, "user_id": r.user_id} for r in rows]
