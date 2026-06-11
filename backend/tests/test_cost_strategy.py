"""Tests for inventory cost strategies (WAC, FIFO, Standard)."""

from decimal import Decimal

import pytest

from app.domain.inventory import (
    FIFOCostTracker,
    StandardCost,
    WeightedAverageCost,
    make_cost_strategy,
)


def D(s: str | int | float) -> Decimal:
    return Decimal(str(s))


class TestWeightedAverageCost:
    def test_first_receipt_sets_cost(self):
        wac = WeightedAverageCost()
        cost = wac.compute_new_unit_cost(
            current_qty=D(0),
            current_avg_cost=D(0),
            incoming_qty=D(100),
            incoming_unit_cost=D(50),
        )
        assert cost == D("50.0000")

    def test_no_incoming_keeps_current_cost(self):
        wac = WeightedAverageCost()
        cost = wac.compute_new_unit_cost(
            current_qty=D(100),
            current_avg_cost=D(50),
            incoming_qty=D(0),
            incoming_unit_cost=D(99),
        )
        assert cost == D("50.0000")

    def test_both_zero_returns_zero(self):
        wac = WeightedAverageCost()
        cost = wac.compute_new_unit_cost(0, 0, 0, 0)
        assert cost == D("0")

    def test_standard_wac_calculation(self):
        """100 @ 50 + 100 @ 60 → new avg = 55"""
        wac = WeightedAverageCost()
        cost = wac.compute_new_unit_cost(
            current_qty=D(100),
            current_avg_cost=D(50),
            incoming_qty=D(100),
            incoming_unit_cost=D(60),
        )
        assert cost == D("55.0000")

    def test_wac_unequal_quantities(self):
        """10 @ 100 + 90 @ 50 → (1000 + 4500) / 100 = 55"""
        wac = WeightedAverageCost()
        cost = wac.compute_new_unit_cost(
            current_qty=D(10),
            current_avg_cost=D(100),
            incoming_qty=D(90),
            incoming_unit_cost=D(50),
        )
        assert cost == D("55.0000")

    def test_decimal_precision(self):
        """0.1 + 0.2 = 0.3 (no float drift)"""
        wac = WeightedAverageCost()
        cost = wac.compute_new_unit_cost(
            current_qty=D(1),
            current_avg_cost=D("0.1"),
            incoming_qty=D(1),
            incoming_unit_cost=D("0.2"),
        )
        # (1 * 0.1 + 1 * 0.2) / 2 = 0.15
        assert cost == D("0.1500")

    def test_three_way_blend(self):
        """Iterate receipt 1, 2, 3 — final cost should be 5.3333"""
        wac = WeightedAverageCost()
        cost = wac.compute_new_unit_cost(D(0), D(0), D(10), D(5))
        # After 1st: 10 @ 5 → 5.0
        cost = wac.compute_new_unit_cost(D(10), D(5), D(10), D(6))
        # After 2nd: 20 @ (10*5+10*6)/20 = 110/20 = 5.5
        cost = wac.compute_new_unit_cost(D(20), D("5.5"), D(10), D(5))
        # After 3rd: 30 @ (20*5.5+10*5)/30 = 160/30 = 5.3333
        assert cost == D("5.3333")

    def test_rejects_negative_quantities(self):
        wac = WeightedAverageCost()
        with pytest.raises(ValueError):
            wac.compute_new_unit_cost(D(-1), 0, 0, 0)
        with pytest.raises(ValueError):
            wac.compute_new_unit_cost(0, 0, D(-1), 0)

    def test_rejects_negative_unit_cost(self):
        wac = WeightedAverageCost()
        with pytest.raises(ValueError):
            wac.compute_new_unit_cost(0, 0, 10, D(-5))


class TestFIFOCost:
    def test_incoming_keeps_own_cost(self):
        from app.domain.inventory import FIFOCost

        fifo = FIFOCost()
        cost = fifo.compute_new_unit_cost(
            current_qty=D(100),
            current_avg_cost=D(50),
            incoming_qty=D(50),
            incoming_unit_cost=D(80),
        )
        assert cost == D("80.0000")


