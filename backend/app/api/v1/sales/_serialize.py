"""Shared response serialization helpers for sales/finance entities.

All order-like entities (Quotation, SalesOrder, DeliveryNote, Invoice,
Contract, PaymentRecord) have a `customer_id` FK and need `customer_name`
in the response to avoid N+1 lookups in the frontend.

This module provides:
- `serialize_with_relations` — single-record serializer
- `bulk_serialize_with_relations` — batch serializer that batch-loads
  customer + parent-order + items in IN queries (no N+1)
- `denormalize_relations_on_list` — helper called by route handlers to
  eagerly assign related objects to each ORM before serialization

Why explicit eager loading (not joinedload):
- aiosqlite (the test backend) does NOT support async lazy loading;
  joinedload + relationship(lazy="selectin") still triggers async I/O
  in some code paths.
- The existing PDF endpoint (`/quotations/{id}/pdf`) already uses the
  pattern of explicit `quote.customer = await scalar_one_or_none()`.
- We follow the same pattern for consistency.
"""

from sqlalchemy import inspect as _inspect
from sqlalchemy import select


def _is_loaded(obj, attr: str) -> bool:
    """True if the relationship attribute has been loaded onto the ORM instance.

    Use this to safely access `obj.foo.bar` without triggering async
    lazy-loads (which fail in aiosqlite).
    """
    return attr not in _inspect(obj).unloaded


def serialize_quotation(quote) -> dict:
    from sqlalchemy import inspect
    insp = inspect(quote)
    cust_loaded = "customer" not in insp.unloaded
    opp_loaded = "opportunity" not in insp.unloaded
    items_loaded = "items" not in insp.unloaded

    customer_name = quote.customer.name if (cust_loaded and quote.customer) else None
    opportunity_title = quote.opportunity.title if (opp_loaded and quote.opportunity) else None
    items = [_serialize_quotation_item(it) for it in (quote.items or [])] if items_loaded else []

    return {
        "id": quote.id,
        "quotation_no": quote.quotation_no,
        "customer_id": quote.customer_id,
        "customer_name": customer_name,
        "opportunity_id": quote.opportunity_id,
        "opportunity_title": opportunity_title,
        "title": quote.title,
        "total_amount": float(quote.total_amount or 0),
        "status": quote.status,
        "valid_until": quote.valid_until.isoformat() if quote.valid_until else None,
        "notes": quote.notes,
        "created_at": quote.created_at.isoformat() if quote.created_at else None,
        "updated_at": quote.updated_at.isoformat() if quote.updated_at else None,
        "items": items,
    }


def _serialize_quotation_item(it) -> dict:
    return {
        "id": it.id,
        "quotation_id": it.quotation_id,
        "product_id": it.product_id,
        "product_name": it.product_name,
        "quantity": it.quantity,
        "unit_price": float(it.unit_price) if it.unit_price is not None else None,
        "total_price": float(it.total_price) if it.total_price is not None else None,
        "cost_price": float(it.cost_price) if it.cost_price is not None else None,
        "untaxed_cost": float(it.untaxed_cost) if it.untaxed_cost is not None else None,
        "taxed_cost": float(it.taxed_cost) if it.taxed_cost is not None else None,
        "sales_profit": float(it.sales_profit) if it.sales_profit is not None else None,
        "notes": it.notes,
    }


def serialize_sales_order(order) -> dict:
    from sqlalchemy import inspect
    insp = inspect(order)
    cust_loaded = "customer" not in insp.unloaded
    quot_loaded = "quotation" not in insp.unloaded
    items_loaded = "items" not in insp.unloaded

    customer_name = order.customer.name if (cust_loaded and order.customer) else None
    quotation_no = order.quotation.quotation_no if (quot_loaded and order.quotation) else None
    items = [_serialize_sales_order_item(it) for it in (order.items or [])] if items_loaded else []

    return {
        "id": order.id,
        "order_no": order.order_no,
        "customer_id": order.customer_id,
        "customer_name": customer_name,
        "quotation_id": order.quotation_id,
        "quotation_no": quotation_no,
        "total_amount": float(order.total_amount or 0),
        "status": order.status,
        "order_date": order.order_date.isoformat() if order.order_date else None,
        "delivery_date": order.delivery_date.isoformat() if order.delivery_date else None,
        "notes": order.notes,
        "created_at": order.created_at.isoformat() if order.created_at else None,
        "updated_at": order.updated_at.isoformat() if order.updated_at else None,
        "items": items,
    }


def _serialize_sales_order_item(it) -> dict:
    return {
        "id": it.id,
        "order_id": it.order_id,
        "product_id": it.product_id,
        "product_name": it.product_name,
        "quantity": it.quantity,
        "unit_price": float(it.unit_price) if it.unit_price is not None else None,
        "total_price": float(it.total_price) if it.total_price is not None else None,
        "notes": it.notes,
    }


