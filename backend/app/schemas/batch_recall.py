"""Pydantic schemas for batch recall API responses.

Stage 18 / Production Batch Management.
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class RecallRequest(BaseModel):
    """Request body for POST /inventory/batches/{id}/recall."""

    reason: str = Field(
        ...,
        min_length=1,
        description="召回原因（必填，会写入审计字段）",
    )
    actor: str | None = Field(
        None,
        description="操作人；省略时使用当前认证用户",
    )


class RecallAck(BaseModel):
    """Audit metadata for a completed recall."""

    previous_status: str
    reason: str
    actor: str


class RecallImpactResponse(BaseModel):
    """Response payload for both preview and post-recall endpoints."""

    batch: dict
    affected_customers: list[dict] = Field(default_factory=list)
    deliveries: list[dict] = Field(default_factory=list)
    customer_count: int = 0
    delivery_count: int = 0
    total_quantity_consumed: int = 0
    frozen_remaining: int = 0
    recall: RecallAck | None = None