class TestFIFOCostTracker:
    def test_deduct_single_batch(self):
        t = FIFOCostTracker()
        t.add_batch(qty=10, unit_cost=D(5))
        cogs, consumed = t.deduct(7)
        assert cogs == D("35.00")
        assert consumed == [(D(7), D(5))]

    def test_deduct_spans_multiple_batches(self):
        t = FIFOCostTracker()
        t.add_batch(qty=5, unit_cost=D(10))
        t.add_batch(qty=10, unit_cost=D(12))
        cogs, consumed = t.deduct(8)
        # 5 @ 10 + 3 @ 12 = 50 + 36 = 86
        assert cogs == D("86.00")
        assert consumed == [(D(5), D(10)), (D(3), D(12))]
        # Remaining: 7 @ 12
        cogs2, _ = t.deduct(5)
        assert cogs2 == D("60.00")

    def test_deduct_more_than_available_raises(self):
        t = FIFOCostTracker()
        t.add_batch(qty=5, unit_cost=D(10))
        with pytest.raises(ValueError, match="Insufficient FIFO stock"):
            t.deduct(10)

    def test_deduct_zero_rejected(self):
        t = FIFOCostTracker()
        with pytest.raises(ValueError):
            t.deduct(0)

    def test_add_zero_qty_rejected(self):
        t = FIFOCostTracker()
        with pytest.raises(ValueError):
            t.add_batch(0, 10)

    def test_consume_all_batches(self):
        t = FIFOCostTracker()
        t.add_batch(qty=3, unit_cost=D(5))
        t.add_batch(qty=2, unit_cost=D(7))
        cogs, consumed = t.deduct(5)
        assert cogs == D("29.00")  # 15 + 14
        assert len(consumed) == 2
        # No stock left → error
        with pytest.raises(ValueError):
            t.deduct(1)


class TestStandardCost:
    def test_standard_cost_ignores_incoming(self):
        std = StandardCost(D(50))
        cost = std.compute_new_unit_cost(
            current_qty=D(100),
            current_avg_cost=D(50),
            incoming_qty=D(10),
            incoming_unit_cost=D(99),  # ignored
        )
        assert cost == D("50.0000")

    def test_standard_variance_calculation(self):
        std = StandardCost(D(50))
        # Actual is 60 → 10 over standard
        assert std.compute_variance(D(60)) == D("10.0000")
        # Actual is 45 → 5 under standard
        assert std.compute_variance(D(45)) == D("-5.0000")

    def test_standard_rejects_negative(self):
        with pytest.raises(ValueError):
            StandardCost(D(-1))

    def test_standard_cost_property(self):
        std = StandardCost(D(75.5))
        assert std.standard_cost == D("75.5")


class TestCostStrategyFactory:
    def test_make_wac(self):
        s = make_cost_strategy("weighted_average")
        assert isinstance(s, WeightedAverageCost)
        assert s.name == "weighted_average"

    def test_make_fifo(self):
        from app.domain.inventory import FIFOCost

        s = make_cost_strategy("fifo")
        assert isinstance(s, FIFOCost)

    def test_make_standard_requires_arg(self):
        with pytest.raises(ValueError, match="standard_unit_cost"):
            make_cost_strategy("standard")

    def test_make_standard_with_arg(self):
        s = make_cost_strategy("standard", standard_unit_cost=Decimal(50))
        assert isinstance(s, StandardCost)

    def test_unknown_strategy_raises(self):
        with pytest.raises(ValueError, match="Unknown cost strategy"):
            make_cost_strategy("lifo")  # LIFO is not allowed under IFRS

    def test_case_insensitive(self):
        s = make_cost_strategy("weighted_average")
        assert isinstance(s, WeightedAverageCost)


class TestCostStrategyContract:
    """Verify the CostStrategy ABC is properly defined."""

    def test_cannot_instantiate_abstract(self):
        from app.domain.inventory.cost_strategy import CostStrategy

        with pytest.raises(TypeError):
            CostStrategy()

    def test_subclass_must_implement_compute(self):
        from app.domain.inventory.cost_strategy import CostStrategy

        class Incomplete(CostStrategy):
            name = "incomplete"

        with pytest.raises(TypeError):
            Incomplete()
