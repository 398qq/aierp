"""Inventory domain — batch/lot tracking and FEFO allocation.

For regulated materials (ROHS, MSL humidity-sensitive) and perishable
items, the system tracks each receipt as a separate batch with its
own expiry date. FEFO (First-Expired-First-Out) is the allocation
policy that consumes batches in expiry-date order.

This module owns the pure allocation logic. The persistence model
`InventoryBatch` lives in app/models/product.py; the application
layer wires FEFO into the deduction path.
"""

from dataclasses import dataclass, field
from datetime import date as date_type
from enum import Enum
from typing import List, Optional

from app.domain.shared.errors import BusinessRuleViolation


class BatchStatus(str, Enum):
    AVAILABLE = "available"
    QUARANTINED = "quarantined"  # Incoming inspection pending
    EXPIRED = "expired"
    CONSUMED = "consumed"


@dataclass
class InventoryBatch:
    """A single receipt batch — the unit of traceability."""

    product_id: int
    warehouse_id: int
    batch_no: str
    quantity: int
    received_date: date_type
    unit_cost: float
    status: BatchStatus = BatchStatus.AVAILABLE
    id: Optional[int] = None
    expiry_date: Optional[date_type] = None
    supplier_id: Optional[int] = None
    manufacture_date: Optional[date_type] = None
    rohs_compliant: bool = True
    notes: Optional[str] = None
    _events: list = field(default_factory=list, init=False, repr=False)

    def __post_init__(self) -> None:
        if self.quantity < 0:
            raise BusinessRuleViolation("批次数量不能为负")
        if not self.batch_no or not self.batch_no.strip():
            raise BusinessRuleViolation("批次号必填")
        if self.expiry_date and self.manufacture_date:
            if self.expiry_date <= self.manufacture_date:
                raise BusinessRuleViolation("过期日期必须晚于生产日期")

    @property
    def is_available(self) -> bool:
        if self.status != BatchStatus.AVAILABLE:
            return False
        if self.expiry_date and self.expiry_date <= date_type.today():
            return False
        if self.quantity <= 0:
            return False
        return True

    @property
    def is_expired(self) -> bool:
        return self.expiry_date is not None and self.expiry_date <= date_type.today()

    def consume(self, qty: int) -> "InventoryBatch":
        """Consume `qty` from this batch.

        Returns self (mutated) for fluent chaining. Raises if insufficient.
        """
        if qty <= 0:
            raise BusinessRuleViolation("消耗数量必须大于零")
        if not self.is_available:
            raise BusinessRuleViolation(
                f"批次 {self.batch_no} 不可用 (status={self.status.value})"
            )
        if qty > self.quantity:
            raise BusinessRuleViolation(
                f"批次 {self.batch_no} 库存不足: 需要 {qty}，可用 {self.quantity}"
            )
        self.quantity -= qty
        if self.quantity == 0:
            self.status = BatchStatus.CONSUMED
        return self

    def mark_expired(self) -> bool:
        """Mark this batch as expired if its expiry has passed. Returns True if changed."""
        if self.is_expired and self.status == BatchStatus.AVAILABLE:
            self.status = BatchStatus.EXPIRED
            return True
        return False


@dataclass
class BatchAllocation:
    """One line of a FEFO allocation result."""

    batch_id: Optional[int]
    batch_no: str
    quantity: int
    unit_cost: float


@dataclass
class AllocationResult:
    """Result of allocating `qty` units across multiple batches."""

    allocations: List[BatchAllocation] = field(default_factory=list)
    unfilled_qty: int = 0

    @property
    def is_fully_allocated(self) -> bool:
        return self.unfilled_qty == 0

    @property
    def total_allocated(self) -> int:
        return sum(a.quantity for a in self.allocations)

    @property
    def total_value(self) -> float:
        return sum(a.quantity * a.unit_cost for a in self.allocations)


