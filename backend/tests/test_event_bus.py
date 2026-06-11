"""Tests for the in-process event bus."""

import asyncio

import pytest

from app.core.event_bus import EventBus
from app.domain.sales.events import OrderConfirmed, OrderCancelled


@pytest.fixture
def bus():
    return EventBus()


class TestEventBus:
    def test_sync_handler_receives_event(self, bus):
        received = []
        bus.subscribe(OrderConfirmed, lambda e: received.append(e))
        event = OrderConfirmed(aggregate_id=1, customer_id=10, total_amount=99.5)
        asyncio.run(bus.publish(event))
        assert len(received) == 1
        assert received[0].aggregate_id == 1

    def test_async_handler_receives_event(self, bus):
        received = []

        async def handler(event):
            received.append(event)

        bus.subscribe(OrderConfirmed, handler)
        event = OrderConfirmed(aggregate_id=2)
        asyncio.run(bus.publish(event))
        assert len(received) == 1

    def test_multiple_handlers_all_called(self, bus):
        a, b = [], []
        bus.subscribe(OrderConfirmed, lambda e: a.append(e))
        bus.subscribe(OrderConfirmed, lambda e: b.append(e))
        asyncio.run(bus.publish(OrderConfirmed(aggregate_id=1)))
        assert len(a) == 1
        assert len(b) == 1

    def test_handler_for_different_event_not_called(self, bus):
        received = []
        bus.subscribe(OrderCancelled, lambda e: received.append(e))
        asyncio.run(bus.publish(OrderConfirmed(aggregate_id=1)))
        assert received == []

    def test_failing_sync_handler_does_not_break_publisher(self, bus):
        received = []

        def bad(event):
            raise ValueError("boom")

        bus.subscribe(OrderConfirmed, bad)
        bus.subscribe(OrderConfirmed, lambda e: received.append(e))
        asyncio.run(bus.publish(OrderConfirmed(aggregate_id=1)))
        assert len(received) == 1  # Second handler still ran

    def test_failing_async_handler_does_not_break_publisher(self, bus):
        received = []

        async def bad(event):
            raise ValueError("boom")

        async def good(event):
            received.append(event)

        bus.subscribe(OrderConfirmed, bad)
        bus.subscribe(OrderConfirmed, good)
        asyncio.run(bus.publish(OrderConfirmed(aggregate_id=1)))
        assert len(received) == 1

    def test_clear_removes_handlers(self, bus):
        bus.subscribe(OrderConfirmed, lambda e: None)
        assert bus.handler_count(OrderConfirmed) == 1
        bus.clear()
        assert bus.handler_count(OrderConfirmed) == 0

    def test_handler_count(self, bus):
        bus.subscribe(OrderConfirmed, lambda e: None)
        bus.subscribe(OrderConfirmed, lambda e: None)

        async def h(event):
            pass

        bus.subscribe(OrderConfirmed, h)
        assert bus.handler_count(OrderConfirmed) == 3
