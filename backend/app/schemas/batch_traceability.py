"""Pydantic schemas for batch traceability API responses.

Stage 18 / Production Batch Management.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class BatchCoreInfo(BaseModel):
    """Core inventory batch info with product / supplier / warehouse names."""

    id: int
    batch_no: str
    product_id: int
    product_name: str | None = None
    product_sku: str | None = None
    warehouse_id: int
    warehouse_name: str | None = None
    supplier_id: int | None = None
    supplier_name: str | None = None
    quantity: int
    locked_quantity: int
    unit_cost: float
    received_date: datetime | None = None
    manufacture_date: datetime | None = None
    expiry_date: datetime | None = None
    status: str
    rohs_compliant: bool
    msl_level: str | None = None
    certificate_url: str | None = None
    notes: str | None = None


class StockInRecord(BaseModel):
    """A stock_in inventory transaction linked to a batch (receipt history)."""

    id: int
    reference_type: str | None = None
    reference_id: int | None = None
    quantity: int
    before_qty: int | None = None
    after_qty: int | None = None
    created_at: datetime | None = None
    notes: str | None = None


class PurchaseOrderRef(BaseModel):
    """Lightweight PO reference (used in upstream traceability)."""

    id: int
    po_no: str | None = None
    supplier_id: int | None = None
    status: str | None = None
    order_date: datetime | None = None
    expected_date: datetime | None = None
    total_amount: float = 0.0


class UpstreamInfo(BaseModel):
    """Who supplied this batch + how it was received."""

    supplier: dict[str, Any] | None = None
    purchase_orders: list[PurchaseOrderRef] = Field(default_factory=list)
    stock_in_records: list[StockInRecord] = Field(default_factory=list)


class DeliveryConsumption(BaseModel):
    """A delivery note that consumed qty from this batch."""

    transaction_id: int
    transaction_at: datetime | None = None
    quantity: int
    delivery_note_id: int | None = None
    delivery_no: str | None = None
    sales_order_id: int | None = None
    sales_order_no: str | None = None
    customer_id: int | None = None
    customer_name: str | None = None


class DownstreamInfo(BaseModel):
    """Where this batch has gone (deliveries, customers, totals)."""

    deliveries: list[DeliveryConsumption] = Field(default_factory=list)
    customers: list[dict[str, Any]] = Field(default_factory=list)
    total_consumed: int = 0
    remaining_qty: int = 0
    delivery_count: int = 0
    customer_count: int = 0


class BatchTraceabilityResponse(BaseModel):
    """Top-level traceability response — batch + upstream + downstream."""

    batch: BatchCoreInfo
    upstream: UpstreamInfo
    downstream: DownstreamInfo