# Watchtower Dashboard Refactor 实现计划

> **面向 AI 代理的工作者：** 必需子技能：使用 superpowers:subagent-driven-development（推荐）或 superpowers:executing-plans 逐任务实现此计划。步骤使用复选框（`- [ ]`）语法来跟踪进度。

**目标：** 重构 Watchtower Dashboard（前端 + 后端），同行为同 API 同 UI；解出 4 痛点：性能（gather + cache）、代码组织（拆函数 + 拆组件）、视觉（design tokens + StatusTag）、Pro v6 一致性（useApiQuery + 12 backend pytest + 9 frontend vitest）。

**架构：** 后端将 `scan_all` 拆为 4 个域 scan + 1 个 AI summary + 1 个 persist；`asyncio.gather` 并行 4 scan；用版本控制缓存（300s scan / 600s report）避开 AI 重复打；4 个写点 bump 失效。前端将 222 行 tsx 拆为 5 个纯展示子组件 + 1 个壳 + useApiQuery 接入；CSS 用 CSS Module，零 magic color。

**技术栈：** Python 3.12 / FastAPI / SQLAlchemy 2.0 async / Redis cache_service / React 19 / TypeScript / UmiJS Max / Pro v6 (`useApiQuery`) / Ant Design 6 + ProComponents 3 / Vitest + Testing Library.

**参考 spec:** `docs/superpowers/specs/2026-07-31-watchtower-refactor-design.md`

---

## 任务 1：scan_churn_risk 函数（RED → GREEN → commit）

**文件：**
- 创建：`backend/tests/services/test_watchtower_service.py`
- 修改：`backend/app/services/watchtower_service.py`

- [ ] **步骤 1：写失败的测试**

```python
# backend/tests/services/test_watchtower_service.py
import pytest
from datetime import datetime, timedelta, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from app.services.watchtower_service import scan_churn_risk

pytestmark = pytest.mark.asyncio


async def test_scan_churn_risk_returns_churned_customers(db: AsyncSession):
    """Customers active in prev period but silent in recent should appear in churn_risk."""
    from app.models.sales import SalesOrder
    from app.models.customer import Customer

    now = datetime.now(timezone.utc)
    lookback = now - timedelta(days=90)
    prev_lookback = lookback - timedelta(days=90)

    # Customer 1: only prev-period order → churn
    c1 = Customer(name="流失客户A", industry="电子", level="A")
    db.add(c1)
    await db.flush()
    so_prev = SalesOrder(customer_id=c1.id, total_amount=100, created_at=prev_lookback + timedelta(days=1))
    db.add(so_prev)

    # Customer 2: recent order → not churn
    c2 = Customer(name="活跃客户B", industry="电子", level="B")
    db.add(c2)
    await db.flush()
    so_recent = SalesOrder(customer_id=c2.id, total_amount=200, created_at=now - timedelta(days=1))
    db.add(so_recent)
    await db.commit()

    result = await scan_churn_risk(db, lookback, prev_lookback)
    names = {r["name"] for r in result}
    assert "流失客户A" in names
    assert "活跃客户B" not in names


async def test_scan_churn_risk_empty_when_no_prev(db: AsyncSession):
    result = await scan_churn_risk(db, datetime.now(timezone.utc), datetime.now(timezone.utc))
    assert result == []
```

- [ ] **步骤 2：跑测试验证失败**

```bash
cd backend && pytest tests/services/test_watchtower_service.py::test_scan_churn_risk_returns_churned_customers -v
```

预期：FAIL，错误 `ImportError: cannot import name 'scan_churn_risk' from 'app.services.watchtower_service'`。

- [ ] **步骤 3：实现 scan_churn_risk**

替换 `backend/app/services/watchtower_service.py` 中现有的 `scan_all` 函数体。从现有实现里抽：

```python
# backend/app/services/watchtower_service.py
"""AI Watchtower — proactive anomaly detection and alert generation across the system."""

import datetime
import logging
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.product import Brand, Inventory, Product
from app.models.sales import SalesOrder
from app.models.customer import Customer, AlertEvent

logger = logging.getLogger(__name__)


async def scan_churn_risk(
    db: AsyncSession,
    lookback: datetime.datetime,
    prev_lookback: datetime.datetime,
) -> list[dict]:
    """Customers active in [prev_lookback, lookback) but silent in [lookback, now).
    Returns: [{customer_id, name, level, industry, signal}], max 20.
    """
    prev_active = set(
        (
            await db.execute(
                select(func.distinct(SalesOrder.customer_id)).where(
                    SalesOrder.created_at.between(prev_lookback, lookback),
                    SalesOrder.deleted_at.is_(None),
                )
            )
        )
        .scalars()
        .all()
    )
    recent_active = set(
        (
            await db.execute(
                select(func.distinct(SalesOrder.customer_id)).where(
                    SalesOrder.created_at >= lookback,
                    SalesOrder.deleted_at.is_(None),
                )
            )
        )
        .scalars()
        .all()
    )
    churned_ids = prev_active - recent_active
    if not churned_ids:
        return []
    churned = (
        await db.execute(
            select(Customer.id, Customer.name, Customer.level, Customer.industry).where(
                Customer.id.in_(list(churned_ids)), Customer.deleted_at.is_(None)
            )
        )
    ).all()
    days = (lookback - prev_lookback).days or 90
    return [
        {
            "customer_id": r[0],
            "name": r[1],
            "level": r[2],
            "industry": r[3],
            "signal": f"最近{days}天无订单",
        }
        for r in churned
    ]


async def scan_order_drop(db, lookback, prev_lookback):  # placeholder, filled in task 2
    raise NotImplementedError


async def scan_low_stock(db):  # placeholder, filled in task 3
    raise NotImplementedError


async def scan_out_of_stock(db):  # placeholder, filled in task 4
    raise NotImplementedError


async def generate_ai_summary(anomalies, total_alerts):  # placeholder, filled in task 5
    raise NotImplementedError


async def _persist_customer_alerts(db, anomalies, now):  # moved from old scan_all, unchanged
    raise NotImplementedError


async def scan_all(db, days_back=90):  # kept for backward compat, re-implemented in task 6
    raise NotImplementedError
```

- [ ] **步骤 4：跑测试验证通过**

```bash
cd backend && pytest tests/services/test_watchtower_service.py -v
```

预期：PASS（2 tests）。

- [ ] **步骤 5：Commit**

```bash
git add backend/tests/services/test_watchtower_service.py backend/app/services/watchtower_service.py
git commit -m "refactor(watchtower): extract scan_churn_risk from scan_all"
```

---

## 任务 2：scan_order_drop 函数

**文件：**
- 修改：`backend/app/services/watchtower_service.py`
- 修改：`backend/tests/services/test_watchtower_service.py`

- [ ] **步骤 1：写失败的测试**

```python
# append to backend/tests/services/test_watchtower_service.py
async def test_scan_order_drop_marks_significant_drops(db: AsyncSession):
    """Customer with prev>=3 orders and recent<50% should be marked as drop."""
    from app.models.sales import SalesOrder
    from app.models.customer import Customer

    now = datetime.now(timezone.utc)
    lookback = now - timedelta(days=90)
    prev_lookback = lookback - timedelta(days=90)

    c = Customer(name="订单下降客户", industry="电子", level="B")
    db.add(c)
    await db.flush()
    cid = c.id
    # 10 prev orders
    for i in range(10):
        db.add(SalesOrder(customer_id=cid, total_amount=100, created_at=prev_lookback + timedelta(days=1, hours=i)))
    # 1 recent order
    db.add(SalesOrder(customer_id=cid, total_amount=100, created_at=now - timedelta(days=1)))
    await db.commit()

    result = await scan_order_drop(db, lookback, prev_lookback)
    assert any(r["customer_id"] == cid for r in result)
    match = next(r for r in result if r["customer_id"] == cid)
    assert match["prev_orders"] == 10
    assert match["recent_orders"] == 1
    assert match["drop_pct"] == 90


async def test_scan_order_drop_below_threshold_excluded(db: AsyncSession):
    """Customer with prev<3 orders should not appear, even with relative drop."""
    from app.models.sales import SalesOrder
    from app.models.customer import Customer

    now = datetime.now(timezone.utc)
    lookback = now - timedelta(days=90)
    prev_lookback = lookback - timedelta(days=90)

    c = Customer(name="小客户", industry="电子", level="C")
    db.add(c)
    await db.flush()
    cid = c.id
    for i in range(2):
        db.add(SalesOrder(customer_id=cid, total_amount=100, created_at=prev_lookback + timedelta(days=1, hours=i)))
    db.add(SalesOrder(customer_id=cid, total_amount=100, created_at=now - timedelta(days=1)))
    await db.commit()

    result = await scan_order_drop(db, lookback, prev_lookback)
    assert all(r["customer_id"] != cid for r in result)
```

- [ ] **步骤 2：跑测试验证失败**

```bash
cd backend && pytest tests/services/test_watchtower_service.py::test_scan_order_drop_marks_significant_drops -v
```

预期：FAIL，`NotImplementedError`。

- [ ] **步骤 3：实现 scan_order_drop**

替换 `watchtower_service.py` 中 `scan_order_drop` 占位符：

