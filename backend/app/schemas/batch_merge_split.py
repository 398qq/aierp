"""Pydantic schemas for batch merge / split API.

Stage 18 P5 / Production Batch Management.
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class MergeRequest(BaseModel):
    """Request body for POST /inventory/batches/merge."""

    batch_ids: list[int] = Field(
        ..., min_length=2,
        description="要合并的批次 id 列表（≥ 2 个，必须同 product+batch_no+warehouse）",
    )
    reason: str = Field(..., min_length=1, description="合并原因（必填）")
    actor: str | None = Field(None, description="操作人；省略时使用当前认证用户")


class MergeResponse(BaseModel):
    """Response payload for a successful merge."""

    survivor_batch_id: int
    consumed_batch_ids: list[int]
    survivor_batch_no: str
    product_id: int
    warehouse_id: int
    total_quantity: int
    weighted_unit_cost: float
    merged_count: int
    reason: str
    actor: str


class SplitRequest(BaseModel):
    """Request body for POST /inventory/batches/{id}/split."""

    quantity: int = Field(..., gt=0, description="拆分数量（必须 < 源数量）")
    new_batch_no: str | None = Field(
        None, description="新 batch 编号；省略时自动生成 -S1, -S2..."
    )
    reason: str = Field(..., min_length=1, description="拆分原因（必填）")
    actor: str | None = Field(None, description="操作人；省略时使用当前认证用户")


class SplitResponse(BaseModel):
    """Response payload for a successful split."""

    src_batch_id: int
    src_warehouse_id: int
    src_remaining: int
    new_batch_id: int
    new_batch_no: str
    new_quantity: int
    new_unit_cost: float
    quantity_split: int
    reason: str
    actor: str
    src_audit_txn_id: int
    new_audit_txn_id: int