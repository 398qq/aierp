"""Pydantic schemas for expiry alert API responses.

Stage 18 / Production Batch Management.
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class ExpiringBatch(BaseModel):
    """A batch that is expiring (or already expired)."""

    id: int
    batch_no: str
    product_id: int
    warehouse_id: int
    quantity: int
    unit_cost: float
    expiry_date: datetime | None = None
    received_date: datetime | None = None
    msl_level: str | None = None
    rohs_compliant: bool
    status: str
    days_until_expiry: int | None = None


class ExpiryScanResponse(BaseModel):
    """Scan result, bucketed."""

    buckets: dict[str, list[ExpiringBatch]] = Field(default_factory=dict)
    total: int
    generated_at: datetime


class ExpiryBucketSummary(BaseModel):
    """One row in the dashboard widget."""

    name: str
    label: str
    severity: str
    count: int


class ExpirySummaryResponse(BaseModel):
    """Dashboard widget payload."""

    total_expiring: int
    counts_by_bucket: dict[str, int]
    buckets: list[ExpiryBucketSummary]