"""Lightweight in-process metrics — counters, gauges, histograms.

No external dependencies. Thread-safe via the GIL. Values are kept in
process memory and reset on restart. To export to Prometheus, install
`prometheus_client` and replace these primitives with `Counter`/`Histogram`
from that package — the metric names and labels remain stable.

API:
    counter = Counter("orders_confirmed_total", "...", ["tier"])
    counter.inc(tier="A")

    histogram = Histogram("ai_call_duration_seconds", "...", ["agent"])
    with histogram.time(agent="customer"):
        ...
"""

from collections import defaultdict
from contextlib import contextmanager
import threading
import time


# Optional prometheus_client integration (Stage 9 Day 2).
# If installed, every inc/set/observe is mirrored to prometheus_client,
# so /metrics/prometheus can export via prometheus_client.generate_latest().
# If not installed, falls back to in-process dict (no behavior change).
try:
    from prometheus_client import Counter as _PCounter, Gauge as _PGauge, Histogram as _PHistogram

    _PROM_AVAILABLE = True
except ImportError:  # pragma: no cover - import-time
    _PROM_AVAILABLE = False


class Counter:
    """Monotonic counter with optional labels.

    Stage 9 Day 2: mirrors writes to prometheus_client when available,
    so /metrics/prometheus can include business metrics in the same
    text exposition as process metrics. Backed by an in-process dict
    for value()/snapshot() (used by /metrics JSON endpoint).
    """

    def __init__(self, name: str, doc: str, labels: list[str] | None = None) -> None:
        self.name = name
        self.doc = doc
        self.labels = labels or []
        self._values: dict[tuple, float] = defaultdict(float)
        self._lock = threading.Lock()
        self._prom: "_PCounter | None" = None
        if _PROM_AVAILABLE:
            try:
                # prometheus_client enforces name pattern [a-zA-Z_:][a-zA-Z0-9_:]*
                self._prom = _PCounter(name, doc, list(self.labels))
            except ValueError:
                # name already registered (re-import in tests) — reuse
                from prometheus_client import REGISTRY as _REG

                for collector in list(_REG._collector_to_names.keys()):  # type: ignore[attr-defined]
                    if name in _REG._names_to_collectors:  # type: ignore[attr-defined]
                        self._prom = _REG._names_to_collectors[name]  # type: ignore[attr-defined]
                        break

    def inc(self, amount: float = 1.0, **label_values) -> None:
        if list(label_values.keys()) != self.labels:
            raise ValueError(
                f"Counter {self.name} expects labels {self.labels}, got {list(label_values.keys())}"
            )
        key = tuple(label_values[label] for label in self.labels)
        with self._lock:
            self._values[key] += amount
        if self._prom is not None and self.labels:
            try:
                self._prom.labels(**label_values).inc(amount)
            except Exception:  # pragma: no cover - defensive
                pass
        elif self._prom is not None:
            try:
                self._prom.inc(amount)
            except Exception:  # pragma: no cover - defensive
                pass

    def value(self, **label_values) -> float:
        key = tuple(label_values[label] for label in self.labels)
        return self._values.get(key, 0.0)

    def snapshot(self) -> dict:
        """Return current values as {labels: value} dict."""
        with self._lock:
            return {k: v for k, v in self._values.items()}


class Gauge:
    """Gauge that can increase/decrease. Stage 9 Day 2: also writes to prometheus_client."""

    def __init__(self, name: str, doc: str, labels: list[str] | None = None) -> None:
        self.name = name
        self.doc = doc
        self.labels = labels or []
        self._values: dict[tuple, float] = defaultdict(float)
        self._lock = threading.Lock()
        self._prom: "_PGauge | None" = None
        if _PROM_AVAILABLE:
            try:
                self._prom = _PGauge(name, doc, list(self.labels))
            except ValueError:
                self._prom = None  # name registered; set/inc still work via in-process

    def set(self, value: float, **label_values) -> None:
        key = tuple(label_values[label] for label in self.labels)
        with self._lock:
            self._values[key] = value
        if self._prom is not None:
            try:
                self._prom.labels(**label_values).set(value)
            except Exception:  # pragma: no cover
                pass

    def inc(self, amount: float = 1.0, **label_values) -> None:
        key = tuple(label_values[label] for label in self.labels)
        with self._lock:
            self._values[key] += amount
        if self._prom is not None:
            try:
                self._prom.labels(**label_values).inc(amount)
            except Exception:  # pragma: no cover
                pass

    def dec(self, amount: float = 1.0, **label_values) -> None:
        key = tuple(label_values[label] for label in self.labels)
        with self._lock:
            self._values[key] -= amount
        if self._prom is not None:
            try:
                self._prom.labels(**label_values).dec(amount)
            except Exception:  # pragma: no cover
                pass

    def value(self, **label_values) -> float:
        key = tuple(label_values[label] for label in self.labels)
        return self._values.get(key, 0.0)

    def snapshot(self) -> dict:
        with self._lock:
            return {k: v for k, v in self._values.items()}


