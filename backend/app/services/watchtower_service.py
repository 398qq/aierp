"""AI Watchtower — proactive anomaly detection and alert generation across the system."""

import datetime
import logging
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.product import Brand, Inventory, Product
from app.models.sales import SalesOrder
from app.models.customer import Customer, AlertEvent

logger = logging.getLogger(__name__)


async def _persist_customer_alerts(db: AsyncSession, anomalies: dict, scan_time: datetime.datetime) -> int:
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
        events.append(AlertEvent(
            customer_id=churn["customer_id"],
            rule_type="churn_risk",
            rule_name="客户流失预警",
            severity="warning",
            message="客户 %s（%s·%s）—— %s"
                    % (churn["name"], churn.get("industry", "未知行业"),
                       churn.get("level", "未知等级"), churn.get("signal", "无信号")),
            is_read=False,
        ))

    for drop in anomalies.get("order_drop", []):
        name = drop.get("name") or f"#{drop['customer_id']}"
        events.append(AlertEvent(
            customer_id=drop["customer_id"],
            rule_type="order_drop",
            rule_name="订单量下降",
            severity="warning",
            message="客户 %s 近90天订单量从 %s 单骤降至 %s 单（降 %s%%）"
                    % (name, drop["prev_orders"], drop["recent_orders"], drop["drop_pct"]),
            is_read=False,
        ))

    if events:
        db.add_all(events)
        written = len(events)

    return written


