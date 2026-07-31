"""AI Watchtower — proactive anomaly detection and alert generation across the system."""

import datetime
import logging
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

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
    db: AsyncSession, lookback: datetime.datetime, prev_lookback: datetime.datetime
) -> list[dict]:
    raise NotImplementedError


async def scan_low_stock(db: AsyncSession) -> list[dict]:
    raise NotImplementedError


async def scan_out_of_stock(db: AsyncSession) -> list[dict]:
    raise NotImplementedError


async def generate_ai_summary(anomalies: dict, total_alerts: int) -> dict | None:
    raise NotImplementedError


async def scan_all(db: AsyncSession, days_back: int = 90) -> dict:
    raise NotImplementedError
