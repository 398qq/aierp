from __future__ import annotations

import logging

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.customer import Customer
from app.models.product import CustomerProductCode

logger = logging.getLogger(__name__)


async def _apply_customer_product_codes(
    db: AsyncSession,
    customer_id: int | None,
    items: list[dict],
) -> list[dict]:
    """Fill missing customer-facing identities without overwriting snapshots."""
    product_ids = {
        int(item["product_id"])
        for item in items
        if item.get("product_id") is not None
    }
    if not customer_id or not product_ids:
        return items
    rows = (
        await db.scalars(
            select(CustomerProductCode).where(
                CustomerProductCode.customer_id == customer_id,
                CustomerProductCode.product_id.in_(product_ids),
                CustomerProductCode.is_active.is_(True),
                CustomerProductCode.deleted_at.is_(None),
            )
        )
    ).all()
    mapping = {row.product_id: row for row in rows}
    for item in items:
        link = mapping.get(item.get("product_id"))
        if link is None:
            continue
        if not item.get("customer_part_no"):
            item["customer_part_no"] = link.customer_part_no
        if not item.get("customer_product_name"):
            item["customer_product_name"] = link.customer_product_name
    return items


def _customer_search_ids(q: str):
    pattern = f"%{q}%"
    return select(Customer.id).where(
        Customer.deleted_at.is_(None),
        or_(
            Customer.name.ilike(pattern),
            Customer.short_name.ilike(pattern),
            Customer.code.ilike(pattern),
            Customer.contact_person.ilike(pattern),
            Customer.phone.ilike(pattern),
        ),
    )


def _sales_item_ids(item_model, parent_col, text_col, q: str):
    pattern = f"%{q}%"
    customer_part_no = getattr(item_model, "customer_part_no", None)
    text_filter = text_col.ilike(pattern)
    if customer_part_no is not None:
        text_filter = or_(text_filter, customer_part_no.ilike(pattern))
    return select(parent_col).where(
        item_model.deleted_at.is_(None),
        text_filter,
    )


QUOTE_COST_TAX_RATE = 0.13


def _normalize_quotation_items(
    items_data: list[dict] | None,
) -> tuple[list[dict], float]:
    items: list[dict] = []
    total = 0.0
    for raw in items_data or []:
        item = raw.model_dump() if hasattr(raw, "model_dump") else dict(raw)
        qty = int(item.get("quantity") or 1)
        unit_price = float(item.get("unit_price") or 0)
        discount_rate = min(max(float(item.get("discount_rate") or 0), 0), 100)
        line_total = qty * unit_price * (1 - discount_rate / 100)
        cost_price = float(item.get("cost_price") or 0)
        taxed_cost = qty * cost_price
        untaxed_cost = taxed_cost / (1 + QUOTE_COST_TAX_RATE)
        sales_profit = line_total - taxed_cost
        item["quantity"] = qty
        item["unit_price"] = unit_price
        item["discount_rate"] = discount_rate
        item["total_price"] = line_total
        item["cost_price"] = cost_price
        item["untaxed_cost"] = untaxed_cost
        item["taxed_cost"] = taxed_cost
        item["sales_profit"] = sales_profit
        total += line_total
        items.append(item)
    return items, total


def _normalize_sales_order_items(
    items_data: list[dict] | None,
) -> tuple[list[dict], float]:
    items: list[dict] = []
    total = 0.0
    for raw in items_data or []:
        item = raw.model_dump() if hasattr(raw, "model_dump") else dict(raw)
        qty = int(item.get("quantity") or 1)
        unit_price = float(item.get("unit_price") or 0)
        total_price = item.get("total_price")
        line_total = float(total_price) if total_price is not None else qty * unit_price
        item["quantity"] = qty
        item["unit_price"] = unit_price
        item["total_price"] = line_total
        total += line_total
        items.append(item)
    return items, total


# ============================================================
# Opportunity CRUD