class Histogram:
    """Histogram with predefined buckets (in seconds). Stage 9 Day 2: also writes to prometheus_client."""

    DEFAULT_BUCKETS = (0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0)

    def __init__(
        self,
        name: str,
        doc: str,
        labels: list[str] | None = None,
        buckets: tuple = DEFAULT_BUCKETS,
    ) -> None:
        self.name = name
        self.doc = doc
        self.labels = labels or []
        self.buckets = tuple(sorted(buckets))
        # {label_tuple: {"counts": [bucket_counts], "sum": total_sum, "count": total_count}}
        self._values: dict[tuple, dict] = {}
        self._lock = threading.Lock()
        self._prom: "_PHistogram | None" = None
        if _PROM_AVAILABLE:
            try:
                self._prom = _PHistogram(name, doc, list(self.labels), buckets=list(self.buckets))
            except ValueError:
                self._prom = None  # already registered

    def observe(self, value: float, **label_values) -> None:
        if list(label_values.keys()) != self.labels:
            raise ValueError(
                f"Histogram {self.name} expects labels {self.labels}, got {list(label_values.keys())}"
            )
        key = tuple(label_values[label] for label in self.labels)
        with self._lock:
            if key not in self._values:
                self._values[key] = {
                    "counts": [0] * (len(self.buckets) + 1),  # +1 for +Inf
                    "sum": 0.0,
                    "count": 0,
                }
            slot = self._values[key]
            placed = False
            for i, b in enumerate(self.buckets):
                if value <= b:
                    slot["counts"][i] += 1
                    placed = True
                    break
            if not placed:
                slot["counts"][-1] += 1
            slot["sum"] += value
            slot["count"] += 1
        if self._prom is not None:
            try:
                self._prom.labels(**label_values).observe(value)
            except Exception:  # pragma: no cover
                pass

    @contextmanager
    def time(self, **label_values):
        start = time.perf_counter()
        try:
            yield
        finally:
            self.observe(time.perf_counter() - start, **label_values)

    def snapshot(self) -> dict:
        with self._lock:
            return {k: dict(v) for k, v in self._values.items()}


# ── Business metrics ──────────────────────────────────────────────────────

orders_confirmed_total = Counter(
    "orders_confirmed_total",
    "Total sales orders confirmed.",
    labels=["customer_tier"],
)

orders_cancelled_total = Counter(
    "orders_cancelled_total",
    "Total sales orders cancelled.",
    labels=["previous_status", "reason"],
)

inventory_reserved_total = Counter(
    "inventory_reserved_total",
    "Total successful stock reservations.",
    labels=["product_category"],
)

inventory_release_failures_total = Counter(
    "inventory_release_failures_total",
    "Total stock release failures on order cancel.",
)

inventory_concurrent_conflicts_total = Counter(
    "inventory_concurrent_conflicts_total",
    "Total optimistic-lock conflicts on inventory.",
)

ai_call_duration_seconds = Histogram(
    "ai_call_duration_seconds",
    "AI call latency.",
    labels=["agent", "outcome"],
)

event_dispatch_duration_seconds = Histogram(
    "event_dispatch_duration_seconds",
    "Domain event dispatch latency.",
    labels=["event_type"],
)

domain_events_total = Counter(
    "domain_events_total",
    "Total domain events published.",
    labels=["event_type"],
)