async def scan_all(db: AsyncSession, days_back: int = 90) -> dict:
    """Run full system scan and return all detected anomalies with AI analysis."""

    now = datetime.datetime.utcnow()
    lookback = now - datetime.timedelta(days=days_back)
    prev_lookback = lookback - datetime.timedelta(days=days_back)

    anomalies = {}

    # --- Customer Churn Risk ---
    # Customers who had orders in prev period but none in recent period
    prev_active = set((await db.execute(
        select(func.distinct(SalesOrder.customer_id)).where(
            SalesOrder.created_at.between(prev_lookback, lookback),
            SalesOrder.deleted_at.is_(None),
        )
    )).scalars().all())

    recent_active = set((await db.execute(
        select(func.distinct(SalesOrder.customer_id)).where(
            SalesOrder.created_at >= lookback,
            SalesOrder.deleted_at.is_(None),
        )
    )).scalars().all())

    churned_ids = prev_active - recent_active
    if churned_ids:
        churned = (await db.execute(
            select(Customer.id, Customer.name, Customer.level, Customer.industry)
            .where(Customer.id.in_(list(churned_ids)), Customer.deleted_at.is_(None))
        )).all()
        anomalies["churn_risk"] = [
            {"customer_id": r[0], "name": r[1], "level": r[2], "industry": r[3],
             "signal": f"最近{days_back}天无订单"}
            for r in churned
        ]

    # --- Order Volume Drop ---
    # Compare order count per customer period-over-period
    recent_counts = dict((await db.execute(
        select(SalesOrder.customer_id, func.count(SalesOrder.id))
        .where(SalesOrder.created_at >= lookback, SalesOrder.deleted_at.is_(None))
        .group_by(SalesOrder.customer_id)
    )).all() or [])

    prev_counts = dict((await db.execute(
        select(SalesOrder.customer_id, func.count(SalesOrder.id))
        .where(SalesOrder.created_at.between(prev_lookback, lookback), SalesOrder.deleted_at.is_(None))
        .group_by(SalesOrder.customer_id)
    )).all() or [])

    order_drops = []
    for cid in set(list(recent_counts.keys()) + list(prev_counts.keys())):
        prev_c = prev_counts.get(cid, 0)
        recent_c = recent_counts.get(cid, 0)
        if prev_c >= 3 and recent_c < prev_c * 0.5:
            order_drops.append({"customer_id": cid, "prev_orders": prev_c,
                                "recent_orders": recent_c, "drop_pct": round((1 - recent_c / prev_c) * 100)})

    if order_drops:
        cids = [d["customer_id"] for d in order_drops[:20]]
        cnames = dict((await db.execute(
            select(Customer.id, Customer.name).where(Customer.id.in_(cids), Customer.deleted_at.is_(None))
        )).all() or [])
        anomalies["order_drop"] = [
            {**d, "name": cnames.get(d["customer_id"], f"#{d['customer_id']}")}
            for d in order_drops[:20]
        ]

    # --- Low Stock Alerts ---
    low_stock = (await db.execute(
        select(Product.id, Product.name, Product.sku, Inventory.quantity, Inventory.safety_stock,
               Brand.name)
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
    )).all()

    if low_stock:
        anomalies["low_stock"] = [
            {"product_id": r[0], "product_name": f"{r[2] or ''} {r[1]}",
             "brand": r[5] or "未知", "qty": r[3], "safety": r[4] or 0}
            for r in low_stock
        ]

    # --- Out of Stock ---
    out_of_stock = (await db.execute(
        select(Product.id, Product.name, Product.sku, Brand.name)
        .join(Inventory, Product.id == Inventory.product_id)
        .outerjoin(Brand, Product.brand_id == Brand.id)
        .where(
            Inventory.quantity <= 0,
            Product.deleted_at.is_(None),
            Inventory.deleted_at.is_(None),
        )
        .limit(20)
    )).all()

    if out_of_stock:
        anomalies["out_of_stock"] = [
            {"product_id": r[0], "product_name": f"{r[2] or ''} {r[1]}", "brand": r[3] or "未知"}
            for r in out_of_stock
        ]

    # --- Build AI analysis text ---
    alert_text_parts = []
    if "churn_risk" in anomalies:
        alert_text_parts.append(f"**流失风险客户 ({len(anomalies['churn_risk'])}个):**\n" +
                                "\n".join(f"- {a['name']} ({a['industry'] or '未知行业'}, {a['level'] or '未知等级'}) — {a['signal']}"
                                          for a in anomalies["churn_risk"][:10]))
    if "order_drop" in anomalies:
        alert_text_parts.append(f"\n**订单量下降客户 ({len(anomalies['order_drop'])}个):**\n" +
                                "\n".join(f"- {a['name']}: {a['prev_orders']}单→{a['recent_orders']}单 (降{a['drop_pct']}%)"
                                          for a in anomalies["order_drop"][:10]))
    if "low_stock" in anomalies:
        alert_text_parts.append(f"\n**低库存产品 ({len(anomalies['low_stock'])}个):**\n" +
                                "\n".join(f"- [{a['brand']}] {a['product_name']}: {a['qty']}件 (安全线{a['safety']}件)"
                                          for a in anomalies["low_stock"][:10]))
    if "out_of_stock" in anomalies:
        alert_text_parts.append(f"\n**缺货产品 ({len(anomalies['out_of_stock'])}个):**\n" +
                                "\n".join(f"- [{a['brand']}] {a['product_name']}"
                                          for a in anomalies["out_of_stock"][:10]))

    alert_text = "\n".join(alert_text_parts) if alert_text_parts else "无明显异常"

    total_alerts = (
        len(anomalies.get("churn_risk", [])) +
        len(anomalies.get("order_drop", [])) +
        len(anomalies.get("low_stock", [])) +
        len(anomalies.get("out_of_stock", []))
    )

    # AI summary
    ai_summary = None
    if alert_text_parts:
        from app.services.ai.client import ai_client
        from app.services.ai.prompts import watchtower_prompt

        schema = {
            "severity": "string: 正常/需关注/紧急",
            "summary": "string, 2-3 sentence overall assessment",
            "top_actions": ["string, prioritized actions to take"],
            "risk_areas": ["string, risk areas identified"],
        }
        try:
            ai_summary = await ai_client.chat_structured(
                [{"role": "system", "content": "你是一个ERP系统监控专家，擅长发现经营异常并提供优先级建议。"},
                 {"role": "user", "content": watchtower_prompt(alert_text, total_alerts)}],
                schema,
            )
        except Exception as e:
            logger.error(f"Watchtower AI analysis failed: {e}")
            ai_summary = {"severity": "正常", "summary": "AI分析暂不可用", "top_actions": [], "risk_areas": []}

    return {
        "scanned_at": now.isoformat(),
        "total_alerts": total_alerts,
        "severity": ai_summary.get("severity") if ai_summary else "正常",
        "summary": ai_summary.get("summary") if ai_summary else "",
        "top_actions": ai_summary.get("top_actions") if ai_summary else [],
        "risk_areas": ai_summary.get("risk_areas") if ai_summary else [],
        "alerts_persisted": await _persist_customer_alerts(db, anomalies, now),
        "anomalies": {
            "churn_risk": anomalies.get("churn_risk", []),
            "order_drop": anomalies.get("order_drop", []),
            "low_stock": anomalies.get("low_stock", []),
            "out_of_stock": anomalies.get("out_of_stock", []),
        },
    }
