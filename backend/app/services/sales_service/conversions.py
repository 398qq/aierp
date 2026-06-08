from __future__ import annotations

import logging
from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.sales import (
    DeliveryNote,
    DeliveryNoteItem,
    Quotation,
    SalesOrder,
    SalesOrderItem,
)
from app.services.docno import generate_doc_no

logger = logging.getLogger(__name__)


async def convert_quotation_to_order(db: AsyncSession, quote: Quotation) -> SalesOrder:
    if quote.status == "won":
        raise ValueError(f"Quotation {quote.id} already converted to an order")
    order_no = await generate_doc_no(db, "SO", SalesOrder, "order_no")
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
    if order.status in ("completed", "cancelled"):
        return None
    existing = await db.execute(
        select(func.count()).where(DeliveryNote.sales_order_id == order.id, DeliveryNote.deleted_at.is_(None))
    )
    existing_count = existing.scalar() or 0
    if existing_count > 0:
        return None
    delivery_no = await generate_doc_no(db, "DN", DeliveryNote, "delivery_no")
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

