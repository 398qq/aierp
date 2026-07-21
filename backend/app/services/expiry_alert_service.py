"""Expiry alert service — Stage 18 / Production Batch Management.

Scans inventory batches approaching or past their expiry date, bucketed into:
  - expired   (expiry_date < today)
  - 7d        (within next 7 days)
  - 30d       (within next 8–30 days)
  - 90d       (within next 31–90 days)

Excludes consumed / recalled batches. Powers the dashboard widget and the
scheduled notification job.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, cast

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.product import InventoryBatchORM

logger = logging.getLogger(__name__)


def _iso(value: Any) -> str | None:
    """Serialize datetime-like value to ISO 8601 string (or None)."""
    return value.isoformat() if value is not None else None


# ── constants ────────────────────────────────────────────────────────

EXPIRED = "expired"
BUCKET_7D = "7d"
BUCKET_30D = "30d"
BUCKET_90D = "90d"

VALID_BUCKETS = {EXPIRED, BUCKET_7D, BUCKET_30D, BUCKET_90D}


@dataclass(frozen=True)
class ExpiryBucket:
    """Time window for an expiry alert bucket."""

    name: str
    label: str
    severity: str  # 'critical' | 'high' | 'medium' | 'low'
    days_min: int  # inclusive
    days_max: int  # inclusive; for 'expired' this is 0 (today is included)


BUCKETS: dict[str, ExpiryBucket] = {
    EXPIRED: ExpiryBucket(EXPIRED, "已过期", "critical", days_min=-36500, days_max=0),
    BUCKET_7D: ExpiryBucket(BUCKET_7D, "7天内到期", "high", days_min=1, days_max=7),
    BUCKET_30D: ExpiryBucket(BUCKET_30D, "30天内到期", "medium", days_min=8, days_max=30),
    BUCKET_90D: ExpiryBucket(BUCKET_90D, "90天内到期", "low", days_min=31, days_max=90),
}


# ── service ─────────────────────────────────────────────────────────


class ExpiryAlertService:
    """Scan inventory batches for upcoming / past expiry dates."""

    async def scan(
        self,
        db: AsyncSession,
        *,
        buckets: list[str] | None = None,
        warehouse_id: int | None = None,
        limit_per_bucket: int = 100,
        now: datetime | None = None,
    ) -> dict[str, list[dict[str, Any]]]:
        """Return a dict bucket_name → list of batch records, ordered by expiry.

        Args:
            buckets: subset of valid bucket names; defaults to all four.
            warehouse_id: optional warehouse filter.
            limit_per_bucket: cap per bucket to avoid huge payloads.
            now: reference time (defaults to UTC now). Useful for tests.
        """
        now = now or datetime.now(timezone.utc)
        buckets = buckets or list(VALID_BUCKETS)
        unknown = [b for b in buckets if b not in VALID_BUCKETS]
        if unknown:
            raise ValueError(f"未知 bucket: {unknown}; 合法值: {sorted(VALID_BUCKETS)}")

        result: dict[str, list[dict[str, Any]]] = {b: [] for b in buckets}

        # Stage 19 P1 #2: collapse the 4-bucket loop into a single query with
        # a CASE-WHEN bucket label, then group in Python. Replaces 4 DB
        # roundtrips with 1 (4x latency win on cold connections).
        from sqlalchemy import case  # local import keeps top tidy

        bucket_expr = case(
            (InventoryBatchORM.expiry_date < now, EXPIRED),
            (
                InventoryBatchORM.expiry_date <= now + timedelta(days=7),
                BUCKET_7D,
            ),
            (
                InventoryBatchORM.expiry_date <= now + timedelta(days=30),
                BUCKET_30D,
            ),
            (
                InventoryBatchORM.expiry_date <= now + timedelta(days=90),
                BUCKET_90D,
            ),
            else_=None,
        ).label("bucket")

        # Wide outer window: from deepest expired through 90d ahead.
        stmt = (
            select(InventoryBatchORM, bucket_expr)
            .where(
                and_(
                    InventoryBatchORM.expiry_date.is_not(None),
                    InventoryBatchORM.expiry_date
                    >= now + timedelta(days=BUCKETS[EXPIRED].days_min),
                    InventoryBatchORM.expiry_date
                    <= now + timedelta(days=BUCKETS[BUCKET_90D].days_max),
                    InventoryBatchORM.quantity > 0,
                    InventoryBatchORM.status.notin_(["consumed", "recalled"]),
                )
            )
            .order_by(InventoryBatchORM.expiry_date.asc())
        )
        if warehouse_id is not None:
            stmt = stmt.where(InventoryBatchORM.warehouse_id == warehouse_id)

        rows = (await db.execute(stmt)).all()
        today = now.date()
        for batch, bucket_name in rows:
            if bucket_name is None or bucket_name not in result:
                continue
            if len(result[bucket_name]) >= limit_per_bucket:
                continue
            # Calendar-day diff (stable under clock drift).
            expiry_py = cast(datetime | None, batch.expiry_date)
            days_until = (
                (expiry_py.date() - today).days if expiry_py else None
            )
            result[bucket_name].append(
                {
                    "id": batch.id,
                    "batch_no": batch.batch_no,
                    "product_id": batch.product_id,
                    "warehouse_id": batch.warehouse_id,
                    "quantity": batch.quantity,
                    "unit_cost": float(batch.unit_cost or 0),
                    "expiry_date": _iso(batch.expiry_date),
                    "received_date": _iso(batch.received_date),
                    "msl_level": batch.msl_level,
                    "rohs_compliant": batch.rohs_compliant,
                    "status": batch.status,
                    "days_until_expiry": days_until,
                }
            )

        logger.info(
            "Expiry scan (1-query)Expiry scan complete: buckets=%s, totals=%s",
            buckets,
            {b: len(v) for b, v in result.items()},
        )
        return result

    async def get_summary(
        self,
        db: AsyncSession,
        *,
        warehouse_id: int | None = None,
        now: datetime | None = None,
    ) -> dict[str, Any]:
        """Return a summary for the dashboard widget."""
        buckets_data = await self.scan(
            db,
            warehouse_id=warehouse_id,
            limit_per_bucket=10000,  # for counting only
            now=now,
        )
        counts = {b: len(v) for b, v in buckets_data.items()}
        total = sum(counts.values())
        return {
            "total_expiring": total,
            "counts_by_bucket": counts,
            "buckets": [
                {
                    "name": BUCKETS[b].name,
                    "label": BUCKETS[b].label,
                    "severity": BUCKETS[b].severity,
                    "count": counts[b],
                }
                for b in [EXPIRED, BUCKET_7D, BUCKET_30D, BUCKET_90D]
            ],
        }


# Module-level singleton.
expiry_alert_service = ExpiryAlertService()