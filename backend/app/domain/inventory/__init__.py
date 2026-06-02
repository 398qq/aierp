"""Inventory domain — cost strategies, batch tracking, allocation policies."""

from app.domain.inventory.batch import (
    AllocationResult,
    BatchAllocation,
    BatchStatus,
    InventoryBatch,
    allocate_fefo,
    allocate_fifo_by_received,
    mark_expired_batches,
)
from app.domain.inventory.cost_strategy import (
    CostStrategy,
    FIFOBatch,
    FIFOCost,
    FIFOCostTracker,
    StandardCost,
    WeightedAverageCost,
    make_cost_strategy,
)

__all__ = [
    "CostStrategy",
    "FIFOBatch",
    "FIFOCost",
    "FIFOCostTracker",
    "StandardCost",
    "WeightedAverageCost",
    "make_cost_strategy",
    "BatchStatus",
    "InventoryBatch",
    "BatchAllocation",
    "AllocationResult",
    "allocate_fefo",
    "allocate_fifo_by_received",
    "mark_expired_batches",
]
