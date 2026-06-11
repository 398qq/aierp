"""Auto-commission on invoice fully paid (Stage 7 Part 2).

When an invoice reaches `paid` status, automatically create a draft
Commission record for the sales user attached to the order.

Idempotency: skip if a commission already exists for (sales_order_id, sales_user_id).
Commission rate: pulled from sales_targets if set, else default 5%.

Trigger points:
1. payment.update() → _reconcile_invoice_if_fully_paid() → _maybe_create_commission()
2. invoice.update(status="paid") — direct path (e.g. write-off)

Stage 7 simplification: only one Commission per (sales_order, sales_user).
No splitting, no tier logic, no retroactive adjustments. Those are
follow-ups once the basic loop works.
"""

from datetime import datetime
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.finance import Commission, Invoice, SalesTarget
from app.models.sales import SalesOrder
from app.models.customer import Customer
from app.services.docno import generate_doc_no


# Default commission rate when no SalesTarget override is set
DEFAULT_COMMISSION_RATE = 0.05


async def _get_rate_for_user(db: AsyncSession, sales_user_id: int) -> float:
    """Look up commission rate from user's active SalesTarget.

    Falls back to DEFAULT_COMMISSION_RATE (5%) if no active target.
    """
    target = await db.scalar(
        select(SalesTarget)
        .where(
            SalesTarget.user_id == sales_user_id,
            SalesTarget.status == "active",
            SalesTarget.deleted_at.is_(None),
        )
        .order_by(SalesTarget.id.desc())
    )
    if target is None:
        return DEFAULT_COMMISSION_RATE
    rate = getattr(target, "commission_rate", None)
    if rate is None:
        return DEFAULT_COMMISSION_RATE
    return float(rate)


async def _maybe_create_commission(
    db: AsyncSession,
    invoice: Invoice,
) -> Optional[Commission]:
    """Create one draft Commission for the paid invoice's sales order.

    Returns the new Commission, or None if:
    - invoice has no sales_order_id
    - sales order has no customer / no owner
    - a Commission already exists for (sales_order_id, sales_user_id)
    """
    if invoice.sales_order_id is None:
        return None

    # Load order + customer
    order = await db.scalar(
        select(SalesOrder).where(
            SalesOrder.id == invoice.sales_order_id,
            SalesOrder.deleted_at.is_(None),
        )
    )
    if order is None:
        return None

    customer = await db.scalar(select(Customer).where(Customer.id == order.customer_id))
    if customer is None:
        return None

    owner = (
        getattr(customer, "owner", None) or getattr(order, "assigned_to", None) or ""
    )
    if not owner:
        # No sales user to attribute commission to — skip (silent)
        return None

    # sales_user_id: try parse "owner" string as numeric user id.
    # Many customers store owner as a user name; fall back to skip if not numeric.
    try:
        sales_user_id = int(owner)
    except (ValueError, TypeError):
        # owner is a name, not an ID. Cannot create commission without a user link.
        return None

    # Idempotency: skip if commission already exists
    existing = await db.scalar(
        select(Commission).where(
            Commission.sales_order_id == invoice.sales_order_id,
            Commission.sales_user_id == sales_user_id,
            Commission.deleted_at.is_(None),
        )
    )
    if existing is not None:
        return None

    base = float(invoice.amount or 0)
    rate = await _get_rate_for_user(db, sales_user_id)
    commission_amount = round(base * rate, 2)

    period = datetime.utcnow().strftime("%Y-%m")
    commission_no = await generate_doc_no(db, "CM", Commission, "commission_no")

    commission = Commission(
        commission_no=commission_no,
        sales_order_id=invoice.sales_order_id,
        sales_user_id=sales_user_id,
        customer_id=order.customer_id,
        base_amount=base,
        rate=rate,
        commission_amount=commission_amount,
        paid_amount=0,
        status="draft",
        period=period,
        notes=f"Auto-created from invoice {invoice.invoice_no} payment",
    )
    db.add(commission)
    await db.commit()
    await db.refresh(commission)

    # Stage 8 Day 4: Telegram notification (best-effort, never blocks)
    try:
        from app.services.telegram_notifier import send_message

        msg = (
            f"💰 <b>New Commission</b>\n"
            f"Order: {order.order_no or '(no no)'}\n"
            f"Invoice: {invoice.invoice_no}\n"
            f"Customer: {customer.name}\n"
            f"Base: ¥{base:,.2f} × {rate * 100:.1f}% = "
            f"<b>¥{commission_amount:,.2f}</b>\n"
            f"Period: {period} | Status: draft"
        )
        await send_message(msg)
    except Exception:
        # Telegram failure must not abort the commission flow
        pass

    return commission


async def on_invoice_paid(
    db: AsyncSession,
    invoice_id: int,
) -> Optional[Commission]:
    """Public entry point: call when an invoice reaches `paid` status.

    Idempotent. Returns the created Commission, or None.
    """
    invoice = await db.scalar(
        select(Invoice).where(Invoice.id == invoice_id, Invoice.deleted_at.is_(None))
    )
    if invoice is None or invoice.status != "paid":
        return None
    return await _maybe_create_commission(db, invoice)
