"""Single guarded and audited write path for ERP lifecycle changes."""

from collections.abc import Callable
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.services.audit_service import log_transition

TransitionGuard = Callable[[str, str], None]


async def transition_status(
    db: AsyncSession,
    entity: Any,
    target: str,
    *,
    guard: TransitionGuard,
    aggregate_type: str,
    actor: str | int | None = None,
    action: str | None = None,
    reason: str | None = None,
) -> bool:
    """Validate, mutate, and audit one status change in the caller transaction."""
    current_value = entity.status
    current = getattr(current_value, "value", current_value)
    if current == target:
        return False

    guard(str(current), target)
    entity.status = target

    aggregate_no = next(
        (
            getattr(entity, field)
            for field in (
                "order_no",
                "quotation_no",
                "delivery_no",
                "invoice_no",
                "payment_no",
                "contract_no",
                "receipt_no",
                "ticket_no",
            )
            if getattr(entity, field, None)
        ),
        None,
    )
    await log_transition(
        db,
        aggregate_type=aggregate_type,
        aggregate_id=int(entity.id),
        aggregate_no=aggregate_no,
        status_before=str(current),
        status_after=target,
        action=action or target,
        actor=str(actor) if actor is not None else "system",
        reason=reason,
        customer_id=getattr(entity, "customer_id", None),
        sales_order_id=(
            entity.id
            if aggregate_type == "SalesOrder"
            else getattr(entity, "sales_order_id", None)
        ),
    )
    return True