```python
async def scan_order_drop(
    db: AsyncSession,
    lookback: datetime.datetime,
    prev_lookback: datetime.datetime,
) -> list[dict]:
    """Per-customer order count prev vs recent; drop >50% with prev>=3.
    Returns: [{customer_id, name, prev_orders, recent_orders, drop_pct}], max 20.
    """
    recent_counts = dict(
        (
            await db.execute(
                select(SalesOrder.customer_id, func.count(SalesOrder.id))
                .where(
                    SalesOrder.created_at >= lookback, SalesOrder.deleted_at.is_(None)
                )
                .group_by(SalesOrder.customer_id)
            )
        ).all()
        or []
    )
    prev_counts = dict(
        (
            await db.execute(
                select(SalesOrder.customer_id, func.count(SalesOrder.id))
                .where(
                    SalesOrder.created_at.between(prev_lookback, lookback),
                    SalesOrder.deleted_at.is_(None),
                )
                .group_by(SalesOrder.customer_id)
            )
        ).all()
        or []
    )

    order_drops = []
    for cid in set(list(recent_counts.keys()) + list(prev_counts.keys())):
        prev_c = prev_counts.get(cid, 0)
        recent_c = recent_counts.get(cid, 0)
        if prev_c >= 3 and recent_c < prev_c * 0.5:
            order_drops.append(
                {
                    "customer_id": cid,
                    "prev_orders": prev_c,
                    "recent_orders": recent_c,
                    "drop_pct": round((1 - recent_c / prev_c) * 100),
                }
            )

    if not order_drops:
        return []

    cids = [d["customer_id"] for d in order_drops[:20]]
    cnames = dict(
        (
            await db.execute(
                select(Customer.id, Customer.name).where(
                    Customer.id.in_(cids), Customer.deleted_at.is_(None)
                )
            )
        ).all()
        or []
    )
    return [
        {**d, "name": cnames.get(d["customer_id"], f"#{d['customer_id']}")}
        for d in order_drops[:20]
    ]
```

- [ ] **步骤 4：跑测试验证通过**

```bash
cd backend && pytest tests/services/test_watchtower_service.py -v
```

预期：PASS（4 tests）。

- [ ] **步骤 5：Commit**

```bash
git add backend/app/services/watchtower_service.py backend/tests/services/test_watchtower_service.py
git commit -m "refactor(watchtower): extract scan_order_drop from scan_all"
```

---

## 任务 3：scan_low_stock 函数

**文件：**
- 修改：`backend/app/services/watchtower_service.py`
- 修改：`backend/tests/services/test_watchtower_service.py`

- [ ] **步骤 1：写失败的测试**

```python
# append to backend/tests/services/test_watchtower_service.py
async def test_scan_low_stock_returns_below_safety(db: AsyncSession):
    """Products with 0<qty<=safety_stock should appear; qty<=0 should NOT (that's out_of_stock)."""
    from app.models.product import Brand, Product, Inventory

    brand = Brand(name="BrandX")
    db.add(brand)
    await db.flush()
    p_low = Product(name="低库存品", sku="LOW-1", brand_id=brand.id)
    p_oos = Product(name="缺货品", sku="OOS-1", brand_id=brand.id)
    db.add_all([p_low, p_oos])
    await db.flush()
    db.add_all([
        Inventory(product_id=p_low.id, quantity=2, safety_stock=10),  # low
        Inventory(product_id=p_oos.id, quantity=0, safety_stock=5),   # out of stock, NOT low
    ])
    await db.commit()

    result = await scan_low_stock(db)
    skus = {r["product_id"] for r in result}
    assert p_low.id in skus
    assert p_oos.id not in skus
    match = next(r for r in result if r["product_id"] == p_low.id)
    assert match["qty"] == 2
    assert match["safety"] == 10
```

- [ ] **步骤 2：跑测试验证失败**

```bash
cd backend && pytest tests/services/test_watchtower_service.py::test_scan_low_stock_returns_below_safety -v
```

预期：FAIL，`NotImplementedError`。

- [ ] **步骤 3：实现 scan_low_stock**

替换 `watchtower_service.py` 中 `scan_low_stock` 占位符：

```python
async def scan_low_stock(db: AsyncSession) -> list[dict]:
    """Inventory 0 < qty <= safety_stock. Returns 20 rows: product_id, product_name, brand, qty, safety.
    """
    rows = (
        await db.execute(
            select(
                Product.id,
                Product.name,
                Product.sku,
                Inventory.quantity,
                Inventory.safety_stock,
                Brand.name,
            )
            .join(Inventory, Product.id == Inventory.product_id)
            .outerjoin(Brand, Product.brand_id == Brand.id)
            .where(
                Inventory.quantity <= Inventory.safety_stock,
                Inventory.quantity > 0,
                Product.deleted_at.is_(None),
                Inventory.deleted_at.is_(None),
            )
            .order_by(Inventory.quantity)
            .limit(20)
        )
    ).all()
    return [
        {
            "product_id": r[0],
            "product_name": f"{r[2] or ''} {r[1]}",
            "brand": r[5] or "未知",
            "qty": r[3],
            "safety": r[4] or 0,
        }
        for r in rows
    ]
```

- [ ] **步骤 4：跑测试验证通过**

```bash
cd backend && pytest tests/services/test_watchtower_service.py -v
```

预期：PASS（5 tests）。

- [ ] **步骤 5：Commit**

```bash
git add backend/app/services/watchtower_service.py backend/tests/services/test_watchtower_service.py
git commit -m "refactor(watchtower): extract scan_low_stock from scan_all"
```

---

## 任务 4：scan_out_of_stock 函数

**文件：**
- 修改：`backend/app/services/watchtower_service.py`
- 修改：`backend/tests/services/test_watchtower_service.py`

- [ ] **步骤 1：写失败的测试**

```python
# append to backend/tests/services/test_watchtower_service.py
async def test_scan_out_of_stock_returns_zero_qty(db: AsyncSession):
    """Products with qty<=0 should appear in out_of_stock; qty>0 should NOT."""
    from app.models.product import Brand, Product, Inventory

    brand = Brand(name="BrandY")
    db.add(brand)
    await db.flush()
    p_oos = Product(name="缺货品", sku="OOS-2", brand_id=brand.id)
    p_ok = Product(name="正常品", sku="OK-2", brand_id=brand.id)
    db.add_all([p_oos, p_ok])
    await db.flush()
    db.add_all([
        Inventory(product_id=p_oos.id, quantity=0, safety_stock=5),
        Inventory(product_id=p_ok.id, quantity=100, safety_stock=10),
    ])
    await db.commit()

    result = await scan_out_of_stock(db)
    skus = {r["product_id"] for r in result}
    assert p_oos.id in skus
    assert p_ok.id not in skus
```

- [ ] **步骤 2：跑测试验证失败**

```bash
cd backend && pytest tests/services/test_watchtower_service.py::test_scan_out_of_stock_returns_zero_qty -v
```

预期：FAIL，`NotImplementedError`。

- [ ] **步骤 3：实现 scan_out_of_stock**

替换 `watchtower_service.py` 中 `scan_out_of_stock` 占位符：

```python
async def scan_out_of_stock(db: AsyncSession) -> list[dict]:
    """Inventory qty <= 0. Returns 20 rows: product_id, product_name, brand.
    """
    rows = (
        await db.execute(
            select(Product.id, Product.name, Product.sku, Brand.name)
            .join(Inventory, Product.id == Inventory.product_id)
            .outerjoin(Brand, Product.brand_id == Brand.id)
            .where(
                Inventory.quantity <= 0,
                Product.deleted_at.is_(None),
                Inventory.deleted_at.is_(None),
            )
            .limit(20)
        )
    ).all()
    return [
        {
            "product_id": r[0],
            "product_name": f"{r[2] or ''} {r[1]}",
            "brand": r[3] or "未知",
        }
        for r in rows
    ]
```

- [ ] **步骤 4：跑测试验证通过**

```bash
cd backend && pytest tests/services/test_watchtower_service.py -v
```

预期：PASS（6 tests）。

- [ ] **步骤 5：Commit**

```bash
git add backend/app/services/watchtower_service.py backend/tests/services/test_watchtower_service.py
git commit -m "refactor(watchtower): extract scan_out_of_stock from scan_all"
```

---

## 任务 5：generate_ai_summary 函数

**文件：**
- 修改：`backend/app/services/watchtower_service.py`
- 修改：`backend/tests/services/test_watchtower_service.py`

- [ ] **步骤 1：写失败的测试**

```python
# append to backend/tests/services/test_watchtower_service.py
async def test_generate_ai_summary_no_anomalies(monkeypatch):
    """Empty anomalies should still call AI once with '无明显异常' text."""
    from app.services import watchtower_service
    called = {"count": 0, "last_text": None}

    async def fake_chat(messages, schema):
        called["count"] += 1
        called["last_text"] = messages[1]["content"]
        return {"severity": "正常", "summary": "ok", "top_actions": [], "risk_areas": []}

    from app.services.ai import client as ai_client_module
    monkeypatch.setattr(ai_client_module.ai_client, "chat_structured", fake_chat)

    result = await watchtower_service.generate_ai_summary({}, 0)
    assert called["count"] == 1
    assert "无明显异常" in called["last_text"]
    assert result["severity"] == "正常"


async def test_generate_ai_summary_failure_falls_back(monkeypatch):
    """If ai_client throws, return fallback {severity: 正常, summary: 'AI分析暂不可用', ...}."""
    from app.services import watchtower_service
    from app.services.ai import client as ai_client_module

    async def fake_chat(messages, schema):
        raise RuntimeError("AI service down")

    monkeypatch.setattr(ai_client_module.ai_client, "chat_structured", fake_chat)

    anomalies = {"churn_risk": [{"name": "A", "industry": "电子", "level": "A", "signal": "x"}]}
    result = await watchtower_service.generate_ai_summary(anomalies, 1)
    assert result["severity"] == "正常"
    assert "暂不可用" in result["summary"]
    assert result["top_actions"] == []
    assert result["risk_areas"] == []
```

- [ ] **步骤 2：跑测试验证失败**

```bash
cd backend && pytest tests/services/test_watchtower_service.py::test_generate_ai_summary_no_anomalies -v
```

预期：FAIL，`NotImplementedError`。

- [ ] **步骤 3：实现 generate_ai_summary**

替换 `watchtower_service.py` 中 `generate_ai_summary` 占位符：

