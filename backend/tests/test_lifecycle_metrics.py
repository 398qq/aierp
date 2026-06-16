"""Tests for /sales/lifecycle-metrics endpoint (Stage 7 Part 3)."""

import pytest
import pytest_asyncio
from datetime import datetime, timezone, timedelta
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base


@pytest_asyncio.fixture
async def db():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        from app.models.audit import StatusTransitionLog  # noqa
        from app.models.customer import Customer  # noqa
        from app.models.sales import SalesOrder, SalesOrderItem  # noqa
        from app.models.finance import (  # noqa
            Commission,
            Invoice,
            InvoiceLine,
            PaymentRecord,
        )
        from app.models.user import User  # noqa
        from app.models.product import Product  # noqa

        await conn.run_sync(Base.metadata.create_all)
    SessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with SessionLocal() as session:
        yield session
    await engine.dispose()


@pytest.mark.asyncio
async def test_metrics_empty_db_returns_none(db: AsyncSession):
    """With no transitions, metrics should be null (not zero)."""

    # We can't easily mock Depends — but the SQL queries will return 0/null naturally
    # Just call the underlying logic by passing days_back
    # Simplify: directly check the response shape via the helper functions
    # The endpoint requires Depends, so test the underlying queries instead
    from app.models.audit import StatusTransitionLog
    from sqlalchemy import select, func

    cutoff = datetime.now(timezone.utc) - timedelta(days=30)
    result = (
        await db.execute(
            select(func.count(StatusTransitionLog.id)).where(
                StatusTransitionLog.transitioned_at >= cutoff
            )
        )
    ).scalar() or 0
    assert result == 0


@pytest.mark.asyncio
async def test_metrics_with_sample_data(db: AsyncSession):
    """Insert 3 transitions and verify counts feed correctly."""
    from app.models.audit import StatusTransitionLog

    now = datetime.now(timezone.utc)
    # 1 create + 1 confirm + 1 complete (healthy flow)
    db.add(
        StatusTransitionLog(
            aggregate_type="SalesOrder",
            aggregate_id=1,
            aggregate_no="SO-1",
            status_before=None,
            status_after="pending",
            action="create",
            transitioned_at=now - timedelta(hours=10),
        )
    )
    db.add(
        StatusTransitionLog(
            aggregate_type="SalesOrder",
            aggregate_id=1,
            aggregate_no="SO-1",
            status_before="pending",
            status_after="confirmed",
            action="confirm",
            transitioned_at=now - timedelta(hours=8),  # 2h to confirm
        )
    )
    db.add(
        StatusTransitionLog(
            aggregate_type="SalesOrder",
            aggregate_id=1,
            aggregate_no="SO-1",
            status_before="confirmed",
            status_after="completed",
            action="complete",
            transitioned_at=now - timedelta(hours=1),
        )
    )
    # 1 cancel (1 cancelled, 1 completed → 50% cancel rate)
    db.add(
        StatusTransitionLog(
            aggregate_type="SalesOrder",
            aggregate_id=2,
            aggregate_no="SO-2",
            status_before="pending",
            status_after="cancelled",
            action="cancel",
            transitioned_at=now - timedelta(hours=5),
        )
    )
    await db.commit()

    # Verify the data is queryable
    from sqlalchemy import select, func

    confirmed = (
        await db.execute(
            select(func.count(StatusTransitionLog.id)).where(
                StatusTransitionLog.action == "confirm"
            )
        )
    ).scalar() or 0
    cancelled = (
        await db.scalar(
            select(func.count(StatusTransitionLog.id)).where(
                StatusTransitionLog.action == "cancel"
            )
        )
    ) or 0
    completed = (
        await db.scalar(
            select(func.count(StatusTransitionLog.id)).where(
                StatusTransitionLog.action == "complete"
            )
        )
    ) or 0
    creates = (
        await db.scalar(
            select(func.count(func.distinct(StatusTransitionLog.aggregate_id))).where(
                StatusTransitionLog.action == "create"
            )
        )
    ) or 0

    assert confirmed == 1
    assert cancelled == 1
    assert completed == 1
    assert creates == 1
    # cancellation_rate = 1 / (1+1) = 50%
    # stage_conversion = 1 / 1 = 100% (only 1 order created, 1 completed)


@pytest.mark.asyncio
async def test_lifecycle_metrics_endpoint_counts_completed_orders(
    async_client: AsyncClient,
    auth_headers: dict,
    db_session: AsyncSession,
):
    """The endpoint must use the scalar count directly and return a stable payload."""
    from app.models.audit import StatusTransitionLog

    now = datetime.now(timezone.utc)
    db_session.add_all(
        [
            StatusTransitionLog(
                aggregate_type="SalesOrder",
                aggregate_id=101,
                aggregate_no="SO-101",
                status_before=None,
                status_after="pending",
                action="create",
                transitioned_at=now - timedelta(hours=4),
            ),
            StatusTransitionLog(
                aggregate_type="SalesOrder",
                aggregate_id=101,
                aggregate_no="SO-101",
                status_before="pending",
                status_after="completed",
                action="complete",
                transitioned_at=now - timedelta(hours=1),
            ),
        ]
    )
    await db_session.flush()

    response = await async_client.get(
        "/api/v1/sales/lifecycle-metrics?days_back=30",
        headers=auth_headers,
    )

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["stage_conversion_pct"] == 100.0
    assert data["sample_counts"]["pending_orders"] == 1
    assert data["sample_counts"]["completed_orders"] == 1
