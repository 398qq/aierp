from __future__ import annotations

import logging
from datetime import datetime, timezone

from app.domain.states import assert_can_transition_sales_order
from app.domain.shared.errors import BusinessRuleViolation
from app.models.product import Product
from app.models.sales import SalesOrder, SalesOrderItem
from app.services.base_crud import BaseCRUDService
from app.services.docno import generate_doc_no
from app.services.sales_service._helpers import (
    _apply_customer_product_codes,
    _customer_search_ids,
    _normalize_sales_order_items,
    _sales_item_ids,
)
from app.services.sales_service.delivery_notes import _auto_lock_sales_order
from app.services.state_transition_service import transition_status
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


# ── Service ────────────────────────────────────────────────────────────


class SalesOrderService(BaseCRUDService):
    """Sales-order service.

    Stage 1 refactor: business methods are now on this class. The class
    inherits generic CRUD from ``BaseCRUDService`` (list/get/create/update/
    delete with filters/sort). Sales-order specific behaviour (items
    normalization, status transitions, customer-state handoff) lives as
    methods prefixed ``order_`` to avoid colliding with the base contract.
    Module-level functions below remain as thin proxies for back-compat.
    """

    model = SalesOrder

    # ── Business read paths ───────────────────────────────────────────

    async def list_orders(
        self,
        db: AsyncSession,
        *,
        page: int = 1,
        page_size: int = 20,
        customer_id: int | None = None,
        status: str | None = None,
        q: str | None = None,
        sort_by: str = "id",
        sort_order: str = "desc",
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
            item_ids = _sales_item_ids(
                SalesOrderItem, SalesOrderItem.order_id, SalesOrderItem.product_name, q
            )
            search_filter = or_(
                SalesOrder.order_no.ilike(pattern),
                SalesOrder.notes.ilike(pattern),
                SalesOrder.customer_id.in_(_customer_search_ids(q)),
                SalesOrder.id.in_(item_ids),
            )
            base = base.where(search_filter)
            cnt = cnt.where(search_filter)

        total = (await db.execute(cnt)).scalar() or 0

        allowed_sorts = {
            "id",
            "order_no",
            "total_amount",
            "status",
            "order_date",
            "delivery_date",
            "created_at",
            "updated_at",
        }
        sort_by = sort_by if sort_by in allowed_sorts else "id"
        sort_col = getattr(SalesOrder, sort_by, SalesOrder.id)
        base = base.order_by(
            sort_col.desc() if sort_order == "desc" else sort_col.asc()
        )
        rows = (
            (await db.execute(base.offset((page - 1) * page_size).limit(page_size)))
            .scalars()
            .all()
        )

        return {"list": rows, "total": total, "page": page, "page_size": page_size}

    async def get_order(self, db: AsyncSession, order_id: int) -> SalesOrder | None:
        result = await db.execute(
            select(SalesOrder).where(
                SalesOrder.id == order_id, SalesOrder.deleted_at.is_(None)
            )
        )
        return result.scalar_one_or_none()

    # ── Business write paths ──────────────────────────────────────────

    async def create_order(
        self,
        db: AsyncSession,
        data: dict,
        items_data: list[dict] | None = None,
    ) -> SalesOrder:
        if not data.get("order_no"):
            data["order_no"] = await generate_doc_no(db, "SO", SalesOrder, "order_no")
        if not data.get("order_date"):
            data["order_date"] = datetime.now(timezone.utc)
        normalized_items, total = _normalize_sales_order_items(items_data)
        await _apply_customer_product_codes(db, data.get("customer_id"), normalized_items)
        product_ids = {
            item.get("product_id")
            for item in normalized_items
            if item.get("product_id")
        }
        if product_ids:
            blocked = list(
                (
                    await db.scalars(
                        select(Product).where(
                            Product.id.in_(product_ids),
                            Product.status.in_({"frozen", "inactive"}),
                        )
                    )
                ).all()
            )
            if blocked:
                raise BusinessRuleViolation(
                    f"产品已冻结或停用，不能下单: {', '.join(item.sku or item.name for item in blocked)}"
                )
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

    async def update_order_with_items(
        self,
        db: AsyncSession,
        order: SalesOrder,
        data: dict,
        actor: str | int | None = None,
    ) -> SalesOrder:
        old_status = order.status
        new_status = data.get("status")
        if new_status and new_status != old_status:
            await transition_status(
                db,
                order,
                new_status,
                guard=assert_can_transition_sales_order,
                aggregate_type="SalesOrder",
                actor=actor,
            )
        items_data = data.pop("items", None)
        for k, v in data.items():
            if v is not None and k != "items":
                setattr(order, k, v)
        if items_data is not None:
            normalized_items, total = _normalize_sales_order_items(items_data)
            await _apply_customer_product_codes(
                db, data.get("customer_id", order.customer_id), normalized_items
            )
            product_ids = {
                item.get("product_id")
                for item in normalized_items
                if item.get("product_id")
            }
            if product_ids:
                blocked = list(
                    (
                        await db.scalars(
                            select(Product).where(
                                Product.id.in_(product_ids),
                                Product.status.in_({"frozen", "inactive"}),
                            )
                        )
                    ).all()
                )
                if blocked:
                    raise BusinessRuleViolation(
                        f"产品已冻结或停用，不能下单: {', '.join(item.sku or item.name for item in blocked)}"
                    )
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

        # Trigger customer state machine transition on completion
        if new_status == "completed" and old_status != "completed":
            from app.services.customer_state_service import on_first_order_completed

            await on_first_order_completed(db, order.customer_id)

        return order

    async def soft_delete_order(self, db: AsyncSession, order: SalesOrder) -> None:
        order.deleted_at = datetime.now(timezone.utc)
        await db.commit()


# ── Module-level proxies (back-compat) ────────────────────────────────


async def list_sales_orders(
    db: AsyncSession,
    *,
    page: int = 1,
    page_size: int = 20,
    customer_id: int | None = None,
    status: str | None = None,
    q: str | None = None,
    sort_by: str = "id",
    sort_order: str = "desc",
) -> dict:
    return await sales_order_service.list_orders(
        db,
        page=page,
        page_size=page_size,
        customer_id=customer_id,
        status=status,
        q=q,
        sort_by=sort_by,
        sort_order=sort_order,
    )


async def get_sales_order(db: AsyncSession, order_id: int) -> SalesOrder | None:
    return await sales_order_service.get_order(db, order_id)


async def create_sales_order(
    db: AsyncSession, data: dict, items_data: list[dict] | None = None
) -> SalesOrder:
    return await sales_order_service.create_order(db, data, items_data)


async def update_sales_order(
    db: AsyncSession,
    order: SalesOrder,
    data: dict,
    actor: str | int | None = None,
) -> SalesOrder:
    return await sales_order_service.update_order_with_items(db, order, data, actor)


async def delete_sales_order(db: AsyncSession, order: SalesOrder) -> None:
    await sales_order_service.soft_delete_order(db, order)


sales_order_service = SalesOrderService()
