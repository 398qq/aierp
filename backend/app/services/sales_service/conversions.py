from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import TYPE_CHECKING

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.states import (
    assert_can_transition_credit_note,
    assert_can_transition_quotation,
    assert_can_transition_return,
    assert_can_transition_sales_order,
)
from app.models.finance import CreditNote, Invoice, InvoiceLine
from app.models.sales import (
    DeliveryNote,
    DeliveryNoteItem,
    Quotation,
    SalesOrder,
    SalesOrderItem,
)

if TYPE_CHECKING:
    from app.models.sales import ReturnNote, ReturnNoteItem  # noqa: F401
from app.services.base_crud import BaseCRUDService
from app.services.docno import generate_doc_no
from app.services.state_transition_service import transition_status

logger = logging.getLogger(__name__)


# ── Service ────────────────────────────────────────────────────────────


class SalesConversionService(BaseCRUDService):
    """Cross-document conversion business logic.

    Stage 1: the canonical implementation now lives on this class.
    Module-level functions below remain as thin proxies for back-compat.
    """

    model = Quotation  # placeholder; conversions are document-cross-cutting

    async def _load_delivery_context(
        self, db: AsyncSession, note: DeliveryNote
    ) -> tuple[SalesOrder | None, list[DeliveryNoteItem]]:
        """Load conversion dependencies without async relationship lazy loads."""
        order = await db.scalar(
            select(SalesOrder).where(
                SalesOrder.id == note.sales_order_id,
                SalesOrder.deleted_at.is_(None),
            )
        )
        items = list(
            (
                await db.scalars(
                    select(DeliveryNoteItem).where(
                        DeliveryNoteItem.delivery_note_id == note.id,
                        DeliveryNoteItem.deleted_at.is_(None),
                    )
                )
            ).all()
        )
        return order, items

    async def convert_quotation_to_order(
        self, db: AsyncSession, quote: Quotation
    ) -> SalesOrder:
        assert_can_transition_quotation(quote.status, "won")
        existing_order = await db.scalar(
            select(SalesOrder).where(
                SalesOrder.quotation_id == quote.id,
                SalesOrder.deleted_at.is_(None),
            )
        )
        if existing_order is not None:
            raise ValueError(
                f"报价单已转换为销售订单 {existing_order.order_no or existing_order.id}"
            )
        order_no = await generate_doc_no(db, "SO", SalesOrder, "order_no")
        order = SalesOrder(
            order_no=order_no,
            customer_id=quote.customer_id,
            quotation_id=quote.id,
            total_amount=quote.total_amount,
            status="pending",
            currency=quote.currency,
            incoterms=quote.incoterms,
            payment_terms=quote.payment_terms,
            discount_rate=quote.discount_rate,
            discount_amount=quote.discount_amount,
            subtotal=quote.subtotal,
            order_date=datetime.now(timezone.utc),
        )
        db.add(order)
        await db.flush()

        for qi in quote.items:
            soi = SalesOrderItem(
                order_id=order.id,
                product_id=qi.product_id,
                product_name=qi.product_name,
                customer_part_no=qi.customer_part_no,
                customer_product_name=qi.customer_product_name,
                quantity=qi.quantity,
                unit=qi.unit,
                unit_price=qi.unit_price,
                total_price=qi.total_price,
                tax_rate=qi.tax_rate,
                discount_rate=qi.discount_rate,
            )
            db.add(soi)

        await transition_status(
            db,
            quote,
            "won",
            guard=assert_can_transition_quotation,
            aggregate_type="Quotation",
            action="convert_to_order",
        )
        await db.commit()
        await db.refresh(order)
        return order

    async def convert_order_to_delivery(
        self, db: AsyncSession, order: SalesOrder
    ) -> DeliveryNote | None:
        if order.status in ("completed", "cancelled"):
            return None
        existing = await db.execute(
            select(DeliveryNote).where(
                DeliveryNote.sales_order_id == order.id,
                DeliveryNote.deleted_at.is_(None),
            )
        )
        existing_note = existing.scalar_one_or_none()
        if existing_note is not None:
            return existing_note
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
                customer_part_no=soi.customer_part_no,
                customer_product_name=soi.customer_product_name,
                quantity=soi.quantity,
            )
            db.add(dni)

        # Auto-transition order state: conversion to delivery = commitment
        if order.status in ("pending", "draft"):
            await transition_status(
                db,
                order,
                "confirmed",
                guard=assert_can_transition_sales_order,
                aggregate_type="SalesOrder",
                action="create_delivery",
            )
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
                Invoice.delivery_note_id == note.id,
                Invoice.deleted_at.is_(None),
            )
        )
        if (existing.scalar() or 0) > 0:
            return None

        invoice_no = await generate_doc_no(db, "INV", Invoice, "invoice_no")
        order, delivery_items = await self._load_delivery_context(db, note)

        inv = Invoice(
            invoice_no=invoice_no,
            sales_order_id=note.sales_order_id,
            delivery_note_id=note.id,
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

        for dni in delivery_items:
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
        order, delivery_items = await self._load_delivery_context(db, note)
        rn = ReturnNote(
            return_no=return_no,
            delivery_note_id=note.id,
            sales_order_id=note.sales_order_id,
            customer_id=note.customer_id,
            total_amount=float(order.total_amount) if order else 0,
            status="pending",
            reason=reason or "",
        )
        db.add(rn)
        await db.flush()
        await transition_status(
            db,
            rn,
            "approved",
            guard=assert_can_transition_return,
            aggregate_type="ReturnNote",
            action="create_from_delivery",
        )

        for dni in delivery_items:
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


async def complete_return_note(db: AsyncSession, return_note_id: int) -> dict | None:
    """Complete a return note: transition to completed + auto-generate credit note.

    Returns dict with {return_status, credit_note_no, credit_note_amount}
    or None if validation fails.
    """
    from app.models.sales import ReturnNote
    from app.services.docno import generate_doc_no

    rn = await db.get(ReturnNote, return_note_id)
    if not rn or rn.deleted_at:
        return None
    if rn.status != "approved":
        return None

    await transition_status(
        db,
        rn,
        "completed",
        guard=assert_can_transition_return,
        aggregate_type="ReturnNote",
        action="complete",
    )

    # Auto-generate credit note
    cn_no = await generate_doc_no(db, "CN", CreditNote, "credit_note_no")
    cn = CreditNote(
        credit_note_no=cn_no,
        customer_id=rn.customer_id,
        sales_order_id=rn.sales_order_id,
        return_note_id=rn.id,
        amount=-float(rn.total_amount),
        tax_amount=-round(float(rn.total_amount) * 0.13, 4),
        status="draft",
        reason=rn.reason or "退货冲红",
    )
    db.add(cn)
    await db.flush()
    await transition_status(
        db,
        cn,
        "issued",
        guard=assert_can_transition_credit_note,
        aggregate_type="CreditNote",
        action="issue_for_return",
    )
    await db.commit()
    await db.refresh(cn)

    return {
        "return_status": rn.status,
        "credit_note_no": cn.credit_note_no,
        "credit_note_amount": cn.amount,
    }


sales_conversion_service = SalesConversionService()
