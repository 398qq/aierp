"""Tests for the lightweight distributed tracing implementation."""

import asyncio
import json
import logging
import time

import pytest

from app.core.tracing import (
    Span,
    SpanStatus,
    Tracer,
    get_current_span,
    get_current_trace_id,
    root_span,
    tracer_backend,
)


@pytest.fixture
def capture_logs(caplog):
    caplog.set_level(logging.INFO, logger="app.trace")
    return caplog


class TestSpanBasics:
    def test_default_state(self):
        span = Span(name="test", trace_id="abc")
        assert span.name == "test"
        assert span.trace_id == "abc"
        assert span.span_id is not None
        assert span.parent_id is None
        assert span.status == SpanStatus.UNSET
        assert span.attributes == {}

    def test_set_attribute(self):
        span = Span(name="t", trace_id="t1")
        span.set_attribute("db.statement", "SELECT 1")
        assert span.attributes["db.statement"] == "SELECT 1"

    def test_set_attributes_bulk(self):
        span = Span(name="t", trace_id="t1")
        span.set_attributes({"a": 1, "b": 2, "c": 3})
        assert span.attributes == {"a": 1, "b": 2, "c": 3}

    def test_add_event(self):
        span = Span(name="t", trace_id="t1")
        span.add_event("cache_hit", {"key": "user:1"})
        assert len(span.events) == 1
        assert span.events[0]["name"] == "cache_hit"
        assert span.events[0]["attributes"] == {"key": "user:1"}

    def test_record_exception_sets_error_status(self):
        span = Span(name="t", trace_id="t1")
        span.record_exception(ValueError("boom"))
        assert span.status == SpanStatus.ERROR
        assert any(e["name"] == "exception" for e in span.events)

    def test_set_status(self):
        span = Span(name="t", trace_id="t1")
        span.set_status(SpanStatus.OK, description="completed normally")
        assert span.status == SpanStatus.OK
        assert span.attributes["status_description"] == "completed normally"

    def test_duration_ms_positive_after_delay(self):
        span = Span(name="t", trace_id="t1")
        time.sleep(0.01)
        span.finish()
        assert span.duration_ms >= 10

    def test_finish_idempotent(self):
        span = Span(name="t", trace_id="t1")
        span.finish()
        first_end = span.end_time
        span.finish()  # Second call should be no-op
        assert span.end_time == first_end


class TestTracerStartAsCurrentSpan:
    def test_basic_context_manager(self, capture_logs):
        tracer = Tracer("test")
        with tracer.start_as_current_span("my_op") as span:
            assert get_current_span() is span
            assert span.name == "my_op"
        # After exit, current span is reset
        assert get_current_span() is None
        assert span.status == SpanStatus.OK

    def test_attributes_passed_in(self, capture_logs):
        tracer = Tracer("test")
        with tracer.start_as_current_span("op", attributes={"k": "v"}) as span:
            assert span.attributes["k"] == "v"
            assert span.attributes["tracer"] == "test"

    def test_exception_sets_error_status(self, capture_logs):
        tracer = Tracer("test")
        with pytest.raises(RuntimeError, match="boom"):
            with tracer.start_as_current_span("fail_op") as span:
                raise RuntimeError("boom")
        assert span.status == SpanStatus.ERROR

    def test_nested_spans_form_hierarchy(self, capture_logs):
        tracer = Tracer("test")
        with tracer.start_as_current_span("parent") as parent:
            with tracer.start_as_current_span("child") as child:
                assert child.parent_id == parent.span_id
                assert child.trace_id == parent.trace_id
                with tracer.start_as_current_span("grandchild") as gc:
                    assert gc.parent_id == child.span_id
                    assert gc.trace_id == parent.trace_id

    def test_unrelated_span_is_not_child(self, capture_logs):
        tracer = Tracer("test")
        with tracer.start_as_current_span("a") as a:
            with tracer.start_as_current_span("b") as b:
                pass
        # b's parent is a, not itself
        assert b.parent_id == a.span_id
        assert b.span_id != a.span_id

    def test_async_nesting_preserves_trace_id(self, capture_logs):
        async def child():
            await asyncio.sleep(0.001)
            return get_current_trace_id()

        async def parent():
            with tracer_backend.start_as_current_span("parent") as p:
                child_trace = await child()
                return p.trace_id, child_trace

        async def run():
            return await parent()

        parent_trace, child_trace = asyncio.run(run())
        assert parent_trace == child_trace
        assert parent_trace != ""