domain_errors_total = Counter(
    "domain_errors_total",
    "Total domain errors raised.",
    labels=["error_type"],
)

# ── Cache metrics ─────────────────────────────────────────────────────────

cache_hits_total = Counter(
    "cache_hits_total",
    "Total cache hits, labeled by cache family.",
    labels=["family"],
)

cache_misses_total = Counter(
    "cache_misses_total",
    "Total cache misses, labeled by cache family.",
    labels=["family"],
)

cache_invalidations_total = Counter(
    "cache_invalidations_total",
    "Total cache invalidations (version bumps or deletes).",
    labels=["family"],
)

cache_hit_ratio = Gauge(
    "cache_hit_ratio",
    "Cache hit ratio (hits / (hits + misses)) per family. Sampled by the metrics endpoint.",
    labels=["family"],
)

cache_lookup_duration_seconds = Histogram(
    "cache_lookup_duration_seconds",
    "Cache lookup latency.",
    labels=["family", "outcome"],
)


def reset_all() -> None:
    for m in (
        orders_confirmed_total,
        orders_cancelled_total,
        inventory_reserved_total,
        inventory_release_failures_total,
        inventory_concurrent_conflicts_total,
        domain_events_total,
        domain_errors_total,
        cache_hits_total,
        cache_misses_total,
        cache_invalidations_total,
    ):
        m._values.clear()  # type: ignore[attr-defined]
    for g in (cache_hit_ratio,):
        g._values.clear()  # type: ignore[attr-defined]
    for h in (
        ai_call_duration_seconds,
        event_dispatch_duration_seconds,
        cache_lookup_duration_seconds,
    ):
        h._values.clear()  # type: ignore[attr-defined]


def all_snapshots() -> dict:
    """Return all metric values — for debugging or export."""
    return {
        "counters": {
            m.name: m.snapshot()  # type: ignore[attr-defined]
            for m in (
                orders_confirmed_total,
                orders_cancelled_total,
                inventory_reserved_total,
                inventory_release_failures_total,
                inventory_concurrent_conflicts_total,
                domain_events_total,
                domain_errors_total,
                cache_hits_total,
                cache_misses_total,
                cache_invalidations_total,
            )
        },
        "gauges": {
            g.name: g.snapshot()  # type: ignore[attr-defined]
            for g in (cache_hit_ratio,)
        },
        "histograms": {
            h.name: h.snapshot()  # type: ignore[attr-defined]
            for h in (
                ai_call_duration_seconds,
                event_dispatch_duration_seconds,
                cache_lookup_duration_seconds,
            )
        },
    }


