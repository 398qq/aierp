"""Reusable datetime helpers.

Extracted from api/v1/customers/stats.py during Stage 1 refactor.
Centralized so services (not routes) own these primitives.
"""

from __future__ import annotations

from datetime import datetime, timezone


def safe_float(value) -> float:
    """Convert to float, returning 0.0 for None or unconvertible values."""
    try:
        if value is None:
            return 0.0
        return float(value)
    except Exception:
        return 0.0


def to_utc(dt_value: datetime | None) -> datetime | None:
    """Ensure a datetime is timezone-aware in UTC.

    Naive datetimes are assumed to be UTC (this matches the project convention
    where DB columns are stored as UTC).
    """
    if dt_value is None:
        return None
    if dt_value.tzinfo is None:
        return dt_value.replace(tzinfo=timezone.utc)
    return dt_value.astimezone(timezone.utc)


def days_since(dt_value: datetime | None, now: datetime) -> int:
    """Days between `dt_value` and `now`. Returns 999 when value is None."""
    value = to_utc(dt_value)
    if value is None:
        return 999
    return max(0, (now - value).days)
