"""Sales CRUD service — opportunities, quotations, orders, delivery notes."""

import json
import logging
from datetime import datetime, timedelta, timezone

import httpx
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.config import settings
from app.models.customer import Customer
from app.models.product import Product, Warehouse
from app.models.sales import (
    DeliveryNote,
    DeliveryNoteItem,
    Inquiry,
    Opportunity,
    Quotation,
    QuotationItem,
    SalesOrder,
    SalesOrderItem,
)
from app.models.finance import SalesTarget
from app.services.docno import generate_doc_no
from app.services.inventory_service import deduct_for_delivery, lock_for_sales_order

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


def _normalize_quotation_items(items_data: list[dict] | None) -> tuple[list[dict], float]:
    items: list[dict] = []
    total = 0.0
    for raw in items_data or []:
        item = raw.model_dump() if hasattr(raw, "model_dump") else dict(raw)
        qty = int(item.get("quantity") or 1)
        unit_price = float(item.get("unit_price") or 0)
        total_price = item.get("total_price")
        line_total = float(total_price) if total_price is not None else qty * unit_price
        cost_price = float(item.get("cost_price") or 0)
        untaxed_cost = qty * cost_price
        taxed_cost = untaxed_cost * (1 + QUOTE_COST_TAX_RATE)
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


# ============================================================
# Opportunity CRUD
# ============================================================

async def list_opportunities(
    db: AsyncSession, *, page: int = 1, page_size: int = 20,
    customer_id: int | None = None, status: str | None = None,
    stage: str | None = None, assigned_to: str | None = None,
    q: str | None = None,
    sort_by: str = "id", sort_order: str = "desc",
) -> dict:
    base = select(Opportunity).where(Opportunity.deleted_at.is_(None))
    cnt = select(func.count(Opportunity.id)).where(Opportunity.deleted_at.is_(None))

    if customer_id:
        base = base.where(Opportunity.customer_id == customer_id)
        cnt = cnt.where(Opportunity.customer_id == customer_id)
    if status:
        base = base.where(Opportunity.status == status)
        cnt = cnt.where(Opportunity.status == status)
    if stage:
        base = base.where(Opportunity.stage == stage)
        cnt = cnt.where(Opportunity.stage == stage)
    if assigned_to:
        base = base.where(Opportunity.assigned_to == assigned_to)
        cnt = cnt.where(Opportunity.assigned_to == assigned_to)
    if q and q.strip():
        pattern = f"%{q.strip()}%"
        search_filter = or_(
            Opportunity.title.ilike(pattern),
            Opportunity.description.ilike(pattern),
            Opportunity.notes.ilike(pattern),
            Opportunity.source.ilike(pattern),
            Opportunity.assigned_to.ilike(pattern),
            Opportunity.customer_id.in_(_customer_search_ids(q.strip())),
        )
        base = base.where(search_filter)
        cnt = cnt.where(search_filter)

    total = (await db.execute(cnt)).scalar() or 0

    allowed_sorts = {"id", "title", "amount", "status", "stage", "win_probability", "expected_close_date", "created_at", "updated_at"}
    sort_by = sort_by if sort_by in allowed_sorts else "id"
    sort_col = getattr(Opportunity, sort_by, Opportunity.id)
    base = base.order_by(sort_col.desc() if sort_order == "desc" else sort_col.asc())
    rows = (await db.execute(base.offset((page - 1) * page_size).limit(page_size))).scalars().all()

    return {"list": rows, "total": total, "page": page, "page_size": page_size}


async def get_opportunity(db: AsyncSession, opp_id: int) -> Opportunity | None:
    result = await db.execute(
        select(Opportunity).where(Opportunity.id == opp_id, Opportunity.deleted_at.is_(None))
    )
    return result.scalar_one_or_none()


async def create_opportunity(db: AsyncSession, data: dict) -> Opportunity:
    opp = Opportunity(**data)
    db.add(opp)
    await db.commit()
    await db.refresh(opp)
    return opp


async def update_opportunity(db: AsyncSession, opp: Opportunity, data: dict) -> Opportunity:
    for k, v in data.items():
        if v is not None:
            setattr(opp, k, v)
    await db.commit()
    await db.refresh(opp)
    return opp


async def delete_opportunity(db: AsyncSession, opp: Opportunity) -> None:
    opp.deleted_at = datetime.now(timezone.utc)
    await db.commit()


# ============================================================
# Quotation CRUD
# ============================================================

