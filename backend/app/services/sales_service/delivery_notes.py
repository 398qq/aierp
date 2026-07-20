"""DeliveryNote CRUD + inventory hooks (auto-deduct, auto-lock)."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.domain.shared.errors import InsufficientStockError
from app.domain.states import assert_can_transition_delivery
from app.models.finance import PaymentRecord
from app.models.product import Warehouse
from app.models.sales import DeliveryNote, DeliveryNoteItem, SalesOrder, SalesOrderItem
from app.services.base_crud import BaseCRUDService
from app.services.docno import generate_doc_no
from app.services.inventory_service import deduct_for_delivery, lock_for_sales_order
from app.services.sales_service._helpers import (
    _apply_customer_product_codes,
    _customer_search_ids,
    _sales_item_ids,
)

logger = logging.getLogger(__name__)


# ── Service ────────────────────────────────────────────────────────────


class DeliveryNoteService(BaseCRUDService):
    """Delivery note service.

    Stage 1: business methods are class methods on this service. Module-level
    functions below remain as thin proxies for back-compat.
    """

    model = DeliveryNote

    # ── read paths ────────────────────────────────────────────────────

    async def list_delivery_notes(
        self,
        db: AsyncSession,
        *,
        page: int = 1,
        page_size: int = 20,
        customer_id: int | None = None,
        status: str | None = None,
        sales_order_id: int | None = None,
        q: str | None = None,
        sort_by: str = "id",
        sort_order: str = "desc",
    ) -> dict:
        base = select(DeliveryNote).where(DeliveryNote.deleted_at.is_(None))
        cnt = select(func.count(DeliveryNote.id)).where(
            DeliveryNote.deleted_at.is_(None)
        )

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
            item_ids = _sales_item_ids(
                DeliveryNoteItem,
                DeliveryNoteItem.delivery_note_id,
                DeliveryNoteItem.product_name,
                q,
            )
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

        allowed_sorts = {
            "id",
            "delivery_no",
            "status",
            "delivery_date",
            "received_date",
            "created_at",
            "updated_at",
        }
        sort_by = sort_by if sort_by in allowed_sorts else "id"
        sort_col = getattr(DeliveryNote, sort_by, DeliveryNote.id)
        base = base.order_by(
            sort_col.desc() if sort_order == "desc" else sort_col.asc()
        )
        rows = (
            (await db.execute(base.offset((page - 1) * page_size).limit(page_size)))
            .scalars()
            .all()
        )

        return {"list": rows, "total": total, "page": page, "page_size": page_size}

    async def get_delivery_note(
        self, db: AsyncSession, note_id: int
    ) -> DeliveryNote | None:
        result = await db.execute(
            select(DeliveryNote).where(
                DeliveryNote.id == note_id, DeliveryNote.deleted_at.is_(None)
            )
        )
        return result.scalar_one_or_none()

    # ── write paths ───────────────────────────────────────────────────

    async def _apply_sales_order_to_delivery_data(
        self,
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
                    "customer_part_no": item.customer_part_no,
                    "customer_product_name": item.customer_product_name,
                    "quantity": item.quantity,
                }
                for item in order.items
            ]
        return items_data

    async def create_delivery_note(
        self,
        db: AsyncSession,
        data: dict,
        items_data: list[dict] | None = None,
    ) -> DeliveryNote:
        items_data = await self._apply_sales_order_to_delivery_data(
            db, data, items_data
        )
        if items_data:
            await _apply_customer_product_codes(
                db, data.get("customer_id"), items_data
            )
        if not data.get("delivery_no"):
            data["delivery_no"] = await generate_doc_no(
                db, "DN", DeliveryNote, "delivery_no"
            )
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

    async def update_delivery_note(
        self, db: AsyncSession, note: DeliveryNote, data: dict
    ) -> DeliveryNote:
        old_status = note.status
        new_status = data.get("status")
        if new_status and new_status != old_status:
            assert_can_transition_delivery(old_status, new_status)
        items_data = data.pop("items", None)
        items_data = await self._apply_sales_order_to_delivery_data(
            db, data, items_data
        )
        for k, v in data.items():
            if v is not None and k != "items":
                setattr(note, k, v)
        if items_data is not None:
            await _apply_customer_product_codes(
                db, data.get("customer_id", note.customer_id), items_data
            )
            for item in note.items:
                item.deleted_at = datetime.now(timezone.utc)
            await db.flush()
            for item in items_data:
                db.add(DeliveryNoteItem(delivery_note_id=note.id, **item))
        await db.commit()
        await db.refresh(note)

        if (
            new_status
            and new_status in ("shipped", "completed", "delivered")
            and old_status != new_status
        ):
            await self._auto_deduct_delivery(db, note)
            await self._sync_sales_order_fulfillment_status(db, note.sales_order_id)
            await db.commit()

        return note

    async def _sync_sales_order_fulfillment_status(
        self, db: AsyncSession, order_id: int
    ) -> None:
        """Derive order status from actual downstream delivery documents."""
        order = await db.get(SalesOrder, order_id)
        if order is None:
            return
        ordered_qty = int(
            await db.scalar(
                select(func.coalesce(func.sum(SalesOrderItem.quantity), 0)).where(
                    SalesOrderItem.order_id == order_id,
                    SalesOrderItem.deleted_at.is_(None),
                )
            )
            or 0
        )
        rows = (
            await db.execute(
                select(DeliveryNote.status, func.coalesce(func.sum(DeliveryNoteItem.quantity), 0))
                .join(DeliveryNoteItem, DeliveryNoteItem.delivery_note_id == DeliveryNote.id)
                .where(
                    DeliveryNote.sales_order_id == order_id,
                    DeliveryNote.deleted_at.is_(None),
                    DeliveryNoteItem.deleted_at.is_(None),
                    DeliveryNote.status.in_(["shipped", "delivered", "completed"]),
                )
                .group_by(DeliveryNote.status)
            )
        ).all()
        delivered_qty = sum(int(row[1] or 0) for row in rows)
        statuses = {str(row[0]) for row in rows}
        if ordered_qty and delivered_qty >= ordered_qty and statuses <= {"delivered", "completed"}:
            order.status = "delivered"
        elif delivered_qty > 0:
            order.status = "shipped"

    async def soft_delete_delivery_note(
        self, db: AsyncSession, note: DeliveryNote
    ) -> None:
        note.deleted_at = datetime.now(timezone.utc)
        await db.commit()

    async def mark_delivery_note_paid(
        self,
        db: AsyncSession,
        note: DeliveryNote,
        amount: float | None = None,
        payment_method: str = "bank",
        payment_date: datetime | None = None,
        notes: str | None = None,
    ) -> dict:
        """Record payment for a delivery note. Idempotent on duplicate calls."""
        existing = (
            await db.execute(
                select(PaymentRecord).where(
                    PaymentRecord.delivery_note_id == note.id,
                    PaymentRecord.deleted_at.is_(None),
                )
            )
        ).scalar_one_or_none()
        if existing is not None:
            return {"payment": existing, "created": False}

        if amount is None:
            from app.models.sales import SalesOrder

            order = (
                await db.execute(
                    select(SalesOrder).where(SalesOrder.id == note.sales_order_id)
                )
            ).scalar_one_or_none()
            if order is not None and order.total_amount:
                amount = float(order.total_amount)
            else:
                amount = sum((item.quantity or 0) for item in note.items) * 1.0

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

        note.received_date = paid_at
        if note.status == "shipped":
            note.status = "delivered"

        await db.commit()
        await db.refresh(pay)
        return {"payment": pay, "created": True}

    # ── private inventory hooks ───────────────────────────────────────

    async def _auto_deduct_delivery(self, db: AsyncSession, note: DeliveryNote) -> None:
        """Auto-deduct inventory per item on shipped/completed."""
        result = await db.execute(select(Warehouse.id).limit(1))
        warehouse_id = result.scalar() or 1

        for item in note.items:
            if item.product_id and item.quantity > 0:
                try:
                    await deduct_for_delivery(
                        db, item.product_id, warehouse_id, item.quantity, note.id
                    )
                except InsufficientStockError:
                    raise
                except Exception as e:
                    logger.error(
                        "Auto-deduct failed DN#%s product#%s: %s",
                        note.id,
                        item.product_id,
                        e,
                    )

    async def _auto_lock_sales_order(self, db: AsyncSession, order: SalesOrder) -> None:
        """Auto-lock inventory per item on sales order confirmed."""
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
                        order.id,
                        item.product_id,
                        e.context.get("requested"),
                        e.context.get("available"),
                    )
                except Exception as e:
                    logger.error(
                        "Auto-lock failed SO#%s product#%s: %s",
                        order.id,
                        item.product_id,
                        e,
                    )

        if total_requested > 0 and total_locked == 0:
            logger.warning(
                "Order SO#%s confirmed but NO stock locked (%s requested)",
                order.id,
                total_requested,
            )


# ── Module-level proxies (back-compat) ────────────────────────────────


async def list_delivery_notes(
    db: AsyncSession,
    *,
    page: int = 1,
    page_size: int = 20,
    customer_id: int | None = None,
    status: str | None = None,
    sales_order_id: int | None = None,
    q: str | None = None,
    sort_by: str = "id",
    sort_order: str = "desc",
) -> dict:
    return await delivery_note_service.list_delivery_notes(
        db,
        page=page,
        page_size=page_size,
        customer_id=customer_id,
        status=status,
        sales_order_id=sales_order_id,
        q=q,
        sort_by=sort_by,
        sort_order=sort_order,
    )


async def get_delivery_note(db: AsyncSession, note_id: int) -> DeliveryNote | None:
    return await delivery_note_service.get_delivery_note(db, note_id)


async def _apply_sales_order_to_delivery_data(
    db: AsyncSession,
    data: dict,
    items_data: list[dict] | None = None,
) -> list[dict] | None:
    return await delivery_note_service._apply_sales_order_to_delivery_data(
        db, data, items_data
    )


async def create_delivery_note(
    db: AsyncSession, data: dict, items_data: list[dict] | None = None
) -> DeliveryNote:
    return await delivery_note_service.create_delivery_note(db, data, items_data)


async def update_delivery_note(
    db: AsyncSession, note: DeliveryNote, data: dict
) -> DeliveryNote:
    return await delivery_note_service.update_delivery_note(db, note, data)


async def _auto_deduct_delivery(db: AsyncSession, note: DeliveryNote) -> None:
    await delivery_note_service._auto_deduct_delivery(db, note)


async def _auto_lock_sales_order(db: AsyncSession, order: SalesOrder) -> None:
    await delivery_note_service._auto_lock_sales_order(db, order)


async def delete_delivery_note(db: AsyncSession, note: DeliveryNote) -> None:
    await delivery_note_service.soft_delete_delivery_note(db, note)


async def mark_delivery_note_paid(
    db: AsyncSession,
    note: DeliveryNote,
    amount: float | None = None,
    payment_method: str = "bank",
    payment_date: datetime | None = None,
    notes: str | None = None,
) -> dict:
    return await delivery_note_service.mark_delivery_note_paid(
        db, note, amount, payment_method, payment_date, notes
    )


delivery_note_service = DeliveryNoteService()
