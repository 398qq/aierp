"""Tests for commission_notifier (Stage 10 Day 2)."""

import pytest
import pytest_asyncio
from unittest.mock import patch, AsyncMock, MagicMock
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base


@pytest_asyncio.fixture
async def db():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
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
async def test_submit_does_not_notify(db: AsyncSession):
    """draft → pending_approval: low-signal, no Telegram."""
    from app.services.commission_notifier import on_commission_status_changed
    from app.models.finance import Commission

    c = Commission(
        commission_no="CM-N1", sales_order_id=1, sales_user_id=1,
        base_amount=1000, rate=0.05, commission_amount=50, status="pending_approval",
    )
    db.add(c)
    await db.commit()

    with patch("app.services.telegram_notifier.send_message") as mock_send:
        await on_commission_status_changed(
            db=db, commission=c, previous_status="draft",
            new_status="pending_approval", actor="alice",
        )
        # No Telegram call
        mock_send.assert_not_called()


@pytest.mark.asyncio
async def test_approved_sends_telegram(db: AsyncSession):
    """pending_approval → approved: notify sales user."""
    from app.services.commission_notifier import on_commission_status_changed
    from app.models.finance import Commission

    c = Commission(
        commission_no="CM-N2", sales_order_id=1, sales_user_id=1,
        base_amount=2000, rate=0.05, commission_amount=100,
        status="approved", customer_id=1, period="2026-06",
    )
    db.add(c)
    await db.commit()

    with patch("app.services.telegram_notifier.send_message") as mock_send:
        await on_commission_status_changed(
            db=db, commission=c, previous_status="pending_approval",
            new_status="approved", actor="manager",
        )
        mock_send.assert_called_once()
        msg = mock_send.call_args[0][0]
        assert "Approved" in msg
        assert "CM-N2" in msg
        assert "manager" in msg
        assert "\u00a5100" in msg  # amount


@pytest.mark.asyncio
async def test_paid_sends_telegram(db: AsyncSession):
    from app.services.commission_notifier import on_commission_status_changed
    from app.models.finance import Commission

    c = Commission(
        commission_no="CM-N3", sales_order_id=1, sales_user_id=1,
        base_amount=3000, rate=0.05, commission_amount=150, status="paid",
    )
    db.add(c)
    await db.commit()

    with patch("app.services.telegram_notifier.send_message") as mock_send:
        await on_commission_status_changed(
            db=db, commission=c, previous_status="approved",
            new_status="paid", actor="finance",
        )
        mock_send.assert_called_once()
        msg = mock_send.call_args[0][0]
        assert "Paid" in msg
        assert "finance" in msg


@pytest.mark.asyncio
async def test_rejected_sends_telegram(db: AsyncSession):
    from app.services.commission_notifier import on_commission_status_changed
    from app.models.finance import Commission

    c = Commission(
        commission_no="CM-N4", sales_order_id=1, sales_user_id=1,
        base_amount=4000, rate=0.05, commission_amount=200, status="rejected",
    )
    db.add(c)
    await db.commit()

    with patch("app.services.telegram_notifier.send_message") as mock_send:
        await on_commission_status_changed(
            db=db, commission=c, previous_status="pending_approval",
            new_status="rejected", actor="manager",
        )
        mock_send.assert_called_once()
        msg = mock_send.call_args[0][0]
        assert "Rejected" in msg


@pytest.mark.asyncio
async def test_telegram_failure_does_not_raise(db: AsyncSession):
    """Telegram send failure must not propagate."""
    from app.services.commission_notifier import on_commission_status_changed
    from app.models.finance import Commission

    c = Commission(
        commission_no="CM-N5", sales_order_id=1, sales_user_id=1,
        base_amount=5000, rate=0.05, commission_amount=250, status="approved",
    )
    db.add(c)
    await db.commit()

    with patch("app.services.telegram_notifier.send_message",
               side_effect=Exception("telegram down")):
        # Should not raise
        await on_commission_status_changed(
            db=db, commission=c, previous_status="pending_approval",
            new_status="approved", actor="manager",
        )


@pytest.mark.asyncio
async def test_enriches_with_user_order_customer(db: AsyncSession):
    """Message includes sales user name, order no, customer name when available."""
    from app.services.commission_notifier import on_commission_status_changed
    from app.models.finance import Commission
    from app.models.user import User
    from app.models.customer import Customer
    from app.models.sales import SalesOrder

    user = User(id=99, username="alice_star", password="***")
    db.add(user)
    cust = Customer(id=88, name="Acme Corp", owner="99")
    db.add(cust)
    order = SalesOrder(
        id=77, order_no="SO-2026-001", customer_id=88, status="completed", total_amount=20000,
    )
    db.add(order)
    c = Commission(
        commission_no="CM-N6", sales_order_id=77, sales_user_id=99, customer_id=88,
        base_amount=20000, rate=0.05, commission_amount=1000,
        status="paid", period="2026-06",
    )
    db.add(c)
    await db.commit()

    with patch("app.services.telegram_notifier.send_message") as mock_send:
        await on_commission_status_changed(
            db=db, commission=c, previous_status="approved",
            new_status="paid", actor="finance",
        )
        msg = mock_send.call_args[0][0]
        assert "alice_star" in msg
        assert "Acme Corp" in msg
        assert "SO-2026-001" in msg
