"""Application event handlers — subscribers to domain events.

These run inside the same process as the publisher. They should be idempotent
and side-effect-light: cache invalidation, metric emission, audit logging.
For state-mutating side effects (e.g. release reserved stock), keep them in
the same transaction as the originating change rather than in a handler.
"""

from app.core.event_bus import EventBus
from app.core.observability.metrics import (
    domain_events_total,
    inventory_release_failures_total,
    inventory_reserved_total,
    orders_cancelled_total,
    orders_confirmed_total,
)
from app.domain.sales.events import (
    OrderCancelled,
    OrderConfirmed,
    OrderShipped,
)
from app.domain.shared.events import DomainEvent

import logging

logger = logging.getLogger(__name__)


def register_default_handlers(bus: EventBus) -> None:
    """Register all built-in event handlers.

    Idempotent: calling twice will register handlers twice, so call only once
    during application startup.
    """

    @bus.subscribe
    def _log_order_confirmed(event: OrderConfirmed) -> None:  # type: ignore[arg-type]
        logger.info(
            "OrderConfirmed SO#%s customer=%s total=%.2f lines=%d",
            event.aggregate_id,
            event.customer_id,
            event.total_amount,
            len(event.lines),
        )
        orders_confirmed_total.inc(customer_tier="unknown")
        domain_events_total.inc(event_type=event.event_name)

    @bus.subscribe
    def _log_order_cancelled(event: OrderCancelled) -> None:  # type: ignore[arg-type]
        logger.info(
            "OrderCancelled SO#%s previous=%s reason=%s lines=%d",
            event.aggregate_id,
            event.previous_status,
            event.reason,
            len(event.lines),
        )
        orders_cancelled_total.inc(
            previous_status=event.previous_status,
            reason=event.reason[:32],  # bound cardinality
        )
        domain_events_total.inc(event_type=event.event_name)

    @bus.subscribe
    def _log_order_shipped(event: OrderShipped) -> None:  # type: ignore[arg-type]
        logger.info(
            "OrderShipped SO#%s full=%s lines=%d",
            event.aggregate_id,
            event.is_full,
            len(event.lines),
        )
        domain_events_total.inc(event_type=event.event_name)

    @bus.subscribe
    def _count_domain_events(event: DomainEvent) -> None:  # type: ignore[arg-type]
        # Catch-all for events without a dedicated counter
        domain_events_total.inc(event_type=event.event_name)


def register_inventory_handlers(bus: EventBus) -> None:
    """Wire OrderCancelled → inventory release.

    This subscriber releases reserved stock when an order is cancelled.
    Uses the InventoryRepository (concurrency-safe) and runs after the
    UoW commits the order state change.
    """

    @bus.subscribe
    async def _release_stock_on_cancel(event: OrderCancelled) -> None:  # type: ignore[arg-type]
        # Only release stock if order was previously confirmed (had reserved stock)
        if event.previous_status not in ("confirmed", "partially_shipped"):
            return

        # We need a fresh DB session because the event handler runs after the
        # originating transaction committed. Lazy-import to avoid loading
        # infrastructure on every event.
        from app.database import async_session
        from app.infrastructure.persistence.inventory_repo import InventoryRepository

        async with async_session() as session:
            repo = InventoryRepository(session)
            released = 0
            failed = 0
            for product_id, qty in event.lines:
                try:
                    ok = await repo.release(
                        product_id=product_id,
                        warehouse_id=1,  # Default; multi-warehouse selection is future work
                        qty=int(qty),
                    )
                    if ok:
                        released += 1
                        inventory_reserved_total.inc(
                            amount=-1,
                            product_category="unknown",
                        )
                except Exception as e:
                    failed += 1
                    inventory_release_failures_total.inc()
                    logger.warning(
                        "Failed to release stock for product=%s qty=%s: %s",
                        product_id,
                        qty,
                        e,
                    )
            await session.commit()

            logger.info(
                "Released stock for cancelled order SO#%s: %d/%d lines, %d failed",
                event.aggregate_id,
                released,
                len(event.lines),
                failed,
            )
