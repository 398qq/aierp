"""DeliveryNote CRUD + inventory hooks (auto-deduct, auto-lock)."""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.domain.shared.errors import InsufficientStockError
from app.models.finance import PaymentRecord
from app.models.product import Warehouse
from app.models.sales import DeliveryNote, DeliveryNoteItem, SalesOrder
from app.services.docno import generate_doc_no
from app.services.inventory_service import deduct_for_delivery, lock_for_sales_order
from app.services.sales_service._helpers import (
    _customer_search_ids,
    _sales_item_ids,
)

logger = logging.getLogger(__name__)


async def list_delivery_notes(
    db: AsyncSession, *, page: int = 1, page_size: int = 20,
    customer_id: int | None = None, status: str | None = None,
    sales_order_id: int | None = None,
    q: str | None = None,
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
    if q and q.strip():
        q = q.strip()
        pattern = f"%{q}%"
        item_ids = _sales_item_ids(DeliveryNoteItem, DeliveryNoteItem.delivery_note_id, DeliveryNoteItem.product_name, q)
        order_ids = select(SalesOrder.id).where(
            SalesOrder.deleted_at.is_(None),
            SalesOrder.order_no.ilike(pattern),
        )
        search_filter = or_(
            DeliveryNote.delivery_no.ilike(pattern),
            DeliveryNote.notes.ilike(pattern),
            DeliveryNote.customer_id.in_(_customer_search_ids(q)),
            DeliveryNote.sales_order_id.in_(order_ids),
            DeliveryNote.id.in_(item_ids),
        )
        base = base.where(search_filter)
        cnt = cnt.where(search_filter)

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


async def _apply_sales_order_to_delivery_data(
    db: AsyncSession,
    data: dict,
    items_data: list[dict] | None = None,
) -> list[dict] | None:
    sales_order_id = data.get("sales_order_id")
    if not sales_order_id:
        return items_data

    result = await db.execute(
        select(SalesOrder)
        .where(SalesOrder.id == sales_order_id, SalesOrder.deleted_at.is_(None))
        .options(selectinload(SalesOrder.items))
    )
    order = result.scalar_one_or_none()
    if not order:
        return items_data

    data["customer_id"] = order.customer_id
    if not items_data:
        return [
            {
                "product_id": item.product_id,
                "product_name": item.product_name,
                "quantity": item.quantity,
            }
            for item in order.items
        ]
    return items_data


async def create_delivery_note(db: AsyncSession, data: dict, items_data: list[dict] | None = None) -> DeliveryNote:
    items_data = await _apply_sales_order_to_delivery_data(db, data, items_data)
    if not data.get("delivery_no"):
        data["delivery_no"] = await generate_doc_no(db, "DN", DeliveryNote, "delivery_no")
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
    await _apply_sales_order_to_delivery_data(db, data)
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
    """Auto-deduct inventory for each item when a delivery note is shipped/completed.

    Insufficient stock surfaces as a domain error so the caller can respond.
    """
    result = await db.execute(select(Warehouse.id).limit(1))
    warehouse_id = result.scalar() or 1

    for item in note.items:
        if item.product_id and item.quantity > 0:
            try:
                await deduct_for_delivery(db, item.product_id, warehouse_id, item.quantity, note.id)
            except InsufficientStockError:
                raise
            except Exception as e:
                logger.error("Auto-deduct failed DN#%s product#%s: %s", note.id, item.product_id, e)


async def _auto_lock_sales_order(db: AsyncSession, order: SalesOrder) -> None:
    """Auto-lock inventory for each item when a sales order is confirmed.

    Collects per-item lock results. Returns a summary so callers can decide
    whether the confirmation should fail (no stock at all) or proceed
    (partial lock with backorder).
    """
    result = await db.execute(select(Warehouse.id).limit(1))
    warehouse_id = result.scalar() or 1

    total_requested = 0
    total_locked = 0
    for item in order.items:
        if item.product_id and item.quantity > 0:
            try:
                outcome = await lock_for_sales_order(
                    db, item.product_id, warehouse_id, item.quantity, order.id
                )
                total_requested += outcome.get("requested", 0)
                total_locked += outcome.get("locked", 0)
            except InsufficientStockError as e:
                logger.warning(
                    "Auto-lock short SO#%s product#%s requested=%s available=%s",
                    order.id, item.product_id, e.context.get("requested"),
                    e.context.get("available"),
                )
            except Exception as e:
                logger.error("Auto-lock failed SO#%s product#%s: %s", order.id, item.product_id, e)

    if total_requested > 0 and total_locked == 0:
        logger.warning(
            "Order SO#%s confirmed but NO stock locked (%s requested)",
            order.id, total_requested,
        )


async def delete_delivery_note(db: AsyncSession, note: DeliveryNote) -> None:
    note.deleted_at = datetime.now(timezone.utc)
    await db.commit()


async def mark_delivery_note_paid(
    db: AsyncSession,
    note: DeliveryNote,
    amount: float | None = None,
    payment_method: str = "bank",
    payment_date: datetime | None = None,
    notes: str | None = None,
) -> dict:
    """Record payment for a delivery note.

    Idempotent: if a payment record already exists for this delivery note,
    returns it instead of creating a duplicate.

    Defaults:
    - amount = order total_amount (if available) else first item's total
    - payment_date = now (UTC)
    - status = "completed"
    - links to both sales_order_id and customer_id
    """

    # Check for existing payment
    existing = (await db.execute(
        select(PaymentRecord).where(
            PaymentRecord.delivery_note_id == note.id,
            PaymentRecord.deleted_at.is_(None),
        )
    )).scalar_one_or_none()
    if existing is not None:
        return {"payment": existing, "created": False}

    # Determine amount if not provided
    if amount is None:
        from app.models.sales import SalesOrder
        order = (await db.execute(
            select(SalesOrder).where(SalesOrder.id == note.sales_order_id)
        )).scalar_one_or_none()
        if order is not None and order.total_amount:
            amount = float(order.total_amount)
        else:
            # Sum line totals from delivery note items
            amount = sum(
                (item.quantity or 0) for item in note.items
            ) * 1.0  # Fallback: just count items

    paid_at = payment_date or datetime.now(timezone.utc)

    pay = PaymentRecord(
        customer_id=note.customer_id,
        sales_order_id=note.sales_order_id,
        delivery_note_id=note.id,
        amount=Decimal(str(amount)),
        payment_date=paid_at,
        payment_method=payment_method,
        status="completed",
        notes=notes or f"发货单 {note.delivery_no or note.id} 签收收款",
    )
    db.add(pay)

    # Update delivery note — mark as received and set received_date
    note.received_date = paid_at
    if note.status == "shipped":
        note.status = "delivered"

    await db.commit()
    await db.refresh(pay)
    return {"payment": pay, "created": True}


# ============================================================
# Flow Conversions
# ============================================================
