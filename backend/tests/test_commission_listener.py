"""Tests for auto-commission on invoice paid (Stage 7 Part 2)."""

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.services.commission_listener import on_invoice_paid


@pytest_asyncio.fixture
async def db():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        # Import models so Base knows about them
        from app.models.audit import FieldChangeLog  # noqa
        from app.models.customer import Customer  # noqa
        from app.models.sales import SalesOrder, SalesOrderItem  # noqa
        from app.models.finance import (  # noqa
            Commission, Invoice, InvoiceLine, PaymentRecord,
        )
        from app.models.user import User  # noqa
        from app.models.product import Product  # noqa
        await conn.run_sync(Base.metadata.create_all)
    SessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with SessionLocal() as session:
        yield session
    await engine.dispose()


@pytest.mark.asyncio
async def test_on_invoice_paid_creates_commission(db: AsyncSession):
    from app.models.customer import Customer
    from app.models.sales import SalesOrder
    from app.models.finance import Invoice
    from app.models.user import User

    # Setup: user + customer + order + invoice
    user = User(id=100, username="alice", password="x")
    db.add(user)
    cust = Customer(id=1, name="Acme", contact_person="Alice", owner="100")
    db.add(cust)
    order = SalesOrder(id=10, order_no="SO-001", customer_id=1, status="completed", total_amount=10000)
    db.add(order)
    inv = Invoice(id=20, invoice_no="INV-001", sales_order_id=10, customer_id=1, amount=10000, status="paid")
    db.add(inv)
    await db.commit()

    # Act
    commission = await on_invoice_paid(db, inv.id)

    # Assert
    assert commission is not None
    assert commission.sales_order_id == 10
    assert commission.sales_user_id == 100
    assert commission.base_amount == 10000
    assert float(commission.rate) == 0.05  # default 5%
    assert float(commission.commission_amount) == 500.0  # 10000 * 5%
    assert commission.status == "draft"


@pytest.mark.asyncio
async def test_idempotent_no_double_commission(db: AsyncSession):
    from app.models.customer import Customer
    from app.models.sales import SalesOrder
    from app.models.finance import Invoice, Commission
    from app.models.user import User
    from sqlalchemy import select

    user = User(id=200, username="bob", password="x")
    db.add(user)
    cust = Customer(id=2, name="Beta", contact_person="Bob", owner="200")
    db.add(cust)
    order = SalesOrder(id=20, order_no="SO-002", customer_id=2, status="completed", total_amount=5000)
    db.add(order)
    inv = Invoice(id=30, invoice_no="INV-002", sales_order_id=20, customer_id=2, amount=5000, status="paid")
    db.add(inv)
    await db.commit()

    # First call: creates
    c1 = await on_invoice_paid(db, inv.id)
    assert c1 is not None

    # Second call: returns None (idempotent)
    c2 = await on_invoice_paid(db, inv.id)
    assert c2 is None

    # DB has exactly one
    count = (await db.execute(
        select(Commission).where(Commission.sales_order_id == 20)
    )).scalars().all()
    assert len(count) == 1


@pytest.mark.asyncio
async def test_skips_invoice_without_sales_order(db: AsyncSession):
    """The listener defends against invoices whose sales_order doesn't exist.

    Schema-level: sales_order_id is NOT NULL, so we cannot create a NULL row.
    We test the equivalent path: invoice links to a non-existent order.
    The listener loads the SalesOrder and skips if not found.
    """
    from app.models.customer import Customer
    from app.models.finance import Invoice

    cust = Customer(id=3, name="Gamma", owner="100")
    db.add(cust)
    # sales_order_id=999 points to a non-existent order
    inv = Invoice(id=40, invoice_no="INV-003", sales_order_id=999, customer_id=3, amount=1000, status="paid")
    db.add(inv)
    await db.commit()

    result = await on_invoice_paid(db, inv.id)
    assert result is None  # skipped (order not found)


@pytest.mark.asyncio
async def test_skips_unpaid_invoice(db: AsyncSession):
    from app.models.customer import Customer
    from app.models.sales import SalesOrder
    from app.models.finance import Invoice

    cust = Customer(id=4, name="Delta", owner="100")
    db.add(cust)
    order = SalesOrder(id=30, order_no="SO-003", customer_id=4, status="pending", total_amount=1000)
    db.add(order)
    inv = Invoice(id=50, invoice_no="INV-004", sales_order_id=30, customer_id=4, amount=1000, status="issued")  # not paid
    db.add(inv)
    await db.commit()

    result = await on_invoice_paid(db, inv.id)
    assert result is None  # invoice not paid


@pytest.mark.asyncio
async def test_skips_when_owner_not_numeric(db: AsyncSession):
    """If customer.owner is a name (not a user id), skip commission creation.

    Common case: 'owner' field stores a name like '张三' rather than a numeric FK.
    The system cannot resolve to a user without a name→id mapping (out of scope for Stage 7).
    """
    from app.models.customer import Customer
    from app.models.sales import SalesOrder
    from app.models.finance import Invoice

    cust = Customer(id=5, name="Epsilon", owner="张三")  # name, not id
    db.add(cust)
    order = SalesOrder(id=40, order_no="SO-004", customer_id=5, status="completed", total_amount=2000)
    db.add(order)
    inv = Invoice(id=60, invoice_no="INV-005", sales_order_id=40, customer_id=5, amount=2000, status="paid")
    db.add(inv)
    await db.commit()

    result = await on_invoice_paid(db, inv.id)
    assert result is None  # owner not numeric, skip
