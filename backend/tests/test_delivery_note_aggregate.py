"""Tests for DeliveryNote aggregate."""

from datetime import datetime

import pytest

from app.domain.sales.delivery import (
    DeliveryLine,
    DeliveryNote,
    DeliveryStatus,
)
from app.domain.sales.events import DeliveryShipped
from app.domain.shared.errors import (
    BusinessRuleViolation,
    InvalidStateTransition,
)


def _line(product_id: int = 1, name: str = "Product A", qty: int = 10) -> DeliveryLine:
    return DeliveryLine(product_id=product_id, product_name=name, quantity=qty)


class TestDeliveryLine:
    def test_rejects_zero_quantity(self):
        with pytest.raises(BusinessRuleViolation):
            _line(qty=0)

    def test_rejects_negative_quantity(self):
        with pytest.raises(BusinessRuleViolation):
            _line(qty=-1)

    def test_zero_product_id_allowed(self):
        line = _line(product_id=None, qty=5)
        assert line.product_id is None


class TestDeliveryNoteBasic:
    def test_total_quantity(self):
        note = DeliveryNote(
            sales_order_id=1,
            customer_id=10,
            lines=[_line(qty=5), _line(qty=3)],
        )
        assert note.total_quantity == 8

    def test_empty_note(self):
        note = DeliveryNote(sales_order_id=1, customer_id=10)
        assert note.total_quantity == 0

    def test_default_status_draft(self):
        note = DeliveryNote(sales_order_id=1, customer_id=10)
        assert note.status == DeliveryStatus.DRAFT

    def test_add_line_in_draft(self):
        note = DeliveryNote(sales_order_id=1, customer_id=10)
        note.add_line(_line())
        assert len(note.lines) == 1

    def test_add_line_after_ship_raises(self):
        note = DeliveryNote(
            sales_order_id=1,
            customer_id=10,
            lines=[_line()],
        )
        note.ship()
        with pytest.raises(InvalidStateTransition):
            note.add_line(_line())


class TestDeliveryNoteShip:
    def test_ship_moves_to_shipped(self):
        note = DeliveryNote(
            sales_order_id=1,
            customer_id=10,
            lines=[_line()],
        )
        note.ship()
        assert note.status == DeliveryStatus.SHIPPED

    def test_ship_sets_delivery_date(self):
        note = DeliveryNote(
            sales_order_id=1,
            customer_id=10,
            lines=[_line()],
        )
        note.ship()
        assert note.delivery_date is not None
        assert isinstance(note.delivery_date, datetime)

    def test_ship_emits_event(self):
        note = DeliveryNote(
            sales_order_id=99,
            customer_id=10,
            lines=[_line(product_id=1, qty=5), _line(product_id=2, qty=3)],
        )
        note.ship()
        events = note.collect_events()
        assert len(events) == 1
        assert isinstance(events[0], DeliveryShipped)
        assert events[0].sales_order_id == 99
        assert events[0].lines == ((1, 5), (2, 3))

    def test_ship_empty_raises(self):
        note = DeliveryNote(sales_order_id=1, customer_id=10, lines=[])
        with pytest.raises(BusinessRuleViolation, match="空发货单"):
            note.ship()

    def test_double_ship_raises(self):
        note = DeliveryNote(
            sales_order_id=1,
            customer_id=10,
            lines=[_line()],
        )
        note.ship()
        with pytest.raises(InvalidStateTransition):
            note.ship()


class TestDeliveryNoteReceipt:
    def test_confirm_receipt_after_shipped(self):
        note = DeliveryNote(
            sales_order_id=1,
            customer_id=10,
            lines=[_line()],
        )
        note.ship()
        note.confirm_receipt()
        assert note.status == DeliveryStatus.RECEIVED
        assert note.received_date is not None

    def test_confirm_receipt_from_draft_raises(self):
        note = DeliveryNote(
            sales_order_id=1,
            customer_id=10,
            lines=[_line()],
        )
        with pytest.raises(InvalidStateTransition):
            note.confirm_receipt()


class TestDeliveryNoteCancel:
    def test_cancel_draft_works(self):
        note = DeliveryNote(
            sales_order_id=1,
            customer_id=10,
            lines=[_line()],
        )
        note.cancel(reason="customer changed mind")
        assert note.status == DeliveryStatus.CANCELLED

    def test_cancel_shipped_works(self):
        note = DeliveryNote(
            sales_order_id=1,
            customer_id=10,
            lines=[_line()],
        )
        note.ship()
        note.cancel(reason="wrong address")
        assert note.status == DeliveryStatus.CANCELLED

    def test_cancel_received_raises(self):
        note = DeliveryNote(
            sales_order_id=1,
            customer_id=10,
            lines=[_line()],
        )
        note.ship()
        note.confirm_receipt()
        with pytest.raises(InvalidStateTransition):
            note.cancel(reason="too late")

    def test_cancel_already_cancelled_raises(self):
        note = DeliveryNote(
            sales_order_id=1,
            customer_id=10,
            lines=[_line()],
        )
        note.cancel(reason="first cancel")
        with pytest.raises(InvalidStateTransition):
            note.cancel(reason="second cancel")
