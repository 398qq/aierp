"""Structured JSON logging — ELK / Loki / Datadog friendly.

Provides a `JsonFormatter` that emits one JSON object per log line
with all the context needed for log aggregation:

    {"ts": "2026-06-02T15:30:00.123Z", "level": "INFO", "logger": "app.sales",
     "message": "Order confirmed", "request_id": "req_abc",
     "user_id": 42, "extra": {...}}

Also provides a `context_logger` helper to attach fields like
request_id / user_id to the current asyncio task's logger context.
"""

import json
import logging
import sys
import traceback
from contextvars import ContextVar
from typing import Any

# Context variables survive across await boundaries within the same task
_request_id_var: ContextVar[str | None] = ContextVar("request_id", default=None)
_user_id_var: ContextVar[int | None] = ContextVar("user_id", default=None)


def set_request_id(rid: str | None) -> None:
    _request_id_var.set(rid)


def get_request_id() -> str | None:
    return _request_id_var.get()


def set_user_id(uid: int | None) -> None:
    _user_id_var.set(uid)


def get_user_id() -> int | None:
    return _user_id_var.get()


class JsonFormatter(logging.Formatter):
    """Format log records as single-line JSON.

    Always includes: ts, level, logger, message.
    Includes if present: request_id, user_id, exception (with traceback).
    Pass-through any `extra` dict fields.
    """

    # Standard LogRecord attributes that should NOT be duplicated as `extra`
    RESERVED = {
        "args",
        "asctime",
        "created",
        "exc_info",
        "exc_text",
        "filename",
        "funcName",
        "levelname",
        "levelno",
        "lineno",
        "module",
        "msecs",
        "message",
        "msg",
        "name",
        "pathname",
        "process",
        "processName",
        "relativeCreated",
        "stack_info",
        "thread",
        "threadName",
    }

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "ts": self._format_timestamp(record.created),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        # Inject context
        rid = _request_id_var.get()
        if rid is not None:
            payload["request_id"] = rid
        uid = _user_id_var.get()
        if uid is not None:
            payload["user_id"] = uid

        # Path / line — useful for trace correlation
        payload["path"] = record.pathname
        payload["line"] = record.lineno

        # Pass-through `extra` fields
        for key, value in record.__dict__.items():
            if key in self.RESERVED or key.startswith("_"):
                continue
            if key in payload:
                continue
            try:
                json.dumps(value)  # skip non-serializable
                payload[key] = value
            except (TypeError, ValueError):
                payload[key] = repr(value)

        # Exception
        if record.exc_info:
            payload["exception"] = {
                "type": record.exc_info[0].__name__ if record.exc_info[0] else None,
                "message": str(record.exc_info[1]) if record.exc_info[1] else None,
                "traceback": "".join(traceback.format_exception(*record.exc_info)),
            }

        return json.dumps(payload, ensure_ascii=False, default=str)

    @staticmethod
    def _format_timestamp(epoch: float) -> str:
        # ISO 8601 with milliseconds and Z suffix
        from datetime import datetime, timezone

        dt = datetime.fromtimestamp(epoch, tz=timezone.utc)
        return dt.strftime("%Y-%m-%dT%H:%M:%S.") + f"{int(dt.microsecond / 1000):03d}Z"


def configure_json_logging(
    level: int = logging.INFO,
    stream=None,
) -> None:
    """Replace the root logger's handler with a JSON one.

    Idempotent: removes any previously-installed handler to avoid
    duplicate log lines when called more than once (e.g. in tests).
    """
    handler = logging.StreamHandler(stream or sys.stdout)
    handler.setFormatter(JsonFormatter())

    root = logging.getLogger()
    # Remove any existing handlers we installed
    for h in list(root.handlers):
        if isinstance(h.formatter, JsonFormatter):
            root.removeHandler(h)
    root.addHandler(handler)
    root.setLevel(level)

    # Tone down noisy 3rd-party loggers
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)


def with_context(logger: logging.Logger, **kwargs) -> logging.LoggerAdapter:
    """Return a logger adapter that injects extra fields into every record.

    Usage:
        log = with_context(logger, customer_id=42, order_no="SO001")
        log.info("Order confirmed")
    """
    return logging.LoggerAdapter(logger, extra=kwargs)
