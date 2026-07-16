"""Unit tests for all sales/finance state machines.

Tests the assert_can_transition_*() functions — no DB, pure logic.
"""

import pytest
from app.domain.shared.errors import InvalidStateTransition
from app.domain.states import (
    assert_can_transition_contract,
    assert_can_transition_commission,
    assert_can_transition_delivery,
    assert_can_transition_invoice,
    assert_can_transition_opportunity,
    assert_can_transition_payment,
    assert_can_transition_quotation,
    assert_can_transition_sales_order,
)


# ── Helpers ────────────────────────────────────────────────────────────


def assert_ok(current: str, target: str, fn) -> None:
    """Assert transition is valid; raises AssertionError if it throws."""
    try:
        fn(current, target)
    except InvalidStateTransition as e:
        pytest.fail(
            f"Expected ok: {current} → {target}, got InvalidStateTransition: {e}"
        )


def assert_blocked(current: str, target: str, fn) -> None:
    """Assert transition is blocked."""
    with pytest.raises(InvalidStateTransition):
        fn(current, target)


# ── Opportunity ────────────────────────────────────────────────────────


class TestOpportunityStateMachine:
    """Opportunity: active → won | lost; lost → active."""

    def test_active_to_won(self):
        assert_ok("active", "won", assert_can_transition_opportunity)

    def test_active_to_lost(self):
        assert_ok("active", "lost", assert_can_transition_opportunity)

    def test_lost_to_active(self):
        assert_ok("lost", "active", assert_can_transition_opportunity)

    def test_won_is_terminal(self):
        assert_blocked("won", "active", assert_can_transition_opportunity)
        assert_blocked("won", "lost", assert_can_transition_opportunity)

    def test_lost_blocked_except_reopen(self):
        assert_blocked("lost", "won", assert_can_transition_opportunity)

    def test_unknown_status_rejected(self):
        assert_blocked("bogus", "active", assert_can_transition_opportunity)


# ── Quotation ──────────────────────────────────────────────────────────


class TestQuotationStateMachine:
    """draft → sent → accepted | rejected | expired → won."""

    def test_draft_to_sent(self):
        assert_ok("draft", "sent", assert_can_transition_quotation)

    def test_draft_to_won(self):
        assert_ok("draft", "won", assert_can_transition_quotation)

    def test_draft_to_rejected(self):
        assert_ok("draft", "rejected", assert_can_transition_quotation)

    def test_sent_to_accepted(self):
        assert_ok("sent", "accepted", assert_can_transition_quotation)

    def test_sent_to_rejected(self):
        assert_ok("sent", "rejected", assert_can_transition_quotation)

    def test_sent_to_expired(self):
        assert_ok("sent", "expired", assert_can_transition_quotation)

    def test_sent_to_won(self):
        assert_ok("sent", "won", assert_can_transition_quotation)

    def test_sent_to_lost(self):
        assert_ok("sent", "lost", assert_can_transition_quotation)

    def test_accepted_to_won(self):
        assert_ok("accepted", "won", assert_can_transition_quotation)

    def test_won_is_terminal(self):
        assert_blocked("won", "draft", assert_can_transition_quotation)
        assert_blocked("won", "sent", assert_can_transition_quotation)

    def test_rejected_is_terminal(self):
        assert_blocked("rejected", "sent", assert_can_transition_quotation)

    def test_lost_is_terminal(self):
        assert_blocked("lost", "sent", assert_can_transition_quotation)
        assert_blocked("lost", "won", assert_can_transition_quotation)

    def test_draft_cannot_jump_to_accepted(self):
        assert_blocked("draft", "accepted", assert_can_transition_quotation)


# ── SalesOrder ─────────────────────────────────────────────────────────


