"""Tests for SalesOrder state machine (Stage 2 Day 1)."""

from decimal import Decimal

import pytest

from app.domain.sales.order import (
    OrderLine,
    OrderStatus,
    SalesOrder,
)
from app.domain.shared.errors import (
    BusinessRuleViolation,
    InvalidStateTransition,
)


def _make_order(**overrides):
    defaults = dict(
        customer_id=1,
        owner="Alice",
        lines=[OrderLine(product_id=10, product_name="MCU", quantity=100, unit_price=2.5)],
    )
    defaults.update(overrides)
    return SalesOrder(**defaults)


# ── Happy path ─────────────────────────────────────────────────────────


def test_new_order_defaults_to_pending():
    order = _make_order()
    assert order.status == OrderStatus.PENDING
    assert order.total_amount == pytest.approx(250.0)
    assert order.created_at is not None
    assert order.confirmed_at is None


def test_pending_to_confirmed_emits_event():
    order = _make_order()
    order.confirm()
    assert order.status == OrderStatus.CONFIRMED
    assert order.confirmed_at is not None
    events = order.collect_events()
    assert len(events) == 1
    assert events[0].aggregate_type == "SalesOrder"
    assert events[0].order_no == ""  # not yet persisted
    assert events[0].customer_id == 1
    assert events[0].owner == "Alice"
    assert events[0].lines == ((10, 100),)


def test_full_lifecycle_pending_to_completed():
    order = _make_order()
    order.confirm()
    order.ship()
    order.complete()
    assert order.status == OrderStatus.COMPLETED
    assert order.completed_at is not None
    events = order.collect_events()
    assert [type(e).__name__ for e in events] == [
        "OrderConfirmed", "OrderShipped", "OrderCompleted"
    ]
    assert events[-1].owner == "Alice"
    assert events[-1].total_amount == pytest.approx(250.0)


# ── Illegal transitions ───────────────────────────────────────────────


def test_cannot_confirm_twice():
    order = _make_order()
    order.confirm()
    with pytest.raises(InvalidStateTransition, match="confirmed → confirmed"):
        order.confirm()


def test_cannot_ship_before_confirm():
    order = _make_order()
    with pytest.raises(InvalidStateTransition, match="pending → shipped"):
        order.ship()


def test_cannot_complete_before_ship():
    order = _make_order()
    order.confirm()
    with pytest.raises(InvalidStateTransition, match="confirmed → completed"):
        order.complete()


def test_cannot_cancel_after_shipped():
    order = _make_order()
    order.confirm()
    order.ship()
    with pytest.raises(InvalidStateTransition, match="shipped → cancelled"):
        order.cancel("客户反悔")


def test_completed_is_terminal():
    order = _make_order()
    order.confirm()
    order.ship()
    order.complete()
    for method, target in [
        ("confirm", "confirmed"),
        ("ship", "shipped"),
        ("complete", "completed"),
    ]:
        with pytest.raises(InvalidStateTransition, match=f"completed → {target}"):
            getattr(order, method)()


# ── Cancel paths ──────────────────────────────────────────────────────


def test_cancel_from_pending_appends_reason_to_notes():
    order = _make_order(notes="原价订单")
    order.cancel("客户取消")
    assert order.status == OrderStatus.CANCELLED
    assert order.cancelled_at is not None
    assert "客户取消" in order.notes
    assert order.notes.startswith("原价订单")


def test_cancel_from_confirmed_allowed():
    order = _make_order()
    order.confirm()
    order.collect_events()  # clear confirm event
    order.cancel("报价错误")
    assert order.status == OrderStatus.CANCELLED


def test_cancel_requires_reason():
    order = _make_order()
    with pytest.raises(BusinessRuleViolation, match="必须填写原因"):
        order.cancel("")


def test_cancel_after_completed_raises():
    order = _make_order()
    order.confirm()
    order.ship()
    order.complete()
    with pytest.raises(InvalidStateTransition, match="completed → cancelled"):
        order.cancel("已经完成了")


# ── Business rules ────────────────────────────────────────────────────


def test_confirm_empty_order_raises():
    order = SalesOrder(customer_id=1, owner="Alice", total_amount=100.0)
    # No lines, no total override -- __post_init__ should catch it
    with pytest.raises(BusinessRuleViolation, match="至少有一个明细"):
        SalesOrder(customer_id=1, owner="Alice")


def test_confirm_without_owner_raises():
    order = _make_order(owner=None)
    with pytest.raises(BusinessRuleViolation, match="必须有负责人"):
        order.confirm()


def test_lines_locked_after_confirm():
    order = _make_order()
    order.confirm()
    with pytest.raises(InvalidStateTransition, match="confirmed 状态不可修改"):
        order.add_line(OrderLine(product_id=20, product_name="Sensor", quantity=5, unit_price=10.0))


def test_invalid_line_quantity_raises():
    with pytest.raises(BusinessRuleViolation, match="数量必须大于零"):
        OrderLine(product_id=10, product_name="MCU", quantity=0, unit_price=2.5)


def test_invalid_line_unit_price_raises():
    with pytest.raises(BusinessRuleViolation, match="单价不能为负"):
        OrderLine(product_id=10, product_name="MCU", quantity=10, unit_price=-1.0)


# ── Total recalculation ──────────────────────────────────────────────


def test_add_line_recalcs_total():
    order = _make_order()
    assert order.total_amount == pytest.approx(250.0)
    order.add_line(OrderLine(product_id=20, product_name="Sensor", quantity=50, unit_price=1.0))
    assert order.total_amount == pytest.approx(300.0)
    order.remove_line(0)
    assert order.total_amount == pytest.approx(50.0)


# ── Event collection ─────────────────────────────────────────────────


def test_collect_events_clears_buffer():
    order = _make_order()
    order.confirm()
    events1 = order.collect_events()
    assert len(events1) == 1
    events2 = order.collect_events()
    assert events2 == []
    # Re-collecting should not double-fire
    order.ship()
    events3 = order.collect_events()
    assert len(events3) == 1


def test_no_events_on_invalid_transition():
    order = _make_order()
    with pytest.raises(InvalidStateTransition):
        order.ship()  # PENDING → SHIPPED is illegal
    assert order.collect_events() == []
