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
    for i in range(10):
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
    """Products with 0<qty<=safety_stock should appear; qty<=0 should NOT."""
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


async def test_generate_ai_summary_no_anomalies(monkeypatch):
    """Empty anomalies should still call AI once with '无明显异常' text."""
    from app.services import watchtower_service
    from app.services.ai import client as ai_client_module

    called = {"count": 0, "last_text": None}

    async def fake_chat(messages, schema):
        called["count"] += 1
        called["last_text"] = messages[1]["content"]
        return {
            "severity": "正常",
            "summary": "ok",
            "top_actions": [],
            "risk_areas": [],
        }

    monkeypatch.setattr(ai_client_module.ai_client, "chat_structured", fake_chat)

    result = await watchtower_service.generate_ai_summary({}, 0)
    assert called["count"] == 1
    assert "无明显异常" in called["last_text"]
    assert result["severity"] == "正常"


async def test_generate_ai_summary_failure_falls_back(monkeypatch):
    """If ai_client throws, return fallback {severity: '正常', summary: 'AI分析暂不可用', ...}."""
    from app.services import watchtower_service
    from app.services.ai import client as ai_client_module

    async def fake_chat(messages, schema):
        raise RuntimeError("AI service down")

    monkeypatch.setattr(ai_client_module.ai_client, "chat_structured", fake_chat)

    anomalies = {
        "churn_risk": [{"name": "A", "industry": "电子", "level": "A", "signal": "x"}]
    }
    result = await watchtower_service.generate_ai_summary(anomalies, 1)
    assert result["severity"] == "正常"
    assert "暂不可用" in result["summary"]
    assert result["top_actions"] == []
    assert result["risk_areas"] == []


async def test_persist_customer_alerts_dynamic_lookback(db_session):
    """Message should reflect lookback_days parameter, not hardcoded 90."""
    from datetime import datetime, timezone

    from sqlalchemy import select

    from app.models.customer import AlertEvent, Customer
    from app.services.watchtower_service import _persist_customer_alerts

    customer = Customer(name="下降客户A", industry="电子", level="A")
    db_session.add(customer)
    await db_session.flush()
    cid = customer.id

    await _persist_customer_alerts(
        db_session,
        {
            "order_drop": [
                {
                    "customer_id": cid,
                    "name": "下降客户A",
                    "prev_orders": 10,
                    "recent_orders": 2,
                    "drop_pct": 80,
                }
            ],
            "churn_risk": [],
        },
        scan_time=datetime.now(timezone.utc),
        lookback_days=30,
    )
    await db_session.commit()

    alert = (
        await db_session.execute(
            select(AlertEvent).where(AlertEvent.rule_type == "order_drop")
        )
    ).scalar_one_or_none()
    assert alert is not None
    assert "近30天" in alert.message
