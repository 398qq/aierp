"""Customer AI — text/time cleaners and bounded value coercion.

Pure helpers; no I/O. The original `customer_ai` module re-declared each of
these at module scope, which made them impossible to import for unit tests
without pulling in OCR dependencies. They live here so `recognition.py`,
`insights.py`, and `work_queue.py` can share a single cleaner module.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any


def clean_choice(value: Any, allowed: set[str] | frozenset[str]) -> str | None:
    """Return ``value`` if it is a non-empty string in ``allowed``, else ``None``."""
    if not value:
        return None
    normalized = str(value).strip()
    return normalized if normalized in allowed else None


def clean_text(value: Any) -> str | None:
    """Return trimmed string or ``None`` for empty/None input."""
    if value is None:
        return None
    normalized = str(value).strip()
    return normalized or None


def clean_datetime_text(value: Any) -> str | None:
    """Coerce ISO-ish string to ``YYYY-MM-DD HH:MM:SS`` (UTC-naive)."""
    if not value:
        return None
    normalized = str(value).strip().replace("T", " ")
    if not normalized:
        return None
    try:
        return datetime.fromisoformat(normalized).strftime("%Y-%m-%d %H:%M:%S")
    except ValueError:
        return None


def clean_confidence(value: Any) -> float:
    """Coerce a value into [0.0, 1.0]; invalid → 0.0."""
    try:
        confidence = float(value)
    except (TypeError, ValueError):
        return 0.0
    return max(0.0, min(1.0, confidence))


def round_metric(value: float) -> float:
    return round(float(value), 2)


def clean_float(value: Any) -> float | None:
    """Coerce to non-negative float; None/invalid/negative → ``None``."""
    if value in (None, ""):
        return None
    try:
        amount = float(value)
    except (TypeError, ValueError):
        return None
    return amount if amount >= 0 else None


def safe_float(value: Any) -> float:
    """Coerce to float; ``None``/invalid → 0.0. Never raises."""
    try:
        if value is None:
            return 0.0
        return float(value)
    except Exception:
        return 0.0


def to_utc(dt_value: datetime | None) -> datetime | None:
    """Treat naive datetimes as UTC and convert aware datetimes to UTC."""
    if dt_value is None:
        return None
    if dt_value.tzinfo is None:
        return dt_value.replace(tzinfo=timezone.utc)
    return dt_value.astimezone(timezone.utc)


def days_since(dt_value: datetime | None, now: datetime) -> int:
    """Calendar days between ``dt_value`` and ``now`` (sentinel 999 for None)."""
    value = to_utc(dt_value)
    if value is None:
        return 999
    return max(0, (now - value).days)


__all__ = [
    "clean_choice",
    "clean_text",
    "clean_datetime_text",
    "clean_confidence",
    "clean_float",
    "round_metric",
    "safe_float",
    "to_utc",
    "days_since",
]
