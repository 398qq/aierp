"""Process-local event bus — synchronous in-process pub/sub.

Use for cross-cutting concerns where the publisher doesn't need to wait for
the consumer to finish. For multi-process or persistent delivery, swap with
Redis Streams or RabbitMQ.
"""

import asyncio
import logging
from collections import defaultdict
from typing import Any, Callable, TypeVar, Union

logger = logging.getLogger(__name__)


SyncHandler = Callable[[Any], None]
AsyncHandler = Callable[[Any], Any]
Handler = Union[SyncHandler, AsyncHandler]

F = TypeVar("F", bound=Handler)


class EventBus:
    """In-process event dispatcher.

    Handlers are dispatched in registration order. A failing handler logs and
    continues — the publisher is never blocked by a bad subscriber. Use this
    only for fire-and-forget concerns (caches, metrics, audit logs). Critical
    side effects belong inside the same transaction as the originating change.
    """

    def __init__(self) -> None:
        self._handlers: dict[type, list[SyncHandler]] = defaultdict(list)
        self._async_handlers: dict[type, list[AsyncHandler]] = defaultdict(list)

    def subscribe(
        self,
        event_type_or_handler: Union[type, Handler, None] = None,
        handler: Handler | None = None,
    ) -> Any:
        """Register a handler. Three usage patterns:

        1. ``@bus.subscribe`` (bare decorator — auto-detect event type from
           the handler's first parameter annotation).
        2. ``@bus.subscribe(EventType)`` (decorator with explicit type).
        3. ``bus.subscribe(EventType, handler_fn)`` (imperative call).
        """
        if handler is not None:
            self._register(event_type_or_handler, handler)  # type: ignore[arg-type]
            return handler

        if event_type_or_handler is None:
            raise TypeError(
                "@bus.subscribe requires either an event type or a handler function"
            )

        if isinstance(event_type_or_handler, type):
            return self._make_decorator(event_type_or_handler)

        if callable(event_type_or_handler):
            evt_t = self._infer_event_type(event_type_or_handler)
            self._register(evt_t, event_type_or_handler)  # type: ignore[arg-type]
            return event_type_or_handler

        raise TypeError(f"Unsupported subscribe argument: {event_type_or_handler!r}")

    def _make_decorator(self, event_type: type) -> Callable[[F], F]:
        def decorator(func: F) -> F:
            self._register(event_type, func)  # type: ignore[arg-type]
            return func

        return decorator

    def _register(self, event_type: Any, handler: Handler) -> None:
        if event_type is None:
            raise TypeError("EventBus.subscribe requires an event type")
        if asyncio.iscoroutinefunction(handler):
            self._async_handlers[event_type].append(handler)  # type: ignore[arg-type]
        else:
            self._handlers[event_type].append(handler)  # type: ignore[arg-type]

    @staticmethod
    def _infer_event_type(func: Handler) -> type:
        hints = getattr(func, "__annotations__", {}) or {}
        if not hints:
            raise TypeError(
                f"@bus.subscribe on {func.__name__!r} requires either an event type "
                "argument or a typed first parameter to infer the event type from"
            )
        first_param = next(iter(hints.values()), None)
        if first_param is None:
            raise TypeError(f"No parameter annotation on {func.__name__!r}")
        origin = getattr(first_param, "__origin__", None)
        if origin is not None:
            return origin
        return first_param  # type: ignore[return-value]

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
