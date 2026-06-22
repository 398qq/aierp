from __future__ import annotations

import logging
from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.states import assert_can_transition_quotation
from app.models.finance import Invoice, InvoiceLine
from app.models.sales import (
    DeliveryNote,
    DeliveryNoteItem,
    Quotation,
    SalesOrder,
    SalesOrderItem,
)
from app.services.base_crud import BaseCRUDService
from app.services.docno import generate_doc_no

logger = logging.getLogger(__name__)


# ── Service ────────────────────────────────────────────────────────────


class SalesConversionService(BaseCRUDService):
    """Cross-document conversion business logic.

    Stage 1: the canonical implementation now lives on this class.
    Module-level functions below remain as thin proxies for back-compat.
    """

    model = Quotation  # placeholder; conversions are document-cross-cutting

    async def convert_quotation_to_order(
        self, db: AsyncSession, quote: Quotation
    ) -> SalesOrder:
        assert_can_transition_quotation(quote.status, "won")
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

    async def convert_order_to_delivery(
        self, db: AsyncSession, order: SalesOrder
    ) -> DeliveryNote | None:
        if order.status in ("completed", "cancelled"):
            return None
        existing = await db.execute(
            select(func.count()).where(
                DeliveryNote.sales_order_id == order.id,
                DeliveryNote.deleted_at.is_(None),
            )
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

        # Auto-transition order state: conversion to delivery = commitment
        if order.status in ("pending", "draft"):
            order.status = "confirmed"
        await db.commit()
        await db.refresh(note)
        return note

    async def convert_delivery_to_invoice(
        self, db: AsyncSession, note: DeliveryNote
    ) -> Invoice | None:
        """Convert a delivered delivery note into an invoice.

        Guards:
        - Delivery must be delivered or shipped (not pending/cancelled)
        - No duplicate invoice for the same delivery note
        """
        if note.status not in ("shipped", "delivered"):
            return None

        existing = await db.execute(
            select(func.count()).where(
                Invoice.sales_order_id == note.sales_order_id,
                Invoice.deleted_at.is_(None),
            )
        )
        if (existing.scalar() or 0) > 0:
            return None

        invoice_no = await generate_doc_no(db, "INV", Invoice, "invoice_no")
        order = (
            await db.get(SalesOrder, note.sales_order_id)
            if note.sales_order_id
            else None
        )

        inv = Invoice(
            invoice_no=invoice_no,
            sales_order_id=note.sales_order_id,
            customer_id=note.customer_id,
            amount=float(order.total_amount) if order else 0,
            tax_amount=round(float(order.total_amount) * 0.13, 4) if order else 0,
            invoice_date=datetime.now(timezone.utc),
            due_date=datetime.now(timezone.utc)
            if not (order and order.delivery_date)
            else order.delivery_date,
            status="draft",
        )
        db.add(inv)
        await db.flush()

        for dni in note.items:
            line = InvoiceLine(
                invoice_id=inv.id,
                product_id=dni.product_id,
                product_name=dni.product_name,
                quantity=dni.quantity,
                unit_price=getattr(dni, "unit_price", None),
                total_price=getattr(dni, "total_price", None),
            )
            db.add(line)

        await db.commit()
        await db.refresh(inv)
        return inv

    async def convert_delivery_to_return(
        self, db: AsyncSession, note: DeliveryNote, reason: str = ""
    ) -> "ReturnNote | None":
        """Convert a delivered delivery note into a return note.

        Guards: delivery must be delivered, no duplicate return.
        """
        from app.models.sales import ReturnNote, ReturnNoteItem

        if note.status not in ("shipped", "delivered"):
            return None

        existing = await db.execute(
            select(func.count()).where(
                ReturnNote.delivery_note_id == note.id,
                ReturnNote.deleted_at.is_(None),
            )
        )
        if (existing.scalar() or 0) > 0:
            return None

        return_no = await generate_doc_no(db, "RTN", ReturnNote, "return_no")
        rn = ReturnNote(
            return_no=return_no,
            delivery_note_id=note.id,
            sales_order_id=note.sales_order_id,
            customer_id=note.customer_id,
            total_amount=(
                float(note.sales_order.total_amount) if note.sales_order else 0
            ),
            status="pending",
            reason=reason or "",
        )
        db.add(rn)
        await db.flush()

        for dni in note.items:
            db.add(
                ReturnNoteItem(
                    return_note_id=rn.id,
                    product_id=dni.product_id,
                    product_name=dni.product_name,
                    quantity=dni.quantity,
                    unit_price=getattr(dni, "unit_price", None),
                    total_price=getattr(dni, "total_price", None),
                )
            )

        await db.commit()
        await db.refresh(rn)
        return rn


# ── Module-level proxies (back-compat) ────────────────────────────────


async def convert_quotation_to_order(db: AsyncSession, quote: Quotation) -> SalesOrder:
    return await sales_conversion_service.convert_quotation_to_order(db, quote)


async def convert_order_to_delivery(
    db: AsyncSession, order: SalesOrder
) -> DeliveryNote | None:
    return await sales_conversion_service.convert_order_to_delivery(db, order)


async def convert_delivery_to_invoice(
    db: AsyncSession, note: DeliveryNote
) -> Invoice | None:
    return await sales_conversion_service.convert_delivery_to_invoice(db, note)


async def convert_delivery_to_return(
    db: AsyncSession, note: DeliveryNote, reason: str = ""
) -> "ReturnNote | None":
    return await sales_conversion_service.convert_delivery_to_return(db, note, reason)


sales_conversion_service = SalesConversionService()
