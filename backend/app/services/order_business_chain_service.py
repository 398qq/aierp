"""Sales-order-centred document chain and financial reconciliation summary."""

from __future__ import annotations

from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.finance import Contract, Invoice, PaymentRecord
from app.models.product import Product
from app.models.sales import (
    DeliveryNote,
    DeliveryNoteItem,
    Opportunity,
    Quotation,
    SalesOrder,
    SalesOrderItem,
)


def _money(value: Any) -> float:
    return round(float(value or 0), 2)


async def get_order_business_chain(db: AsyncSession, order_id: int) -> dict | None:
    order = await db.scalar(
        select(SalesOrder).where(
            SalesOrder.id == order_id, SalesOrder.deleted_at.is_(None)
        )
    )
    if order is None:
        return None

    quotation = None
    opportunity = None
    if order.quotation_id:
        quotation = await db.scalar(
            select(Quotation).where(
                Quotation.id == order.quotation_id,
                Quotation.deleted_at.is_(None),
            )
        )
        if quotation and quotation.opportunity_id:
            opportunity = await db.scalar(
                select(Opportunity).where(
                    Opportunity.id == quotation.opportunity_id,
                    Opportunity.deleted_at.is_(None),
                )
            )

    deliveries = list(
        (
            await db.scalars(
                select(DeliveryNote)
                .where(
                    DeliveryNote.sales_order_id == order_id,
                    DeliveryNote.deleted_at.is_(None),
                )
                .order_by(DeliveryNote.created_at)
            )
        ).all()
    )
    contracts = list(
        (
            await db.scalars(
                select(Contract)
                .where(
                    Contract.sales_order_id == order_id,
                    Contract.deleted_at.is_(None),
                )
                .order_by(Contract.created_at)
            )
        ).all()
    )
    invoices = list(
        (
            await db.scalars(
                select(Invoice)
                .where(
                    Invoice.sales_order_id == order_id,
                    Invoice.deleted_at.is_(None),
                )
                .order_by(Invoice.created_at)
            )
        ).all()
    )
    payments = list(
        (
            await db.scalars(
                select(PaymentRecord)
                .where(
                    PaymentRecord.sales_order_id == order_id,
                    PaymentRecord.deleted_at.is_(None),
                )
                .order_by(PaymentRecord.created_at)
            )
        ).all()
    )

    ordered_qty = int(
        await db.scalar(
            select(func.coalesce(func.sum(SalesOrderItem.quantity), 0)).where(
                SalesOrderItem.order_id == order_id,
                SalesOrderItem.deleted_at.is_(None),
            )
        )
        or 0
    )
    active_deliveries = [item for item in deliveries if item.status != "cancelled"]
    delivered_qty = 0
    delivery_ids = [item.id for item in active_deliveries]
    delivered_items: list[DeliveryNoteItem] = []
    if delivery_ids:
        delivered_items = list(
            (
                await db.scalars(
                    select(DeliveryNoteItem).where(
                        DeliveryNoteItem.delivery_note_id.in_(delivery_ids),
                        DeliveryNoteItem.deleted_at.is_(None),
                    )
                )
            ).all()
        )
        delivered_qty = sum(int(item.quantity or 0) for item in delivered_items)

    order_items = list(
        (
            await db.scalars(
                select(SalesOrderItem)
                .where(
                    SalesOrderItem.order_id == order_id,
                    SalesOrderItem.deleted_at.is_(None),
                )
                .order_by(SalesOrderItem.id)
            )
        ).all()
    )
    product_ids = {item.product_id for item in order_items if item.product_id}
    products = {}
    if product_ids:
        products = {
            product.id: product
            for product in (
                await db.scalars(select(Product).where(Product.id.in_(product_ids)))
            ).all()
        }

    def delivered_for(order_item: SalesOrderItem) -> int:
        return sum(
            int(item.quantity or 0)
            for item in delivered_items
            if (
                order_item.product_id is not None
                and item.product_id == order_item.product_id
            )
            or (
                order_item.product_id is None
                and item.product_id is None
                and (item.product_name or "").strip().casefold()
                == (order_item.product_name or "").strip().casefold()
            )
        )

    order_amount = _money(order.total_amount)
    invoiced_amount = _money(
        sum(float(item.amount or 0) for item in invoices if item.status != "cancelled")
    )
    paid_amount = _money(
        sum(
            float(item.amount or 0)
            for item in payments
            if item.status in {"paid", "completed"}
        )
    )

    def ref(
        item: Any,
        number_field: str,
        *,
        date_field: str | None = None,
        amount_field: str | None = None,
    ) -> dict:
        result = {
            "id": item.id,
            "number": getattr(item, number_field) or f"#{item.id}",
            "status": item.status,
        }
        if date_field:
            result["date"] = getattr(item, date_field, None)
        if amount_field:
            result["amount"] = _money(getattr(item, amount_field, None))
        return result

    return {
        "order": ref(order, "order_no"),
        "opportunity": ref(opportunity, "title") if opportunity else None,
        "quotation": ref(quotation, "quotation_no") if quotation else None,
        "contracts": [
            ref(item, "contract_no", date_field="signed_date", amount_field="amount")
            for item in contracts
        ],
        "deliveries": [
            ref(item, "delivery_no", date_field="delivery_date") for item in deliveries
        ],
        "invoices": [
            ref(item, "invoice_no", date_field="invoice_date", amount_field="amount")
            for item in invoices
        ],
        "payments": [
            {
                "id": item.id,
                "number": item.transaction_ref or f"#{item.id}",
                "status": item.status,
                "amount": _money(item.amount),
                "date": item.payment_date,
            }
            for item in payments
        ],
        "item_progress": [
            {
                "order_item_id": item.id,
                "product_id": item.product_id,
                "product_code": (
                    products[item.product_id].sku or products[item.product_id].mpn
                    if item.product_id in products
                    else None
                ),
                "ordered_quantity": int(item.quantity or 0),
                "delivered_quantity": min(delivered_for(item), int(item.quantity or 0)),
                "pending_quantity": max(
                    int(item.quantity or 0) - delivered_for(item), 0
                ),
            }
            for item in order_items
        ],
        "progress": {
            "ordered_quantity": ordered_qty,
            "delivered_quantity": delivered_qty,
            "pending_delivery_quantity": max(ordered_qty - delivered_qty, 0),
            "delivery_percent": round(min(delivered_qty / ordered_qty * 100, 100), 1)
            if ordered_qty
            else 0,
            "order_amount": order_amount,
            "invoiced_amount": invoiced_amount,
            "uninvoiced_amount": max(round(order_amount - invoiced_amount, 2), 0),
            "invoice_percent": round(min(invoiced_amount / order_amount * 100, 100), 1)
            if order_amount
            else 0,
            "paid_amount": paid_amount,
            "outstanding_amount": max(round(order_amount - paid_amount, 2), 0),
            "payment_percent": round(min(paid_amount / order_amount * 100, 100), 1)
            if order_amount
            else 0,
        },
    }


