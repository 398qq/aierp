"""Tests for SalesOrder aggregate — state machine and event emission.

Pure domain tests, no DB. These run in <100ms.
"""

from decimal import Decimal

import pytest

from app.domain.sales.entities import (
    OrderLine,
    OrderStatus,
    SalesOrder,
    ensure_order_found,
)
from app.domain.sales.events import (
    OrderCancelled,
    OrderConfirmed,
    OrderShipped,
)
from app.domain.shared.errors import (
    BusinessRuleViolation,
    InvalidStateTransition,
    NotFoundError,
)


def _line(product_id: int = 1, qty: int = 5, price: str = "10.0") -> OrderLine:
    return OrderLine(
        product_id=product_id,
        product_name=f"Product {product_id}",
        quantity=qty,
        unit_price=Decimal(price),
    )


class TestOrderLine:
    def test_subtotal_calculates_correctly(self):
        line = _line(qty=3, price="12.50")
        assert line.subtotal == Decimal("37.50")

    def test_rejects_zero_quantity(self):
        with pytest.raises(BusinessRuleViolation):
            _line(qty=0)

    def test_rejects_negative_quantity(self):
        with pytest.raises(BusinessRuleViolation):
            _line(qty=-1)

    def test_rejects_negative_price(self):
        with pytest.raises(BusinessRuleViolation):
            _line(price="-1.0")

    def test_zero_price_allowed(self):
        line = _line(price="0")
        assert line.subtotal == Decimal("0")


class TestSalesOrderBasic:
    def test_total_is_sum_of_lines(self):
        order = SalesOrder(
            customer_id=1,
            lines=[_line(qty=2, price="10"), _line(qty=3, price="20")],
        )
        assert order.total == Decimal("80")

    def test_empty_order_total_is_zero(self):
        order = SalesOrder(customer_id=1)
        assert order.total == Decimal("0")

    def test_starts_in_draft(self):
        order = SalesOrder(customer_id=1)
        assert order.status == OrderStatus.DRAFT


class TestSalesOrderConfirm:
    def test_confirm_draft_moves_to_confirmed(self):
        order = SalesOrder(customer_id=1, lines=[_line()])
        order.confirm()
        assert order.status == OrderStatus.CONFIRMED

    def test_confirm_emits_event_with_total_and_lines(self):
        order = SalesOrder(
            customer_id=42,
            lines=[_line(product_id=10, qty=2, price="5")],
        )
        order.confirm()
        events = order.collect_events()
        assert len(events) == 1
        e = events[0]
        assert isinstance(e, OrderConfirmed)
        assert e.customer_id == 42
        assert e.total_amount == 10.0
        assert e.lines == ((10, "Product 10", 2),)

    def test_confirm_empty_order_raises(self):
        order = SalesOrder(customer_id=1, lines=[])
        with pytest.raises(BusinessRuleViolation, match="空订单"):
            order.confirm()

    def test_confirm_already_confirmed_raises(self):
        order = SalesOrder(customer_id=1, lines=[_line()])
        order.confirm()
        with pytest.raises(InvalidStateTransition):
            order.confirm()

    def test_confirm_cancelled_raises(self):
        order = SalesOrder(customer_id=1, lines=[_line()])
        order.cancel(reason="test")
        with pytest.raises(InvalidStateTransition):
            order.confirm()

    def test_collect_events_clears_buffer(self):
        order = SalesOrder(customer_id=1, lines=[_line()])
        order.confirm()
        assert len(order.collect_events()) == 1
        assert order.collect_events() == []  # Cleared


class TestSalesOrderCancel:
    def test_cancel_draft_succeeds(self):
        order = SalesOrder(customer_id=1, lines=[_line()])
        order.cancel(reason="customer changed mind")
        assert order.status == OrderStatus.CANCELLED

    def test_cancel_confirmed_emits_event_with_lines(self):
        order = SalesOrder(
            customer_id=1,
            lines=[_line(product_id=10, qty=5), _line(product_id=20, qty=3)],
        )
        order.confirm()
        order.collect_events()  # discard confirm event
        order.cancel(reason="out of stock")

        events = order.collect_events()
        assert len(events) == 1
        e = events[0]
        assert isinstance(e, OrderCancelled)
        assert e.previous_status == OrderStatus.CONFIRMED.value
        assert e.lines == ((10, 5), (20, 3))
        assert e.reason == "out of stock"

    def test_cancel_shipped_raises(self):
        order = SalesOrder(customer_id=1, lines=[_line()])
        order.confirm()
        order.ship(shipped_lines=[(1, 5)])
        with pytest.raises(InvalidStateTransition):
            order.cancel(reason="too late")

    def test_cancel_invoiced_raises(self):
        order = SalesOrder(
            customer_id=1, lines=[_line()], status=OrderStatus.INVOICED
        )
        with pytest.raises(InvalidStateTransition):
            order.cancel(reason="invoiced")


class TestSalesOrderShip:
    def test_ship_full_moves_to_shipped(self):
        order = SalesOrder(customer_id=1, lines=[_line(qty=5)])
        order.confirm()
        order.ship(shipped_lines=[(1, 5)])
        assert order.status == OrderStatus.SHIPPED

    def test_ship_partial_moves_to_partially_shipped(self):
        order = SalesOrder(
            customer_id=1,
            lines=[_line(qty=10), _line(qty=20, price="2.0")],
        )
        order.confirm()
        order.ship(shipped_lines=[(1, 5), (2, 10)])
        assert order.status == OrderStatus.PARTIALLY_SHIPPED

    def test_ship_emits_event_with_full_flag(self):
        order = SalesOrder(customer_id=1, lines=[_line(qty=5)])
        order.confirm()
        order.ship(shipped_lines=[(1, 5)])
        events = order.collect_events()
        ship_event = [e for e in events if isinstance(e, OrderShipped)]
        assert len(ship_event) == 1
        assert ship_event[0].is_full is True

    def test_ship_from_draft_raises(self):
        order = SalesOrder(customer_id=1, lines=[_line()])
        with pytest.raises(InvalidStateTransition):
            order.ship(shipped_lines=[(1, 5)])

    def test_ship_empty_lines_raises(self):
        order = SalesOrder(customer_id=1, lines=[_line()])
        order.confirm()
        with pytest.raises(BusinessRuleViolation, match="发货明细"):
            order.ship(shipped_lines=[])


class TestEnsureOrderFound:
    def test_returns_order_when_present(self):
        order = SalesOrder(customer_id=1)
        assert ensure_order_found(order, 1) is order

    def test_raises_not_found_when_missing(self):
        with pytest.raises(NotFoundError) as ei:
            ensure_order_found(None, 99)
        assert ei.value.context["order_id"] == 99
        assert ei.value.http_status == 404
