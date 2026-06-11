"""Commission status change notifier (Stage 10 Day 2).

Sends Telegram messages on:
- approve: notify the sales user (\"your commission is approved\")
- pay: notify the sales user (\"your commission has been paid\")
- reject: notify the sales user (\"your commission was rejected\")
- cancel: notify the sales user (\"your commission was cancelled\")
- submit: minor event (still draft → pending_approval, not in our interest matrix)

Best-effort: any error is logged, never raised. The commission flow must
not break because of a notification hiccup.
"""

import logging
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


# Emoji + label per transition. Don't notify on submit (low signal).
_STATUS_MESSAGES = {
    "approved": (
        "✅",
        "Approved",
        "Your commission has been approved and is awaiting payment.",
    ),
    "paid": (
        "💸",
        "Paid",
        "Your commission has been paid. Funds should be in your account.",
    ),
    "rejected": (
        "❌",
        "Rejected",
        "Your commission was rejected. Check the notes for details.",
    ),
    "cancelled": (
        "🚫",
        "Cancelled",
        "Your commission was cancelled.",
    ),
}


def _fmt_amount(v) -> str:
    try:
        return f"\u00a5{float(v):,.2f}"
    except (TypeError, ValueError):
        return str(v)


async def on_commission_status_changed(
    db: AsyncSession,
    commission: Any,
    previous_status: str,
    new_status: str,
    actor: str,
) -> None:
    """Hook called after a commission status change. Best-effort.

    Loads the related sales user / order / customer to enrich the message.
    """
    info = _STATUS_MESSAGES.get(new_status)
    if info is None:
        # submit / other minor events — log only
        logger.info(
            "commission %s: %s → %s by %s (no notification)",
            getattr(commission, "commission_no", "?"),
            previous_status,
            new_status,
            actor,
        )
        return

    emoji, label, blurb = info

    # Best-effort: load related entities for a richer message.
    sales_user_name = None
    customer_name = None
    order_no = None
    try:
        from app.models.finance import Commission  # noqa
        from app.models.user import User
        from app.models.customer import Customer
        from app.models.sales import SalesOrder
        from sqlalchemy import select

        # Re-fetch commission (may have additional fields populated post-transition)
        # Or trust the input — load FK targets directly.
        if getattr(commission, "sales_user_id", None):
            user = await db.scalar(
                select(User).where(User.id == commission.sales_user_id)
            )
            if user:
                sales_user_name = user.username
        if getattr(commission, "customer_id", None):
            cust = await db.scalar(
                select(Customer).where(Customer.id == commission.customer_id)
            )
            if cust:
                customer_name = cust.name
        if getattr(commission, "sales_order_id", None):
            order = await db.scalar(
                select(SalesOrder).where(SalesOrder.id == commission.sales_order_id)
            )
            if order:
                order_no = order.order_no
    except Exception as exc:  # noqa: BLE001
        logger.debug("commission_notifier enrichment lookup failed: %s", exc)

    msg_lines = [
        f"{emoji} <b>Commission {label}</b>",
        f"No: {getattr(commission, 'commission_no', '?')}",
        f"Status: {previous_status} \u2192 <b>{new_status}</b>",
    ]
    if order_no:
        msg_lines.append(f"Order: {order_no}")
    if customer_name:
        msg_lines.append(f"Customer: {customer_name}")
    if getattr(commission, "period", None):
        msg_lines.append(f"Period: {commission.period}")
    msg_lines.append(
        f"Amount: <b>{_fmt_amount(getattr(commission, 'commission_amount', 0))}</b>"
    )
    if sales_user_name:
        msg_lines.append(f"Sales: {sales_user_name}")
    msg_lines.append(f"By: {actor}")
    if getattr(commission, "notes", None):
        # Last note line
        last_note = commission.notes.strip().splitlines()[-1] if commission.notes.strip() else ""
        if last_note and len(last_note) < 200:
            msg_lines.append(f"\n<i>{last_note}</i>")

    msg = "\n".join(msg_lines)

    try:
        from app.services.telegram_notifier import send_message

        await send_message(msg)
        logger.info(
            "commission %s → %s notification sent to Telegram",
            commission.commission_no,
            new_status,
        )
    except Exception as exc:  # noqa: BLE001
        # Never fail the transition
        logger.warning("telegram send failed for commission %s: %s", commission.commission_no, exc)
