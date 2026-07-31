"""AI Watchtower — proactive anomaly detection and alert generation across the system."""

import datetime
import logging
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.product import Brand, Inventory, Product
from app.models.sales import SalesOrder
from app.models.customer import Customer, AlertEvent

logger = logging.getLogger(__name__)


async def _persist_customer_alerts(
    db: AsyncSession,
    anomalies: dict,
    scan_time: datetime.datetime,
    lookback_days: int = 90,
) -> int:
    """Write customer-related anomalies (churn_risk, order_drop) to AlertEvent table.
    Returns the number of events written.
    """
    written = 0

    # 1. Mark old unread customer alerts as superseded (read=True)
    rule_types = ["churn_risk", "order_drop"]
    await db.execute(
        update(AlertEvent)
        .where(AlertEvent.rule_type.in_(rule_types), AlertEvent.is_read.is_(False))
        .values(is_read=True)
    )

    # 2. Insert fresh events
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
                message=(
                    f"客户 {name} 近{lookback_days}天订单量从 "
                    f"{drop['prev_orders']} 单骤降至 {drop['recent_orders']} 单"
                    f"（降 {drop['drop_pct']}%%）"
                ),
                is_read=False,
            )
        )

    if events:
        db.add_all(events)
        written = len(events)

    return written


async def scan_churn_risk(
    db: AsyncSession,
    lookback: datetime.datetime,
    prev_lookback: datetime.datetime,
) -> list[dict]:
    """Customers active in [prev_lookback, lookback) but silent in [lookback, now).
    Returns: [{customer_id, name, level, industry, signal}].

    No DB-level cap is applied (mirrors the original scan_all behavior).
    Callers can slice the result if a limit is needed.
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
    days = (lookback - prev_lookback).days
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
    )
    return [
        {**d, "name": cnames.get(d["customer_id"], f"#{d['customer_id']}")}
        for d in order_drops[:20]
    ]


def _inventory_qty_query(qty_filter, *, order_by_qty: bool = False) -> select:
    """Shared SELECT for low-stock and out-of-stock queries.

    Always selects 6 columns (id, name, sku, qty, safety, brand_name).
    scan_out_of_stock ignores the last 2 columns in its return mapping.
    """
    return (
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
            qty_filter,
            Product.deleted_at.is_(None),
            Inventory.deleted_at.is_(None),
        )
        .order_by(Inventory.quantity if order_by_qty else None)
        .limit(20)
    )


async def scan_low_stock(db: AsyncSession) -> list[dict]:
    """Inventory 0 < qty <= safety_stock. Returns 20 rows: product_id, product_name, brand, qty, safety."""
    rows = (
        await db.execute(
            _inventory_qty_query(
                (Inventory.quantity <= Inventory.safety_stock)
                & (Inventory.quantity > 0),
                order_by_qty=True,
            )
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


async def scan_out_of_stock(db: AsyncSession) -> list[dict]:
    """Inventory qty <= 0. Returns 20 rows: product_id, product_name, brand."""
    rows = (await db.execute(_inventory_qty_query(Inventory.quantity <= 0))).all()
    return [
        {
            "product_id": r[0],
            "product_name": f"{r[2] or ''} {r[1]}",
            "brand": r[5] or "未知",
        }
        for r in rows
    ]


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
                {
                    "role": "user",
                    "content": watchtower_prompt(alert_text, total_alerts),
                },
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
