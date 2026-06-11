"""Audit log service — Stage 2 Day 3.

Service layer helper for writing status_transition_logs entries.
Append-only: never update or delete. Each call inserts one row.

Used by sales_service/quotations.py / orders.py / delivery_notes.py /
finance_service.py whenever a status field changes. The pattern:

  before: inv.status = "paid"
          await db.commit()

  after:  inv.status = "paid"
          await audit_service.log_transition(
              db,
              aggregate_type="Invoice",
              aggregate_id=inv.id,
              status_before="issued",
              status_after="paid",
              action="pay_full",
              actor=user_id,
          )
          await db.commit()
"""

from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit import StatusTransitionLog


async def log_transition(
    db: AsyncSession,
    aggregate_type: str = "",
    aggregate_id: int = 0,
    status_before: Optional[str] = None,
    status_after: str = "",
    action: str = "",
    *,
    actor: Optional[str] = None,
    reason: Optional[str] = None,
    aggregate_no: Optional[str] = None,
    customer_id: Optional[int] = None,
    sales_order_id: Optional[int] = None,
) -> StatusTransitionLog:
    """Append one row to status_transition_logs.

    Accepts both positional and keyword calls (positional is convenient
    in service-layer hot paths; keyword is safer for ad-hoc logging).

    Args:
        db: async session
        aggregate_type: e.g. "SalesOrder" / "Invoice" / "PaymentRecord"
        aggregate_id: the ORM row id
        status_before: previous status (None for "created" entries)
        status_after: new status
        action: business action (confirm / ship / complete / cancel /
                pay_full / pay_partial / issue / reject / expire / ...)
        actor: who triggered (user_id str; defaults to None, NOT "system"
               — callers that want system attribution should pass
               "system" explicitly to distinguish from real None)
        reason: required for cancel / reverse (free text)
        aggregate_no: human-readable no (e.g. SO20260611001)
        customer_id: foreign key for fast customer-time queries
        sales_order_id: foreign key for SO-related transitions

    Returns:
        The inserted row (with .id, .transitioned_at populated).
    """
    log = StatusTransitionLog(
        aggregate_type=aggregate_type,
        aggregate_id=aggregate_id,
        aggregate_no=aggregate_no,
        status_before=status_before,
        status_after=status_after,
        action=action,
        actor=actor,
        reason=reason,
        customer_id=customer_id,
        sales_order_id=sales_order_id,
    )
    db.add(log)
    # Don't commit here — let the caller commit together with their
    # own state change for atomicity.
    await db.flush()
    return log


# ── Query helpers ─────────────────────────────────────────────────────


async def get_aggregate_timeline(
    db: AsyncSession,
    aggregate_type: str,
    aggregate_id: int,
) -> list[StatusTransitionLog]:
    """Return all transitions for a given aggregate, oldest first.

    Useful for the "订单时间线" UI: show PENDING → CONFIRMED → SHIPPED
    → COMPLETED as a vertical timeline with timestamps + actors.
    """
    from sqlalchemy import select

    result = await db.execute(
        select(StatusTransitionLog)
        .where(
            StatusTransitionLog.aggregate_type == aggregate_type,
            StatusTransitionLog.aggregate_id == aggregate_id,
        )
        .order_by(StatusTransitionLog.transitioned_at.asc())
    )
    return list(result.scalars().all())


async def get_customer_timeline(
    db: AsyncSession,
    customer_id: int,
    *,
    limit: int = 100,
) -> list[StatusTransitionLog]:
    """Return all transitions for a customer (across all aggregates).

    Powers the customer detail page's "近期活动" section.
    """
    from sqlalchemy import select

    result = await db.execute(
        select(StatusTransitionLog)
        .where(StatusTransitionLog.customer_id == customer_id)
        .order_by(StatusTransitionLog.transitioned_at.desc())
        .limit(limit)
    )
    return list(result.scalars().all())


audit_service = type("audit_service", (), {})  # marker, no state needed