```python
async def generate_ai_summary(anomalies: dict, total_alerts: int) -> dict:
    """Build alert_text from anomalies, call ai_client.chat_structured.
    On AI failure returns {severity: '正常', summary: 'AI分析暂不可用', top_actions: [], risk_areas: []}.
    """
    alert_text_parts = []
    if "churn_risk" in anomalies and anomalies["churn_risk"]:
        alert_text_parts.append(
            f"**流失风险客户 ({len(anomalies['churn_risk'])}个):**\n"
            + "\n".join(
                f"- {a['name']} ({a.get('industry') or '未知行业'}, {a.get('level') or '未知等级'}) — {a.get('signal', '无信号')}"
                for a in anomalies["churn_risk"][:10]
            )
        )
    if "order_drop" in anomalies and anomalies["order_drop"]:
        alert_text_parts.append(
            f"\n**订单量下降客户 ({len(anomalies['order_drop'])}个):**\n"
            + "\n".join(
                f"- {a['name']}: {a['prev_orders']}单→{a['recent_orders']}单 (降{a['drop_pct']}%)"
                for a in anomalies["order_drop"][:10]
            )
        )
    if "low_stock" in anomalies and anomalies["low_stock"]:
        alert_text_parts.append(
            f"\n**低库存产品 ({len(anomalies['low_stock'])}个):**\n"
            + "\n".join(
                f"- [{a['brand']}] {a['product_name']}: {a['qty']}件 (安全线{a['safety']}件)"
                for a in anomalies["low_stock"][:10]
            )
        )
    if "out_of_stock" in anomalies and anomalies["out_of_stock"]:
        alert_text_parts.append(
            f"\n**缺货产品 ({len(anomalies['out_of_stock'])}个):**\n"
            + "\n".join(
                f"- [{a['brand']}] {a['product_name']}"
                for a in anomalies["out_of_stock"][:10]
            )
        )

    alert_text = "\n".join(alert_text_parts) if alert_text_parts else "无明显异常"

    if not alert_text_parts:
        from app.services.ai.client import ai_client
        from app.services.ai.prompts import watchtower_prompt
        schema = {
            "severity": "string: 正常/需关注/紧急",
            "summary": "string, 2-3 sentence overall assessment",
            "top_actions": ["string, prioritized actions to take"],
            "risk_areas": ["string, risk areas identified"],
        }
        try:
            return await ai_client.chat_structured(
                [
                    {
                        "role": "system",
                        "content": "你是一个ERP系统监控专家，擅长发现经营异常并提供优先级建议。",
                    },
                    {"role": "user", "content": watchtower_prompt(alert_text, total_alerts)},
                ],
                schema,
            )
        except Exception as e:
            logger.error(f"Watchtower AI analysis failed: {e}")
            return {
                "severity": "正常",
                "summary": "AI分析暂不可用",
                "top_actions": [],
                "risk_areas": [],
            }

    from app.services.ai.client import ai_client
    from app.services.ai.prompts import watchtower_prompt
    schema = {
        "severity": "string: 正常/需关注/紧急",
        "summary": "string, 2-3 sentence overall assessment",
        "top_actions": ["string, prioritized actions to take"],
        "risk_areas": ["string, risk areas identified"],
    }
    try:
        return await ai_client.chat_structured(
            [
                {
                    "role": "system",
                    "content": "你是一个ERP系统监控专家，擅长发现经营异常并提供优先级建议。",
                },
                {"role": "user", "content": watchtower_prompt(alert_text, total_alerts)},
            ],
            schema,
        )
    except Exception as e:
        logger.error(f"Watchtower AI analysis failed: {e}")
        return {
            "severity": "正常",
            "summary": "AI分析暂不可用",
            "top_actions": [],
            "risk_areas": [],
        }
```

- [ ] **步骤 4：跑测试验证通过**

```bash
cd backend && pytest tests/services/test_watchtower_service.py -v
```

预期：PASS（8 tests）。

- [ ] **步骤 5：Commit**

```bash
git add backend/app/services/watchtower_service.py backend/tests/services/test_watchtower_service.py
git commit -m "refactor(watchtower): extract generate_ai_summary with try/except fallback"
```

---

## 任务 6：watchtower_cached_scan（asyncio.gather + 缓存）

**文件：**
- 创建：`backend/app/api/v1/ai/_shared.py`
- 创建：`backend/tests/api/v1/ai/test_watchtower.py`
- 修改：`backend/app/api/v1/ai/watchtower.py`
- 修改：`backend/app/services/watchtower_service.py`（保留 `_persist_customer_alerts`，重写 `scan_all`）

- [ ] **步骤 1：先实现 _persist_customer_alerts（从原 scan_all 搬过来）**

替换 `watchtower_service.py` 中 `_persist_customer_alerts` 占位符：

```python
async def _persist_customer_alerts(
    db: AsyncSession,
    anomalies: dict,
    scan_time: datetime.datetime,
) -> int:
    """Write customer-related anomalies (churn_risk, order_drop) to AlertEvent table.
    Returns the number of events written.
    """
    written = 0
    rule_types = ["churn_risk", "order_drop"]
    await db.execute(
        update(AlertEvent)
        .where(AlertEvent.rule_type.in_(rule_types), AlertEvent.is_read.is_(False))
        .values(is_read=True)
    )

    events = []
    for churn in anomalies.get("churn_risk", []):
        events.append(
            AlertEvent(
                customer_id=churn["customer_id"],
                rule_type="churn_risk",
                rule_name="客户流失预警",
                severity="warning",
                message="客户 %s（%s·%s）—— %s"
                % (
                    churn["name"],
                    churn.get("industry", "未知行业"),
                    churn.get("level", "未知等级"),
                    churn.get("signal", "无信号"),
                ),
                is_read=False,
            )
        )

    for drop in anomalies.get("order_drop", []):
        name = drop.get("name") or f"#{drop['customer_id']}"
        events.append(
            AlertEvent(
                customer_id=drop["customer_id"],
                rule_type="order_drop",
                rule_name="订单量下降",
                severity="warning",
                message="客户 %s 近90天订单量从 %s 单骤降至 %s 单（降 %s%%）"
                % (name, drop["prev_orders"], drop["recent_orders"], drop["drop_pct"]),
                is_read=False,
            )
        )

    if events:
        db.add_all(events)
        written = len(events)
    return written
```

- [ ] **步骤 2：写失败的测试（cache hit）**

```python
# backend/tests/api/v1/ai/test_watchtower.py
import pytest
from unittest.mock import patch, AsyncMock

pytestmark = pytest.mark.asyncio


async def test_scan_all_cached_hit(async_client, auth_headers, test_user):
    """Second call within TTL should not re-run scans."""
    # First call: cache miss → runs scans
    r1 = await async_client.get("/ai/watchtower/scan?days_back=90", headers=auth_headers)
    assert r1.status_code == 200
    body1 = r1.json()
    assert body1["code"] == 0
    assert "anomalies" in body1["data"]

    # Patch one scan to count calls; second request should NOT invoke it
    from app.services import watchtower_service
    with patch.object(
        watchtower_service, "scan_churn_risk", new_callable=AsyncMock
    ) as mock_churn:
        mock_churn.return_value = []
        r2 = await async_client.get("/ai/watchtower/scan?days_back=90", headers=auth_headers)
        assert r2.status_code == 200
        # Cached response → scan_churn_risk was NOT called
        mock_churn.assert_not_called()


async def test_scan_endpoint_shape(async_client, auth_headers, test_user):
    """Response keys must match spec §2.5 exactly."""
    r = await async_client.get("/ai/watchtower/scan?days_back=90", headers=auth_headers)
    assert r.status_code == 200
    data = r.json()["data"]
    expected_keys = {
        "scanned_at", "total_alerts", "severity", "summary",
        "top_actions", "risk_areas", "alerts_persisted", "anomalies",
    }
    assert set(data.keys()) == expected_keys, f"Got {set(data.keys())}"
    assert set(data["anomalies"].keys()) == {
        "churn_risk", "order_drop", "low_stock", "out_of_stock",
    }


async def test_scan_endpoint_unauth(async_client):
    """No token → 401."""
    r = await async_client.get("/ai/watchtower/scan?days_back=90")
    assert r.status_code in (401, 403)
```

- [ ] **步骤 3：跑测试验证失败**

```bash
cd backend && pytest tests/api/v1/ai/test_watchtower.py::test_scan_endpoint_shape -v
```

预期：FAIL（test_scan_endpoint_shape 用现有 scan_all 调通但 _shared.py 还没建，所以 import 失败）。若新文件结构已就位但实现未替换，FAIL 是 ImportError。

- [ ] **步骤 4：实现 _shared.py + 重写 watchtower.py + 重写 scan_all**

创建 `backend/app/api/v1/ai/_shared.py`：