class TestSalesOrderStateMachine:
    """pending → confirmed → shipped → delivered → completed | cancelled.
    Legacy: draft → confirmed (synonym for pending), invoiced → completed."""

    # Canonical happy path
    def test_pending_to_confirmed(self):
        assert_ok("pending", "confirmed", assert_can_transition_sales_order)

    def test_confirmed_to_shipped(self):
        assert_ok("confirmed", "shipped", assert_can_transition_sales_order)

    def test_confirmed_to_partially_shipped(self):
        assert_ok("confirmed", "partially_shipped", assert_can_transition_sales_order)

    def test_partially_shipped_to_shipped(self):
        assert_ok("partially_shipped", "shipped", assert_can_transition_sales_order)

    def test_shipped_to_delivered(self):
        assert_ok("shipped", "delivered", assert_can_transition_sales_order)

    def test_shipped_to_completed(self):
        assert_ok("shipped", "completed", assert_can_transition_sales_order)

    def test_delivered_to_completed(self):
        assert_ok("delivered", "completed", assert_can_transition_sales_order)

    # Cancel at various stages
    def test_pending_to_cancelled(self):
        assert_ok("pending", "cancelled", assert_can_transition_sales_order)

    def test_confirmed_to_cancelled(self):
        assert_ok("confirmed", "cancelled", assert_can_transition_sales_order)

    def test_partially_shipped_to_cancelled(self):
        assert_ok("partially_shipped", "cancelled", assert_can_transition_sales_order)

    # Legacy v1 backward compat
    def test_legacy_draft_to_confirmed(self):
        assert_ok("draft", "confirmed", assert_can_transition_sales_order)

    def test_legacy_draft_to_cancelled(self):
        assert_ok("draft", "cancelled", assert_can_transition_sales_order)

    def test_legacy_invoiced_to_completed(self):
        assert_ok("invoiced", "completed", assert_can_transition_sales_order)

    # Terminal states
    def test_completed_is_terminal(self):
        assert_blocked("completed", "confirmed", assert_can_transition_sales_order)
        assert_blocked("completed", "delivered", assert_can_transition_sales_order)

    def test_cancelled_is_terminal(self):
        assert_blocked("cancelled", "pending", assert_can_transition_sales_order)
        assert_blocked("cancelled", "confirmed", assert_can_transition_sales_order)

    # Invalid jumps
    def test_pending_cannot_jump_to_shipped(self):
        assert_blocked("pending", "shipped", assert_can_transition_sales_order)

    def test_confirmed_cannot_jump_to_completed(self):
        assert_blocked("confirmed", "completed", assert_can_transition_sales_order)

    def test_shipped_cannot_reopen(self):
        assert_blocked("shipped", "confirmed", assert_can_transition_sales_order)

    def test_unknown_blocked(self):
        assert_blocked("bogus", "pending", assert_can_transition_sales_order)


# ── DeliveryNote ───────────────────────────────────────────────────────


class TestDeliveryNoteStateMachine:
    """pending → shipped → delivered | cancelled."""

    def test_pending_to_shipped(self):
        assert_ok("pending", "shipped", assert_can_transition_delivery)

    def test_pending_to_delivered(self):
        assert_ok("pending", "delivered", assert_can_transition_delivery)

    def test_pending_to_cancelled(self):
        assert_ok("pending", "cancelled", assert_can_transition_delivery)

    def test_shipped_to_delivered(self):
        assert_ok("shipped", "delivered", assert_can_transition_delivery)

    def test_shipped_to_cancelled(self):
        assert_ok("shipped", "cancelled", assert_can_transition_delivery)

    def test_delivered_is_terminal(self):
        assert_blocked("delivered", "pending", assert_can_transition_delivery)
        assert_blocked("delivered", "shipped", assert_can_transition_delivery)

    def test_cancelled_is_terminal(self):
        assert_blocked("cancelled", "pending", assert_can_transition_delivery)

    def test_unknown_blocked(self):
        assert_blocked("bogus", "pending", assert_can_transition_delivery)


# ── Invoice ────────────────────────────────────────────────────────────


