"""Tests for Quotation aggregate — pre-sales document state machine."""

from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest

from app.domain.sales.events import QuotationAccepted, QuotationSent
from app.domain.sales.quotation import (
    Quotation,
    QuotationLine,
    QuotationStatus,
)
from app.domain.shared.errors import (
    BusinessRuleViolation,
    InvalidStateTransition,
)


def _line(
    product_id: int = 1,
    name: str = "Test Product",
    qty: int = 5,
    price: str = "100.0",
    cost: str | None = "60.0",
) -> QuotationLine:
    return QuotationLine(
        product_id=product_id,
        product_name=name,
        quantity=qty,
        unit_price=Decimal(price),
        cost_price=Decimal(cost) if cost else None,
    )


class TestQuotationLine:
    def test_subtotal(self):
        line = _line(qty=3, price="12.50")
        assert line.subtotal == Decimal("37.50")

    def test_margin_calculations(self):
        line = _line(price="100", cost="60")
        assert line.margin == Decimal("40")
        assert line.margin_pct == pytest.approx(0.6666, abs=0.001)

    def test_margin_none_when_no_cost(self):
        line = _line(cost=None)
        assert line.margin is None
        assert line.margin_pct is None

    def test_margin_none_when_zero_cost(self):
        line = _line(cost="0")
        assert line.margin is None
        assert line.margin_pct is None

    def test_rejects_zero_quantity(self):
        with pytest.raises(BusinessRuleViolation):
            _line(qty=0)

    def test_rejects_negative_price(self):
        with pytest.raises(BusinessRuleViolation):
            _line(price="-1")


class TestQuotationTotals:
    def test_totals_with_tax(self):
        q = Quotation(
            customer_id=1,
            lines=[_line(qty=2, price="100"), _line(qty=3, price="50")],
        )
        assert q.subtotal == Decimal("350")
        # Tax at 13%
        assert q.tax_amount == Decimal("45.50")
        assert q.total == Decimal("395.50")

    def test_default_validity_is_30_days(self):
        before = datetime.now(timezone.utc)
        q = Quotation(customer_id=1)
        assert q.valid_until is not None
        # 30 days ± a few seconds
        delta = q.valid_until - before
        assert timedelta(days=29, hours=23) < delta < timedelta(days=30, hours=1)

    def test_custom_validity_preserved(self):
        custom = datetime.now(timezone.utc) + timedelta(days=7)
        q = Quotation(customer_id=1, valid_until=custom)
        assert q.valid_until == custom


class TestQuotationSend:
    def test_send_draft_moves_to_sent(self):
        q = Quotation(customer_id=1, lines=[_line()])
        q.send()
        assert q.status == QuotationStatus.SENT

    def test_send_emits_event_with_total(self):
        q = Quotation(
            customer_id=42,
            quotation_no="Q-001",
            lines=[_line(qty=2, price="100")],
        )
        q.send()
        events = q.collect_events()
        assert len(events) == 1
        assert isinstance(events[0], QuotationSent)
        assert events[0].customer_id == 42
        assert events[0].quotation_no == "Q-001"
        assert events[0].total == pytest.approx(226.0, abs=0.1)  # 200 + 26 tax

    def test_send_empty_raises(self):
        q = Quotation(customer_id=1, lines=[])
        with pytest.raises(BusinessRuleViolation, match="空报价单"):
            q.send()

    def test_send_already_sent_raises(self):
        q = Quotation(customer_id=1, lines=[_line()])
        q.send()
        with pytest.raises(InvalidStateTransition):
            q.send()


class TestQuotationAccept:
    def test_accept_sent_moves_to_accepted(self):
        q = Quotation(customer_id=1, lines=[_line()])
        q.send()
        q.accept()
        assert q.status == QuotationStatus.ACCEPTED

    def test_accept_emits_event(self):
        q = Quotation(
            customer_id=1,
            quotation_no="Q-100",
            lines=[_line()],
        )
        q.send()
        q.accept()
        events = q.collect_events()
        accepted = [e for e in events if isinstance(e, QuotationAccepted)]
        assert len(accepted) == 1
        assert accepted[0].quotation_no == "Q-100"

    def test_accept_draft_raises(self):
        q = Quotation(customer_id=1, lines=[_line()])
        with pytest.raises(InvalidStateTransition):
            q.accept()

    def test_accept_expired_raises(self):
        past = datetime.now(timezone.utc) - timedelta(days=1)
        q = Quotation(
            customer_id=1,
            lines=[_line()],
            valid_until=past,
        )
        q.send()
        with pytest.raises(BusinessRuleViolation, match="过期"):
            q.accept()


