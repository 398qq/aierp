"""Tests for Prometheus text exposition format."""

import pytest

from app.core.observability.metrics import (
    ai_call_duration_seconds,
    orders_cancelled_total,
    orders_confirmed_total,
    render_prometheus_text,
    reset_all,
)


@pytest.fixture(autouse=True)
def _reset():
    reset_all()
    yield
    reset_all()


class TestRenderPrometheusText:
    def test_empty_render(self):
        text = render_prometheus_text()
        # Headers should still be present
        assert "# HELP orders_confirmed_total" in text
        assert "# TYPE orders_confirmed_total counter" in text
        assert "# HELP ai_call_duration_seconds" in text
        assert "# TYPE ai_call_duration_seconds histogram" in text

    def test_counter_line_format(self):
        orders_confirmed_total.inc(customer_tier="A")
        orders_confirmed_total.inc(customer_tier="A")
        orders_confirmed_total.inc(customer_tier="B")
        text = render_prometheus_text()
        assert 'orders_confirmed_total{customer_tier="A"} 2' in text
        assert 'orders_confirmed_total{customer_tier="B"} 1' in text

    def test_multi_label_counter(self):
        orders_cancelled_total.inc(
            previous_status="confirmed", reason="customer_request"
        )
        orders_cancelled_total.inc(
            previous_status="confirmed", reason="customer_request"
        )
        text = render_prometheus_text()
        assert (
            'orders_cancelled_total{previous_status="confirmed",reason="customer_request"} 2'
            in text
        )

    def test_histogram_renders_buckets(self):
        ai_call_duration_seconds.observe(0.005, agent="customer", outcome="success")
        ai_call_duration_seconds.observe(0.5, agent="customer", outcome="success")
        ai_call_duration_seconds.observe(5.0, agent="customer", outcome="error")
        text = render_prometheus_text()
        # Buckets are cumulative
        # success: 0.005 falls in le=0.005, 0.5 falls in le=0.5
        # So le=0.005 has 1, le=0.5 has 2, le=+Inf has 2
        assert (
            'ai_call_duration_seconds_bucket{agent="customer",outcome="success",le="0.005"} 1'
            in text
        )
        assert (
            'ai_call_duration_seconds_bucket{agent="customer",outcome="success",le="0.5"} 2'
            in text
        )
        assert (
            'ai_call_duration_seconds_bucket{agent="customer",outcome="success",le="+Inf"} 2'
            in text
        )
        # error: 5.0 is > 5 (boundary), so falls in le=+Inf
        assert (
            'ai_call_duration_seconds_bucket{agent="customer",outcome="error",le="+Inf"} 1'
            in text
        )
        # Sum and count
        assert (
            'ai_call_duration_seconds_count{agent="customer",outcome="success"} 2'
            in text
        )
        assert (
            'ai_call_duration_seconds_count{agent="customer",outcome="error"} 1' in text
        )

    def test_label_escaping(self):
        # Special characters in labels should be escaped
        orders_cancelled_total.inc(previous_status="x", reason='with "quotes"')
        text = render_prometheus_text()
        assert 'reason="with \\"quotes\\""' in text

    def test_text_format_is_valid_prometheus(self):
        # Each line should be: comment, type, sample (metric_name + value)
        # or empty
        orders_confirmed_total.inc(customer_tier="A")
        text = render_prometheus_text()
        for line in text.split("\n"):
            if not line or line.startswith("#"):
                continue
            # Sample lines: name{labels} value  OR  name value
            assert "{" in line  # Our metrics always have labels
            assert "}" in line
            parts = line.rsplit(" ", 1)
            assert len(parts) == 2
            metric_part, value = parts
            # Try to parse value as float
            try:
                float(value)
            except ValueError:
                pytest.fail(f"Value '{value}' is not numeric in line: {line}")