def render_prometheus_text() -> str:
    """Render all metrics in Prometheus text exposition format.

    Compatible with `prometheus_client` textfile collector. Sample:

        # HELP orders_confirmed_total Total sales orders confirmed.
        # TYPE orders_confirmed_total counter
        orders_confirmed_total{customer_tier="A"} 5.0
        orders_confirmed_total{customer_tier="B"} 3.0

        # HELP ai_call_duration_seconds AI call latency.
        # TYPE ai_call_duration_seconds histogram
        ai_call_duration_seconds_bucket{agent="x",outcome="success",le="0.005"} 0
        ...
    """
    lines: list[str] = []

    counter_docs: dict[str, str] = {
        "orders_confirmed_total": "Total sales orders confirmed.",
        "orders_cancelled_total": "Total sales orders cancelled.",
        "inventory_reserved_total": "Total successful stock reservations.",
        "inventory_release_failures_total": "Total stock release failures on order cancel.",
        "inventory_concurrent_conflicts_total": "Total optimistic-lock conflicts on inventory.",
        "domain_events_total": "Total domain events published.",
        "domain_errors_total": "Total domain errors raised.",
        "cache_hits_total": "Total cache hits.",
        "cache_misses_total": "Total cache misses.",
        "cache_invalidations_total": "Total cache invalidations.",
    }
    gauge_docs: dict[str, str] = {
        "cache_hit_ratio": "Cache hit ratio per family (hits / total).",
    }
    histogram_docs: dict[str, str] = {
        "ai_call_duration_seconds": "AI call latency.",
        "event_dispatch_duration_seconds": "Domain event dispatch latency.",
        "cache_lookup_duration_seconds": "Cache lookup latency.",
    }

    counters = {
        "orders_confirmed_total": orders_confirmed_total,
        "orders_cancelled_total": orders_cancelled_total,
        "inventory_reserved_total": inventory_reserved_total,
        "inventory_release_failures_total": inventory_release_failures_total,
        "inventory_concurrent_conflicts_total": inventory_concurrent_conflicts_total,
        "domain_events_total": domain_events_total,
        "domain_errors_total": domain_errors_total,
        "cache_hits_total": cache_hits_total,
        "cache_misses_total": cache_misses_total,
        "cache_invalidations_total": cache_invalidations_total,
    }
    gauges = {
        "cache_hit_ratio": cache_hit_ratio,
    }

    for name, counter in counters.items():
        doc = counter_docs[name]
        lines.append(f"# HELP {name} {doc}")
        lines.append(f"# TYPE {name} counter")
        labels = counter.labels  # type: ignore[attr-defined]
        snap = counter.snapshot()  # type: ignore[attr-defined]
        for label_tuple, value in sorted(snap.items()):
            label_str = ",".join(
                f'{label}="{_escape_label(value)}"'
                for label, value in zip(labels, label_tuple)
            )
            lines.append(f"{name}{{{label_str}}} {_format_value(value)}")
        lines.append("")

    for name, gauge in gauges.items():
        doc = gauge_docs[name]
        lines.append(f"# HELP {name} {doc}")
        lines.append(f"# TYPE {name} gauge")
        labels = gauge.labels  # type: ignore[attr-defined]
        snap = gauge.snapshot()  # type: ignore[attr-defined]
        for label_tuple, value in sorted(snap.items()):
            label_str = ",".join(
                f'{label}="{_escape_label(value)}"'
                for label, value in zip(labels, label_tuple)
            )
            lines.append(f"{name}{{{label_str}}} {_format_value(value)}")
        lines.append("")

    histograms = {
        "ai_call_duration_seconds": ai_call_duration_seconds,
        "event_dispatch_duration_seconds": event_dispatch_duration_seconds,
    }
    for name, hist in histograms.items():
        doc = histogram_docs[name]
        labels = hist.labels  # type: ignore[attr-defined]
        buckets = hist.buckets  # type: ignore[attr-defined]
        lines.append(f"# HELP {name} {doc}")
        lines.append(f"# TYPE {name} histogram")
        snap = hist.snapshot()  # type: ignore[attr-defined]
        for label_tuple, slot in sorted(snap.items()):
            base_label_str = ",".join(
                f'{label}="{_escape_label(value)}"'
                for label, value in zip(labels, label_tuple)
            )
            cumulative = 0
            for b, count in zip(buckets, slot["counts"]):
                cumulative += count
                le_label = f'le="{_format_bucket(b)}"'
                if base_label_str:
                    full = f"{base_label_str},{le_label}"
                else:
                    full = le_label
                lines.append(f"{name}_bucket{{{full}}} {cumulative}")
            # +Inf bucket
            cumulative += slot["counts"][-1] if False else 0
            le_label = 'le="+Inf"'
            if base_label_str:
                full = f"{base_label_str},{le_label}"
            else:
                full = le_label
            lines.append(f"{name}_bucket{{{full}}} {slot['count']}")
            # sum and count
            if base_label_str:
                lines.append(
                    f"{name}_sum{{{base_label_str}}} {_format_value(slot['sum'])}"
                )
                lines.append(f"{name}_count{{{base_label_str}}} {slot['count']}")
            else:
                lines.append(f"{name}_sum {_format_value(slot['sum'])}")
                lines.append(f"{name}_count {slot['count']}")
        lines.append("")

    return "\n".join(lines)


def _escape_label(value) -> str:
    """Escape label values per Prometheus spec."""
    s = str(value)
    return s.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n")


def _format_value(v) -> str:
    """Format a numeric value for Prometheus text."""
    if isinstance(v, float):
        return f"{v:g}"
    return str(v)


def _format_bucket(b) -> str:
    """Format histogram bucket boundary."""
    if isinstance(b, float):
        return f"{b:g}"
    return str(b)