class TestQuotationReject:
    def test_reject_draft_works(self):
        q = Quotation(customer_id=1, lines=[_line()])
        q.reject(reason="price too high")
        assert q.status == QuotationStatus.REJECTED

    def test_reject_sent_works(self):
        q = Quotation(customer_id=1, lines=[_line()])
        q.send()
        q.reject(reason="competitor won")
        assert q.status == QuotationStatus.REJECTED

    def test_reject_accepted_raises(self):
        q = Quotation(customer_id=1, lines=[_line()])
        q.send()
        q.accept()
        with pytest.raises(InvalidStateTransition):
            q.reject(reason="too late")


class TestQuotationExpiration:
    def test_mark_expired_only_for_sent(self):
        q = Quotation(
            customer_id=1,
            lines=[_line()],
            valid_until=datetime.now(timezone.utc) - timedelta(days=1),
        )
        # Draft → still DRAFT
        q.mark_expired()
        assert q.status == QuotationStatus.DRAFT

    def test_mark_expired_requires_past_date(self):
        future = datetime.now(timezone.utc) + timedelta(days=10)
        q = Quotation(customer_id=1, lines=[_line()], valid_until=future)
        q.send()
        q.mark_expired()
        assert q.status == QuotationStatus.SENT  # Not expired yet

    def test_mark_expired_sent_with_past_date(self):
        past = datetime.now(timezone.utc) - timedelta(days=1)
        q = Quotation(customer_id=1, lines=[_line()], valid_until=past)
        q.send()
        q.mark_expired()
        assert q.status == QuotationStatus.EXPIRED


class TestQuotationConvert:
    def test_convert_from_sent(self):
        q = Quotation(customer_id=1, lines=[_line()])
        q.send()
        q.convert_to_order()
        assert q.status == QuotationStatus.WON

    def test_convert_from_accepted(self):
        q = Quotation(customer_id=1, lines=[_line()])
        q.send()
        q.accept()
        q.convert_to_order()
        assert q.status == QuotationStatus.WON

    def test_convert_from_draft_raises(self):
        q = Quotation(customer_id=1, lines=[_line()])
        with pytest.raises(InvalidStateTransition):
            q.convert_to_order()

    def test_convert_from_won_raises(self):
        q = Quotation(customer_id=1, lines=[_line()])
        q.send()
        q.convert_to_order()
        with pytest.raises(InvalidStateTransition):
            q.convert_to_order()


class TestQuotationMutations:
    def test_add_line_in_draft(self):
        q = Quotation(customer_id=1, lines=[_line(product_id=1)])
        q.add_line(_line(product_id=2, qty=3, price="50"))
        assert len(q.lines) == 2

    def test_add_line_in_sent_raises(self):
        q = Quotation(customer_id=1, lines=[_line()])
        q.send()
        with pytest.raises(InvalidStateTransition):
            q.add_line(_line())

    def test_remove_line_in_draft(self):
        q = Quotation(
            customer_id=1,
            lines=[_line(product_id=1), _line(product_id=2)],
        )
        q.remove_line(0)
        assert len(q.lines) == 1
        assert q.lines[0].product_id == 2

    def test_remove_line_invalid_index_raises(self):
        q = Quotation(customer_id=1, lines=[_line()])
        with pytest.raises(IndexError):
            q.remove_line(5)

    def test_remove_line_after_send_raises(self):
        q = Quotation(customer_id=1, lines=[_line()])
        q.send()
        with pytest.raises(InvalidStateTransition):
            q.remove_line(0)


class TestQuotationEventBuffer:
    def test_collect_clears_buffer(self):
        q = Quotation(customer_id=1, lines=[_line()])
        q.send()
        assert len(q.collect_events()) == 1
        assert q.collect_events() == []
