"""Tests for ConvertQuotationToOrderUseCase."""

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.application.sales.convert_quotation import ConvertQuotationToOrderUseCase
from app.domain.shared.errors import NotFoundError
from app.models.customer import Customer
from app.models.product import Product
from app.models.sales import Quotation, QuotationItem


pytestmark = pytest.mark.asyncio


@pytest_asyncio.fixture
async def factory(engine, create_tables):
    return async_sessionmaker(engine, expire_on_commit=False)


@pytest_asyncio.fixture
async def accepted_quotation(factory):
    async with factory() as session:
        customer = Customer(name="Test Co", code="C001")
        product = Product(sku="P001", name="Product A")
        session.add_all([customer, product])
        await session.flush()

        q = Quotation(
            customer_id=customer.id,
            quotation_no="Q-TEST-001",
            status="sent",
            total_amount=0,
        )
        session.add(q)
        await session.flush()

        session.add_all(
            [
                QuotationItem(
                    quotation_id=q.id,
                    product_id=product.id,
                    product_name="Product A",
                    quantity=5,
                    unit_price=100.0,
                    total_price=500.0,
                ),
                QuotationItem(
                    quotation_id=q.id,
                    product_id=product.id,
                    product_name="Product A",
                    quantity=3,
                    unit_price=100.0,
                    total_price=300.0,
                ),
            ]
        )
        await session.commit()
        return q.id, customer.id, product.id


class TestConvertQuotationToOrderUseCase:
    async def test_convert_sent_quotation_creates_order(
        self, factory, accepted_quotation
    ):
        quotation_id, customer_id, product_id = accepted_quotation
        async with factory() as session:
            use_case = ConvertQuotationToOrderUseCase(session, user_id=1)
            domain_order = await use_case.execute(quotation_id)
            await session.commit()

        assert domain_order.status.value == "draft"
        assert domain_order.customer_id == customer_id
        assert domain_order.quotation_id == quotation_id
        assert len(domain_order.lines) == 2
        assert domain_order.total == 800  # 5*100 + 3*100

    async def test_convert_marks_quotation_as_won(
        self, factory, accepted_quotation
    ):
        quotation_id, _, _ = accepted_quotation
        async with factory() as session:
            use_case = ConvertQuotationToOrderUseCase(session, user_id=1)
            await use_case.execute(quotation_id)
            await session.commit()

        async with factory() as verify_session:
            from sqlalchemy import select

            quote = (
                await verify_session.execute(
                    select(Quotation).where(Quotation.id == quotation_id)
                )
            ).scalar_one()
            assert quote.status == "won"

    async def test_convert_nonexistent_raises_not_found(self, factory):
        async with factory() as session:
            use_case = ConvertQuotationToOrderUseCase(session, user_id=1)
            with pytest.raises(NotFoundError) as ei:
                await use_case.execute(quotation_id=99999)
            assert ei.value.http_status == 404

    async def test_convert_generates_order_no(self, factory, accepted_quotation):
        quotation_id, _, _ = accepted_quotation
        async with factory() as session:
            use_case = ConvertQuotationToOrderUseCase(session, user_id=1)
            result = await use_case.execute(quotation_id)
            await session.commit()

        assert result.id is not None
        assert result.order_no is not None
        assert result.order_no.startswith("SO")

        async with factory() as verify_session:
            from app.models.sales import SalesOrder as SalesOrderModel
            from sqlalchemy import select

            order = (
                await verify_session.execute(
                    select(SalesOrderModel).where(
                        SalesOrderModel.quotation_id == quotation_id
                    )
                )
            ).scalar_one()
            assert order.order_no is not None
            assert order.order_no.startswith("SO")

    async def test_adapter_persists_canonical_won_status(self, factory, accepted_quotation):
        quotation_id, _, _ = accepted_quotation
        async with factory() as session:
            use_case = ConvertQuotationToOrderUseCase(
                session,
                user_id=1,
                final_quotation_status="won",
            )
            result = await use_case.execute(quotation_id)
            await session.commit()

        assert result.id is not None
        assert result.order_no is not None

        async with factory() as verify_session:
            from sqlalchemy import select

            quote = (
                await verify_session.execute(
                    select(Quotation).where(Quotation.id == quotation_id)
                )
            ).scalar_one()
            assert quote.status == "won"

    async def test_double_convert_raises(self, factory, accepted_quotation):
        quotation_id, _, _ = accepted_quotation
        async with factory() as session:
            use_case = ConvertQuotationToOrderUseCase(session, user_id=1)
            await use_case.execute(quotation_id)
            await session.commit()

        # Second attempt: quotation is now CONVERTED, cannot convert again
        async with factory() as session:
            use_case2 = ConvertQuotationToOrderUseCase(session, user_id=1)
            from app.domain.shared.errors import InvalidStateTransition

            with pytest.raises(InvalidStateTransition):
                await use_case2.execute(quotation_id)