```python
"""Watchtower shared cache wrappers."""

import asyncio
import datetime
import hashlib
import json
import logging

from sqlalchemy.ext.asyncio import AsyncSession

from app.services.cache_service import (
    cache_get_versioned,
    cache_set_versioned,
)
from app.services import watchtower_service

logger = logging.getLogger(__name__)

DASHBOARD_SCAN_CACHE_TTL = 300  # 5 min
DASHBOARD_REPORT_CACHE_TTL = 600  # 10 min


def _cache_key(**parts: object) -> str:
    canonical = json.dumps(parts, sort_keys=True, default=str)
    digest = hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:16]
    return f"watchtower:{digest}"


async def watchtower_cached_scan(db: AsyncSession, days_back: int) -> dict:
    key = _cache_key(endpoint="scan", days_back=days_back)
    try:
        cached = await cache_get_versioned("watchtower:scan", key)
        if cached is not None:
            return json.loads(cached)
    except (json.JSONDecodeError, TypeError):
        pass

    now = datetime.datetime.now(datetime.timezone.utc)
    lookback = now - datetime.timedelta(days=days_back)
    prev_lookback = lookback - datetime.timedelta(days=days_back)

    results = await asyncio.gather(
        watchtower_service.scan_churn_risk(db, lookback, prev_lookback),
        watchtower_service.scan_order_drop(db, lookback, prev_lookback),
        watchtower_service.scan_low_stock(db),
        watchtower_service.scan_out_of_stock(db),
        return_exceptions=True,
    )
    anomalies = {}
    for key_name, result in zip(
        ["churn_risk", "order_drop", "low_stock", "out_of_stock"], results
    ):
        if isinstance(result, Exception):
            logger.warning(f"watchtower.scan.{key_name} failed: {result}")
            anomalies[key_name] = []
        else:
            anomalies[key_name] = result

    total_alerts = sum(len(v) for v in anomalies.values())
    ai = await watchtower_service.generate_ai_summary(anomalies, total_alerts)
    persisted = await watchtower_service._persist_customer_alerts(db, anomalies, now)

    result = {
        "scanned_at": now.isoformat(),
        "total_alerts": total_alerts,
        "severity": ai.get("severity", "正常"),
        "summary": ai.get("summary", ""),
        "top_actions": ai.get("top_actions", []),
        "risk_areas": ai.get("risk_areas", []),
        "alerts_persisted": persisted,
        "anomalies": anomalies,
    }

    await cache_set_versioned(
        "watchtower:scan", key,
        json.dumps(result, default=str),
        DASHBOARD_SCAN_CACHE_TTL,
    )
    return result


async def watchtower_cached_report(db: AsyncSession) -> dict:
    """Wrap /ai/daily-report. TTL 600s; bumped by scheduler at midnight (see task 9)."""
    key = _cache_key(endpoint="report")
    try:
        cached = await cache_get_versioned("watchtower:report", key)
        if cached is not None:
            return json.loads(cached)
    except (json.JSONDecodeError, TypeError):
        pass

    # Reuse the existing daily-report logic; extracted in next task
    from app.api.v1.ai.watchtower import _compute_daily_report
    result = await _compute_daily_report(db)

    await cache_set_versioned(
        "watchtower:report", key,
        json.dumps(result, default=str),
        DASHBOARD_REPORT_CACHE_TTL,
    )
    return result
```

替换 `backend/app/api/v1/ai/watchtower.py`（薄路由 + 提取 _compute_daily_report）：

```python
"""Watchtower routes — system-wide anomaly scan and daily report."""

import logging
from datetime import datetime as dt, timezone
from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.api.v1.ai._shared import watchtower_cached_scan, watchtower_cached_report
from app.database import get_db
from app.schemas.common import fail, ok

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ai", tags=["ai"])


@router.get("/watchtower/scan")
async def watchtower_scan(
    days_back: int = Query(90),
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(get_current_user),
):
    try:
        result = await watchtower_cached_scan(db, days_back)
        return ok(result)
    except Exception as e:
        return fail(str(e), 500)


async def _compute_daily_report(db: AsyncSession) -> dict:
    """Generate daily cross-domain report. Moved from inline route handler."""
    now = dt.now(timezone.utc)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)

    from app.models.sales import SalesOrder
    from app.models.customer import Customer
    from app.models.product import Inventory
    from app.models.transaction import Payment

    today_orders = (
        await db.execute(
            select(
                func.count(SalesOrder.id),
                func.coalesce(func.sum(SalesOrder.total_amount), 0),
            ).where(
                SalesOrder.deleted_at.is_(None),
                SalesOrder.created_at >= today_start,
            )
        )
    ).first()
    orders_count = today_orders[0] if today_orders else 0
    orders_amount = float(today_orders[1]) if today_orders else 0.0

    new_cust = (
        await db.execute(
            select(func.count(Customer.id)).where(
                Customer.deleted_at.is_(None),
                Customer.created_at >= today_start,
            )
        )
    ).scalar() or 0

    low_stock = (
        await db.execute(
            select(func.count(Inventory.id)).where(
                Inventory.deleted_at.is_(None),
                Inventory.quantity <= Inventory.safety_stock,
                Inventory.quantity > 0,
            )
        )
    ).scalar() or 0
    out_of_stock = (
        await db.execute(
            select(func.count(Inventory.id)).where(
                Inventory.deleted_at.is_(None),
                Inventory.quantity <= 0,
            )
        )
    ).scalar() or 0

    today_payments = (
        await db.execute(
            select(
                func.count(Payment.id), func.coalesce(func.sum(Payment.amount), 0)
            ).where(
                Payment.deleted_at.is_(None),
                Payment.created_at >= today_start,
            )
        )
    ).first()
    payments_count = today_payments[0] if today_payments else 0
    payments_amount = float(today_payments[1]) if today_payments else 0.0

    report = {
        "report_date": today_start.strftime("%Y-%m-%d"),
        "generated_at": now.isoformat(),
        "metrics": {
            "orders_today": orders_count,
            "revenue_today": round(orders_amount, 2),
            "new_customers": new_cust,
            "payments_today": payments_count,
            "payments_amount_today": round(payments_amount, 2),
            "low_stock_items": low_stock,
            "out_of_stock_items": out_of_stock,
        },
    }

    try:
        from app.services.ai.client import ai_client
        prompt = (
            f"Today's ERP snapshot ({report['report_date']}):\n"
            f"- New orders: {orders_count}, revenue: ¥{orders_amount:,.2f}\n"
            f"- New customers: {new_cust}\n"
            f"- Payments received: {payments_count}, amount: ¥{payments_amount:,.2f}\n"
            f"- Low stock products: {low_stock}\n"
            f"- Out of stock products: {out_of_stock}\n\n"
            f"Write a 2-3 sentence executive daily briefing in Chinese. "
            f"Highlight what's notable, any warning signs, and one recommended action."
        )
        schema = {
            "summary": "string, 2-3 sentence executive briefing in Chinese",
            "mood": "string: 良好/一般/需关注",
            "top_action": "string, single most important action today",
        }
        ai = await ai_client.chat_structured(
            [
                {
                    "role": "system",
                    "content": "你是一个ERP日报助手，擅长用简洁的语言总结每日经营状况。",
                },
                {"role": "user", "content": prompt},
            ],
            schema,
        )
        report["ai_summary"] = ai.get("summary", "")
        report["mood"] = ai.get("mood", "一般")
        report["top_action"] = ai.get("top_action", "")
    except Exception as e:
        logger.warning(f"Daily report AI summary failed: {e}")
        report["ai_summary"] = "AI摘要暂不可用"
        report["mood"] = "一般"
        report["top_action"] = ""
    return report


@router.get("/daily-report")
async def daily_report(
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(get_current_user),
):
    try:
        result = await watchtower_cached_report(db)
        return ok(result)
    except Exception as e:
        return fail(str(e), 500)
```

替换 `watchtower_service.py` 中 `scan_all` 占位符（保留向后兼容，调用新拆出的函数）：

```python
async def scan_all(db: AsyncSession, days_back: int = 90) -> dict:
    """Backward-compatible wrapper. Prefer watchtower_cached_scan in new code."""
    from app.api.v1.ai._shared import watchtower_cached_scan
    return await watchtower_cached_scan(db, days_back)
```

- [ ] **步骤 5：跑测试验证通过**

```bash
cd backend && pytest tests/api/v1/ai/test_watchtower.py -v
```

预期：PASS（3 tests：`test_scan_all_cached_hit`, `test_scan_endpoint_shape`, `test_scan_endpoint_unauth`）。

- [ ] **步骤 6：Commit**

```bash
git add backend/app/api/v1/ai/_shared.py backend/app/api/v1/ai/watchtower.py backend/app/services/watchtower_service.py backend/tests/api/v1/ai/test_watchtower.py
git commit -m "refactor(watchtower): asyncio.gather + versioned cache for /watchtower/scan"
```

---

## 任务 7：cache_bump_version 写点（4 个文件）

**文件：**
- 修改：`backend/app/api/v1/customers/*.py`
- 修改：`backend/app/api/v1/sales/orders.py`
- 修改：`backend/app/api/v1/inventory/*.py`
- 修改：`backend/app/api/v1/payments/*.py`

- [ ] **步骤 1：定位现有 bump 写点**

```bash
cd backend && grep -rn "cache_bump_version" app/api/v1/customers/ app/api/v1/sales/orders.py app/api/v1/inventory/ app/api/v1/payments/ | head -20
```

预期输出：列出每个文件中已有的 `cache_bump_version(...)` 调用。每个文件至少 1 处（确认这 4 个目录都有现成的 cache 失效模式）。

- [ ] **步骤 2：在 customers 写操作后加 watchtower bump**

打开 `app/api/v1/customers/crud.py`（或主 create/update/delete handler），在已有 `await cache_bump_version("customers:...")` 调用后**追加一行**：

```python
        await cache_bump_version("watchtower:scan")
```

参考现有 pattern 复制即可。**不要改已有调用**，只 append。

- [ ] **步骤 3：在 sales/orders.py 加 watchtower bump**

```python
# 在 create / update 路由的 commit 之后, 已有 cache_bump_version 之后:
        await cache_bump_version("watchtower:scan")
```

- [ ] **步骤 4：在 inventory 写点加 watchtower bump**

```python
# 在 adjust / update 路由 commit 之后:
        await cache_bump_version("watchtower:scan")
```

- [ ] **步骤 5：在 payments 写点加 watchtower bump**

```python
# 在 create_payment 路由 commit 之后:
        await cache_bump_version("watchtower:scan")
```

- [ ] **步骤 6：跑测试 + make lint 验证**

```bash
cd backend && ruff check app/api/v1/customers/ app/api/v1/sales/orders.py app/api/v1/inventory/ app/api/v1/payments/ && mypy app/ --explicit-package-bases --ignore-missing-imports --exclude "app/api/v1/(permissions|finance|sales).py" | tail -5
```

预期：ruff all checks passed；mypy Success 或同前基线（不要新增 errors）。

- [ ] **步骤 7：Commit**

