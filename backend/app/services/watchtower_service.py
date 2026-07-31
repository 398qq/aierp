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
    db: AsyncSession, anomalies: dict, scan_time: datetime.datetime
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
                message="客户 %s 近90天订单量从 %s 单骤降至 %s 单（降 %s%%）"
                % (name, drop["prev_orders"], drop["recent_orders"], drop["drop_pct"]),
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


async def scan_low_stock(db: AsyncSession) -> list[dict]:
    """Inventory 0 < qty <= safety_stock. Returns 20 rows: product_id, product_name, brand, qty, safety."""
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


async def scan_out_of_stock(db: AsyncSession) -> list[dict]:
    raise NotImplementedError


async def generate_ai_summary(anomalies: dict, total_alerts: int) -> dict | None:
    raise NotImplementedError


async def scan_all(db: AsyncSession, days_back: int = 90) -> dict:
    raise NotImplementedError