def serialize_delivery_note(note) -> dict:
    from sqlalchemy import inspect
    insp = inspect(note)
    # Only access relationships that are already loaded; otherwise return None
    # to avoid triggering async lazy-loads (aiosqlite can't handle them).
    so_loaded = "sales_order" in insp.unloaded and False or "sales_order" not in insp.unloaded
    cust_loaded = "customer" not in insp.unloaded
    items_loaded = "items" not in insp.unloaded

    sales_order_no = None
    if so_loaded and note.sales_order is not None:
        sales_order_no = note.sales_order.order_no
    customer_name = None
    if cust_loaded and note.customer is not None:
        customer_name = note.customer.name
    items = [_serialize_delivery_note_item(it) for it in (note.items or [])] if items_loaded else []

    return {
        "id": note.id,
        "delivery_no": note.delivery_no,
        "sales_order_id": note.sales_order_id,
        "sales_order_no": sales_order_no,
        "customer_id": note.customer_id,
        "customer_name": customer_name,
        "status": note.status,
        "delivery_date": note.delivery_date.isoformat() if note.delivery_date else None,
        "received_date": note.received_date.isoformat() if note.received_date else None,
        "notes": note.notes,
        "created_at": note.created_at.isoformat() if note.created_at else None,
        "updated_at": note.updated_at.isoformat() if note.updated_at else None,
        "items": items,
    }


def _serialize_delivery_note_item(it) -> dict:
    return {
        "id": it.id,
        "delivery_note_id": it.delivery_note_id,
        "product_id": it.product_id,
        "product_name": it.product_name,
        "quantity": it.quantity,
        "notes": it.notes,
    }


def serialize_invoice(inv) -> dict:
    return {
        "id": inv.id,
        "invoice_no": inv.invoice_no,
        "sales_order_id": inv.sales_order_id,
        "sales_order_no": inv.sales_order.order_no if inv.sales_order else None,
        "customer_id": inv.customer_id,
        "customer_name": inv.customer.name if inv.customer else None,
        "amount": float(inv.amount or 0),
        "tax_amount": float(inv.tax_amount or 0),
        "invoice_date": inv.invoice_date.isoformat() if inv.invoice_date else None,
        "invoice_type": inv.invoice_type,
        "status": inv.status,
        "notes": inv.notes,
        "created_at": inv.created_at.isoformat() if inv.created_at else None,
        "updated_at": inv.updated_at.isoformat() if inv.updated_at else None,
    }


async def attach_customer_and_quotation(db, entity, model_cls, customer_id_attr: str = "customer_id"):
    """Attach `entity.customer` and `entity.quotation` (if present) eagerly.

    Avoids async lazy loads. Call this before serializing any Quotation /
    SalesOrder / DeliveryNote / Invoice.

    NB: For many-to-one relationships, assigning `entity.foo = None` in
    SQLAlchemy would set the FK column to None. We therefore only assign
    when the target row is actually found, otherwise leave the relationship
    untouched.
    """
    from app.models.customer import Customer
    from app.models.sales import Quotation
    customer_id = getattr(entity, customer_id_attr, None)
    if customer_id:
        cust = (await db.execute(select(Customer).where(Customer.id == customer_id))).scalar_one_or_none()
        if cust is not None:
            entity.customer = cust
        # If not found, leave as-is (still None / un-loaded)
    quotation_id = getattr(entity, "quotation_id", None)
    if quotation_id:
        q = (await db.execute(select(Quotation).where(Quotation.id == quotation_id))).scalar_one_or_none()
        if q is not None:
            entity.quotation = q
    return entity


async def attach_sales_order(db, entity, sales_order_id_attr: str = "sales_order_id"):
    """Attach `entity.sales_order` (if present) eagerly.

    Used for DeliveryNote, Invoice, PaymentRecord.

    Same caveat as `attach_customer_and_quotation`: don't assign `None`
    to a many-to-one relationship, or SQLAlchemy will null the FK.
    """
    from app.models.sales import SalesOrder
    sales_order_id = getattr(entity, sales_order_id_attr, None)
    if sales_order_id:
        so = (await db.execute(select(SalesOrder).where(SalesOrder.id == sales_order_id))).scalar_one_or_none()
        if so is not None:
            entity.sales_order = so
    return entity


async def attach_items(db, entity, item_model, foreign_key_attr: str):
    """Attach `entity.<items_attr>` list eagerly, filtered by deleted_at IS NULL."""
    fk_value = getattr(entity, "id", None)
    if fk_value is None:
        return entity
    fk_col = getattr(item_model, foreign_key_attr)
    rows = (await db.execute(
        select(item_model)
        .where(fk_col == fk_value, item_model.deleted_at.is_(None))
    )).scalars().all()
    setattr(entity, "items", list(rows))
    return entity