```bash
git add backend/app/api/v1/customers/ backend/app/api/v1/sales/orders.py backend/app/api/v1/inventory/ backend/app/api/v1/payments/
git commit -m "refactor(watchtower): bump watchtower:scan cache on customer/order/inventory/payment writes"
```

---

## 任务 8：daily-report 缓存测试 + 验证

**文件：**
- 修改：`backend/tests/api/v1/ai/test_watchtower.py`

- [ ] **步骤 1：写失败的测试**

```python
# append to backend/tests/api/v1/ai/test_watchtower.py
async def test_daily_report_cached(async_client, auth_headers, test_user):
    """Second call within TTL should not re-run queries."""
    from app.api.v1.ai import watchtower as watchtower_route

    with patch.object(
        watchtower_route, "_compute_daily_report", new_callable=AsyncMock
    ) as mock_compute:
        mock_compute.return_value = {
            "report_date": "2026-07-31",
            "generated_at": "2026-07-31T10:00:00+00:00",
            "metrics": {},
        }
        r1 = await async_client.get("/ai/daily-report", headers=auth_headers)
        assert r1.status_code == 200
        assert mock_compute.call_count == 1
        r2 = await async_client.get("/ai/daily-report", headers=auth_headers)
        assert r2.status_code == 200
        # Cached: not called again
        assert mock_compute.call_count == 1
```

- [ ] **步骤 2：跑测试验证通过**

```bash
cd backend && pytest tests/api/v1/ai/test_watchtower.py::test_daily_report_cached -v
```

预期：PASS（已在任务 6 中实现了 `watchtower_cached_report` + `_compute_daily_report` 拆分）。

- [ ] **步骤 3：Commit**

```bash
git add backend/tests/api/v1/ai/test_watchtower.py
git commit -m "test(watchtower): verify daily-report cache hit skips recompute"
```

---

## 任务 9：scheduler job bump_watchtower_report_at_midnight

**文件：**
- 修改：`backend/app/jobs/scheduler.py`

- [ ] **步骤 1：读现有 scheduler.py 的注册 pattern**

```bash
cd backend && grep -n "scheduler.add_job\|@asynccontextmanager\|AsyncIOScheduler" app/jobs/scheduler.py | head -10
```

预期：找到注册 entry 的位置 + 现有 cron pattern（参考 `app/jobs/scheduler.py` 中其他 daily 0:05 触发的 job）。

- [ ] **步骤 2：添加 bump function + 注册 entry**

在 `app/jobs/scheduler.py` 已有 daily-job 注册附近加：

```python
async def bump_watchtower_report_at_midnight() -> None:
    """跨午夜失效 daily report cache. cron: 5 0 * * * (UTC)"""
    from app.services.cache_service import cache_bump_version
    await cache_bump_version("watchtower:report")
    logger.info("watchtower:report cache bumped at midnight")
```

在 scheduler 启动序列（`_register_jobs` 或类似函数）中加一行：

```python
    scheduler.add_job(
        bump_watchtower_report_at_midnight,
        CronTrigger(hour=0, minute=5),
        id="bump_watchtower_report_midnight",
        replace_existing=True,
    )
```

- [ ] **步骤 3：导入 + 验证**

```bash
cd backend && python -c "from app.jobs.scheduler import bump_watchtower_report_at_midnight; print('import ok')" && ruff check app/jobs/scheduler.py
```

预期：`import ok`；ruff clean。

- [ ] **步骤 4：Commit**

```bash
git add backend/app/jobs/scheduler.py
git commit -m "refactor(watchtower): scheduler job to bump daily-report cache at 00:05 UTC"
```

---

## 任务 10：types/watchtower.ts

**文件：**
- 创建：`frontend/src/types/watchtower.ts`

- [ ] **步骤 1：写类型**

```typescript
// frontend/src/types/watchtower.ts
export type AnomalyDomain = "churn_risk" | "order_drop" | "low_stock" | "out_of_stock";

export interface AnomalyRow {
  domain: AnomalyDomain;
  domainLabel: string;
  customer_id?: number;
  product_id?: number;
  name?: string;
  signal?: string;
  prev_orders?: number;
  recent_orders?: number;
  drop_pct?: number;
  qty?: number;
  safety?: number;
  brand?: string;
}

export interface WatchtowerScanResponse {
  scanned_at: string;
  total_alerts: number;
  severity: "紧急" | "需关注" | "正常";
  summary: string;
  top_actions: string[];
  risk_areas: string[];
  alerts_persisted: number;
  anomalies: Record<AnomalyDomain, AnomalyRow[]>;
}
```

- [ ] **步骤 2：tsc 验证**

```bash
cd frontend && npx tsc --noEmit
```

预期：EXIT=0，no errors.

- [ ] **步骤 3：Commit**

```bash
git add frontend/src/types/watchtower.ts
git commit -m "refactor(frontend): add watchtower types for scan response"
```

---

## 任务 11：WatchtowerDashboard useApiQuery 迁移（先 1 文件，再拆）

**文件：**
- 修改：`frontend/src/pages/dashboard/WatchtowerDashboard.tsx`
- 创建：`frontend/src/pages/dashboard/WatchtowerDashboard.module.css`
- 创建：`frontend/src/test/dashboard/WatchtowerDashboard.test.tsx`

- [ ] **步骤 1：写失败的测试**

```typescript
// frontend/src/test/dashboard/WatchtowerDashboard.test.tsx
import { describe, it, expect, vi } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter } from "react-router-dom";
import WatchtowerDashboard from "@/pages/dashboard/WatchtowerDashboard";
import * as api from "@/api";

function makeWrapper() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return ({ children }: { children: React.ReactNode }) => (
    <QueryClientProvider client={qc}>
      <MemoryRouter>{children}</MemoryRouter>
    </QueryClientProvider>
  );
}

const mockScanResponse = {
  code: 0,
  data: {
    scanned_at: "2026-07-31T10:00:00+00:00",
    total_alerts: 3,
    severity: "需关注",
    summary: "AI summary text",
    top_actions: ["Action 1"],
    risk_areas: ["sales"],
    alerts_persisted: 1,
    anomalies: {
      churn_risk: [
        { domain: "churn_risk", domainLabel: "客户流失风险", customer_id: 1, name: "客户X", signal: "90天无订单" },
      ],
      order_drop: [],
      low_stock: [],
      out_of_stock: [],
    },
  },
};

describe("WatchtowerDashboard", () => {
  it("renders loading state initially", () => {
    vi.spyOn(api, "getWatchtowerScan").mockReturnValue(new Promise(() => {}));
    const Wrapper = makeWrapper();
    render(<Wrapper><WatchtowerDashboard /></Wrapper>);
    expect(screen.getByRole("status")).toBeInTheDocument();  // Spin
  });

  it("renders data when query resolves", async () => {
    vi.spyOn(api, "getWatchtowerScan").mockResolvedValue(mockScanResponse as any);
    const Wrapper = makeWrapper();
    render(<Wrapper><WatchtowerDashboard /></Wrapper>);
    await waitFor(() => {
      expect(screen.getByText("全局监控中心")).toBeInTheDocument();
    });
    expect(screen.getByText("异常总数")).toBeInTheDocument();
    expect(screen.getByText("AI summary text")).toBeInTheDocument();
  });

  it("renders error state with retry", async () => {
    vi.spyOn(api, "getWatchtowerScan").mockRejectedValue(new Error("boom"));
    const Wrapper = makeWrapper();
    render(<Wrapper><WatchtowerDashboard /></Wrapper>);
    await waitFor(() => {
      expect(screen.getByText(/监控扫描失败|重试/)).toBeInTheDocument();
    });
  });

  it("renders empty state when total_alerts=0", async () => {
    vi.spyOn(api, "getWatchtowerScan").mockResolvedValue({
      code: 0,
      data: { ...mockScanResponse.data, total_alerts: 0, severity: "正常", top_actions: [], risk_areas: [], anomalies: { churn_risk: [], order_drop: [], low_stock: [], out_of_stock: [] } },
    } as any);
    const Wrapper = makeWrapper();
    render(<Wrapper><WatchtowerDashboard /></Wrapper>);
    await waitFor(() => {
      expect(screen.getByText(/未检测到异常/)).toBeInTheDocument();
    });
  });

  it("refresh button triggers refetch", async () => {
    const mock = vi.spyOn(api, "getWatchtowerScan").mockResolvedValue(mockScanResponse as any);
    const Wrapper = makeWrapper();
    render(<Wrapper><WatchtowerDashboard /></Wrapper>);
    await waitFor(() => screen.getByText("全局监控中心"));
    mock.mockClear();
    await userEvent.click(screen.getByRole("button", { name: /刷新/ }));
    await waitFor(() => expect(mock).toHaveBeenCalled());
  });
});
```

- [ ] **步骤 2：跑测试验证失败**

```bash
cd frontend && npx vitest run src/test/dashboard/WatchtowerDashboard.test.tsx
```

预期：FAIL（File not found `src/test/dashboard/` 或 import 错误）。

- [ ] **步骤 3：写新 WatchtowerDashboard.tsx（~80 行 + useApiQuery，不拆组件）**

替换 `frontend/src/pages/dashboard/WatchtowerDashboard.tsx`：