async def get_opportunity_business_chain(
    db: AsyncSession, opportunity_id: int
) -> dict | None:
    """Return every downstream document created from an opportunity.

    Quotations are the authoritative bridge: orders and their finance/logistics
    documents are included only when their quotation belongs to this opportunity.
    """
    opportunity = await db.scalar(
        select(Opportunity).where(
            Opportunity.id == opportunity_id,
            Opportunity.deleted_at.is_(None),
        )
    )
    if opportunity is None:
        return None

    quotations = list(
        (
            await db.scalars(
                select(Quotation)
                .where(
                    Quotation.opportunity_id == opportunity_id,
                    Quotation.deleted_at.is_(None),
                )
                .order_by(Quotation.created_at.desc())
            )
        ).all()
    )
    quotation_ids = [item.id for item in quotations]
    orders: list[SalesOrder] = []
    if quotation_ids:
        orders = list(
            (
                await db.scalars(
                    select(SalesOrder)
                    .where(
                        SalesOrder.quotation_id.in_(quotation_ids),
                        SalesOrder.deleted_at.is_(None),
                    )
                    .order_by(SalesOrder.created_at.desc())
                )
            ).all()
        )

    order_chains = []
    for order in orders:
        chain = await get_order_business_chain(db, order.id)
        if chain is not None:
            order_chains.append(chain)

    quoted_amount = _money(sum(float(item.total_amount or 0) for item in quotations))
    ordered_amount = _money(sum(float(item.total_amount or 0) for item in orders))
    return {
        "opportunity": {
            "id": opportunity.id,
            "number": f"OPP-{opportunity.id:06d}",
            "title": opportunity.title,
            "status": opportunity.status,
            "stage": opportunity.stage,
            "amount": _money(opportunity.amount),
        },
        "quotations": [
            {
                "id": item.id,
                "number": item.quotation_no or f"#{item.id}",
                "status": item.status,
                "amount": _money(item.total_amount),
                "created_at": item.created_at,
            }
            for item in quotations
        ],
        "orders": order_chains,
        "summary": {
            "quotation_count": len(quotations),
            "order_count": len(orders),
            "quoted_amount": quoted_amount,
            "ordered_amount": ordered_amount,
            "conversion_rate": round(len(orders) / len(quotations) * 100, 1)
            if quotations
            else 0,
        },
    }