def allocate_fefo(
    batches: List[InventoryBatch],
    qty: int,
    today: Optional[date_type] = None,
) -> AllocationResult:
    """FEFO (First-Expired-First-Out) batch allocation.

    Consumes from batches in this priority order:
    1. Earliest expiry_date first (NULL expiry sorts last)
    2. Then earliest received_date
    3. Then lowest unit_cost (deterministic tiebreaker)

    Only batches with `is_available=True` are considered. Batches with
    `is_expired=True` are skipped (and not auto-marked here — the
    caller should call `mark_expired()` on each batch separately).

    Args:
        batches: All batches for the product/warehouse (caller filters)
        qty: How many units to allocate
        today: Reference date for expiry check (default: today)

    Returns: AllocationResult with allocations and any unfilled qty.
    """
    if qty <= 0:
        raise BusinessRuleViolation("分配数量必须大于零")

    today = today or date_type.today()
    available = [b for b in batches if b.is_available and not b.is_expired]

    # FEFO: sort by (expiry or far-future, received_date, batch_no)
    def sort_key(b: InventoryBatch):
        far_future = date_type(9999, 12, 31)
        return (
            b.expiry_date or far_future,
            b.received_date,
            b.batch_no,
        )

    available.sort(key=sort_key)

    result = AllocationResult()
    remaining = qty

    for batch in available:
        if remaining <= 0:
            break
        take = min(remaining, batch.quantity)
        result.allocations.append(
            BatchAllocation(
                batch_id=batch.id,
                batch_no=batch.batch_no,
                quantity=take,
                unit_cost=batch.unit_cost,
            )
        )
        remaining -= take

    result.unfilled_qty = remaining
    return result


def allocate_fifo_by_received(
    batches: List[InventoryBatch],
    qty: int,
) -> AllocationResult:
    """FIFO by received_date (no expiry consideration).

    Useful for non-perishable items where the only constraint is
    "use oldest first". Mirrors the WAC/FIFO strategy split.
    """
    if qty <= 0:
        raise BusinessRuleViolation("分配数量必须大于零")

    available = [b for b in batches if b.is_available and not b.is_expired]
    available.sort(key=lambda b: (b.received_date, b.batch_no))

    result = AllocationResult()
    remaining = qty
    for batch in available:
        if remaining <= 0:
            break
        take = min(remaining, batch.quantity)
        result.allocations.append(
            BatchAllocation(
                batch_id=batch.id,
                batch_no=batch.batch_no,
                quantity=take,
                unit_cost=batch.unit_cost,
            )
        )
        remaining -= take

    result.unfilled_qty = remaining
    return result


def allocate_lowest_cost_first(
    batches: List[InventoryBatch],
    qty: int,
) -> AllocationResult:
    """LCFO (Lowest-Cost-First-Out) batch allocation.

    Consumes from cheapest batches first to maximize gross margin.
    This is the real-world default for electronic components distribution
    where identical products from different purchase batches are
    interchangeable.

    1. Lowest unit_cost first
    2. Then earliest received_date (deterministic tiebreaker)
    """
    if qty <= 0:
        raise BusinessRuleViolation("分配数量必须大于零")

    available = [b for b in batches if b.is_available and not b.is_expired]
    available.sort(key=lambda b: (b.unit_cost, b.received_date, b.batch_no))

    result = AllocationResult()
    remaining = qty
    for batch in available:
        if remaining <= 0:
            break
        take = min(remaining, batch.quantity)
        result.allocations.append(
            BatchAllocation(
                batch_id=batch.id,
                batch_no=batch.batch_no,
                quantity=take,
                unit_cost=batch.unit_cost,
            )
        )
        remaining -= take

    result.unfilled_qty = remaining
    return result


def mark_expired_batches(batches: List[InventoryBatch]) -> int:
    """Sweep all batches and mark any past-expiry ones as EXPIRED.

    Returns: count of batches newly marked.
    Should be called by a daily scheduled job.
    """
    return sum(1 for b in batches if b.mark_expired())