```tsx
import { Col, Row, Spin, Alert, Button, Typography } from "antd";
import { WarningOutlined, ReloadOutlined } from "@ant-design/icons";
import { useApiQuery } from "@/lib/queries";
import { getWatchtowerScan } from "@/api";
import { getApiErrorMessage } from "@/api/client";
import { EmptyState, FullPageLoader, StatusTag } from "@/ui";
import styles from "./WatchtowerDashboard.module.css";
import type { WatchtowerScanResponse } from "@/types/watchtower";

const { Title, Text } = Typography;
const SCAN_LOOKBACK_DAYS = 90;

const severityColor = (s: string) =>
  s === "紧急" ? "danger" : s === "需关注" ? "warning" : "success";

const domainLabels: Record<string, string> = {
  churn_risk: "客户流失风险",
  order_drop: "订单量下降",
  low_stock: "低库存",
  out_of_stock: "缺货",
};

const safeFormatDate = (d: string | undefined | null): string => {
  if (!d) return "未知时间";
  try {
    const date = new Date(d);
    if (isNaN(date.getTime())) return "无效时间";
    return date.toLocaleString();
  } catch {
    return "无效时间";
  }
};

export default function WatchtowerDashboard() {
  const query = useApiQuery<WatchtowerScanResponse>(
    ["watchtower", "scan", SCAN_LOOKBACK_DAYS],
    `/ai/watchtower/scan?days_back=${SCAN_LOOKBACK_DAYS}`,
    null,
    { staleTime: 60 * 1000, refetchInterval: false },
  );

  if (query.isLoading) return <FullPageLoader />;
  if (query.error) {
    return (
      <Alert
        type="error"
        message={getApiErrorMessage(query.error)}
        className={styles.errorAlert}
        action={<Button onClick={() => query.refetch()}>重试</Button>}
      />
    );
  }
  if (!query.data) return null;

  const data = query.data;
  const anomalyEntries = Object.entries(data.anomalies || {}).filter(([, v]) => v.length > 0);

  return (
    <div className={styles.page}>
      <div className={styles.header}>
        <Title level={4} className={styles.title}>
          <WarningOutlined /> 全局监控中心
        </Title>
        <Text type="secondary">扫描时间: {safeFormatDate(data.scanned_at)}</Text>
        <Button
          icon={<ReloadOutlined />}
          onClick={() => query.refetch()}
          loading={query.isFetching}
        >
          刷新
        </Button>
      </div>

      <Row gutter={[16, 16]} className={styles.kpiRow}>
        <Col xs={24} sm={6}>
          <div className={styles.kpiCard}>
            <Text>异常总数</Text>
            <div className={styles.kpiValue}>{data.total_alerts}</div>
          </div>
        </Col>
        <Col xs={24} sm={6}>
          <div className={styles.kpiCard}>
            <Text>严重程度</Text>
            <StatusTag tone={severityColor(data.severity) as any}>
              {data.severity}
            </StatusTag>
          </div>
        </Col>
        <Col xs={24} sm={6}>
          <div className={styles.kpiCard}>
            <Text>异常领域</Text>
            {data.risk_areas?.length
              ? data.risk_areas.map((a, i) => (
                  <StatusTag tone="danger" key={i}>{a}</StatusTag>
                ))
              : <StatusTag tone="success">无</StatusTag>}
          </div>
        </Col>
        <Col xs={24} sm={6}>
          <div className={styles.kpiCard}>
            <Text>领域分布</Text>
            {anomalyEntries.length
              ? anomalyEntries.map(([domain, items]) => (
                  <StatusTag
                    key={domain}
                    tone={items.length > 5 ? "danger" : "warning"}
                  >
                    {domainLabels[domain] || domain}: {items.length}
                  </StatusTag>
                ))
              : <Text type="secondary">暂无异常</Text>}
          </div>
        </Col>
      </Row>

      <div className={styles.section}>
        <Text strong>AI 分析摘要</Text>
        <div className={styles.aiSummary}>{data.summary}</div>
      </div>

      {data.top_actions?.length > 0 && (
        <div className={styles.section}>
          <Text strong>优先行动</Text>
          <ol className={styles.topActions}>
            {data.top_actions.map((item, i) => (
              <li key={i}>{item}</li>
            ))}
          </ol>
        </div>
      )}

      <div className={styles.section}>
        <Text strong>异常详情</Text>
        {anomalyEntries.length > 0 ? (
          <pre className={styles.anomalyPre}>
            {JSON.stringify(
              anomalyEntries.flatMap(([domain, items]) =>
                items.map((it) => ({ ...it, domain, domainLabel: domainLabels[domain] || domain }))
              ),
              null,
              2,
            )}
          </pre>
        ) : (
          <EmptyState description="未检测到异常，系统运行正常" />
        )}
      </div>
    </div>
  );
}
```

创建 `frontend/src/pages/dashboard/WatchtowerDashboard.module.css`：

```css
/* frontend/src/pages/dashboard/WatchtowerDashboard.module.css */
.page {
  padding: 24px;
}

.header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 16px;
  margin-bottom: 24px;
}

.title {
  margin: 0;
}

.kpiRow {
  margin-bottom: 24px;
}

.kpiCard {
  background: var(--ant-color-bg-container);
  border: 1px solid var(--ant-color-border-secondary);
  border-radius: 8px;
  padding: 16px;
  min-height: 96px;
}

.kpiValue {
  font-size: 32px;
  font-weight: 600;
  margin-top: 8px;
  font-variant-numeric: tabular-nums;
}

.section {
  background: var(--ant-color-bg-container);
  border: 1px solid var(--ant-color-border-secondary);
  border-radius: 8px;
  padding: 16px;
  margin-bottom: 16px;
}

.aiSummary {
  margin-top: 8px;
  white-space: pre-wrap;
}

.topActions {
  margin: 8px 0 0;
  padding-left: 20px;
}

.anomalyPre {
  background: var(--ant-color-bg-layout);
  padding: 12px;
  border-radius: 4px;
  overflow-x: auto;
  font-size: 12px;
  margin: 8px 0 0;
}

.errorAlert {
  margin: 24px;
}
```

- [ ] **步骤 4：跑测试验证通过**

```bash
cd frontend && npx vitest run src/test/dashboard/WatchtowerDashboard.test.tsx
```

预期：PASS（5 tests）。

- [ ] **步骤 5：跑 tsc + lint**

```bash
cd frontend && npx tsc --noEmit && npx eslint src/pages/dashboard/WatchtowerDashboard.tsx
```

预期：EXIT=0；ESLint clean。

- [ ] **步骤 6：Commit**

```bash
git add frontend/src/pages/dashboard/WatchtowerDashboard.tsx frontend/src/pages/dashboard/WatchtowerDashboard.module.css frontend/src/test/dashboard/WatchtowerDashboard.test.tsx
git commit -m "refactor(frontend): WatchtowerDashboard useApiQuery + StatusTag + design tokens"
```

---

## 任务 12-16：拆 5 个子组件

> 5 个子组件是同一模式的重复，**每个组件 3 步：写测试 → 写实现 → 跑测试+commit**。
> 任务 12-16 按这个结构展开，但下面只展开 ScanHeader（任务 12）和 KpiCards（任务 13）作为模板；其余 3 个组件（AiSummary / TopActions / AnomalyTable）让执行者按相同结构自己写。

### 任务 12：ScanHeader 组件

**文件：**
- 创建：`frontend/src/pages/dashboard/components/ScanHeader.tsx`
- 创建：`frontend/src/pages/dashboard/components/ScanHeader.module.css`
- 创建：`frontend/src/test/dashboard/ScanHeader.test.tsx`
- 修改：`frontend/src/pages/dashboard/WatchtowerDashboard.tsx`

- [ ] **步骤 1：写测试**

```typescript
// frontend/src/test/dashboard/ScanHeader.test.tsx
import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { ScanHeader } from "@/pages/dashboard/components/ScanHeader";

describe("ScanHeader", () => {
  it("renders title and timestamp", () => {
    render(<ScanHeader scanned_at="2026-07-31T10:00:00Z" loading={false} onRefresh={() => {}} />);
    expect(screen.getByText("全局监控中心")).toBeInTheDocument();
    expect(screen.getByText(/2026/)).toBeInTheDocument();
  });

  it("calls onRefresh when refresh button clicked", async () => {
    const onRefresh = vi.fn();
    render(<ScanHeader scanned_at="2026-07-31T10:00:00Z" loading={false} onRefresh={onRefresh} />);
    await userEvent.click(screen.getByRole("button", { name: /刷新/ }));
    expect(onRefresh).toHaveBeenCalledOnce();
  });

  it("shows loading state on refresh button", () => {
    render(<ScanHeader scanned_at="2026-07-31T10:00:00Z" loading={true} onRefresh={() => {}} />);
    expect(screen.getByRole("button", { name: /刷新/ })).toHaveAttribute("aria-busy", "true");
  });
});
```

- [ ] **步骤 2：写实现**

```tsx
// frontend/src/pages/dashboard/components/ScanHeader.tsx
import { Button, Space, Typography } from "antd";
import { WarningOutlined, ReloadOutlined } from "@ant-design/icons";
import styles from "./ScanHeader.module.css";

const { Title, Text } = Typography;

const safeFormatDate = (d: string | undefined | null): string => {
  if (!d) return "未知时间";
  try {
    const date = new Date(d);
    if (isNaN(date.getTime())) return "无效时间";
    return date.toLocaleString();
  } catch {
    return "无效时间";
  }
};

export interface ScanHeaderProps {
  scanned_at: string;
  loading: boolean;
  onRefresh: () => void;
}

export function ScanHeader({ scanned_at, loading, onRefresh }: ScanHeaderProps) {
  return (
    <div className={styles.header}>
      <Title level={4} className={styles.title}>
        <WarningOutlined /> 全局监控中心
      </Title>
      <Space>
        <Text type="secondary">扫描时间: {safeFormatDate(scanned_at)}</Text>
        <Button
          icon={<ReloadOutlined />}
          onClick={onRefresh}
          loading={loading}
          aria-label="刷新"
        >
          刷新
        </Button>
      </Space>
    </div>
  );
}
```

```css
/* frontend/src/pages/dashboard/components/ScanHeader.module.css */
.header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 16px;
  margin-bottom: 24px;
}

.title {
  margin: 0;
}
```

- [ ] **步骤 3：跑测试 + 替换 WatchtowerDashboard 中的对应段 + commit**

```bash
cd frontend && npx vitest run src/test/dashboard/ScanHeader.test.tsx
```

