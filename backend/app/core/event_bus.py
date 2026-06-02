"""Process-local event bus — synchronous in-process pub/sub.

Use for cross-cutting concerns where the publisher doesn't need to wait for
the consumer to finish. For multi-process or persistent delivery, swap with
Redis Streams or RabbitMQ.
"""

from collections import defaultdict
from typing import Any, Callable
import asyncio
import logging

logger = logging.getLogger(__name__)


SyncHandler = Callable[[Any], None]
AsyncHandler = Callable[[Any], Any]


class EventBus:
    """In-process event dispatcher.

    Handlers are dispatched in registration order. A failing handler logs and
    continues — the publisher is never blocked by a bad subscriber. Use this
    only for fire-and-forget concerns (caches, metrics, audit logs). Critical
    side effects belong inside the same transaction as the originating change.
    """

    def __init__(self) -> None:
        self._handlers: dict[type, list[Callable]] = defaultdict(list)
        self._async_handlers: dict[type, list[Callable]] = defaultdict(list)

    def subscribe(
        self,
        event_type: type | None = None,
        handler: Callable | None = None,
    ) -> Any:
        """Register a handler. Sync handlers run inline; async handlers are awaited.

        Can be called as a decorator @bus.subscribe(event_type) or
        @bus.subscribe (auto-detect from type annotation).
        """
        if handler is not None:
            # Called as @bus.subscribe(EventType) or @bus.subscribe(EventType, handler)
            actual_handler = handler
        else:
            # Called as a decorator @bus.subscribe without args — handler is the
            # event_type argument, i.e. the decorated function
            def decorator(func: Callable) -> Callable:
                evt_t = event_type  # type: ignore[assignment]  # it's actually the func here
                if evt_t is None:
                    raise TypeError("@bus.subscribe decorator requires an event type argument")
                if asyncio.iscoroutinefunction(func):
                    self._async_handlers[evt_t].append(func)
                else:
                    self._handlers[evt_t].append(func)
                return func
            return decorator

        # Called with explicit args
        if asyncio.iscoroutinefunction(actual_handler):
            self._async_handlers[event_type].append(actual_handler)  # type: ignore[arg-type]
        else:
            self._handlers[event_type].append(actual_handler)  # type: ignore[arg-type]

    async def publish(self, event: Any) -> None:
        """Dispatch an event to all registered handlers (sync + async)."""
        event_type = type(event)
        for handler in self._handlers.get(event_type, []):
            try:
                handler(event)
            except Exception:
                logger.exception(
                    "Sync handler %s failed for %s",
                    handler.__name__,
                    event.__class__.__name__,
                )

        for handler in self._async_handlers.get(event_type, []):
            try:
                result = handler(event)
                if asyncio.iscoroutine(result):
                    await result
            except Exception:
                logger.exception(
                    "Async handler %s failed for %s",
                    handler.__name__,
                    event.__class__.__name__,
                )

    def clear(self) -> None:
        """Remove all subscribers — useful for test isolation."""
        self._handlers.clear()
        self._async_handlers.clear()

    def handler_count(self, event_type: type) -> int:
        return len(self._handlers.get(event_type, [])) + len(
            self._async_handlers.get(event_type, [])
        )


event_bus = EventBus()
