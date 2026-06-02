"""Tests for Unit of Work — transaction and event dispatch semantics."""

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.application.uow import get_uow, init_uow
from app.core.event_bus import EventBus
from app.domain.sales.events import OrderConfirmed
from app.models.product import Inventory, Product, Warehouse


pytestmark = pytest.mark.asyncio


@pytest_asyncio.fixture
async def event_bus():
    bus = EventBus()
    init_uow(async_sessionmaker, bus)  # placeholder; test uses its own factory
    yield bus


@pytest_asyncio.fixture
async def uow_factory(engine, create_tables):
    factory = async_sessionmaker(engine, expire_on_commit=False)
    init_uow(factory, EventBus())
    yield factory
    # Reset module-level state to avoid leaking across tests
    import app.application.uow as uow_mod
    uow_mod._session_factory = None
    uow_mod._event_bus = None


class TestUnitOfWork:
    async def test_commit_persists_data(self, uow_factory):
        async with get_uow() as uow:
            wh = Warehouse(name="Main WH")
            product = Product(sku="TEST-1", name="Test")
            uow.session.add_all([wh, product])
            await uow.session.flush()
            inv = Inventory(
                product_id=product.id,
                warehouse_id=wh.id,
                quantity=50,
                version=0,
            )
            uow.session.add(inv)
        # Auto-committed on context exit
        async with uow_factory() as verify_session:
            result = (await verify_session.execute(
                __import__("sqlalchemy").select(Inventory).where(Inventory.quantity == 50)
            )).scalar_one()
            assert result.quantity == 50

    async def test_rollback_discards_data_and_events(self, uow_factory):
        bus = EventBus()
        import app.application.uow as uow_mod
        uow_mod._event_bus = bus

        received = []
        bus.subscribe(OrderConfirmed, lambda e: received.append(e))

        with pytest.raises(RuntimeError, match="intentional"):
            async with get_uow() as uow:
                wh = Warehouse(name="To Rollback")
                uow.session.add(wh)
                uow.track_event(OrderConfirmed(aggregate_id=1))
                raise RuntimeError("intentional")

        # Event must NOT be dispatched after rollback
        assert received == []

    async def test_commit_dispatches_events(self, uow_factory):
        bus = EventBus()
        import app.application.uow as uow_mod
        uow_mod._event_bus = bus

        received = []
        bus.subscribe(OrderConfirmed, lambda e: received.append(e))

        async with get_uow() as uow:
            uow.track_event(OrderConfirmed(aggregate_id=42, customer_id=7))

        # Event was dispatched after commit
        assert len(received) == 1
        assert received[0].aggregate_id == 42

    async def test_commit_dispatches_events_in_order(self, uow_factory):
        bus = EventBus()
        import app.application.uow as uow_mod
        uow_mod._event_bus = bus

        received_ids = []
        bus.subscribe(OrderConfirmed, lambda e: received_ids.append(e.aggregate_id))

        async with get_uow() as uow:
            uow.track_event(OrderConfirmed(aggregate_id=1))
            uow.track_event(OrderConfirmed(aggregate_id=2))
            uow.track_event(OrderConfirmed(aggregate_id=3))

        assert received_ids == [1, 2, 3]

    async def test_double_commit_is_safe(self, uow_factory):
        bus = EventBus()
        import app.application.uow as uow_mod
        uow_mod._event_bus = bus

        received = []
        bus.subscribe(OrderConfirmed, lambda e: received.append(e))

        async with get_uow() as uow:
            uow.track_event(OrderConfirmed(aggregate_id=1))
            await uow.commit()
            await uow.commit()  # no-op

        assert len(received) == 1

    async def test_raises_when_not_initialized(self):
        import app.application.uow as uow_mod
        uow_mod._session_factory = None
        with pytest.raises(RuntimeError, match="not initialized"):
            async with get_uow():
                pass