预期：PASS（3 tests）。然后在 `WatchtowerDashboard.tsx` 中删掉 `ScanHeader` 对应 JSX 块，换成 `<ScanHeader scanned_at={data.scanned_at} loading={query.isFetching} onRefresh={() => query.refetch()} />`，跑 `npx tsc --noEmit` + `npx eslint`，再 commit：

```bash
git add frontend/src/pages/dashboard/components/ScanHeader.tsx frontend/src/pages/dashboard/components/ScanHeader.module.css frontend/src/test/dashboard/ScanHeader.test.tsx frontend/src/pages/dashboard/WatchtowerDashboard.tsx
git commit -m "refactor(frontend): extract ScanHeader from WatchtowerDashboard"
```

### 任务 13：KpiCards 组件

**文件：**
- 创建：`frontend/src/pages/dashboard/components/KpiCards.tsx`
- 创建：`frontend/src/pages/dashboard/components/KpiCards.module.css`
- 创建：`frontend/src/test/dashboard/KpiCards.test.tsx`
- 修改：`frontend/src/pages/dashboard/WatchtowerDashboard.tsx`

- [ ] **步骤 1：写测试**

```typescript
// frontend/src/test/dashboard/KpiCards.test.tsx
import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { KpiCards } from "@/pages/dashboard/components/KpiCards";

describe("KpiCards", () => {
  it("renders total_alerts and severity with correct tone", () => {
    render(
      <KpiCards
        totalAlerts={5}
        severity="紧急"
        riskAreas={["sales"]}
        domainDistribution={[["low_stock", 3]]}
      />,
    );
    expect(screen.getByText("5")).toBeInTheDocument();
    expect(screen.getByText("紧急")).toBeInTheDocument();
  });

  it("renders risk_areas as danger tags", () => {
    render(
      <KpiCards
        totalAlerts={0}
        severity="正常"
        riskAreas={["a", "b"]}
        domainDistribution={[]}
      />,
    );
    expect(screen.getByText("a")).toBeInTheDocument();
    expect(screen.getByText("b")).toBeInTheDocument();
  });

  it("renders no-risk fallback when riskAreas is empty", () => {
    render(
      <KpiCards totalAlerts={0} severity="正常" riskAreas={[]} domainDistribution={[]} />,
    );
    expect(screen.getByText("无")).toBeInTheDocument();
  });
});
```

- [ ] **步骤 2：写实现**

```tsx
// frontend/src/pages/dashboard/components/KpiCards.tsx
import { Col, Row, Typography } from "antd";
import { StatusTag } from "@/ui";
import styles from "./KpiCards.module.css";

const { Text } = Typography;

const severityTone = (s: string) =>
  s === "紧急" ? "danger" : s === "需关注" ? "warning" : "success";

const domainLabels: Record<string, string> = {
  churn_risk: "客户流失风险",
  order_drop: "订单量下降",
  low_stock: "低库存",
  out_of_stock: "缺货",
};

export interface KpiCardsProps {
  totalAlerts: number;
  severity: string;
  riskAreas: string[];
  domainDistribution: Array<[string, number]>;
}

export function KpiCards({ totalAlerts, severity, riskAreas, domainDistribution }: KpiCardsProps) {
  return (
    <Row gutter={[16, 16]} className={styles.row}>
      <Col xs={24} sm={6}>
        <div className={styles.card}>
          <Text>异常总数</Text>
          <div className={styles.value}>{totalAlerts}</div>
        </div>
      </Col>
      <Col xs={24} sm={6}>
        <div className={styles.card}>
          <Text>严重程度</Text>
          <div className={styles.severity}>
            <StatusTag tone={severityTone(severity) as any}>{severity}</StatusTag>
          </div>
        </div>
      </Col>
      <Col xs={24} sm={6}>
        <div className={styles.card}>
          <Text>异常领域</Text>
          <div className={styles.areaList}>
            {riskAreas.length
              ? riskAreas.map((a, i) => (
                  <StatusTag tone="danger" key={i}>{a}</StatusTag>
                ))
              : <StatusTag tone="success">无</StatusTag>}
          </div>
        </div>
      </Col>
      <Col xs={24} sm={6}>
        <div className={styles.card}>
          <Text>领域分布</Text>
          <div className={styles.areaList}>
            {domainDistribution.length
              ? domainDistribution.map(([domain, count]) => (
                  <StatusTag key={domain} tone={count > 5 ? "danger" : "warning"}>
                    {domainLabels[domain] || domain}: {count}
                  </StatusTag>
                ))
              : <Text type="secondary">暂无异常</Text>}
          </div>
        </div>
      </Col>
    </Row>
  );
}
```

```css
/* frontend/src/pages/dashboard/components/KpiCards.module.css */
.row {
  margin-bottom: 24px;
}

.card {
  background: var(--ant-color-bg-container);
  border: 1px solid var(--ant-color-border-secondary);
  border-radius: 8px;
  padding: 16px;
  min-height: 96px;
}

.value {
  font-size: 32px;
  font-weight: 600;
  margin-top: 8px;
  font-variant-numeric: tabular-nums;
}

.severity {
  margin-top: 8px;
}

.areaList {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
  margin-top: 8px;
}
```

- [ ] **步骤 3：跑测试 + 替换 + commit**

```bash
cd frontend && npx vitest run src/test/dashboard/KpiCards.test.tsx
```

预期：PASS（3 tests）。然后在 `WatchtowerDashboard.tsx` 删掉对应 JSX 块，换成 `<KpiCards totalAlerts={data.total_alerts} severity={data.severity} riskAreas={data.risk_areas} domainDistribution={anomalyEntries.map(([d, items]) => [d, items.length])} />`，tsc + eslint，再 commit：

```bash
git add frontend/src/pages/dashboard/components/KpiCards.tsx frontend/src/pages/dashboard/components/KpiCards.module.css frontend/src/test/dashboard/KpiCards.test.tsx frontend/src/pages/dashboard/WatchtowerDashboard.tsx
git commit -m "refactor(frontend): extract KpiCards from WatchtowerDashboard"
```

### 任务 14：AiSummary 组件

**文件：**
- 创建：`frontend/src/pages/dashboard/components/AiSummary.tsx`
- 创建：`frontend/src/pages/dashboard/components/AiSummary.module.css`
- 创建：`frontend/src/test/dashboard/AiSummary.test.tsx`
- 修改：`frontend/src/pages/dashboard/WatchtowerDashboard.tsx`

- [ ] **步骤 1：写测试**

```typescript
// frontend/src/test/dashboard/AiSummary.test.tsx
import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { AiSummary } from "@/pages/dashboard/components/AiSummary";

describe("AiSummary", () => {
  it("renders the AI summary text", () => {
    render(<AiSummary text="今日系统运行正常。" />);
    expect(screen.getByText("今日系统运行正常。")).toBeInTheDocument();
    expect(screen.getByText("AI 分析摘要")).toBeInTheDocument();
  });

  it("renders empty text fallback without crashing", () => {
    render(<AiSummary text="" />);
    expect(screen.getByText("AI 分析摘要")).toBeInTheDocument();
  });
});
```

- [ ] **步骤 2：写实现**

```tsx
// frontend/src/pages/dashboard/components/AiSummary.tsx
import { Typography } from "antd";
import styles from "./AiSummary.module.css";

const { Text } = Typography;

export interface AiSummaryProps {
  text: string;
}

export function AiSummary({ text }: AiSummaryProps) {
  return (
    <div className={styles.section}>
      <Text strong>AI 分析摘要</Text>
      <div className={styles.body}>{text || "暂无 AI 摘要"}</div>
    </div>
  );
}
```

```css
/* frontend/src/pages/dashboard/components/AiSummary.module.css */
.section {
  background: var(--ant-color-bg-container);
  border: 1px solid var(--ant-color-border-secondary);
  border-radius: 8px;
  padding: 16px;
  margin-bottom: 16px;
}

.body {
  margin-top: 8px;
  white-space: pre-wrap;
}
```

- [ ] **步骤 3：跑测试 + 替换 + commit**

```bash
cd frontend && npx vitest run src/test/dashboard/AiSummary.test.tsx
```

预期：PASS（2 tests）。然后替换 + tsc + eslint + commit：

```bash
git add frontend/src/pages/dashboard/components/AiSummary.tsx frontend/src/pages/dashboard/components/AiSummary.module.css frontend/src/test/dashboard/AiSummary.test.tsx frontend/src/pages/dashboard/WatchtowerDashboard.tsx
git commit -m "refactor(frontend): extract AiSummary from WatchtowerDashboard"
```

### 任务 15：TopActions 组件

**文件：**
- 创建：`frontend/src/pages/dashboard/components/TopActions.tsx`
- 创建：`frontend/src/pages/dashboard/components/TopActions.module.css`
- 创建：`frontend/src/test/dashboard/TopActions.test.tsx`
- 修改：`frontend/src/pages/dashboard/WatchtowerDashboard.tsx`

- [ ] **步骤 1：写测试**

```typescript
// frontend/src/test/dashboard/TopActions.test.tsx
import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { TopActions } from "@/pages/dashboard/components/TopActions";

describe("TopActions", () => {
  it("renders list of items in order", () => {
    render(<TopActions items={["联系客户A", "补货 SKU-X"]} />);
    const items = screen.getAllByRole("listitem");
    expect(items).toHaveLength(2);
    expect(items[0]).toHaveTextContent("1. 联系客户A");
    expect(items[1]).toHaveTextContent("2. 补货 SKU-X");
  });

  it("renders nothing when items empty", () => {
    const { container } = render(<TopActions items={[]} />);
    expect(container).toBeEmptyDOMElement();
  });
});
```

- [ ] **步骤 2：写实现**

```tsx
// frontend/src/pages/dashboard/components/TopActions.tsx
import { Typography } from "antd";
import styles from "./TopActions.module.css";

const { Text } = Typography;

export interface TopActionsProps {
  items: string[];
}

export function TopActions({ items }: TopActionsProps) {
  if (!items.length) return null;
  return (
    <div className={styles.section}>
      <Text strong>优先行动</Text>
      <ol className={styles.list}>
        {items.map((item, i) => (
          <li key={i}>{item}</li>
        ))}
      </ol>
    </div>
  );
}
```

