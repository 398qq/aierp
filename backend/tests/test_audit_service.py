"""Tests for audit_service.log_transition + query helpers.

Stage 2 Day 3 — 状态审计 append-only 日志。
"""

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.audit_service import (
    get_aggregate_timeline,
    get_customer_timeline,
    log_transition,
)


@pytest_asyncio.fixture
async def db():
    """Yield a fresh in-memory sqlite session for isolation."""
    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
    from app.database import Base

    # Import all models to register tables

    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with session_factory() as session:
        yield session
    await engine.dispose()


# ── log_transition ────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_log_simple_transition(db: AsyncSession):
    log = await log_transition(
        db,
        aggregate_type="SalesOrder",
        aggregate_id=100,
        status_before="pending",
        status_after="confirmed",
        action="confirm",
    )
    await db.commit()
    assert log.id is not None
    assert log.transitioned_at is not None
    assert log.aggregate_type == "SalesOrder"
    assert log.aggregate_id == 100
    assert log.status_before == "pending"
    assert log.status_after == "confirmed"
    assert log.action == "confirm"
    assert log.actor is None  # default is None, callers pass "system" explicitly


@pytest.mark.asyncio
async def test_log_with_full_context(db: AsyncSession):
    log = await log_transition(
        db,
        aggregate_type="Invoice",
        aggregate_id=200,
        aggregate_no="INV20260611001",
        status_before="issued",
        status_after="cancelled",
        action="cancel",
        actor="user_42",
        reason="客户拒收",
        customer_id=1,
        sales_order_id=100,
    )
    await db.commit()
    assert log.aggregate_no == "INV20260611001"
    assert log.actor == "user_42"
    assert log.reason == "客户拒收"
    assert log.customer_id == 1
    assert log.sales_order_id == 100


@pytest.mark.asyncio
async def test_log_with_null_status_before_for_creation(db: AsyncSession):
    """Creation events have no 'before' status."""
    log = await log_transition(
        db,
        aggregate_type="SalesOrder",
        aggregate_id=101,
        status_before=None,
        status_after="pending",
        action="create",
    )
    await db.commit()
    assert log.status_before is None
    assert log.status_after == "pending"


@pytest.mark.asyncio
async def test_default_actor_is_none(db: AsyncSession):
    log = await log_transition(
        db,
        aggregate_type="PaymentRecord",
        aggregate_id=300,
        status_before="pending",
        status_after="completed",
        action="auto_reconcile",
    )
    await db.commit()
    assert log.actor is None  # Default; explicit "system" is caller's job


# ── get_aggregate_timeline ────────────────────────────────────────────


@pytest.mark.asyncio
async def test_aggregate_timeline_returns_oldest_first(db: AsyncSession):
    # 4 transitions for SO #100: pending → confirmed → shipped → completed
    for prev, new, action in [
        (None, "pending", "create"),
        ("pending", "confirmed", "confirm"),
        ("confirmed", "shipped", "ship"),
        ("shipped", "completed", "complete"),
    ]:
        await log_transition(
            db,
            aggregate_type="SalesOrder",
            aggregate_id=100,
            status_before=prev,
            status_after=new,
            action=action,
        )
        await db.commit()

    timeline = await get_aggregate_timeline(db, "SalesOrder", 100)
    assert len(timeline) == 4
    assert [t.status_after for t in timeline] == ["pending", "confirmed", "shipped", "completed"]
    assert [t.action for t in timeline] == ["create", "confirm", "ship", "complete"]


@pytest.mark.asyncio
async def test_aggregate_timeline_filters_by_aggregate_id(db: AsyncSession):
    """SO #100 and SO #200 should be separate timelines."""
    await log_transition(db, "SalesOrder", 100, None, "pending", "create")
    await log_transition(db, "SalesOrder", 200, None, "pending", "create")
    await log_transition(db, "SalesOrder", 100, "pending", "confirmed", "confirm")
    await db.commit()

    timeline_100 = await get_aggregate_timeline(db, "SalesOrder", 100)
    timeline_200 = await get_aggregate_timeline(db, "SalesOrder", 200)
    assert len(timeline_100) == 2
    assert len(timeline_200) == 1


