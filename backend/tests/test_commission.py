"""Tests for Commission aggregate — state machine, Decimal math, validation."""

import pytest

from app.domain.shared.errors import InvalidStateTransition
from app.domain.states import (
    COMMISSION_STATUSES,
    COMMISSION_TRANSITIONS,
    assert_can_transition_commission,
)
from app.services.finance_service import _compute_commission_amount


class TestCommissionStateMachine:
    def test_legal_transitions_defined(self):
        assert "draft" in COMMISSION_TRANSITIONS
        assert "pending_approval" in COMMISSION_TRANSITIONS
        assert "approved" in COMMISSION_TRANSITIONS
        assert "paid" in COMMISSION_TRANSITIONS

    def test_draft_can_go_to_pending_approval(self):
        assert "pending_approval" in COMMISSION_TRANSITIONS["draft"]

    def test_draft_can_be_cancelled(self):
        assert "cancelled" in COMMISSION_TRANSITIONS["draft"]

    def test_pending_approval_can_be_approved(self):
        assert "approved" in COMMISSION_TRANSITIONS["pending_approval"]

    def test_pending_approval_can_be_rejected(self):
        assert "rejected" in COMMISSION_TRANSITIONS["pending_approval"]

    def test_approved_can_be_paid(self):
        assert "paid" in COMMISSION_TRANSITIONS["approved"]

    def test_paid_is_terminal(self):
        assert COMMISSION_TRANSITIONS["paid"] == set()

    def test_cancelled_is_terminal(self):
        assert COMMISSION_TRANSITIONS["cancelled"] == set()

    def test_legal_transition_passes(self):
        # Should not raise
        assert_can_transition_commission("draft", "pending_approval")
        assert_can_transition_commission("pending_approval", "approved")
        assert_can_transition_commission("approved", "paid")

    def test_illegal_transition_raises(self):
        with pytest.raises(InvalidStateTransition):
            assert_can_transition_commission("draft", "paid")  # skipping approval

    def test_paid_cannot_transition(self):
        with pytest.raises(InvalidStateTransition):
            assert_can_transition_commission("paid", "cancelled")

    def test_unknown_status_raises(self):
        with pytest.raises(InvalidStateTransition):
            assert_can_transition_commission("draft", "flying")


class TestCommissionAmountCalculation:
    def test_zero_rate(self):
        assert _compute_commission_amount(10000, 0) == 0

    def test_zero_base(self):
        assert _compute_commission_amount(0, 0.05) == 0

    def test_typical_calculation(self):
        # ¥10,000 base × 5% rate = ¥500
        assert _compute_commission_amount(10000, 0.05) == 500.0

    def test_high_rate(self):
        # ¥10,000 base × 100% rate = ¥10,000
        assert _compute_commission_amount(10000, 1.0) == 10000.0

    def test_decimal_precision(self):
        # ¥333.33 × 7.5% = ¥24.99975 → rounded to 6 decimals = ¥24.999750
        result = _compute_commission_amount(333.33, 0.075)
        assert abs(result - 24.999750) < 1e-6

    def test_no_float_drift(self):
        # Naive float math: 0.1 + 0.2 = 0.30000000000000004
        # Our Decimal path should give exact results
        result = _compute_commission_amount(1.0, 0.3)
        assert result == 0.3  # exact, not 0.30000000000000004

    def test_small_amount(self):
        # ¥0.01 × 50% = ¥0.005
        result = _compute_commission_amount(0.01, 0.5)
        assert abs(result - 0.005) < 1e-9


class TestCommissionValidation:
    def test_all_statuses_documented(self):
        # Every status in TRANSITIONS must also be in STATUSES
        for s in COMMISSION_TRANSITIONS:
            assert s in COMMISSION_STATUSES

    def test_terminal_states_have_no_outgoing(self):
        assert COMMISSION_TRANSITIONS["paid"] == set()
        assert COMMISSION_TRANSITIONS["cancelled"] == set()
