"""Pydantic schemas for batch transfer API.

Stage 18 P4 / Production Batch Management.
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class TransferRequest(BaseModel):
    """Request body for POST /inventory/batches/{id}/transfer."""

    dst_warehouse_id: int = Field(
        ..., gt=0, description="目标仓库 id（必须不同于源仓库）"
    )
    quantity: int = Field(..., gt=0, description="调拨数量（必须 > 0）")
    reason: str = Field(
        ..., min_length=1, description="调拨原因（必填，写入审计字段）"
    )
    actor: str | None = Field(
        None, description="操作人；省略时使用当前认证用户"
    )


class TransferResponse(BaseModel):
    """Response payload for a successful transfer."""

    src_batch_id: int
    src_warehouse_id: int
    src_remaining: int
    dst_batch_id: int
    dst_warehouse_id: int
    dst_quantity: int
    quantity_transferred: int
    new_dst_batch_created: bool
    reason: str
    actor: str
    src_txn_id: int
    dst_txn_id: int