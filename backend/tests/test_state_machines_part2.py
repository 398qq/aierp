"""State machine tests part 2 — Customer + Transaction entities."""

import pytest
from app.domain.shared.errors import InvalidStateTransition
from app.domain.states import (
    CUSTOMER_TRANSITIONS,
    PURCHASE_ORDER_TRANSITIONS,
    GOODS_RECEIPT_TRANSITIONS,
    SUPPLIER_INVOICE_TRANSITIONS,
    TICKET_TRANSITIONS,
    SAMPLE_TRANSITIONS,
    assert_can_transition_customer,
    assert_can_transition_purchase_order,
    assert_can_transition_goods_receipt,
    assert_can_transition_supplier_invoice,
    assert_can_transition_ticket,
    assert_can_transition_sample,
)


def assert_ok(current, target, fn):
    try:
        fn(current, target)
    except InvalidStateTransition as e:
        pytest.fail(f"Expected ok: {current} → {target}, got {e}")


def assert_blocked(current, target, fn):
    with pytest.raises(InvalidStateTransition):
        fn(current, target)


# ── Customer (7 states) ────────────────────────────────────────────────


class TestCustomerStateMachine:
    def test_new_lead_to_active(self):
        assert_ok("new_lead", "active", assert_can_transition_customer)

    def test_new_lead_to_churned(self):
        assert_ok("new_lead", "churned", assert_can_transition_customer)

    def test_active_to_converted(self):
        assert_ok("active", "converted", assert_can_transition_customer)

    def test_active_to_inactive(self):
        assert_ok("active", "inactive", assert_can_transition_customer)

    def test_active_to_churned(self):
        assert_ok("active", "churned", assert_can_transition_customer)

    def test_converted_to_vip(self):
        assert_ok("converted", "vip", assert_can_transition_customer)

    def test_converted_to_inactive(self):
        assert_ok("converted", "inactive", assert_can_transition_customer)

    def test_vip_to_inactive(self):
        assert_ok("vip", "inactive", assert_can_transition_customer)

    def test_vip_to_churned(self):
        assert_ok("vip", "churned", assert_can_transition_customer)

    def test_inactive_to_active(self):
        assert_ok("inactive", "active", assert_can_transition_customer)

    def test_churned_can_reactivate(self):
        assert_ok("churned", "active", assert_can_transition_customer)

    def test_new_lead_cannot_jump_to_vip(self):
        assert_blocked("new_lead", "vip", assert_can_transition_customer)

    def test_active_cannot_jump_to_vip(self):
        assert_blocked("active", "vip", assert_can_transition_customer)

    def test_vip_cannot_go_back_to_converted(self):
        assert_blocked("vip", "converted", assert_can_transition_customer)

    def test_transitions_dict(self):
        assert CUSTOMER_TRANSITIONS["new_lead"] == {"active", "churned"}
        assert CUSTOMER_TRANSITIONS["active"] == {"converted", "inactive", "churned"}
        assert CUSTOMER_TRANSITIONS["converted"] == {"vip", "inactive", "churned"}
        assert CUSTOMER_TRANSITIONS["churned"] == {"active"}


# ── PurchaseOrder (6 states) ──────────────────────────────────────────


class TestPurchaseOrderStateMachine:
    def test_draft_to_approved(self):
        assert_ok("draft", "approved", assert_can_transition_purchase_order)

    def test_draft_to_cancelled(self):
        assert_ok("draft", "cancelled", assert_can_transition_purchase_order)

    def test_approved_to_ordered(self):
        assert_ok("approved", "ordered", assert_can_transition_purchase_order)

    def test_ordered_to_received(self):
        assert_ok("ordered", "received", assert_can_transition_purchase_order)

    def test_ordered_to_partially_received(self):
        assert_ok("ordered", "partially_received", assert_can_transition_purchase_order)

    def test_partially_received_to_received(self):
        assert_ok(
            "partially_received", "received", assert_can_transition_purchase_order
        )

    def test_received_is_terminal(self):
        assert_blocked("received", "draft", assert_can_transition_purchase_order)

    def test_cancelled_is_terminal(self):
        assert_blocked("cancelled", "draft", assert_can_transition_purchase_order)

    def test_draft_cannot_jump_to_received(self):
        assert_blocked("draft", "received", assert_can_transition_purchase_order)

    def test_transitions_dict(self):
        assert PURCHASE_ORDER_TRANSITIONS["draft"] == {"approved", "cancelled"}
        assert PURCHASE_ORDER_TRANSITIONS["ordered"] == {
            "partially_received",
            "received",
            "cancelled",
        }
        assert PURCHASE_ORDER_TRANSITIONS["received"] == set()


# ── GoodsReceipt (4 states) ───────────────────────────────────────────


