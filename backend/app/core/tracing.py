"""Lightweight distributed tracing — OpenTelemetry-compatible API.

Full OpenTelemetry SDK is heavy. This module provides a minimal
no-dep implementation that:

- Tracks spans in a contextvar (auto-propagates across awaits)
- Records timing, attributes, status, events
- Exports spans to the structured logger (json_logging) so they
  flow through the same ELK / Loki / Datadog pipeline as other logs
- API surface mirrors `opentelemetry.trace.Tracer` so callers can
  swap in the real SDK later without changing business code

When OpenTelemetry is installed (optional dep), the module can be
extended to also export OTLP traces via the official SDK.
"""

import logging
import time
import uuid
import json
from contextvars import ContextVar
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Iterator, Optional

logger = logging.getLogger("app.trace")

# Span context — propagates across awaits within the same task
_current_span: ContextVar[Optional["Span"]] = ContextVar("current_span", default=None)
_current_trace_id: ContextVar[str] = ContextVar("current_trace_id", default="")


class SpanStatus(str, Enum):
    UNSET = "unset"
    OK = "ok"
    ERROR = "error"


@dataclass
class Span:
    """A single operation in a trace.

    Span tree: a span has 0..1 parent and 0..N children. Spans form
    a tree that represents a request's causal execution path.
    """

    name: str
    trace_id: str
    span_id: str = field(default_factory=lambda: uuid.uuid4().hex[:16])
    parent_id: Optional[str] = None
    start_time: float = field(default_factory=time.perf_counter)
    end_time: Optional[float] = None
    status: SpanStatus = SpanStatus.UNSET
    attributes: dict[str, Any] = field(default_factory=dict)
    events: list[dict[str, Any]] = field(default_factory=list)
    _finished: bool = False

    def set_attribute(self, key: str, value: Any) -> None:
        self.attributes[key] = value

    def set_attributes(self, attrs: dict[str, Any]) -> None:
        self.attributes.update(attrs)

    def add_event(self, name: str, attributes: Optional[dict[str, Any]] = None) -> None:
        self.events.append(
            {
                "name": name,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "attributes": attributes or {},
            }
        )

    def record_exception(self, exc: BaseException) -> None:
        self.status = SpanStatus.ERROR
        self.add_event(
            "exception",
            {
                "type": type(exc).__name__,
                "message": str(exc),
            },
        )

    def set_status(self, status: SpanStatus, description: Optional[str] = None) -> None:
        self.status = status
        if description:
            self.attributes["status_description"] = description

    @property
    def duration_ms(self) -> float:
        end = self.end_time or time.perf_counter()
        return round((end - self.start_time) * 1000, 2)

    def finish(self) -> None:
        if self._finished:
            return
        self._finished = True
        self.end_time = time.perf_counter()
        self._export()

    def _export(self) -> None:
        """Emit the span as a structured log record via the JsonFormatter
        extras passthrough (prefixed to avoid LogRecord name collisions)."""
        # Build a single dict that the JsonFormatter will serialize.
        # We use a `span_` prefix for the dict to avoid LogRecord
        # reserved-name collisions (e.g. `name`, `level`).
        payload = {
            "span_trace_id": self.trace_id,
            "span_id": self.span_id,
            "span_parent_id": self.parent_id or "",
            "span_name": self.name,
            "span_status": self.status.value,
            "span_duration_ms": self.duration_ms,
            "span_attributes": self.attributes,
            "span_events": self.events,
        }
        msg = "span_completed " + json.dumps(payload, ensure_ascii=False, default=str)
        if self.status == SpanStatus.ERROR:
            logger.error(msg)
        else:
            logger.info(msg)


class Tracer:
    """Factory for creating spans.

    Mirrors `opentelemetry.trace.Tracer` interface:

        tracer = Tracer("aierp.backend")
        with tracer.start_as_current_span("db.query") as span:
            span.set_attribute("db.statement", sql)
            result = await session.execute(stmt)
    """

    def __init__(self, name: str) -> None:
        self.name = name

    def start_span(
        self,
        name: str,
        attributes: Optional[dict[str, Any]] = None,
        parent: Optional[Span] = None,
    ) -> Span:
        """Start a new span. Caller must call `span.finish()` or use
        the `start_as_current_span` context manager."""
        # Inherit trace_id from parent if available
        if parent is not None:
            trace_id = parent.trace_id
            parent_id = parent.span_id
        else:
            current = _current_span.get()
            if current is not None:
                trace_id = current.trace_id
                parent_id = current.span_id
            else:
                # New root — also set the trace_id contextvar
                trace_id = uuid.uuid4().hex
                _current_trace_id.set(trace_id)
                parent_id = None

        span = Span(
            name=name,
            trace_id=trace_id,
            parent_id=parent_id,
        )
        span.set_attribute("tracer", self.name)
        if attributes:
            span.set_attributes(attributes)
        return span

    @contextmanager
    def start_as_current_span(
        self,
        name: str,
        attributes: Optional[dict[str, Any]] = None,
    ) -> Iterator[Span]:
        """Context manager: span is the current span inside the block,
        auto-finished on exit.

        Records exception as a span event and sets ERROR status.
        """
        span = self.start_span(name, attributes=attributes)
        token = _current_span.set(span)
        try:
            yield span
            if span.status == SpanStatus.UNSET:
                span.set_status(SpanStatus.OK)
        except BaseException as exc:
            span.record_exception(exc)
            raise
        finally:
            _current_span.reset(token)
            span.finish()


def get_current_span() -> Optional[Span]:
    """Return the currently active span (for nested instrumentation)."""
    return _current_span.get()


def get_current_trace_id() -> str:
    """Return the trace_id of the current async task (empty if no active span)."""
    return _current_trace_id.get()


# ────────────────────────────────────────────────────────────────────────
# Pre-configured tracers for common modules
# ────────────────────────────────────────────────────────────────────────

tracer_backend = Tracer("aierp.backend")
tracer_db = Tracer("aierp.db")
tracer_ai = Tracer("aierp.ai")
tracer_external = Tracer("aierp.external")


@contextmanager
def root_span(name: str, attributes: Optional[dict[str, Any]] = None) -> Iterator[Span]:
    """Create a new root span (new trace_id).

    Use this to mark the start of a top-level operation like an
    incoming HTTP request or a scheduled job.
    """
    with tracer_backend.start_as_current_span(name, attributes) as span:
        yield span