async def list_quotations(
    db: AsyncSession, *, page: int = 1, page_size: int = 20,
    customer_id: int | None = None, status: str | None = None,
    q: str | None = None,
    sort_by: str = "id", sort_order: str = "desc",
) -> dict:
    base = select(Quotation).where(Quotation.deleted_at.is_(None))
    cnt = select(func.count(Quotation.id)).where(Quotation.deleted_at.is_(None))

    if customer_id:
        base = base.where(Quotation.customer_id == customer_id)
        cnt = cnt.where(Quotation.customer_id == customer_id)
    if status:
        base = base.where(Quotation.status == status)
        cnt = cnt.where(Quotation.status == status)
    if q and q.strip():
        q = q.strip()
        pattern = f"%{q}%"
        item_ids = _sales_item_ids(QuotationItem, QuotationItem.quotation_id, QuotationItem.product_name, q)
        search_filter = or_(
            Quotation.quotation_no.ilike(pattern),
            Quotation.title.ilike(pattern),
            Quotation.notes.ilike(pattern),
            Quotation.customer_id.in_(_customer_search_ids(q)),
            Quotation.id.in_(item_ids),
        )
        base = base.where(search_filter)
        cnt = cnt.where(search_filter)

    total = (await db.execute(cnt)).scalar() or 0

    allowed_sorts = {"id", "quotation_no", "total_amount", "status", "created_at", "updated_at"}
    sort_by = sort_by if sort_by in allowed_sorts else "id"
    sort_col = getattr(Quotation, sort_by, Quotation.id)
    base = base.order_by(sort_col.desc() if sort_order == "desc" else sort_col.asc())
    rows = (await db.execute(base.offset((page - 1) * page_size).limit(page_size))).scalars().all()

    return {"list": rows, "total": total, "page": page, "page_size": page_size}


async def get_quotation(db: AsyncSession, quote_id: int) -> Quotation | None:
    result = await db.execute(
        select(Quotation).where(Quotation.id == quote_id, Quotation.deleted_at.is_(None))
    )
    return result.scalar_one_or_none()


async def create_quotation(db: AsyncSession, data: dict, items_data: list[dict] | None = None) -> Quotation:
    if not data.get("quotation_no"):
        data["quotation_no"] = await generate_doc_no(db, "QT", Quotation, "quotation_no")
    normalized_items, total = _normalize_quotation_items(items_data)
    if normalized_items:
        data["total_amount"] = total
    quote = Quotation(**{k: v for k, v in data.items() if k != "items"})
    db.add(quote)
    await db.flush()

    if normalized_items:
        for item in normalized_items:
            qi = QuotationItem(quotation_id=quote.id, **item)
            db.add(qi)

    await db.commit()
    await db.refresh(quote)
    return quote


async def update_quotation(db: AsyncSession, quote: Quotation, data: dict) -> Quotation:
    items_data = data.pop("items", None)
    for k, v in data.items():
        if v is not None and k != "items":
            setattr(quote, k, v)
    if items_data is not None:
        # Soft-delete existing items, then insert replacements (one transaction)
        for item in quote.items:
            item.deleted_at = datetime.now(timezone.utc)
        await db.flush()
        normalized_items, total = _normalize_quotation_items(items_data)
        for item_data in normalized_items:
            qi = QuotationItem(quotation_id=quote.id, **item_data)
            db.add(qi)
        quote.total_amount = total
    await db.commit()
    await db.refresh(quote)
    return quote


async def get_quotation_stats(db: AsyncSession) -> dict:
    now = datetime.now(timezone.utc)
    soon = now + timedelta(days=7)

    rows = (await db.execute(
        select(Quotation.status, func.count(Quotation.id), func.coalesce(func.sum(Quotation.total_amount), 0))
        .where(Quotation.deleted_at.is_(None))
        .group_by(Quotation.status)
    )).all()

    by_status = {
        status or "unknown": {"count": int(count or 0), "amount": float(amount or 0)}
        for status, count, amount in rows
    }
    total = sum(item["count"] for item in by_status.values())
    total_amount = sum(item["amount"] for item in by_status.values())

    active_statuses = ["draft", "sent"]
    expiring_soon = (await db.execute(
        select(func.count(Quotation.id)).where(
            Quotation.deleted_at.is_(None),
            Quotation.status.in_(active_statuses),
            Quotation.valid_until.is_not(None),
            Quotation.valid_until >= now,
            Quotation.valid_until <= soon,
        )
    )).scalar() or 0
    expired = (await db.execute(
        select(func.count(Quotation.id)).where(
            Quotation.deleted_at.is_(None),
            Quotation.status.in_(active_statuses),
            Quotation.valid_until.is_not(None),
            Quotation.valid_until < now,
        )
    )).scalar() or 0
    converted = (await db.execute(
        select(func.count(func.distinct(SalesOrder.quotation_id))).where(
            SalesOrder.deleted_at.is_(None),
            SalesOrder.quotation_id.is_not(None),
        )
    )).scalar() or 0

    return {
        "total": total,
        "total_amount": float(total_amount),
        "draft": by_status.get("draft", {}).get("count", 0),
        "sent": by_status.get("sent", {}).get("count", 0),
        "won": by_status.get("won", {}).get("count", 0),
        "lost": by_status.get("lost", {}).get("count", 0),
        "won_amount": by_status.get("won", {}).get("amount", 0),
        "expiring_soon": int(expiring_soon),
        "expired": int(expired),
        "converted": int(converted),
        "quote_to_order_rate": round((int(converted) / total * 100), 1) if total else 0,
        "by_status": by_status,
    }


