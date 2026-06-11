"""Tests for batch tracking and FEFO/FIFO allocation."""

from datetime import date, timedelta

import pytest

from app.domain.inventory import (
    AllocationResult,
    BatchStatus,
    InventoryBatch,
    allocate_fefo,
    allocate_fifo_by_received,
    mark_expired_batches,
)
from app.domain.shared.errors import BusinessRuleViolation


def _batch(
    batch_no: str = "B001",
    qty: int = 100,
    received: date | None = None,
    expiry: date | None = None,
    cost: float = 10.0,
    status: BatchStatus = BatchStatus.AVAILABLE,
) -> InventoryBatch:
    return InventoryBatch(
        product_id=1,
        warehouse_id=1,
        batch_no=batch_no,
        quantity=qty,
        received_date=received or date(2026, 1, 1),
        unit_cost=cost,
        expiry_date=expiry,
        status=status,
    )


class TestInventoryBatchBasics:
    def test_constructs_with_required_fields(self):
        b = _batch()
        assert b.batch_no == "B001"
        assert b.quantity == 100
        assert b.is_available is True

    def test_rejects_negative_quantity(self):
        with pytest.raises(BusinessRuleViolation, match="数量不能为负"):
            _batch(qty=-1)

    def test_rejects_empty_batch_no(self):
        with pytest.raises(BusinessRuleViolation, match="批次号必填"):
            _batch(batch_no="")

    def test_rejects_expiry_before_manufacture(self):
        with pytest.raises(BusinessRuleViolation, match="过期日期必须晚于"):
            b = _batch(
                received=date(2026, 1, 1),
                expiry=date(2026, 12, 31),
            )
            b.manufacture_date = date(2027, 1, 1)  # After expiry
            b.__post_init__()


class TestBatchAvailability:
    def test_available_when_status_available_and_not_expired(self):
        b = _batch(expiry=date.today() + timedelta(days=30))
        assert b.is_available is True

    def test_unavailable_when_quarantined(self):
        b = _batch(status=BatchStatus.QUARANTINED)
        assert b.is_available is False

    def test_unavailable_when_expired(self):
        b = _batch(expiry=date.today() - timedelta(days=1))
        assert b.is_available is False

    def test_unavailable_when_quantity_zero(self):
        b = _batch(qty=0)
        assert b.is_available is False

    def test_no_expiry_means_no_expiry_check(self):
        b = _batch(expiry=None)
        assert b.is_available is True


class TestBatchConsume:
    def test_consume_partial(self):
        b = _batch(qty=100)
        b.consume(30)
        assert b.quantity == 70
        assert b.status == BatchStatus.AVAILABLE

    def test_consume_full_marks_consumed(self):
        b = _batch(qty=10)
        b.consume(10)
        assert b.quantity == 0
        assert b.status == BatchStatus.CONSUMED

    def test_consume_more_than_available_raises(self):
        b = _batch(qty=50)
        with pytest.raises(BusinessRuleViolation, match="库存不足"):
            b.consume(100)

    def test_consume_zero_rejected(self):
        b = _batch()
        with pytest.raises(BusinessRuleViolation, match="必须大于零"):
            b.consume(0)

    def test_consume_from_quarantined_raises(self):
        b = _batch(status=BatchStatus.QUARANTINED)
        with pytest.raises(BusinessRuleViolation, match="不可用"):
            b.consume(1)

    def test_consume_from_expired_raises(self):
        b = _batch(expiry=date.today() - timedelta(days=1))
        with pytest.raises(BusinessRuleViolation, match="不可用"):
            b.consume(1)


class TestBatchMarkExpired:
    def test_marks_past_expiry(self):
        b = _batch(expiry=date.today() - timedelta(days=1))
        changed = b.mark_expired()
        assert changed is True
        assert b.status == BatchStatus.EXPIRED

    def test_does_not_mark_future_expiry(self):
        b = _batch(expiry=date.today() + timedelta(days=30))
        changed = b.mark_expired()
        assert changed is False
        assert b.status == BatchStatus.AVAILABLE

    def test_does_not_mark_already_expired(self):
        b = _batch(expiry=date.today() - timedelta(days=1), status=BatchStatus.EXPIRED)
        changed = b.mark_expired()
        assert changed is False

    def test_sweep_function_returns_count(self):
        batches = [
            _batch(batch_no="A", expiry=date.today() - timedelta(days=1)),
            _batch(batch_no="B", expiry=date.today() + timedelta(days=30)),
            _batch(batch_no="C", expiry=date.today() - timedelta(days=10)),
        ]
        n = mark_expired_batches(batches)
        assert n == 2
        assert batches[0].status == BatchStatus.EXPIRED
        assert batches[1].status == BatchStatus.AVAILABLE
        assert batches[2].status == BatchStatus.EXPIRED


