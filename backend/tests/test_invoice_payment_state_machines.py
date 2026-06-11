"""Tests for Invoice + PaymentRecord state machines (Stage 2 Day 2)."""

import pytest

from app.domain.sales.invoice import (
    Invoice,
    InvoiceLine,
    InvoiceStatus,
)
from app.domain.sales.payment import (
    PaymentRecord,
    PaymentStatus,
)
from app.domain.shared.errors import (
    BusinessRuleViolation,
    InvalidStateTransition,
)


# ── Invoice ───────────────────────────────────────────────────────────


def _make_invoice(**overrides):
    defaults = dict(
        customer_id=1,
        sales_order_id=100,
        lines=[InvoiceLine(product_id=10, product_name="MCU", quantity=100, unit_price=2.5)],
    )
    defaults.update(overrides)
    return Invoice(**defaults)


def test_new_invoice_defaults_to_draft():
    inv = _make_invoice()
    assert inv.status == InvoiceStatus.DRAFT
    assert inv.amount == pytest.approx(250.0)
    assert inv.tax_amount == pytest.approx(32.50)  # 250 * 0.13
    assert inv.total == pytest.approx(282.50)
    assert inv.paid_amount == 0.0


def test_invoice_lifecycle_draft_to_paid():
    inv = _make_invoice()
    inv.issue()
    assert inv.status == InvoiceStatus.ISSUED
    assert inv.issued_at is not None
    inv.record_payment(282.50)  # full payment
    assert inv.status == InvoiceStatus.PAID
    assert inv.paid_at is not None
    events = inv.collect_events()
    assert [type(e).__name__ for e in events] == ["InvoiceIssued", "InvoicePaid"]


def test_invoice_partial_payment_stays_issued():
    inv = _make_invoice()
    inv.issue()
    inv.record_payment(100.0)
    assert inv.status == InvoiceStatus.ISSUED
    assert inv.paid_amount == pytest.approx(100.0)
    inv.record_payment(182.50)  # remaining
    assert inv.status == InvoiceStatus.PAID


def test_invoice_overpayment_records_but_still_paid():
    inv = _make_invoice()
    inv.issue()
    inv.record_payment(282.50)
    inv.record_payment(50.0)  # overpayment
    assert inv.status == InvoiceStatus.PAID
    assert inv.paid_amount == pytest.approx(332.50)


def test_cannot_issue_empty_invoice():
    inv = Invoice(customer_id=1, sales_order_id=100, total=100.0)  # no lines
    with pytest.raises(BusinessRuleViolation, match="空发票不能开具"):
        inv.issue()


def test_cannot_issue_zero_amount():
    # Edge case: no lines, but total manually set to 0
    inv = Invoice(customer_id=1, sales_order_id=100)
    with pytest.raises(BusinessRuleViolation):
        inv.issue()


def test_cannot_record_payment_on_draft():
    inv = _make_invoice()
    with pytest.raises(InvalidStateTransition, match="draft 状态不能记录付款"):
        inv.record_payment(100.0)


def test_cannot_cancel_paid_invoice():
    inv = _make_invoice()
    inv.issue()
    inv.record_payment(282.50)
    with pytest.raises(InvalidStateTransition, match="paid → cancelled"):
        inv.cancel("已经付了款")


def test_cancel_from_draft_works():
    inv = _make_invoice()
    inv.cancel("测试取消")
    assert inv.status == InvoiceStatus.CANCELLED
    assert "测试取消" in inv.notes


def test_cancel_from_issued_works():
    inv = _make_invoice()
    inv.issue()
    inv.cancel("客户拒收")
    assert inv.status == InvoiceStatus.CANCELLED


def test_cancel_requires_reason():
    inv = _make_invoice()
    with pytest.raises(BusinessRuleViolation, match="必须填写原因"):
        inv.cancel("")


def test_lines_locked_after_issue():
    inv = _make_invoice()
    inv.issue()
    with pytest.raises(InvalidStateTransition, match="issued 状态不可修改"):
        inv.add_line(InvoiceLine(product_id=20, product_name="Sensor", quantity=5, unit_price=10.0))


# ── PaymentRecord ─────────────────────────────────────────────────────


def _make_payment(**overrides):
    defaults = dict(
        customer_id=1,
        amount=282.50,
        invoice_id=200,
        payment_method="bank_transfer",
    )
    defaults.update(overrides)
    return PaymentRecord(**defaults)


def test_new_payment_defaults_to_pending():
    pay = _make_payment()
    assert pay.status == PaymentStatus.PENDING
    assert pay.created_at is not None
    assert pay.completed_at is None


def test_pending_to_completed_emits_event():
    pay = _make_payment()
    pay.complete()
    assert pay.status == PaymentStatus.COMPLETED
    assert pay.completed_at is not None
    assert pay.payment_date is not None
    events = pay.collect_events()
    assert len(events) == 1
    assert events[0].aggregate_type == "PaymentRecord"
    assert events[0].invoice_id == 200
    assert events[0].amount == pytest.approx(282.50)
    assert events[0].method == "bank_transfer"


def test_cannot_complete_twice():
    pay = _make_payment()
    pay.complete()
    with pytest.raises(InvalidStateTransition, match="completed → completed"):
        pay.complete()


def test_cannot_complete_with_no_method():
    pay = _make_payment(payment_method="")
    with pytest.raises(BusinessRuleViolation, match="付款方式不能为空"):
        pay.complete()


def test_payment_overdue_then_completed():
    pay = _make_payment()
    pay.mark_overdue()
    assert pay.status == PaymentStatus.OVERDUE
    pay.complete()
    assert pay.status == PaymentStatus.COMPLETED


def test_overdue_only_from_pending():
    pay = _make_payment()
    pay.complete()
    pay.mark_overdue()  # no-op for non-pending
    assert pay.status == PaymentStatus.COMPLETED


def test_reverse_completed_requires_reason():
    pay = _make_payment()
    pay.complete()
    pay.collect_events()
    with pytest.raises(BusinessRuleViolation, match="冲销付款必须填写原因"):
        pay.reverse("")


def test_reverse_completed_works():
    pay = _make_payment()
    pay.complete()
    pay.collect_events()
    pay.reverse("客户退款")
    assert pay.status == PaymentStatus.REVERSED
    assert "客户退款" in pay.notes


def test_cannot_reverse_pending():
    pay = _make_payment()
    with pytest.raises(InvalidStateTransition, match="状态不可冲销"):
        pay.reverse("refund")


def test_zero_amount_payment_raises():
    with pytest.raises(BusinessRuleViolation, match="付款金额必须大于零"):
        PaymentRecord(customer_id=1, amount=0)


def test_negative_amount_payment_raises():
    with pytest.raises(BusinessRuleViolation, match="付款金额必须大于零"):
        PaymentRecord(customer_id=1, amount=-100.0)


# ── Cross-aggregate: payment auto-completes invoice ──────────────────


def test_payment_completion_event_can_drive_invoice_reconciliation():
    """Simulate the event-bus bridge: payment.completed() emits
    PaymentReceived; invoice.record_payment() updates paid_amount.
    """
    inv = _make_invoice()
    inv.issue()
    inv.collect_events()

    # Simulate event handler
    pay = _make_payment(amount=inv.total)
    pay.complete()
    event = pay.collect_events()[0]

    # Bridge: invoice hears the event
    inv.record_payment(event.amount)
    assert inv.status == InvoiceStatus.PAID