async def duplicate_quotation(db: AsyncSession, quote: Quotation) -> Quotation:
    quotation_no = await generate_doc_no(db, "QT", Quotation, "quotation_no")
    new_quote = Quotation(
        quotation_no=quotation_no,
        customer_id=quote.customer_id,
        opportunity_id=quote.opportunity_id,
        title=f"{quote.title or quote.quotation_no or f'报价单 #{quote.id}'} - 复制",
        total_amount=quote.total_amount,
        status="draft",
        valid_until=quote.valid_until,
        notes=quote.notes,
    )
    db.add(new_quote)
    await db.flush()
    for item in quote.items:
        if item.deleted_at is not None:
            continue
        db.add(QuotationItem(
            quotation_id=new_quote.id,
            product_id=item.product_id,
            product_name=item.product_name,
            quantity=item.quantity,
            unit_price=item.unit_price,
            total_price=item.total_price,
            cost_price=item.cost_price,
            untaxed_cost=item.untaxed_cost,
            taxed_cost=item.taxed_cost,
            sales_profit=item.sales_profit,
            notes=item.notes,
        ))
    await db.commit()
    await db.refresh(new_quote)
    return new_quote


async def update_quotation_status(db: AsyncSession, quote: Quotation, status: str) -> Quotation:
    allowed = {"draft", "sent", "won", "lost"}
    if status not in allowed:
        raise ValueError("无效报价状态")
    quote.status = status
    await db.commit()
    await db.refresh(quote)
    return quote


async def delete_quotation(db: AsyncSession, quote: Quotation) -> None:
    quote.deleted_at = datetime.now(timezone.utc)
    await db.commit()


async def send_quotation(db: AsyncSession, quote: Quotation) -> Quotation:
    """Mark quotation as sent and trigger WeCom notification."""
    quote.status = "sent"
    await db.commit()
    await db.refresh(quote)
    # Send WeCom notification in background
    try:
        await _notify_quotation_sent(quote)
    except Exception as e:
        logger.warning(f"[Quotation] Failed to send WeCom notification: {e}")
    return quote


async def _notify_quotation_sent(quote: Quotation) -> None:
    """Send WeCom webhook notification for a sent quotation."""
    webhook_url = getattr(settings, "WECOM_WEBHOOK_URL", None)
    if not webhook_url:
        logger.warning("[Quotation] WECOM_WEBHOOK_URL not configured, skipping notification")
        return

    content_lines = [
        "📋 **报价单已发送**",
        "",
        f"**报价单号**：{quote.quotation_no or f'#{quote.id}'}",
        f"**客户ID**：{quote.customer_id}",
        f"**总金额**：¥{float(quote.total_amount or 0):,.2f}",
        "**状态**：已发送",
        f"**有效期**：{quote.valid_until.strftime('%Y-%m-%d') if quote.valid_until else '未设置'}",
        "",
        f"🔗 查看详情：/sales/quotations/{quote.id}",
        f"⏰ 时间：{datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')}",
    ]

    payload = {
        "msgtype": "markdown",
        "markdown": {
            "content": "\n".join(content_lines),
        },
    }

    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.post(webhook_url, json=payload)
        if resp.status_code == 200:
            logger.info(f"[Quotation] WeCom notification sent for quote {quote.id}")
        else:
            logger.warning(f"[Quotation] WeCom notification failed: {resp.status_code} {resp.text}")