class TestFEFOAllocation:
    def test_consumes_earliest_expiry_first(self):
        batches = [
            _batch(batch_no="LATE", expiry=date(2027, 6, 1), qty=50),
            _batch(batch_no="EARLY", expiry=date(2026, 12, 1), qty=50),
            _batch(batch_no="MID", expiry=date(2027, 3, 1), qty=50),
        ]
        result = allocate_fefo(batches, qty=30)
        assert len(result.allocations) == 1
        assert result.allocations[0].batch_no == "EARLY"
        assert result.allocations[0].quantity == 30
        assert result.unfilled_qty == 0

    def test_spans_multiple_batches(self):
        today = date.today()
        batches = [
            _batch(batch_no="B1", expiry=today + timedelta(days=30), qty=20),
            _batch(batch_no="B2", expiry=today + timedelta(days=180), qty=30),
        ]
        result = allocate_fefo(batches, qty=35)
        assert len(result.allocations) == 2
        assert result.allocations[0].batch_no == "B1"
        assert result.allocations[0].quantity == 20
        assert result.allocations[1].batch_no == "B2"
        assert result.allocations[1].quantity == 15
        assert result.unfilled_qty == 0

    def test_unfilled_when_insufficient(self):
        batches = [_batch(batch_no="B1", qty=10)]
        result = allocate_fefo(batches, qty=50)
        assert result.total_allocated == 10
        assert result.unfilled_qty == 40

    def test_skips_expired_batches(self):
        batches = [
            _batch(batch_no="EXPIRED", expiry=date(2026, 1, 1), qty=100),
            _batch(batch_no="GOOD", expiry=date(2027, 1, 1), qty=50),
        ]
        # Force EXPIRED batch status (otherwise is_expired already filters it)
        batches[0].status = BatchStatus.EXPIRED
        result = allocate_fefo(batches, qty=30)
        assert len(result.allocations) == 1
        assert result.allocations[0].batch_no == "GOOD"

    def test_skips_quarantined_batches(self):
        batches = [
            _batch(batch_no="Q", status=BatchStatus.QUARANTINED, qty=100),
            _batch(batch_no="OK", qty=50),
        ]
        result = allocate_fefo(batches, qty=20)
        assert result.allocations[0].batch_no == "OK"

    def test_no_expiry_sorts_last(self):
        batches = [
            _batch(batch_no="NO_EXP", expiry=None, qty=10),
            _batch(batch_no="WITH_EXP", expiry=date(2099, 1, 1), qty=10),
        ]
        result = allocate_fefo(batches, qty=5)
        assert result.allocations[0].batch_no == "WITH_EXP"

    def test_total_value_calculates_correctly(self):
        today = date.today()
        batches = [
            _batch(batch_no="A", qty=10, cost=5.0, expiry=today + timedelta(days=30)),
            _batch(batch_no="B", qty=10, cost=10.0, expiry=today + timedelta(days=180)),
        ]
        result = allocate_fefo(batches, qty=15)
        # 10 @ 5.0 + 5 @ 10.0 = 100
        assert result.total_value == 100.0

    def test_rejects_zero_qty(self):
        with pytest.raises(BusinessRuleViolation):
            allocate_fefo([], qty=0)

    def test_rejects_negative_qty(self):
        with pytest.raises(BusinessRuleViolation):
            allocate_fefo([], qty=-1)

    def test_is_fully_allocated_property(self):
        batches = [_batch(qty=100)]
        result = allocate_fefo(batches, qty=50)
        assert result.is_fully_allocated is True

    def test_unfilled_qty_property(self):
        batches = [_batch(qty=10)]
        result = allocate_fefo(batches, qty=20)
        assert result.is_fully_allocated is False
        assert result.unfilled_qty == 10


class TestFIFOByReceivedAllocation:
    def test_consumes_oldest_received_first(self):
        batches = [
            _batch(batch_no="NEW", received=date(2026, 6, 1), qty=50),
            _batch(batch_no="OLD", received=date(2026, 1, 1), qty=50),
        ]
        result = allocate_fifo_by_received(batches, qty=20)
        assert result.allocations[0].batch_no == "OLD"

    def test_ignores_expiry(self):
        """FIFO by received_date should consume in arrival order regardless of expiry."""
        batches = [
            _batch(
                batch_no="EXPIRES_SOON",
                received=date(2026, 6, 1),
                expiry=date(2026, 7, 1),
                qty=10,
            ),
            _batch(
                batch_no="EXPIRES_LATER",
                received=date(2026, 1, 1),
                expiry=date(2030, 1, 1),
                qty=10,
            ),
        ]
        result = allocate_fifo_by_received(batches, qty=5)
        # FIFO by received_date → OLDER (EXPIRES_LATER) comes first
        assert result.allocations[0].batch_no == "EXPIRES_LATER"


class TestAllocationResultHelpers:
    def test_total_allocated_empty(self):
        r = AllocationResult()
        assert r.total_allocated == 0
        assert r.total_value == 0

    def test_unfilled_starts_zero(self):
        r = AllocationResult()
        assert r.unfilled_qty == 0
        assert r.is_fully_allocated is True
