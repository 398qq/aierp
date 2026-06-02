"""Observability — metrics, tracing, structured logging.

This module is a lightweight in-process metrics implementation that has
no external dependencies. If `prometheus_client` is installed, it can
be plugged in by replacing the metric types in `prometheus_compat.py`.

Metrics exposed:
- `orders_confirmed_total{customer_tier}` — counter
- `orders_cancelled_total{reason}` — counter
- `inventory_reserved_total{product_category}` — counter
- `inventory_release_failures_total` — counter
- `ai_call_duration_seconds{agent, outcome}` — histogram
- `slow_query_total` — counter
- `event_dispatch_duration_seconds{event_type}` — histogram
"""
