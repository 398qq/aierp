import pytest
from datetime import datetime, timedelta, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from app.services.watchtower_service import (
    scan_churn_risk,
    scan_order_drop,
    scan_low_stock,
    scan_out_of_stock,
)

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


async def test_scan_low_stock_returns_below_safety(db_session: AsyncSession):
    """Products with 0<qty<=safety_stock should appear; qty<=0 should NOT (that's out_of_stock)."""
    from app.models.product import Brand, Product, Inventory, Warehouse

    warehouse = Warehouse(name="测试仓库", location="TEST-LOC")
    db_session.add(warehouse)
    await db_session.flush()
    brand = Brand(name="BrandX")
    db_session.add(brand)
    await db_session.flush()
    p_low = Product(name="低库存品", sku="LOW-1", brand_id=brand.id)
    p_oos = Product(name="缺货品", sku="OOS-1", brand_id=brand.id)
    db_session.add_all([p_low, p_oos])
    await db_session.flush()
    db_session.add_all(
        [
            Inventory(
                product_id=p_low.id,
                warehouse_id=warehouse.id,
                quantity=2,
                safety_stock=10,
            ),
            Inventory(
                product_id=p_oos.id,
                warehouse_id=warehouse.id,
                quantity=0,
                safety_stock=5,
            ),
        ]
    )
    await db_session.commit()

    result = await scan_low_stock(db_session)
    ids = {r["product_id"] for r in result}
    assert p_low.id in ids
    assert p_oos.id not in ids
    match = next(r for r in result if r["product_id"] == p_low.id)
    assert match["qty"] == 2
    assert match["safety"] == 10


async def test_scan_out_of_stock_returns_zero_qty(db_session: AsyncSession):
    """Products with qty<=0 should appear in out_of_stock; qty>0 should NOT."""
    from app.models.product import Brand, Product, Inventory, Warehouse

    warehouse = Warehouse(name="测试仓库2", location="TEST-LOC2")
    db_session.add(warehouse)
    await db_session.flush()
    brand = Brand(name="BrandY")
    db_session.add(brand)
    await db_session.flush()
    p_oos = Product(name="缺货品", sku="OOS-2", brand_id=brand.id)
    p_ok = Product(name="正常品", sku="OK-2", brand_id=brand.id)
    db_session.add_all([p_oos, p_ok])
    await db_session.flush()
    db_session.add_all(
        [
            Inventory(
                product_id=p_oos.id,
                warehouse_id=warehouse.id,
                quantity=0,
                safety_stock=5,
            ),
            Inventory(
                product_id=p_ok.id,
                warehouse_id=warehouse.id,
                quantity=100,
                safety_stock=10,
            ),
        ]
    )
    await db_session.commit()

    result = await scan_out_of_stock(db_session)
    ids = {r["product_id"] for r in result}
    assert p_oos.id in ids
    assert p_ok.id not in ids
