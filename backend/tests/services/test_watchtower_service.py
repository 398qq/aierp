import pytest
from datetime import datetime, timedelta, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from app.services.watchtower_service import scan_churn_risk

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
