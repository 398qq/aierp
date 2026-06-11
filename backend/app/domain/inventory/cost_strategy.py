"""Cost accounting strategies — Weighted Average, FIFO, Standard.

This module owns inventory cost calculation. Different industries prefer
different methods:

- **Weighted Average (WAC)**: Smooths price volatility. Best for
  commodity-like inventory (resistors, capacitors, ICs). Recommended
  default for electronic components.
- **FIFO**: First-in-first-out. Required by IFRS for some categories.
  Tracks each purchase batch's cost separately.
- **Standard Cost**: Pre-set cost per item, variances analyzed
  separately. Best for mass production.

The strategy pattern lets the application pick a method per warehouse
or per product, without changing the inventory update path.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal
from typing import List, Tuple


class CostStrategy(ABC):
    """Strategy interface for inventory costing methods."""

    name: str = ""

    @abstractmethod
    def compute_new_unit_cost(
        self,
        current_qty: Decimal,
        current_avg_cost: Decimal,
        incoming_qty: Decimal,
        incoming_unit_cost: Decimal,
    ) -> Decimal:
        """Compute the new unit cost after receiving `incoming_qty` units.

        Returns: new unit cost per item, rounded to 4 decimal places.
        """


class WeightedAverageCost(CostStrategy):
    """Moving weighted-average cost.

    After receiving a new batch, the per-unit cost becomes:

        new_cost = (current_qty × current_cost + incoming_qty × incoming_cost)
                   / (current_qty + incoming_qty)

    This is the GAAP-recommended method for fungible inventory where
    individual units are interchangeable.
    """

    name = "weighted_average"
    QUANTIZE = Decimal("0.0001")  # 4 decimal places

    def compute_new_unit_cost(
        self,
        current_qty: Decimal,
        current_avg_cost: Decimal,
        incoming_qty: Decimal,
        incoming_unit_cost: Decimal,
    ) -> Decimal:
        if current_qty < 0 or incoming_qty < 0:
            raise ValueError("quantities must be non-negative")
        if incoming_unit_cost < 0:
            raise ValueError("unit cost must be non-negative")
        if current_qty == 0 and incoming_qty == 0:
            return Decimal("0")
        if current_qty == 0:
            # No previous stock — new cost is the incoming cost
            return incoming_unit_cost.quantize(self.QUANTIZE, rounding=ROUND_HALF_UP)
        if incoming_qty == 0:
            # No new stock — cost unchanged
            return current_avg_cost.quantize(self.QUANTIZE, rounding=ROUND_HALF_UP)

        total_value = (current_qty * current_avg_cost) + (
            incoming_qty * incoming_unit_cost
        )
        total_qty = current_qty + incoming_qty
        new_cost = (total_value / total_qty).quantize(
            self.QUANTIZE, rounding=ROUND_HALF_UP
        )
        return new_cost


class FIFOCost(CostStrategy):
    """First-In-First-Out cost — delegates to per-batch storage.

    The actual FIFO math happens at deduction time, walking through
    batches in chronological order. This strategy class only computes
    the new cost for the *incoming* batch (which is always the
    incoming unit cost).

    For deduction, the application layer must call
    `FIFOCostTracker.deduct(qty)` which maintains the batch queue.
    """

    name = "fifo"

    def compute_new_unit_cost(
        self,
        current_qty: Decimal,
        current_avg_cost: Decimal,
        incoming_qty: Decimal,
        incoming_unit_cost: Decimal,
    ) -> Decimal:
        # FIFO doesn't recompute aggregate cost on receipt
        return incoming_unit_cost.quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)


class StandardCost(CostStrategy):
    """Pre-set standard cost per item.

    Receipts do NOT change the standard cost; the variance between
    standard and actual goes to a separate Purchase Price Variance
    account. This is the recommended approach for mass production
    but uncommon in electronic components distribution.
    """

    name = "standard"

    def __init__(self, standard_unit_cost: Decimal) -> None:
        if standard_unit_cost < 0:
            raise ValueError("standard cost must be non-negative")
        self._standard = standard_unit_cost

    def compute_new_unit_cost(
        self,
        current_qty: Decimal,
        current_avg_cost: Decimal,
        incoming_qty: Decimal,
        incoming_unit_cost: Decimal,
    ) -> Decimal:
        return self._standard.quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)

    @property
    def standard_cost(self) -> Decimal:
        return self._standard

    def compute_variance(self, actual_cost: Decimal) -> Decimal:
        """Return Purchase Price Variance = actual - standard × qty=1."""
        return (actual_cost - self._standard).quantize(
            Decimal("0.0001"), rounding=ROUND_HALF_UP
        )


@dataclass
class FIFOBatch:
    """A FIFO purchase batch with its specific cost."""

    qty: Decimal
    unit_cost: Decimal


class FIFOCostTracker:
    """Tracks FIFO batches for deduction in arrival order.

    Used by the inventory deduction path to compute the exact COGS
    by consuming oldest batches first.
    """

    def __init__(self) -> None:
        self._batches: List[FIFOBatch] = []

    def add_batch(self, qty: Decimal, unit_cost: Decimal) -> None:
        if qty <= 0:
            raise ValueError("batch qty must be positive")
        self._batches.append(FIFOBatch(qty=Decimal(qty), unit_cost=Decimal(unit_cost)))

    def deduct(self, qty: Decimal) -> Tuple[Decimal, List[Tuple[Decimal, Decimal]]]:
        """Deduct `qty` from the oldest batches first.

        Returns: (total_cogs, [(consumed_qty, unit_cost), ...])
        """
        if qty <= 0:
            raise ValueError("deduct qty must be positive")
        remaining = Decimal(qty)
        total_cogs = Decimal("0")
        consumed: List[Tuple[Decimal, Decimal]] = []
        for batch in list(self._batches):
            if remaining <= 0:
                break
            consumed_qty = min(remaining, batch.qty)
            line_cogs = (consumed_qty * batch.unit_cost).quantize(
                Decimal("0.01"), rounding=ROUND_HALF_UP
            )
            total_cogs += line_cogs
            consumed.append((consumed_qty, batch.unit_cost))
            batch.qty -= consumed_qty
            remaining -= consumed_qty
        if remaining > 0:
            raise ValueError(
                f"Insufficient FIFO stock: tried to deduct {qty}, "
                f"only {qty - remaining} available"
            )
        # Prune empty batches
        self._batches = [b for b in self._batches if b.qty > 0]
        return total_cogs, consumed


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------


def make_cost_strategy(name: str, **kwargs) -> CostStrategy:
    """Construct a cost strategy by name.

    Args:
        name: "weighted_average" | "fifo" | "standard"
        standard_unit_cost: required for "standard"

    Raises:
        ValueError: on unknown name or missing args.
    """
    name = name.lower()
    if name == "weighted_average":
        return WeightedAverageCost()
    if name == "fifo":
        return FIFOCost()
    if name == "standard":
        if "standard_unit_cost" not in kwargs:
            raise ValueError("standard cost requires standard_unit_cost kwarg")
        return StandardCost(kwargs["standard_unit_cost"])
    raise ValueError(f"Unknown cost strategy: {name!r}")