class TestExportToLogs:
    def test_span_emits_log_on_finish(self, capture_logs):
        tracer = Tracer("test")
        with tracer.start_as_current_span("op", attributes={"foo": "bar"}):
            pass
        # The log was emitted with span_completed message
        records = [r for r in capture_logs.records if "span_completed" in r.message]
        assert len(records) == 1

    def test_log_contains_trace_metadata(self, capture_logs):
        tracer = Tracer("test")
        with tracer.start_as_current_span("op") as span:
            span.set_attribute("user.id", 42)
        record = next(r for r in capture_logs.records if "span_completed" in r.message)
        # Metadata is in the message body as JSON
        body = record.message.split("span_completed ", 1)[1]
        payload = json.loads(body)
        assert payload["span_trace_id"] == span.trace_id
        assert payload["span_id"] == span.span_id
        assert payload["span_name"] == "op"
        assert payload["span_status"] == "ok"
        assert payload["span_attributes"]["user.id"] == 42

    def test_error_span_logs_at_error_level(self, capture_logs):
        tracer = Tracer("test")
        try:
            with tracer.start_as_current_span("fail"):
                raise ValueError("nope")
        except ValueError:
            pass
        record = next(r for r in capture_logs.records if "span_completed" in r.message)
        assert record.levelname == "ERROR"
        import json

        body = record.message.split("span_completed ", 1)[1]
        payload = json.loads(body)
        assert payload["span_status"] == "error"


class TestRootSpan:
    def test_root_span_creates_new_trace(self, capture_logs):
        with root_span("incoming_request") as span:
            assert span.parent_id is None
            assert get_current_trace_id() == span.trace_id

    def test_root_inside_root_uses_new_trace(self, capture_logs):
        """Nested root_span creates a child of the first."""
        with root_span("outer") as outer:
            with root_span("inner") as inner:
                # inner is a child of outer (it has the outer trace_id)
                assert inner.trace_id == outer.trace_id
                assert inner.parent_id == outer.span_id


class TestGetCurrentTraceId:
    def test_empty_when_no_active_span(self):
        # Clear any active state
        from app.core.tracing import _current_trace_id

        _current_trace_id.set("")
        assert get_current_trace_id() == ""

    def test_returns_trace_id_within_span(self):
        from app.core.tracing import _current_span

        _current_span.set(None)
        with tracer_backend.start_as_current_span("op") as span:
            assert get_current_trace_id() == span.trace_id


class TestRealApiRequestTracing:
    """Simulate a real request flow."""

    def test_simulated_db_query_chain(self, capture_logs):
        tracer = Tracer("api")
        with tracer.start_as_current_span("GET /api/v1/sales-orders") as request_span:
            request_span.set_attribute("http.method", "GET")
            request_span.set_attribute("http.path", "/api/v1/sales-orders")

            # DB query
            with tracer.start_as_current_span("db.query") as db_span:
                db_span.set_attribute(
                    "db.statement", "SELECT * FROM sales_orders LIMIT 20"
                )
                db_span.set_attribute("db.rows", 20)
                time.sleep(0.001)

            # AI call
            with tracer.start_as_current_span("ai.summarize") as ai_span:
                ai_span.set_attribute("ai.model", "MiniMax-M3")
                ai_span.set_attribute("ai.tokens", 500)
                time.sleep(0.001)

        # All 3 spans share the same trace_id
        assert request_span.trace_id == db_span.trace_id == ai_span.trace_id

        # Hierarchy
        assert db_span.parent_id == request_span.span_id
        assert ai_span.parent_id == request_span.span_id
