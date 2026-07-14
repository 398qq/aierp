"""Customer auto-transition service — event-driven + scheduled.

Implements the 7-state customer lifecycle machine:
    new_lead → active → converted → vip | inactive → churned

Triggers:
    Real-time: create_first_opportunity(), complete_first_order(), re_engage()
    Scheduled (daily 02:00): promote_to_vip(), mark_inactive()
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.shared.errors import InvalidStateTransition
from app.domain.states import (
    assert_can_transition_customer,
)
from app.models.customer import CustomerStatus

logger = logging.getLogger(__name__)

# 12-month revenue threshold for VIP (¥500,000)
VIP_REVENUE_THRESHOLD = 500_000.0
# Days without interaction before marking inactive
INACTIVE_DAYS = 90


async def _transition(
    db: AsyncSession, customer_id: int, current: str, target: str
) -> bool:
    """Apply a single customer state transition if legal. Returns True if changed.

    Uses optimistic locking: the UPDATE WHERE clause checks that the row still
    holds *current* status, preventing silent double-transitions under concurrency.
    """
    if current == target:
        return False
    try:
        assert_can_transition_customer(current, target)
    except InvalidStateTransition:
        return False

    from app.models.customer import Customer

    result = await db.execute(
        update(Customer)
        .where(
            Customer.id == customer_id,
            Customer.status == current,
            Customer.deleted_at.is_(None),
        )
        .values(status=target, updated_at=datetime.now(timezone.utc))
    )
    if getattr(result, "rowcount", 0) == 0:
        logger.warning(
            "Customer #%d: concurrent modification detected, %s → %s skipped",
            customer_id,
            current,
            target,
        )
        return False

    logger.info("Customer #%d: %s → %s (auto)", customer_id, current, target)
    return True


# ── Real-time triggers (called from opportunity / sales-order services) ──


async def on_first_opportunity(db: AsyncSession, customer_id: int) -> None:
    """When the first opportunity is created for a new_lead customer."""
    from app.models.customer import Customer

    row = await db.execute(
        select(Customer.status).where(
            Customer.id == customer_id, Customer.deleted_at.is_(None)
        )
    )
    status = row.scalar()
    if status == CustomerStatus.NEW_LEAD:
        await _transition(db, customer_id, status, CustomerStatus.ACTIVE)


async def on_first_order_completed(db: AsyncSession, customer_id: int) -> None:
    """When the first sales order is completed for an active customer."""
    from app.models.customer import Customer

    row = await db.execute(
        select(Customer.status).where(
            Customer.id == customer_id, Customer.deleted_at.is_(None)
        )
    )
    status = row.scalar()
    if status in (CustomerStatus.NEW_LEAD, CustomerStatus.ACTIVE):
        await _transition(db, customer_id, status, CustomerStatus.CONVERTED)


async def on_re_engage(db: AsyncSession, customer_id: int) -> None:
    """When an inactive customer interacts again."""
    from app.models.customer import Customer

    row = await db.execute(
        select(Customer.status).where(
            Customer.id == customer_id, Customer.deleted_at.is_(None)
        )
    )
    status = row.scalar()
    if status in (CustomerStatus.INACTIVE, CustomerStatus.CHURNED):
        await _transition(db, customer_id, status, CustomerStatus.ACTIVE)


# ── Scheduled job (daily 02:00) ──


async def run_customer_status_job(db: AsyncSession) -> dict:
    """Daily customer status maintenance job.

    Returns summary of transitions performed.
    """
    from app.models.customer import Customer
    from app.models.sales import SalesOrder

    summary: dict[str, int] = {
        "to_vip": 0,
        "to_inactive": 0,
        "total_checked": 0,
    }

    now = datetime.now(timezone.utc)
    cutoff_inactive = now - timedelta(days=INACTIVE_DAYS)
    cutoff_vip = now - timedelta(days=365)

    # ── Active/Converted → Inactive (no interaction > 90 days) ──
    stale = await db.execute(
        select(Customer.id, Customer.status).where(
            Customer.deleted_at.is_(None),
            Customer.status.in_(
                [CustomerStatus.ACTIVE, CustomerStatus.CONVERTED, CustomerStatus.VIP]
            ),
            Customer.last_contacted_at.is_not(None),
            Customer.last_contacted_at < cutoff_inactive,
        )
    )
    for cid, status in stale.all():
        summary["total_checked"] += 1
        if await _transition(db, cid, status, CustomerStatus.INACTIVE):
            summary["to_inactive"] += 1

    # ── Converted → VIP (12-month revenue > ¥500,000) ──
    high_value = await db.execute(
        select(Customer.id, func.sum(SalesOrder.total_amount))
        .join(SalesOrder, SalesOrder.customer_id == Customer.id)
        .where(
            Customer.deleted_at.is_(None),
            Customer.status == CustomerStatus.CONVERTED,
            SalesOrder.deleted_at.is_(None),
            SalesOrder.status == "completed",
            SalesOrder.order_date >= cutoff_vip,
        )
        .group_by(Customer.id)
        .having(func.sum(SalesOrder.total_amount) >= VIP_REVENUE_THRESHOLD)
    )
    for cid, revenue in high_value.all():
        summary["total_checked"] += 1
        if await _transition(db, cid, CustomerStatus.CONVERTED, CustomerStatus.VIP):
            summary["to_vip"] += 1

    await db.commit()
    return summary
