"""Tests for /commissions/batch-transition (Stage 11 Day 2)."""

import json

import pytest
import pytest_asyncio
from unittest.mock import patch, AsyncMock
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.commissions import batch_transition
from app.models.customer import Customer
from app.models.finance import Commission
from app.models.sales import SalesOrder
from app.models.user import User


async def _create_commission_source(db_session: AsyncSession, index: int = 1):
    user = User(username=f"commission-user-{index}", password="test", role="sales")
    customer = Customer(name=f"Commission Customer {index}")
    db_session.add_all([user, customer])
    await db_session.flush()
    order = SalesOrder(
        order_no=f"SO-COMM-{index}",
        customer_id=customer.id,
        total_amount=1000,
        status="completed",
    )
    db_session.add(order)
    await db_session.flush()
    return user, customer, order


@pytest_asyncio.fixture
async def setup_commissions(db_session: AsyncSession):
    """Insert test commissions and return them via db_session fixture."""
    items = []
    for i in range(1, 4):
        user, customer, order = await _create_commission_source(db_session, i)
        c = Commission(
            commission_no=f"CM-B{i}",
            sales_order_id=order.id,
            sales_user_id=user.id,
            customer_id=customer.id,
            base_amount=1000,
            rate=0.05,
            commission_amount=50,
            status="pending_approval",
        )
        db_session.add(c)
        items.append(c)
    await db_session.commit()
    yield db_session, items


@pytest.mark.asyncio
async def test_batch_approve_mixed_success_and_failure(setup_commissions):
    """Mixed: some succeed, some fail. Both reported."""
    db, items = setup_commissions
    user = {"id": items[0].sales_user_id, "username": "manager"}

    with patch("app.services.cache_service.cache_bump_version", new_callable=AsyncMock):
        result = await batch_transition(
            payload={
                "ids": [item.id for item in items] + [9999],
                "to": "approved",
                "notes": "monthly batch",
            },
            db=db,
            user=user,
        )

    assert result["code"] == 0
    succeeded = result["data"]["succeeded"]
    failed = result["data"]["failed"]
    # 3 real ids should succeed; 9999 should fail with not-found
    assert len(succeeded) == 3, f"got: {result['data']}"
    assert len(failed) == 1
    assert failed[0]["id"] == 9999
    assert "not found" in failed[0]["error"]


@pytest.mark.asyncio
async def test_batch_empty_ids_returns_400(db_session: AsyncSession):
    user = {"id": 42, "username": "manager"}
    result = await batch_transition(
        payload={"ids": [], "to": "approved"},
        db=db_session,
        user=user,
    )
    body = json.loads(result.body)
    assert body["code"] == 400
    assert result.status_code == 400


@pytest.mark.asyncio
async def test_batch_invalid_target_returns_400(db_session: AsyncSession):
    user = {"id": 42, "username": "manager"}
    result = await batch_transition(
        payload={"ids": [1], "to": "invalid_status"},
        db=db_session,
        user=user,
    )
    body = json.loads(result.body)
    assert body["code"] == 400
    assert result.status_code == 400


@pytest.mark.asyncio
async def test_batch_paid_with_amount(db_session: AsyncSession):
    """Paid batch with shared paid_amount propagates to each row."""
    ids = []
    for i in range(3):
        user, customer, order = await _create_commission_source(db_session, i)
        c = Commission(
            commission_no=f"CM-P{i}",
            sales_order_id=order.id,
            sales_user_id=user.id,
            customer_id=customer.id,
            base_amount=2000,
            rate=0.05,
            commission_amount=100,
            status="approved",
        )
        db_session.add(c)
        await db_session.flush()
        ids.append(c.id)
    await db_session.commit()

    user = {"id": 42, "username": "finance"}
    with patch("app.services.cache_service.cache_bump_version", new_callable=AsyncMock):
        result = await batch_transition(
            payload={
                "ids": ids,
                "to": "paid",
                "paid_amount": 100.0,
                "notes": "May payout",
            },
            db=db_session,
            user=user,
        )
    assert result["code"] == 0
    assert result["data"]["summary"]["succeeded"] == 3, f"got: {result['data']}"

    # Verify the rows were paid
    from sqlalchemy import select

    rows = (
        (await db_session.execute(select(Commission).where(Commission.id.in_(ids))))
        .scalars()
        .all()
    )
    for r in rows:
        assert r.status == "paid"
        assert float(r.paid_amount) == 100.0


@pytest.mark.asyncio
async def test_batch_bumps_cache_once(db_session: AsyncSession):
    """Single cache bump at end, not per-id (saves N cache invalidations)."""
    user = {"id": 42, "username": "manager"}
    # All non-existent — but transitions get called, cache should still bump once
    with patch(
        "app.services.cache_service.cache_bump_version", new_callable=AsyncMock
    ) as mock_bump:
        await batch_transition(
            payload={"ids": [1, 2, 3], "to": "approved"},
            db=db_session,
            user=user,
        )
    # Even when all fail, cache is still bumped once for the dashboard
    assert mock_bump.call_count == 1
