import pytest
from datetime import datetime, timedelta, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from app.services.watchtower_service import scan_churn_risk, scan_order_drop

pytestmark = pytest.mark.asyncio


async def test_scan_churn_risk_returns_churned_customers(db_session: AsyncSession):
    """Customers active in prev period but silent in recent should appear in churn_risk."""
    from app.models.sales import SalesOrder
    from app.models.customer import Customer

    now = datetime.now(timezone.utc)
    lookback = now - timedelta(days=90)
    prev_lookback = lookback - timedelta(days=90)

    c1 = Customer(name="流失客户A", industry="电子", level="A")
    db_session.add(c1)
    await db_session.flush()
    so_prev = SalesOrder(
        customer_id=c1.id,
        total_amount=100,
        created_at=prev_lookback + timedelta(days=1),
    )
    db_session.add(so_prev)

    c2 = Customer(name="活跃客户B", industry="电子", level="B")
    db_session.add(c2)
    await db_session.flush()
    so_recent = SalesOrder(
        customer_id=c2.id, total_amount=200, created_at=now - timedelta(days=1)
    )
    db_session.add(so_recent)
    await db_session.commit()

    result = await scan_churn_risk(db_session, lookback, prev_lookback)
    names = {r["name"] for r in result}
    assert "流失客户A" in names
    assert "活跃客户B" not in names


async def test_scan_churn_risk_empty_when_no_prev(db_session: AsyncSession):
    result = await scan_churn_risk(
        db_session,
        datetime.now(timezone.utc),
        datetime.now(timezone.utc),
    )
    assert result == []


async def test_scan_order_drop_marks_significant_drops(db_session: AsyncSession):
    """Customer with prev>=3 orders and recent<50% should be marked as drop."""
    from app.models.sales import SalesOrder
    from app.models.customer import Customer

    now = datetime.now(timezone.utc)
    lookback = now - timedelta(days=90)
    prev_lookback = lookback - timedelta(days=90)

    c = Customer(name="订单下降客户", industry="电子", level="B")
    db_session.add(c)
    await db_session.flush()
    cid = c.id
    # 10 prev orders
    for i in range(10):
        db_session.add(
            SalesOrder(
                customer_id=cid,
                total_amount=100,
                created_at=prev_lookback + timedelta(days=1, hours=i),
            )
        )
    # 1 recent order
    db_session.add(
        SalesOrder(
            customer_id=cid, total_amount=100, created_at=now - timedelta(days=1)
        )
    )
    await db_session.commit()

    result = await scan_order_drop(db_session, lookback, prev_lookback)
    assert any(r["customer_id"] == cid for r in result)
    match = next(r for r in result if r["customer_id"] == cid)
    assert match["prev_orders"] == 10
    assert match["recent_orders"] == 1
    assert match["drop_pct"] == 90


async def test_scan_order_drop_below_threshold_excluded(db_session: AsyncSession):
    """Customer with prev<3 orders should not appear, even with relative drop."""
    from app.models.sales import SalesOrder
    from app.models.customer import Customer

    now = datetime.now(timezone.utc)
    lookback = now - timedelta(days=90)
    prev_lookback = lookback - timedelta(days=90)

    c = Customer(name="小客户", industry="电子", level="C")
    db_session.add(c)
    await db_session.flush()
    cid = c.id
    for i in range(2):
        db_session.add(
            SalesOrder(
                customer_id=cid,
                total_amount=100,
                created_at=prev_lookback + timedelta(days=1, hours=i),
            )
        )
    db_session.add(
        SalesOrder(
            customer_id=cid, total_amount=100, created_at=now - timedelta(days=1)
        )
    )
    await db_session.commit()

    result = await scan_order_drop(db_session, lookback, prev_lookback)
    assert all(r["customer_id"] != cid for r in result)
