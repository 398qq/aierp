"""Tests for commission state machine (Stage 10 Day 1)."""

import pytest
import pytest_asyncio
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
async def test_draft_to_pending_approval(db: AsyncSession):
    from app.models.finance import Commission
    from app.domain.states.finance import assert_can_transition_commission
    from app.domain.shared.errors import InvalidStateTransition

    c = Commission(
        commission_no="CM-001", sales_order_id=1, sales_user_id=1,
        base_amount=1000, rate=0.05, commission_amount=50,
        status="draft",
    )
    db.add(c)
    await db.commit()
    assert c.status == "draft"
    # Transition allowed
    assert_can_transition_commission("draft", "pending_approval")
    assert_can_transition_commission("draft", "cancelled")
    # Not allowed
    with pytest.raises(InvalidStateTransition):
        assert_can_transition_commission("draft", "paid")
    with pytest.raises(InvalidStateTransition):
        assert_can_transition_commission("draft", "approved")


@pytest.mark.asyncio
async def test_pending_to_approved_rejected(db: AsyncSession):
    from app.domain.states.finance import assert_can_transition_commission
    from app.domain.shared.errors import InvalidStateTransition

    # Allowed
    assert_can_transition_commission("pending_approval", "approved")
    assert_can_transition_commission("pending_approval", "rejected")
    assert_can_transition_commission("pending_approval", "draft")  # back to draft
    # Not allowed
    with pytest.raises(InvalidStateTransition):
        assert_can_transition_commission("pending_approval", "paid")


@pytest.mark.asyncio
async def test_approved_to_paid(db: AsyncSession):
    from app.domain.states.finance import assert_can_transition_commission
    from app.domain.shared.errors import InvalidStateTransition

    assert_can_transition_commission("approved", "paid")
    assert_can_transition_commission("approved", "cancelled")
    with pytest.raises(InvalidStateTransition):
        assert_can_transition_commission("approved", "rejected")


@pytest.mark.asyncio
async def test_paid_is_terminal(db: AsyncSession):
    from app.domain.states.finance import assert_can_transition_commission
    from app.domain.shared.errors import InvalidStateTransition

    # paid → no transitions allowed
    with pytest.raises(InvalidStateTransition):
        assert_can_transition_commission("paid", "approved")
    with pytest.raises(InvalidStateTransition):
        assert_can_transition_commission("paid", "cancelled")
    with pytest.raises(InvalidStateTransition):
        assert_can_transition_commission("paid", "pending_approval")


@pytest.mark.asyncio
async def test_cancelled_is_terminal(db: AsyncSession):
    from app.domain.states.finance import assert_can_transition_commission
    from app.domain.shared.errors import InvalidStateTransition

    with pytest.raises(InvalidStateTransition):
        assert_can_transition_commission("cancelled", "approved")
    with pytest.raises(InvalidStateTransition):
        assert_can_transition_commission("cancelled", "paid")


@pytest.mark.asyncio
async def test_update_commission_advances_state(db: AsyncSession):
    """Service update_commission applies the transition + side effects."""
    from app.models.finance import Commission
    from app.services.finance_service import update_commission

    c = Commission(
        commission_no="CM-002", sales_order_id=1, sales_user_id=1,
        base_amount=2000, rate=0.05, commission_amount=100,
        status="draft",
    )
    db.add(c)
    await db.commit()

    # Submit for approval
    updated = await update_commission(db, c, {"status": "pending_approval"})
    assert updated.status == "pending_approval"

    # Approve (sets approved_at)
    c2 = await update_commission(db, c, {"status": "approved", "approved_by": 42})
    assert c2.status == "approved"
    assert c2.approved_at is not None
    assert c2.approved_by == 42

    # Mark paid
    c3 = await update_commission(db, c, {"status": "paid"})
    assert c3.status == "paid"
    assert c3.paid_at is not None
    assert float(c3.paid_amount) == 100.0  # defaulted to commission_amount


@pytest.mark.asyncio
async def test_invalid_transition_raises(db: AsyncSession):
    """Service update_commission raises on illegal transition."""
    from app.models.finance import Commission
    from app.services.finance_service import update_commission
    from app.domain.shared.errors import InvalidStateTransition

    c = Commission(
        commission_no="CM-003", sales_order_id=1, sales_user_id=1,
        base_amount=1000, rate=0.05, commission_amount=50,
        status="draft",
    )
    db.add(c)
    await db.commit()

    # draft → paid is illegal
    with pytest.raises(InvalidStateTransition):
        await update_commission(db, c, {"status": "paid"})


@pytest.mark.asyncio
async def test_no_op_status_update_is_skipped(db: AsyncSession):
    """If status not in data, no transition check."""
    from app.models.finance import Commission
    from app.services.finance_service import update_commission

    c = Commission(
        commission_no="CM-004", sales_order_id=1, sales_user_id=1,
        base_amount=1000, rate=0.05, commission_amount=50,
        status="approved",
    )
    db.add(c)
    await db.commit()

    # Update notes only — no status transition
    updated = await update_commission(db, c, {"notes": "manual note"})
    assert updated.status == "approved"
    assert updated.notes == "manual note"