async def create_quotation_from_inquiry(
    db: AsyncSession, *, inquiry_id: int,
    items: list[dict],
    customer_id: int | None = None,
    title: str | None = None,
    valid_until: datetime | None = None,
    notes: str | None = None,
) -> Quotation:
    """Create a new quotation from an inquiry record, pre-filled with matched products."""
    result = await db.execute(select(Inquiry).where(Inquiry.id == inquiry_id))
    inquiry = result.scalar_one_or_none()
    if not inquiry:
        raise ValueError(f"Inquiry {inquiry_id} not found")

    cid = customer_id or inquiry.customer_id
    if not cid:
        cid = 244  # 公众客户 fallback
    quotation_no = await generate_doc_no(db, "QT", Quotation, "quotation_no")

    quote = Quotation(
        quotation_no=quotation_no,
        customer_id=cid,
        title=title or f"询价单 #{inquiry_id} 报价",
        total_amount=0,
        status="draft",
        valid_until=valid_until or (datetime.now(timezone.utc) + timedelta(days=30)),
        notes=notes,
    )
    db.add(quote)
    await db.flush()

    total = 0.0
    # Auto-populate items from inquiry.matched_products if not provided
    if items:
        normalized_items, total = _normalize_quotation_items(items)
        for item in normalized_items:
            db.add(QuotationItem(quotation_id=quote.id, **item))
    else:
        try:
            matched = json.loads(inquiry.matched_products) if inquiry.matched_products else []
        except Exception:
            matched = []
        for mp in matched:
            pid = mp.get("id") or mp.get("product_id")
            if not pid:
                # Resolve by SKU
                sku = mp.get("sku")
                if sku:
                    pr = (await db.execute(
                        select(Product.id).where(Product.sku == sku).limit(1)
                    )).scalar_one_or_none()
                    pid = pr
            if not pid:
                continue
            qty = mp.get("quantity") or mp.get("stock_qty") or 1
            up = mp.get("unit_price") or 0
            tp = qty * up
            total += tp
            qi = QuotationItem(
                quotation_id=quote.id,
                product_id=pid,
                product_name=mp.get("name") or mp.get("product_name") or "",
                quantity=qty,
                unit_price=up,
                total_price=tp,
            )
            db.add(qi)

    quote.total_amount = total
    await db.commit()
    await db.refresh(quote)
    return quote


# ============================================================
# Sales Order CRUD
# ============================================================

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
    order = SalesOrder(**{k: v for k, v in data.items() if k != "items"})
    db.add(order)
    await db.flush()

    if items_data:
        for item in items_data:
            soi = SalesOrderItem(order_id=order.id, **item)
            db.add(soi)

    await db.commit()
    await db.refresh(order)
    return order


async def update_sales_order(db: AsyncSession, order: SalesOrder, data: dict) -> SalesOrder:
    old_status = order.status
    for k, v in data.items():
        if v is not None and k != "items":
            setattr(order, k, v)
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

async def list_delivery_notes(
    db: AsyncSession, *, page: int = 1, page_size: int = 20,
    customer_id: int | None = None, status: str | None = None,
    sales_order_id: int | None = None,
    q: str | None = None,
    sort_by: str = "id", sort_order: str = "desc",
) -> dict:
    base = select(DeliveryNote).where(DeliveryNote.deleted_at.is_(None))
    cnt = select(func.count(DeliveryNote.id)).where(DeliveryNote.deleted_at.is_(None))

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
        item_ids = _sales_item_ids(DeliveryNoteItem, DeliveryNoteItem.delivery_note_id, DeliveryNoteItem.product_name, q)
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

    allowed_sorts = {"id", "delivery_no", "status", "delivery_date", "received_date", "created_at", "updated_at"}
    sort_by = sort_by if sort_by in allowed_sorts else "id"
    sort_col = getattr(DeliveryNote, sort_by, DeliveryNote.id)
    base = base.order_by(sort_col.desc() if sort_order == "desc" else sort_col.asc())
    rows = (await db.execute(base.offset((page - 1) * page_size).limit(page_size))).scalars().all()

    return {"list": rows, "total": total, "page": page, "page_size": page_size}


async def get_delivery_note(db: AsyncSession, note_id: int) -> DeliveryNote | None:
    result = await db.execute(
        select(DeliveryNote).where(DeliveryNote.id == note_id, DeliveryNote.deleted_at.is_(None))
    )
    return result.scalar_one_or_none()


async def _apply_sales_order_to_delivery_data(
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
                "quantity": item.quantity,
            }
            for item in order.items
        ]
    return items_data


async def create_delivery_note(db: AsyncSession, data: dict, items_data: list[dict] | None = None) -> DeliveryNote:
    items_data = await _apply_sales_order_to_delivery_data(db, data, items_data)
    if not data.get("delivery_no"):
        data["delivery_no"] = await generate_doc_no(db, "DN", DeliveryNote, "delivery_no")
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


