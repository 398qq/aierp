"""Unit of Work — explicit transaction boundary + event publication.

Wraps a single SQLAlchemy session. Caller accumulates domain events via
`track_event`; on `commit()` events are dispatched on the event bus AFTER the
DB transaction succeeds. On `rollback()` events are discarded.

Use as:

    async with get_uow() as uow:
        order = await repo.find(order_id)
        order.confirm()              # mutates aggregate + collects events
        for ev in order.collect_events():
            uow.track_event(ev)
        await repo.save(uow.session, order)
    # ← auto-commit + auto-dispatch on exit

Or with FastAPI Depends:

    @router.post(...)
    async def handler(uow: UnitOfWork = Depends(get_uow)):
        ...
"""

from contextlib import asynccontextmanager
from typing import Optional, TYPE_CHECKING
import logging

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

if TYPE_CHECKING:
    from app.core.event_bus import EventBus

logger = logging.getLogger(__name__)


class UnitOfWork:
    """Wraps one DB session + a list of pending events."""

    def __init__(self, session: AsyncSession, bus: "EventBus | None" = None) -> None:
        self.session = session
        self._bus = bus
        self._pending_events: list = []
        self._committed = False
        self._rolled_back = False

    @property
    def events(self) -> list:
        return self._pending_events

    def track_event(self, event) -> None:
        """Buffer a domain event for publication after commit."""
        self._pending_events.append(event)

    async def commit(self) -> None:
        if self._committed or self._rolled_back:
            return
        try:
            await self.session.commit()
            await self._dispatch_events()
            self._committed = True
        except Exception:
            await self.rollback()
            raise

    async def rollback(self) -> None:
        if self._rolled_back:
            return
        try:
            await self.session.rollback()
        finally:
            self._pending_events.clear()
            self._rolled_back = True

    async def _dispatch_events(self) -> None:
        if not self._bus or not self._pending_events:
            return
        # Snapshot before iteration in case a handler emits new events
        events = self._pending_events[:]
        self._pending_events.clear()
        for event in events:
            try:
                await self._bus.publish(event)
            except Exception:
                logger.exception(
                    "Event dispatch failed for %s — event will be lost",
                    event.__class__.__name__,
                )


_session_factory: Optional[async_sessionmaker] = None
_event_bus = None


def init_uow(
    session_factory: async_sessionmaker,
    bus: "EventBus | None" = None,
) -> None:
    """Configure UoW for the application. Call once at startup."""
    global _session_factory, _event_bus
    _session_factory = session_factory
    _event_bus = bus


@asynccontextmanager
async def get_uow():
    """Async context manager yielding a fresh UnitOfWork.

    Auto-commits on clean exit; auto-rolls back on exception.
    """
    if _session_factory is None:
        raise RuntimeError("UoW not initialized — call init_uow() at app startup")
    async with _session_factory() as session:
        uow = UnitOfWork(session, bus=_event_bus)
        try:
            yield uow
            if not uow._committed and not uow._rolled_back:
                await uow.commit()
        except Exception:
            if not uow._rolled_back:
                await uow.rollback()
            raise
