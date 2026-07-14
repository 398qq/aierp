from __future__ import annotations

import logging

from sqlalchemy import or_, select

from app.models.customer import Customer

logger = logging.getLogger(__name__)


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
    return select(parent_col).where(
        item_model.deleted_at.is_(None),
        text_col.ilike(pattern),
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
        total_price = item.get("total_price")
        line_total = float(total_price) if total_price is not None else qty * unit_price
        cost_price = float(item.get("cost_price") or 0)
        taxed_cost = qty * cost_price
        untaxed_cost = taxed_cost / (1 + QUOTE_COST_TAX_RATE)
        sales_profit = line_total - taxed_cost
        item["quantity"] = qty
        item["unit_price"] = unit_price
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