class TestInvoiceStateMachine:
    """draft → issued → paid | cancelled. issued → overdue → paid."""

    def test_draft_to_issued(self):
        assert_ok("draft", "issued", assert_can_transition_invoice)

    def test_draft_to_cancelled(self):
        assert_ok("draft", "cancelled", assert_can_transition_invoice)

    def test_issued_to_paid(self):
        assert_ok("issued", "paid", assert_can_transition_invoice)

    def test_issued_to_cancelled(self):
        assert_ok("issued", "cancelled", assert_can_transition_invoice)

    def test_issued_to_overdue(self):
        assert_ok("issued", "overdue", assert_can_transition_invoice)

    def test_overdue_to_paid(self):
        assert_ok("overdue", "paid", assert_can_transition_invoice)

    def test_overdue_to_cancelled(self):
        assert_ok("overdue", "cancelled", assert_can_transition_invoice)

    def test_paid_is_terminal(self):
        assert_blocked("paid", "draft", assert_can_transition_invoice)

    def test_cancelled_is_terminal(self):
        assert_blocked("cancelled", "draft", assert_can_transition_invoice)

    def test_draft_cannot_jump_to_paid(self):
        assert_blocked("draft", "paid", assert_can_transition_invoice)

    def test_overdue_cannot_reopen(self):
        assert_blocked("overdue", "issued", assert_can_transition_invoice)


# ── PaymentRecord ──────────────────────────────────────────────────────


class TestPaymentStateMachine:
    """pending → completed | overdue. overdue → completed."""

    def test_pending_to_completed(self):
        assert_ok("pending", "completed", assert_can_transition_payment)

    def test_pending_to_overdue(self):
        assert_ok("pending", "overdue", assert_can_transition_payment)

    def test_overdue_to_completed(self):
        assert_ok("overdue", "completed", assert_can_transition_payment)

    def test_completed_is_terminal(self):
        assert_blocked("completed", "pending", assert_can_transition_payment)

    def test_overdue_blocked_except_to_completed(self):
        assert_blocked("overdue", "pending", assert_can_transition_payment)


# ── Contract ───────────────────────────────────────────────────────────


class TestContractStateMachine:
    """draft → signed → active → expired | terminated."""

    def test_draft_to_signed(self):
        assert_ok("draft", "signed", assert_can_transition_contract)

    def test_draft_to_cancelled(self):
        assert_ok("draft", "cancelled", assert_can_transition_contract)

    def test_signed_to_active(self):
        assert_ok("signed", "active", assert_can_transition_contract)

    def test_signed_to_cancelled(self):
        assert_ok("signed", "cancelled", assert_can_transition_contract)

    def test_active_to_expired(self):
        assert_ok("active", "expired", assert_can_transition_contract)

    def test_active_to_terminated(self):
        assert_ok("active", "terminated", assert_can_transition_contract)

    def test_expired_is_terminal(self):
        assert_blocked("expired", "active", assert_can_transition_contract)

    def test_terminated_is_terminal(self):
        assert_blocked("terminated", "active", assert_can_transition_contract)

    def test_cancelled_is_terminal(self):
        assert_blocked("cancelled", "draft", assert_can_transition_contract)

    def test_draft_cannot_jump_to_active(self):
        assert_blocked("draft", "active", assert_can_transition_contract)


# ── Commission ─────────────────────────────────────────────────────────


class TestCommissionStateMachine:
    """draft → pending_approval → approved → paid | rejected | cancelled.
    rejected → draft."""

    def test_draft_to_pending_approval(self):
        assert_ok("draft", "pending_approval", assert_can_transition_commission)

    def test_draft_to_cancelled(self):
        assert_ok("draft", "cancelled", assert_can_transition_commission)

    def test_pending_approval_to_approved(self):
        assert_ok("pending_approval", "approved", assert_can_transition_commission)

    def test_pending_approval_to_rejected(self):
        assert_ok("pending_approval", "rejected", assert_can_transition_commission)

    def test_pending_approval_to_draft(self):
        assert_ok("pending_approval", "draft", assert_can_transition_commission)

    def test_approved_to_paid(self):
        assert_ok("approved", "paid", assert_can_transition_commission)

    def test_approved_to_cancelled(self):
        assert_ok("approved", "cancelled", assert_can_transition_commission)

    def test_rejected_to_draft(self):
        assert_ok("rejected", "draft", assert_can_transition_commission)

    def test_paid_is_terminal(self):
        assert_blocked("paid", "draft", assert_can_transition_commission)

    def test_draft_cannot_jump_to_paid(self):
        assert_blocked("draft", "paid", assert_can_transition_commission)

    def test_pending_approval_cannot_jump_to_paid(self):
        assert_blocked("pending_approval", "paid", assert_can_transition_commission)
