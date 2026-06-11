from __future__ import annotations

import json
import logging
from datetime import datetime, timedelta, timezone

import httpx
from app.config import settings
from app.domain.states import assert_can_transition_quotation
from app.models.product import Product
from app.models.sales import Inquiry, Quotation, QuotationItem, SalesOrder
from app.services.docno import generate_doc_no
from app.services.sales_service._helpers import (
    _customer_search_ids,
    _normalize_quotation_items,
    _sales_item_ids,
)
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


async def list_quotations(
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
        item_ids = _sales_item_ids(
            QuotationItem, QuotationItem.quotation_id, QuotationItem.product_name, q
        )
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

    allowed_sorts = {
        "id",
        "quotation_no",
        "total_amount",
        "status",
        "created_at",
        "updated_at",
    }
    sort_by = sort_by if sort_by in allowed_sorts else "id"
    sort_col = getattr(Quotation, sort_by, Quotation.id)
    base = base.order_by(sort_col.desc() if sort_order == "desc" else sort_col.asc())
    rows = (
        (await db.execute(base.offset((page - 1) * page_size).limit(page_size)))
        .scalars()
        .all()
    )

    return {"list": rows, "total": total, "page": page, "page_size": page_size}


async def get_quotation(db: AsyncSession, quote_id: int) -> Quotation | None:
    result = await db.execute(
        select(Quotation).where(
            Quotation.id == quote_id, Quotation.deleted_at.is_(None)
        )
    )
    return result.scalar_one_or_none()


async def create_quotation(
    db: AsyncSession, data: dict, items_data: list[dict] | None = None
) -> Quotation:
    if not data.get("quotation_no"):
        data["quotation_no"] = await generate_doc_no(
            db, "QT", Quotation, "quotation_no"
        )
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
    if "status" in data and data["status"] != quote.status:
        assert_can_transition_quotation(quote.status, data["status"])
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
    return quote


async def get_quotation_stats(db: AsyncSession) -> dict:
    now = datetime.now(timezone.utc)
    soon = now + timedelta(days=7)

    rows = (
        await db.execute(
            select(
                Quotation.status,
                func.count(Quotation.id),
                func.coalesce(func.sum(Quotation.total_amount), 0),
            )
            .where(Quotation.deleted_at.is_(None))
            .group_by(Quotation.status)
        )
    ).all()

    by_status = {
        status or "unknown": {"count": int(count or 0), "amount": float(amount or 0)}
        for status, count, amount in rows
    }
    total = sum(item["count"] for item in by_status.values())
    total_amount = sum(item["amount"] for item in by_status.values())

    active_statuses = ["draft", "sent"]
    expiring_soon = (
        await db.execute(
            select(func.count(Quotation.id)).where(
                Quotation.deleted_at.is_(None),
                Quotation.status.in_(active_statuses),
                Quotation.valid_until.is_not(None),
                Quotation.valid_until >= now,
                Quotation.valid_until <= soon,
            )
        )
    ).scalar() or 0
    expired = (
        await db.execute(
            select(func.count(Quotation.id)).where(
                Quotation.deleted_at.is_(None),
                Quotation.status.in_(active_statuses),
                Quotation.valid_until.is_not(None),
                Quotation.valid_until < now,
            )
        )
    ).scalar() or 0
    converted = (
        await db.execute(
            select(func.count(func.distinct(SalesOrder.quotation_id))).where(
                SalesOrder.deleted_at.is_(None),
                SalesOrder.quotation_id.is_not(None),
            )
        )
    ).scalar() or 0

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
        db.add(
            QuotationItem(
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
            )
        )
    await db.commit()
    await db.refresh(new_quote)
    return new_quote


async def update_quotation_status(
    db: AsyncSession, quote: Quotation, status: str
) -> Quotation:
    assert_can_transition_quotation(quote.status, status)
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
        logger.warning(
            "[Quotation] WECOM_WEBHOOK_URL not configured, skipping notification"
        )
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
            logger.warning(
                f"[Quotation] WeCom notification failed: {resp.status_code} {resp.text}"
            )


async def create_quotation_from_inquiry(
    db: AsyncSession,
    *,
    inquiry_id: int,
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
            matched = (
                json.loads(inquiry.matched_products) if inquiry.matched_products else []
            )
        except Exception:
            matched = []
        for mp in matched:
            pid = mp.get("id") or mp.get("product_id")
            if not pid:
                # Resolve by SKU
                sku = mp.get("sku")
                if sku:
                    pr = (
                        await db.execute(
                            select(Product.id).where(Product.sku == sku).limit(1)
                        )
                    ).scalar_one_or_none()
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