class TestGoodsReceiptStateMachine:
    def test_received_to_inspected(self):
        assert_ok("received", "inspected", assert_can_transition_goods_receipt)

    def test_received_to_accepted(self):
        assert_ok("received", "accepted", assert_can_transition_goods_receipt)

    def test_received_to_rejected(self):
        assert_ok("received", "rejected", assert_can_transition_goods_receipt)

    def test_inspected_to_accepted(self):
        assert_ok("inspected", "accepted", assert_can_transition_goods_receipt)

    def test_inspected_to_rejected(self):
        assert_ok("inspected", "rejected", assert_can_transition_goods_receipt)

    def test_rejected_to_received(self):
        assert_ok("rejected", "received", assert_can_transition_goods_receipt)

    def test_accepted_is_terminal(self):
        assert_blocked("accepted", "received", assert_can_transition_goods_receipt)

    def test_transitions_dict(self):
        assert GOODS_RECEIPT_TRANSITIONS["received"] == {
            "inspected",
            "accepted",
            "rejected",
        }
        assert GOODS_RECEIPT_TRANSITIONS["accepted"] == set()


# ── SupplierInvoice (5 states) ────────────────────────────────────────


class TestSupplierInvoiceStateMachine:
    def test_pending_to_matched(self):
        assert_ok("pending", "matched", assert_can_transition_supplier_invoice)

    def test_matched_to_approved(self):
        assert_ok("matched", "approved", assert_can_transition_supplier_invoice)

    def test_approved_to_paid(self):
        assert_ok("approved", "paid", assert_can_transition_supplier_invoice)

    def test_pending_to_cancelled(self):
        assert_ok("pending", "cancelled", assert_can_transition_supplier_invoice)

    def test_paid_is_terminal(self):
        assert_blocked("paid", "draft", assert_can_transition_supplier_invoice)

    def test_cancelled_is_terminal(self):
        assert_blocked("cancelled", "pending", assert_can_transition_supplier_invoice)

    def test_pending_cannot_jump_to_paid(self):
        assert_blocked("pending", "paid", assert_can_transition_supplier_invoice)

    def test_transitions_dict(self):
        assert SUPPLIER_INVOICE_TRANSITIONS["pending"] == {"matched", "cancelled"}
        assert SUPPLIER_INVOICE_TRANSITIONS["paid"] == set()


# ── Ticket (5 states) ─────────────────────────────────────────────────


class TestTicketStateMachine:
    def test_open_to_in_progress(self):
        assert_ok("open", "in_progress", assert_can_transition_ticket)

    def test_open_to_cancelled(self):
        assert_ok("open", "cancelled", assert_can_transition_ticket)

    def test_in_progress_to_resolved(self):
        assert_ok("in_progress", "resolved", assert_can_transition_ticket)

    def test_resolved_to_closed(self):
        assert_ok("resolved", "closed", assert_can_transition_ticket)

    def test_resolved_to_open(self):
        assert_ok("resolved", "open", assert_can_transition_ticket)

    def test_closed_is_terminal(self):
        assert_blocked("closed", "open", assert_can_transition_ticket)

    def test_cancelled_is_terminal(self):
        assert_blocked("cancelled", "open", assert_can_transition_ticket)

    def test_open_cannot_jump_to_resolved(self):
        assert_blocked("open", "resolved", assert_can_transition_ticket)

    def test_transitions_dict(self):
        assert TICKET_TRANSITIONS["open"] == {"in_progress", "cancelled"}
        assert TICKET_TRANSITIONS["resolved"] == {"closed", "open"}


# ── Sample (5 states) ─────────────────────────────────────────────────


class TestSampleStateMachine:
    def test_pending_to_shipped(self):
        assert_ok("pending", "shipped", assert_can_transition_sample)

    def test_pending_to_cancelled(self):
        assert_ok("pending", "cancelled", assert_can_transition_sample)

    def test_shipped_to_received(self):
        assert_ok("shipped", "received", assert_can_transition_sample)

    def test_shipped_to_cancelled(self):
        assert_ok("shipped", "cancelled", assert_can_transition_sample)

    def test_received_to_evaluated(self):
        assert_ok("received", "evaluated", assert_can_transition_sample)

    def test_evaluated_is_terminal(self):
        assert_blocked("evaluated", "pending", assert_can_transition_sample)

    def test_cancelled_is_terminal(self):
        assert_blocked("cancelled", "pending", assert_can_transition_sample)

    def test_pending_cannot_jump_to_evaluated(self):
        assert_blocked("pending", "evaluated", assert_can_transition_sample)

    def test_transitions_dict(self):
        assert SAMPLE_TRANSITIONS["pending"] == {"shipped", "cancelled"}
        assert SAMPLE_TRANSITIONS["evaluated"] == set()