async def update_delivery_note(db: AsyncSession, note: DeliveryNote, data: dict) -> DeliveryNote:
    old_status = note.status
    await _apply_sales_order_to_delivery_data(db, data)
    for k, v in data.items():
        if v is not None and k != "items":
            setattr(note, k, v)
    await db.commit()
    await db.refresh(note)

    # Auto-deduct inventory when status changes to shipped/completed
    new_status = data.get("status")
    if new_status and new_status in ("shipped", "completed") and old_status != new_status:
        await _auto_deduct_delivery(db, note)

    return note


async def _auto_deduct_delivery(db: AsyncSession, note: DeliveryNote) -> None:
    """Auto-deduct inventory for each item when a delivery note is shipped/completed."""
    result = await db.execute(select(Warehouse.id).limit(1))
    warehouse_id = result.scalar() or 1

    for item in note.items:
        if item.product_id and item.quantity > 0:
            try:
                await deduct_for_delivery(db, item.product_id, warehouse_id, item.quantity, note.id)
            except Exception as e:
                logger.error("Auto-deduct failed DN#%s product#%s: %s", note.id, item.product_id, e)


async def _auto_lock_sales_order(db: AsyncSession, order: SalesOrder) -> None:
    """Auto-lock inventory for each item when a sales order is confirmed."""
    result = await db.execute(select(Warehouse.id).limit(1))
    warehouse_id = result.scalar() or 1

    for item in order.items:
        if item.product_id and item.quantity > 0:
            try:
                await lock_for_sales_order(db, item.product_id, warehouse_id, item.quantity, order.id)
            except Exception as e:
                logger.error("Auto-lock failed SO#%s product#%s: %s", order.id, item.product_id, e)


async def delete_delivery_note(db: AsyncSession, note: DeliveryNote) -> None:
    note.deleted_at = datetime.now(timezone.utc)
    await db.commit()


# ============================================================
# Flow Conversions
# ============================================================

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

async def list_targets(db: AsyncSession, page: int = 1, page_size: int = 20, status: str | None = None) -> dict:
    offset = (page - 1) * page_size
    conditions = [SalesTarget.deleted_at.is_(None)]
    if status:
        conditions.append(SalesTarget.status == status)
    total = (await db.execute(select(func.count()).where(*conditions))).scalar() or 0
    rows = (await db.execute(
        select(SalesTarget).where(*conditions).order_by(SalesTarget.id.desc()).offset(offset).limit(page_size)
    )).scalars().all()
    return {"list": rows, "total": total, "page": page, "page_size": page_size}


async def get_target(db: AsyncSession, target_id: int) -> SalesTarget | None:
    result = await db.execute(
        select(SalesTarget).where(SalesTarget.id == target_id, SalesTarget.deleted_at.is_(None))
    )
    return result.scalar_one_or_none()


async def create_target(db: AsyncSession, data: dict) -> SalesTarget:
    data = {k: v for k, v in data.items() if v is not None}
    target = SalesTarget(**data)
    db.add(target)
    await db.commit()
    await db.refresh(target)
    return target


async def update_target(db: AsyncSession, target: SalesTarget, data: dict) -> SalesTarget:
    for k, v in data.items():
        setattr(target, k, v)
    await db.commit()
    await db.refresh(target)
    return target


async def delete_target(db: AsyncSession, target: SalesTarget):
    target.deleted_at = datetime.now(timezone.utc)
    await db.commit()


async def get_target_summary(db: AsyncSession) -> list:
    rows = (await db.execute(
        select(SalesTarget).where(SalesTarget.deleted_at.is_(None))
    )).scalars().all()
    return [{"id": r.id, "period": r.period, "target_amount": r.target_amount, "target_orders": r.target_orders, "user_id": r.user_id} for r in rows]


async def get_target_stats(db: AsyncSession) -> dict:
    rows = (await db.execute(
        select(SalesTarget).where(SalesTarget.deleted_at.is_(None))
    )).scalars().all()
    total_target = sum(float(r.target_amount or 0) for r in rows)
    total_actual = sum(float(r.actual_amount or 0) for r in rows)
    achievement_pct = round(total_actual / total_target * 100, 1) if total_target else 0
    completed = sum(1 for r in rows if r.status == "completed")
    return {
        "total_target": total_target,
        "total_actual": total_actual,
        "achievement_pct": achievement_pct,
        "count": len(rows),
        "completed": completed,
    }
