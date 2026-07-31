"""Watchtower shared cache wrappers."""

import asyncio
import datetime
import hashlib
import json
import logging

from sqlalchemy.ext.asyncio import AsyncSession

from app.services.cache_service import (
    cache_get_versioned,
    cache_set_versioned,
)
from app.services import watchtower_service

logger = logging.getLogger(__name__)

DASHBOARD_SCAN_CACHE_TTL = 300  # 5 min
DASHBOARD_REPORT_CACHE_TTL = 600  # 10 min


def _cache_key(**parts: object) -> str:
    canonical = json.dumps(parts, sort_keys=True, default=str)
    digest = hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:16]
    return f"watchtower:{digest}"


async def watchtower_cached_scan(
    db: AsyncSession,
    days_back: int,
    now: datetime.datetime,
) -> dict:
    """`now` is injected by the route layer (Clock pattern, CLAUDE.md bottom line).
    Routes are entry points; business logic receives the time, doesn't read it.
    """
    key = _cache_key(endpoint="scan", days_back=days_back)
    try:
        cached = await cache_get_versioned("watchtower:scan", key)
        if cached is not None:
            return json.loads(cached)
    except (json.JSONDecodeError, TypeError) as exc:
        logger.debug("watchtower.scan cache decode failed: %s", exc)

    lookback = now - datetime.timedelta(days=days_back)
    prev_lookback = lookback - datetime.timedelta(days=days_back)

    results = await asyncio.gather(
        watchtower_service.scan_churn_risk(db, lookback, prev_lookback),
        watchtower_service.scan_order_drop(db, lookback, prev_lookback),
        watchtower_service.scan_low_stock(db),
        watchtower_service.scan_out_of_stock(db),
        return_exceptions=True,
    )
    anomalies: dict[str, list[dict[str, object]]] = {}
    for key_name, scan_result in zip(
        ["churn_risk", "order_drop", "low_stock", "out_of_stock"],
        results,
        strict=False,
    ):
        if isinstance(scan_result, Exception):
            logger.warning(f"watchtower.scan.{key_name} failed: {scan_result}")
            anomalies[key_name] = []
        else:
            anomalies[key_name] = scan_result  # type: ignore[assignment]

    total_alerts = sum(len(v) for v in anomalies.values())
    ai = await watchtower_service.generate_ai_summary(anomalies, total_alerts)
    persisted = await watchtower_service._persist_customer_alerts(
        db, anomalies, now, lookback_days=days_back
    )

    result = {
        "scanned_at": now.isoformat(),
        "total_alerts": total_alerts,
        "severity": ai.get("severity", "正常"),
        "summary": ai.get("summary", ""),
        "top_actions": ai.get("top_actions", []),
        "risk_areas": ai.get("risk_areas", []),
        "alerts_persisted": persisted,
        "anomalies": anomalies,
    }

    await cache_set_versioned(
        "watchtower:scan",
        key,
        json.dumps(result, default=str),
        DASHBOARD_SCAN_CACHE_TTL,
    )
    return result


async def watchtower_cached_report(db: AsyncSession, now: datetime.datetime) -> dict:
    """Wrap /ai/daily-report. `now` is injected by the route (Clock pattern).
    TTL 600s; bumped by scheduler at midnight (task 9).
    """
    key = _cache_key(endpoint="report")
    try:
        cached = await cache_get_versioned("watchtower:report", key)
        if cached is not None:
            return json.loads(cached)
    except (json.JSONDecodeError, TypeError) as exc:
        logger.debug("watchtower.report cache decode failed: %s", exc)

    from app.api.v1.ai.watchtower import _compute_daily_report

    result = await _compute_daily_report(db, now)

    await cache_set_versioned(
        "watchtower:report",
        key,
        json.dumps(result, default=str),
        DASHBOARD_REPORT_CACHE_TTL,
    )
    return result