@pytest.mark.asyncio
async def test_aggregate_timeline_filters_by_aggregate_type(db: AsyncSession):
    """Same id but different types should not mix."""
    await log_transition(db, "SalesOrder", 100, None, "pending", "create")
    await log_transition(db, "Invoice", 100, None, "draft", "create")
    await db.commit()

    so_timeline = await get_aggregate_timeline(db, "SalesOrder", 100)
    inv_timeline = await get_aggregate_timeline(db, "Invoice", 100)
    assert len(so_timeline) == 1
    assert so_timeline[0].aggregate_type == "SalesOrder"
    assert len(inv_timeline) == 1
    assert inv_timeline[0].aggregate_type == "Invoice"


# ── get_customer_timeline ─────────────────────────────────────────────


@pytest.mark.asyncio
async def test_customer_timeline_returns_newest_first(db: AsyncSession):
    # 2 transitions for customer 1
    await log_transition(db, "SalesOrder", 100, None, "pending", "create", customer_id=1)
    await db.commit()
    await log_transition(db, "SalesOrder", 100, "pending", "confirmed", "confirm", customer_id=1)
    await db.commit()

    timeline = await get_customer_timeline(db, customer_id=1)
    assert len(timeline) == 2
    # Newest first
    assert timeline[0].action == "confirm"
    assert timeline[1].action == "create"


@pytest.mark.asyncio
async def test_customer_timeline_filters_by_customer(db: AsyncSession):
    await log_transition(db, "SalesOrder", 100, None, "pending", "create", customer_id=1)
    await log_transition(db, "SalesOrder", 200, None, "pending", "create", customer_id=2)
    await db.commit()

    cust_1 = await get_customer_timeline(db, customer_id=1)
    cust_2 = await get_customer_timeline(db, customer_id=2)
    assert len(cust_1) == 1
    assert len(cust_2) == 1
    assert cust_1[0].customer_id == 1
    assert cust_2[0].customer_id == 2


@pytest.mark.asyncio
async def test_customer_timeline_respects_limit(db: AsyncSession):
    for i in range(15):
        await log_transition(
            db, "SalesOrder", 100 + i, None, "pending", "create", customer_id=1
        )
    await db.commit()
    timeline = await get_customer_timeline(db, customer_id=1, limit=5)
    assert len(timeline) == 5


@pytest.mark.asyncio
async def test_audit_log_does_not_commit(db: AsyncSession):
    """log_transition only flushes; caller controls commit atomicity."""
    await log_transition(
        db, "SalesOrder", 100, None, "pending", "create"
    )
    # No commit yet
    # Verify it's visible within session (flushed)
    from sqlalchemy import select
    from app.models.audit import StatusTransitionLog
    result = await db.execute(select(StatusTransitionLog))
    assert len(result.scalars().all()) == 1


# ── Cross-aggregate: full lifecycle audit trail ──────────────────────


@pytest.mark.asyncio
async def test_full_sales_order_lifecycle_creates_4_log_entries(db: AsyncSession):
    """Simulate the full 4-transition lifecycle and verify audit trail."""
    aggregate_id = 100
    transitions = [
        (None, "pending", "create", None),
        ("pending", "confirmed", "confirm", "owner_alice"),
        ("confirmed", "shipped", "ship", "system"),
        ("shipped", "completed", "complete", "system"),
    ]
    for prev, new, action, actor in transitions:
        await log_transition(
            db,
            aggregate_type="SalesOrder",
            aggregate_id=aggregate_id,
            aggregate_no=f"SO{aggregate_id:08d}",
            status_before=prev,
            status_after=new,
            action=action,
            actor=actor,
            customer_id=1,
        )
    await db.commit()

    timeline = await get_aggregate_timeline(db, "SalesOrder", aggregate_id)
    assert len(timeline) == 4
    assert [t.action for t in timeline] == ["create", "confirm", "ship", "complete"]
    assert [t.actor for t in timeline] == [None, "owner_alice", "system", "system"]  # type: ignore[comparison-overlap]
    # All share customer_id
    assert all(t.customer_id == 1 for t in timeline)
