"""Tests for the lightweight in-process metrics module."""

import pytest

from app.core.observability.metrics import (
    Counter,
    Gauge,
    Histogram,
    all_snapshots,
    domain_events_total,
    inventory_concurrent_conflicts_total,
    inventory_release_failures_total,
    orders_confirmed_total,
    reset_all,
)


class TestCounter:
    def test_inc_with_no_labels(self):
        c = Counter("test_total", "test")
        c.inc()
        c.inc()
        c.inc(2.0)
        assert c.value() == 4.0

    def test_inc_with_labels(self):
        c = Counter("test_total", "test", ["tier", "channel"])
        c.inc(tier="A", channel="web")
        c.inc(tier="A", channel="web")
        c.inc(tier="B", channel="api")
        assert c.value(tier="A", channel="web") == 2
        assert c.value(tier="B", channel="api") == 1
        assert c.value(tier="C", channel="x") == 0  # missing → 0

    def test_wrong_labels_raises(self):
        c = Counter("test_total", "test", ["tier"])
        with pytest.raises(ValueError, match="expects labels"):
            c.inc(wrong="A")

    def test_snapshot_returns_copy(self):
        c = Counter("test_total", "test", ["x"])
        c.inc(x="a")
        snap = c.snapshot()
        snap[("a",)] = 999
        assert c.value(x="a") == 1.0  # original unchanged


class TestGauge:
    def test_set_and_inc(self):
        g = Gauge("test_gauge", "test", ["env"])
        g.set(10, env="prod")
        g.inc(5, env="prod")
        g.dec(3, env="prod")
        assert g.value(env="prod") == 12

    def test_separate_labels(self):
        g = Gauge("test_gauge", "test", ["env"])
        g.set(10, env="prod")
        g.set(20, env="dev")
        assert g.value(env="prod") == 10
        assert g.value(env="dev") == 20


class TestHistogram:
    def test_observe_records_in_buckets(self):
        h = Histogram("test_dur", "test", ["op"], buckets=(0.1, 1.0))
        h.observe(0.05, op="a")  # ≤ 0.1
        h.observe(0.5, op="a")  # ≤ 1.0
        h.observe(5.0, op="a")  # > 1.0 → +Inf
        snap = h.snapshot()
        key = ("a",)
        assert snap[key]["count"] == 3
        assert snap[key]["sum"] == pytest.approx(5.55, abs=0.01)
        # buckets: 0.1, 1.0, +Inf — counts [1, 1, 1]
        assert snap[key]["counts"] == [1, 1, 1]

    def test_time_context_manager(self):
        h = Histogram("test_dur", "test", ["op"])
        import time

        with h.time(op="x"):
            time.sleep(0.01)
        snap = h.snapshot()
        assert snap[("x",)]["count"] == 1
        assert snap[("x",)]["sum"] > 0


class TestBusinessMetrics:
    def setup_method(self):
        reset_all()

    def test_orders_confirmed_increments(self):
        orders_confirmed_total.inc(customer_tier="A")
        orders_confirmed_total.inc(customer_tier="A")
        orders_confirmed_total.inc(customer_tier="B")
        snap = orders_confirmed_total.snapshot()
        assert snap[("A",)] == 2
        assert snap[("B",)] == 1

    def test_all_snapshots_structure(self):
        orders_confirmed_total.inc(customer_tier="A")
        domain_events_total.inc(event_type="OrderConfirmed")
        inventory_concurrent_conflicts_total.inc()
        snap = all_snapshots()
        assert "counters" in snap
        assert "histograms" in snap
        assert snap["counters"]["orders_confirmed_total"] == {("A",): 1.0}
        assert snap["counters"]["domain_events_total"] == {("OrderConfirmed",): 1.0}
        assert snap["counters"]["inventory_concurrent_conflicts_total"] == {(): 1.0}

    def test_reset_all_clears(self):
        orders_confirmed_total.inc(customer_tier="A")
        inventory_release_failures_total.inc()
        reset_all()
        assert orders_confirmed_total.snapshot() == {}
        assert inventory_release_failures_total.snapshot() == {}