```css
/* frontend/src/pages/dashboard/components/TopActions.module.css */
.section {
  background: var(--ant-color-bg-container);
  border: 1px solid var(--ant-color-border-secondary);
  border-radius: 8px;
  padding: 16px;
  margin-bottom: 16px;
}

.list {
  margin: 8px 0 0;
  padding-left: 20px;
}
```

- [ ] **步骤 3：跑测试 + 替换 + commit**

```bash
cd frontend && npx vitest run src/test/dashboard/TopActions.test.tsx
```

预期：PASS（2 tests）。然后替换 + tsc + eslint + commit：

```bash
git add frontend/src/pages/dashboard/components/TopActions.tsx frontend/src/pages/dashboard/components/TopActions.module.css frontend/src/test/dashboard/TopActions.test.tsx frontend/src/pages/dashboard/WatchtowerDashboard.tsx
git commit -m "refactor(frontend): extract TopActions from WatchtowerDashboard"
```

### 任务 16：AnomalyTable 组件

**文件：**
- 创建：`frontend/src/pages/dashboard/components/AnomalyTable.tsx`
- 创建：`frontend/src/pages/dashboard/components/AnomalyTable.module.css`
- 创建：`frontend/src/test/dashboard/AnomalyTable.test.tsx`
- 修改：`frontend/src/pages/dashboard/WatchtowerDashboard.tsx`

- [ ] **步骤 1：写测试**

```typescript
// frontend/src/test/dashboard/AnomalyTable.test.tsx
import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { AnomalyTable } from "@/pages/dashboard/components/AnomalyTable";
import type { AnomalyRow } from "@/types/watchtower";

const sampleRows: AnomalyRow[] = [
  { domain: "churn_risk", domainLabel: "客户流失风险", name: "客户A", signal: "90天无订单" },
  { domain: "low_stock", domainLabel: "低库存", name: "SKU-X", signal: "qty=2 / safety=10" },
];

describe("AnomalyTable", () => {
  it("renders all rows", () => {
    render(<AnomalyTable rows={sampleRows} />);
    expect(screen.getByText("客户A")).toBeInTheDocument();
    expect(screen.getByText("SKU-X")).toBeInTheDocument();
  });

  it("renders empty state when rows empty", () => {
    render(<AnomalyTable rows={[]} />);
    expect(screen.getByText(/未检测到异常/)).toBeInTheDocument();
  });
});
```

- [ ] **步骤 2：写实现**

```tsx
// frontend/src/pages/dashboard/components/AnomalyTable.tsx
import { ProTable } from "@ant-design/pro-components";
import type { ProColumns } from "@ant-design/pro-components";
import { EmptyState, StatusTag, erpPagination } from "@/ui";
import type { AnomalyRow } from "@/types/watchtower";
import styles from "./AnomalyTable.module.css";

const columns: ProColumns<AnomalyRow>[] = [
  { title: "领域", dataIndex: "domainLabel", width: 120, render: (d) => <StatusTag>{d}</StatusTag> },
  { title: "名称", dataIndex: "name", ellipsis: true, render: (n) => n ?? "-" },
  { title: "详情", dataIndex: "signal", ellipsis: true, render: (s) => s ?? "-" },
];

export interface AnomalyTableProps {
  rows: AnomalyRow[];
}

export function AnomalyTable({ rows }: AnomalyTableProps) {
  if (rows.length === 0) {
    return <EmptyState description="未检测到异常，系统运行正常" />;
  }
  return (
    <div className={styles.wrapper}>
      <ProTable<AnomalyRow>
        columns={columns}
        dataSource={rows}
        rowKey={(_r, i) => String(i)}
        pagination={erpPagination()}
        search={false}
        options={false}
      />
    </div>
  );
}
```

```css
/* frontend/src/pages/dashboard/components/AnomalyTable.module.css */
.wrapper {
  margin-bottom: 24px;
}
```

- [ ] **步骤 3：跑测试 + 替换 + commit**

```bash
cd frontend && npx vitest run src/test/dashboard/AnomalyTable.test.tsx
```

预期：PASS（2 tests）。然后替换 + tsc + eslint + commit：

```bash
git add frontend/src/pages/dashboard/components/AnomalyTable.tsx frontend/src/pages/dashboard/components/AnomalyTable.module.css frontend/src/test/dashboard/AnomalyTable.test.tsx frontend/src/pages/dashboard/WatchtowerDashboard.tsx
git commit -m "refactor(frontend): extract AnomalyTable from WatchtowerDashboard"
```

---

## 任务 17：WatchtowerDashboard 终态（5 组件组合）

**文件：**
- 修改：`frontend/src/pages/dashboard/WatchtowerDashboard.tsx`

- [ ] **步骤 1：重写为 5 组件纯组合 + magic color 清理**

替换整个 `WatchtowerDashboard.tsx` 为：

```tsx
import { Spin } from "antd";
import { useApiQuery } from "@/lib/queries";
import { getWatchtowerScan } from "@/api";
import { getApiErrorMessage } from "@/api/client";
import { Alert, Button } from "antd";
import { EmptyState } from "@/ui";
import FullPageLoader from "@/ui/FullPageLoader";
import { ScanHeader } from "./components/ScanHeader";
import { KpiCards } from "./components/KpiCards";
import { AiSummary } from "./components/AiSummary";
import { TopActions } from "./components/TopActions";
import { AnomalyTable } from "./components/AnomalyTable";
import type { WatchtowerScanResponse, AnomalyRow, AnomalyDomain } from "@/types/watchtower";
import styles from "./WatchtowerDashboard.module.css";

const SCAN_LOOKBACK_DAYS = 90;
const DOMAIN_LABELS: Record<AnomalyDomain, string> = {
  churn_risk: "客户流失风险",
  order_drop: "订单量下降",
  low_stock: "低库存",
  out_of_stock: "缺货",
};

export default function WatchtowerDashboard() {
  const query = useApiQuery<WatchtowerScanResponse>(
    ["watchtower", "scan", SCAN_LOOKBACK_DAYS],
    `/ai/watchtower/scan?days_back=${SCAN_LOOKBACK_DAYS}`,
    null,
    { staleTime: 60 * 1000, refetchInterval: false },
  );

  if (query.isLoading) return <FullPageLoader />;
  if (query.error) {
    return (
      <Alert
        type="error"
        message={getApiErrorMessage(query.error)}
        className={styles.errorAlert}
        action={<Button onClick={() => query.refetch()}>重试</Button>}
      />
    );
  }
  if (!query.data) return null;

  const data = query.data;
  const anomalyEntries: Array<[AnomalyDomain, AnomalyRow[]]> = (
    Object.entries(data.anomalies) as Array<[AnomalyDomain, AnomalyRow[]]>
  ).filter(([, v]) => v.length > 0);

  const allAnomalies: AnomalyRow[] = anomalyEntries.flatMap(([domain, items]) =>
    items.map((item) => ({ ...item, domain, domainLabel: DOMAIN_LABELS[domain] || domain })),
  );

  return (
    <div className={styles.page}>
      <ScanHeader
        scanned_at={data.scanned_at}
        loading={query.isFetching}
        onRefresh={() => query.refetch()}
      />
      <KpiCards
        totalAlerts={data.total_alerts}
        severity={data.severity}
        riskAreas={data.risk_areas}
        domainDistribution={anomalyEntries.map(([d, items]) => [d, items.length] as [string, number])}
      />
      <AiSummary text={data.summary} />
      {data.top_actions?.length > 0 && <TopActions items={data.top_actions} />}
      <AnomalyTable rows={allAnomalies} />
    </div>
  );
}
```

- [ ] **步骤 2：跑 tsc + lint + 测试**

```bash
cd frontend && npx tsc --noEmit && npx eslint src/pages/dashboard/ && npx vitest run src/test/dashboard/
```

预期：EXIT=0；eslint clean；5 个 test 文件全 pass。

- [ ] **步骤 3：Commit**

```bash
git add frontend/src/pages/dashboard/WatchtowerDashboard.tsx
git commit -m "refactor(frontend): WatchtowerDashboard reduces to 5-component composition"
```

---

## 任务 18：最终验收

**文件：** 无新文件

- [ ] **步骤 1：跑全 backend 测试**

```bash
cd backend && pytest -v
```

预期：PASS（基线 1624 + 12 个新测 = 1636 个全 pass）。

- [ ] **步骤 2：跑后端 lint**

```bash
cd backend && ruff check app/ && mypy app/ --explicit-package-bases --ignore-missing-imports --exclude "app/api/v1/(permissions|finance|sales).py" | tail -5
```

预期：ruff all checks passed；mypy Success: no issues found in 323 source files。

- [ ] **步骤 3：跑前端 build**

```bash
cd frontend && npx tsc --noEmit && npx vitest run && npx eslint src/ && npx tsc -b && max build 2>&1 | tail -20
```

预期：所有 EXIT=0；max build 成功。

- [ ] **步骤 4：Commit（如有自动 fix）**

```bash
git status
# 如果有 auto-fix 产生的 diff:
git add -A && git commit -m "chore: post-refactor lint/format auto-fixes"
# 如果干净:
echo "Clean"
```

- [ ] **步骤 5：最终 commit + push + 开 PR**

```bash
cd /home/ttdiy/aierp && git log --oneline -25
# 确认所有 17 个 commit 都到位
git push -u origin refactor/full-target-form
gh pr create --base master --head refactor/full-target-form --title "refactor(watchtower): split + cache + Pro v6 + tests (same behavior)" --body "..."
```

PR body 引用 spec: `docs/superpowers/specs/2026-07-31-watchtower-refactor-design.md` 和 plan: `docs/superpowers/plans/2026-07-31-watchtower-refactor.md`。
