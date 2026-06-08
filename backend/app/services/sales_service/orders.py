from __future__ import annotations

import logging
from datetime import datetime, timezone

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.sales import SalesOrder, SalesOrderItem
from app.services.docno import generate_doc_no
from app.services.sales_service.delivery_notes import _auto_lock_sales_order
from app.services.sales_service._helpers import (
    _customer_search_ids,
    _normalize_sales_order_items,
    _sales_item_ids,
)


logger = logging.getLogger(__name__)


async def list_sales_orders(
    db: AsyncSession, *, page: int = 1, page_size: int = 20,
    customer_id: int | None = None, status: str | None = None,
    q: str | None = None,
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
    if q and q.strip():
        q = q.strip()
        pattern = f"%{q}%"
        item_ids = _sales_item_ids(SalesOrderItem, SalesOrderItem.order_id, SalesOrderItem.product_name, q)
        search_filter = or_(
            SalesOrder.order_no.ilike(pattern),
            SalesOrder.notes.ilike(pattern),
            SalesOrder.customer_id.in_(_customer_search_ids(q)),
            SalesOrder.id.in_(item_ids),
        )
        base = base.where(search_filter)
        cnt = cnt.where(search_filter)

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
        data["order_no"] = await generate_doc_no(db, "SO", SalesOrder, "order_no")
    if not data.get("order_date"):
        data["order_date"] = datetime.now(timezone.utc)
    normalized_items, total = _normalize_sales_order_items(items_data)
    if normalized_items:
        data["total_amount"] = total
    order = SalesOrder(**{k: v for k, v in data.items() if k != "items"})
    db.add(order)
    await db.flush()

    if normalized_items:
        for item in normalized_items:
            soi = SalesOrderItem(order_id=order.id, **item)
            db.add(soi)

    await db.commit()
    await db.refresh(order)
    return order

async def update_sales_order(db: AsyncSession, order: SalesOrder, data: dict) -> SalesOrder:
    old_status = order.status
    items_data = data.pop("items", None)
    for k, v in data.items():
        if v is not None and k != "items":
            setattr(order, k, v)
    if items_data is not None:
        normalized_items, total = _normalize_sales_order_items(items_data)
        order.items.clear()
        order.total_amount = total
        await db.flush()
        for item in normalized_items:
            db.add(SalesOrderItem(order_id=order.id, **item))
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
