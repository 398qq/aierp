"""JSON serialization helpers for orchestration services."""

import datetime


def _safe_json(obj):
    """Convert objects to JSON-safe dicts, handling datetime etc."""
    if obj is None:
        return None
    if isinstance(obj, (datetime.datetime, datetime.date)):
        return obj.isoformat()
    return str(obj)