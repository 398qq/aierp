"""Tests for sales use cases — orchestration of domain + infrastructure."""

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.application.sales.cancel_order import CancelSalesOrderUseCase
from app.application.sales.confirm_order import ConfirmSalesOrderUseCase
from app.domain.shared.errors import InvalidStateTransition, NotFoundError
from app.domain.shared.events import DomainEvent
from app.domain.sales.events import OrderConfirmed
from app.models.customer import Customer
from app.models.product import Inventory, Product, Warehouse
from app.models.sales import SalesOrder, SalesOrderItem


pytestmark = pytest.mark.asyncio


@pytest_asyncio.fixture
async def use_case_factory(engine, create_tables):
    factory = async_sessionmaker(engine, expire_on_commit=False)
    yield factory


@pytest_asyncio.fixture
async def draft_order(use_case_factory):
    factory = use_case_factory
    async with factory() as session:
        wh = Warehouse(name="Main WH")
        customer = Customer(name="Test Co", code="C001")
        product = Product(sku="P001", name="Product A")
        inventory = Inventory(
            product_id=1,
            warehouse_id=1,
            quantity=100,
            locked_quantity=0,
            version=0,
        )
        session.add_all([wh, customer, product, inventory])
        await session.flush()

        order = SalesOrder(
            order_no="SO-TEST-001",
            customer_id=customer.id,
            status="draft",
            total_amount=0,
        )
        session.add(order)
        await session.flush()

        session.add_all(
            [
                SalesOrderItem(
                    order_id=order.id,
                    product_id=product.id,
                    product_name="Product A",
                    quantity=5,
                    unit_price=10.0,
                ),
                SalesOrderItem(
                    order_id=order.id,
                    product_id=product.id,
                    product_name="Product A",
                    quantity=3,
                    unit_price=10.0,
                ),
            ]
        )
        await session.commit()
        return order.id, customer.id, product.id


class TestConfirmSalesOrderUseCase:
    async def test_confirm_draft_order_succeeds(self, use_case_factory, draft_order):
        order_id, _, _ = draft_order
        factory = use_case_factory

        async with factory() as session:
            use_case = ConfirmSalesOrderUseCase(session, user_id=42)
            domain_order = await use_case.execute(order_id)
            await session.commit()

        assert domain_order.status.value == "confirmed"
        assert len(domain_order.lines) == 2

    async def test_confirm_emits_order_confirmed_event(
        self, use_case_factory, draft_order
    ):
        order_id, _, _ = draft_order
        factory = use_case_factory

        # Set up a captured-event bus for this test
        from app.core.event_bus import EventBus
        import app.application.uow as uow_mod

        bus = EventBus()
        uow_mod._event_bus = bus
        uow_mod._session_factory = factory

        captured: list[DomainEvent] = []
        bus.subscribe(OrderConfirmed, lambda e: captured.append(e))

        from app.application.uow import get_uow

        async with get_uow() as uow:
            use_case = ConfirmSalesOrderUseCase(uow.session, user_id=42)
            domain_order = await use_case.execute(order_id)
            for event in domain_order.collect_events():
                uow.track_event(event)

        assert len(captured) == 1
        assert captured[0].aggregate_id == order_id
        assert captured[0].customer_id is not None
        assert captured[0].total_amount == 80.0  # 5*10 + 3*10
        assert len(captured[0].lines) == 2

    async def test_confirm_nonexistent_raises_not_found(self, use_case_factory):
        factory = use_case_factory
        async with factory() as session:
            use_case = ConfirmSalesOrderUseCase(session, user_id=1)
            with pytest.raises(NotFoundError) as ei:
                await use_case.execute(order_id=99999)
            assert ei.value.http_status == 404

    async def test_double_confirm_raises_invalid_state(
        self, use_case_factory, draft_order
    ):
        order_id, _, _ = draft_order
        factory = use_case_factory

        async with factory() as session:
            use_case = ConfirmSalesOrderUseCase(session, user_id=42)
            await use_case.execute(order_id)
            await session.commit()

        async with factory() as session:
            use_case2 = ConfirmSalesOrderUseCase(session, user_id=42)
            with pytest.raises(InvalidStateTransition):
                await use_case2.execute(order_id)


class TestCancelSalesOrderUseCase:
    async def test_cancel_confirmed_order_succeeds(self, use_case_factory, draft_order):
        order_id, _, _ = draft_order
        factory = use_case_factory

        async with factory() as session:
            await ConfirmSalesOrderUseCase(session, user_id=42).execute(order_id)
            await session.commit()

        async with factory() as session:
            use_case = CancelSalesOrderUseCase(session, user_id=99)
            result = await use_case.execute(order_id, reason="customer changed mind")
            await session.commit()

        assert result.status.value == "cancelled"

    async def test_cancel_draft_order_succeeds(self, use_case_factory, draft_order):
        order_id, _, _ = draft_order
        factory = use_case_factory
        async with factory() as session:
            use_case = CancelSalesOrderUseCase(session, user_id=99)
            result = await use_case.execute(order_id, reason="abandoned")
            await session.commit()
        assert result.status.value == "cancelled"

    async def test_cancel_requires_reason(self, use_case_factory, draft_order):
        order_id, _, _ = draft_order
        factory = use_case_factory
        async with factory() as session:
            use_case = CancelSalesOrderUseCase(session, user_id=99)
            with pytest.raises(ValueError, match="reason is required"):
                await use_case.execute(order_id, reason="")
            with pytest.raises(ValueError, match="reason is required"):
                await use_case.execute(order_id, reason="   ")

    async def test_cancel_emits_event_with_reason(self, use_case_factory, draft_order):
        order_id, _, _ = draft_order
        factory = use_case_factory

        from app.core.event_bus import EventBus
        import app.application.uow as uow_mod
        from app.domain.sales.events import OrderCancelled

        bus = EventBus()
        uow_mod._event_bus = bus
        uow_mod._session_factory = factory

        captured: list[OrderCancelled] = []
        bus.subscribe(OrderCancelled, lambda e: captured.append(e))

        from app.application.uow import get_uow

        async with get_uow() as uow:
            # First confirm
            await ConfirmSalesOrderUseCase(uow.session, user_id=42).execute(order_id)
            await uow.session.commit()
            # Then cancel
            result = await CancelSalesOrderUseCase(uow.session, user_id=99).execute(
                order_id, reason="test reason"
            )
            for event in result.collect_events():
                uow.track_event(event)

        assert len(captured) == 1
        assert captured[0].previous_status == "confirmed"
        assert captured[0].reason == "test reason"
        assert len(captured[0].lines) == 2
