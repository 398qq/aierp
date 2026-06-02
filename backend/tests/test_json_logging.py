"""Tests for structured JSON logging."""

import io
import json
import logging

import pytest

from app.core.json_logging import (
    JsonFormatter,
    configure_json_logging,
    get_request_id,
    get_user_id,
    set_request_id,
    set_user_id,
    with_context,
)


def _format_record(record: logging.LogRecord) -> str:
    return JsonFormatter().format(record)


class TestJsonFormatterBasic:
    def test_emits_valid_json(self):
        record = logging.LogRecord(
            name="test", level=logging.INFO, pathname="x.py", lineno=10,
            msg="hello %s", args=("world",), exc_info=None,
        )
        out = _format_record(record)
        payload = json.loads(out)
        assert payload["level"] == "INFO"
        assert payload["logger"] == "test"
        assert payload["message"] == "hello world"
        assert payload["path"] == "x.py"
        assert payload["line"] == 10

    def test_includes_request_id_from_context(self):
        set_request_id("req_abc123")
        record = logging.LogRecord(
            name="t", level=logging.INFO, pathname="x", lineno=1, msg="m", args=(), exc_info=None,
        )
        payload = json.loads(_format_record(record))
        assert payload["request_id"] == "req_abc123"
        set_request_id(None)

    def test_includes_user_id_from_context(self):
        set_user_id(42)
        record = logging.LogRecord(
            name="t", level=logging.INFO, pathname="x", lineno=1, msg="m", args=(), exc_info=None,
        )
        payload = json.loads(_format_record(record))
        assert payload["user_id"] == 42
        set_user_id(None)

    def test_passes_through_extra(self):
        record = logging.LogRecord(
            name="t", level=logging.INFO, pathname="x", lineno=1, msg="m", args=(), exc_info=None,
        )
        record.order_id = "SO001"
        record.amount = 1500
        payload = json.loads(_format_record(record))
        assert payload["order_id"] == "SO001"
        assert payload["amount"] == 1500

    def test_extra_override_takes_precedence(self):
        """Built-in fields should not be duplicated by extras with same name."""
        record = logging.LogRecord(
            name="t", level=logging.INFO, pathname="x", lineno=1, msg="m", args=(), exc_info=None,
        )
        record.level = "WRONG"  # Should not override the actual level
        payload = json.loads(_format_record(record))
        assert payload["level"] == "INFO"

    def test_handles_non_serializable_extra(self):
        record = logging.LogRecord(
            name="t", level=logging.INFO, pathname="x", lineno=1, msg="m", args=(), exc_info=None,
        )
        # Pass an unserializable object
        class Opaque:
            def __repr__(self):
                return "Opaque()"
        record.obj = Opaque()
        payload = json.loads(_format_record(record))
        assert payload["obj"] == "Opaque()"

    def test_includes_exception(self):
        try:
            raise ValueError("boom")
        except ValueError:
            import sys
            record = logging.LogRecord(
                name="t", level=logging.ERROR, pathname="x", lineno=1, msg="failed",
                args=(), exc_info=sys.exc_info(),
            )
        payload = json.loads(_format_record(record))
        assert "exception" in payload
        assert payload["exception"]["type"] == "ValueError"
        assert "boom" in payload["exception"]["message"]
        assert "Traceback" in payload["exception"]["traceback"]

    def test_timestamp_is_iso8601(self):
        record = logging.LogRecord(
            name="t", level=logging.INFO, pathname="x", lineno=1, msg="m", args=(), exc_info=None,
        )
        payload = json.loads(_format_record(record))
        ts = payload["ts"]
        # Format: 2026-06-02T15:30:00.123Z
        assert ts.endswith("Z")
        assert "T" in ts

    def test_chinese_message_preserved(self):
        record = logging.LogRecord(
            name="t", level=logging.INFO, pathname="x", lineno=1, msg="订单确认", args=(), exc_info=None,
        )
        payload = json.loads(_format_record(record))
        assert payload["message"] == "订单确认"


class TestConfigureJsonLogging:
    def test_replaces_root_handler(self):
        root = logging.getLogger()
        # Clear existing handlers
        for h in list(root.handlers):
            root.removeHandler(h)

        configure_json_logging(level=logging.WARNING)

        assert len(root.handlers) == 1
        handler = root.handlers[0]
        assert isinstance(handler.formatter, JsonFormatter)
        assert root.level == logging.WARNING

    def test_idempotent(self):
        root = logging.getLogger()
        for h in list(root.handlers):
            root.removeHandler(h)

        configure_json_logging()
        # First install: 1 handler
        assert len(root.handlers) == 1
        assert isinstance(root.handlers[0].formatter, JsonFormatter)

        configure_json_logging()
        # Second call should not stack handlers
        assert len(root.handlers) == 1
        assert isinstance(root.handlers[0].formatter, JsonFormatter)

    def test_writes_to_stream(self):
        stream = io.StringIO()
        configure_json_logging(stream=stream)
        logging.getLogger("test.stream").info("hello")
        # Stream contents may not be flushed yet — force flush
        for h in logging.getLogger().handlers:
            h.flush()
        output = stream.getvalue()
        # Should contain a JSON object
        lines = [line for line in output.split("\n") if line.strip()]
        assert any('"message": "hello"' in line for line in lines)


class TestWithContext:
    def test_logger_adapter_injects_extra(self):
        logger = logging.getLogger("test.adapter")
        logger.setLevel(logging.INFO)
        stream = io.StringIO()
        handler = logging.StreamHandler(stream)
        handler.setFormatter(JsonFormatter())
        logger.addHandler(handler)

        log = with_context(logger, customer_id=42, order_no="SO001")
        log.info("test message")

        handler.flush()
        lines = [line for line in stream.getvalue().split("\n") if line.strip()]
        # Find the line with our message
        for line in lines:
            if '"test message"' in line:
                payload = json.loads(line)
                assert payload["customer_id"] == 42
                assert payload["order_no"] == "SO001"
                return
        pytest.fail(f"No matching line in: {stream.getvalue()}")


class TestContextVars:
    def test_request_id_round_trip(self):
        set_request_id("req_xyz")
        assert get_request_id() == "req_xyz"
        set_request_id(None)
        assert get_request_id() is None

    def test_user_id_round_trip(self):
        set_user_id(99)
        assert get_user_id() == 99
        set_user_id(None)
        assert get_user_id() is None

    def test_default_is_none(self):
        # Clear first
        set_request_id(None)
        set_user_id(None)
        assert get_request_id() is None
        assert get_user_id() is None


class TestJsonLineFormat:
    def test_one_record_one_line(self):
        """Critical: each log record must be a single line for log shippers."""
        record = logging.LogRecord(
            name="t", level=logging.INFO, pathname="x", lineno=1,
            msg="multi\nline\nmessage", args=(), exc_info=None,
        )
        out = _format_record(record)
        assert out.count("\n") == 0  # No actual newlines in the output
