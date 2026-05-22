"""Watchtower routes — system-wide anomaly scan and daily report."""

import logging
from datetime import datetime as dt, timezone
from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
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
    """Scan all domains for anomalies — overdue payments, low stock, churn risk, etc."""
    from app.services.watchtower_service import scan_all

    try:
        result = await scan_all(db, days_back)
        return ok(result)
    except Exception as e:
        return fail(str(e), 500)


@router.get("/daily-report")
async def daily_report(
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(get_current_user),
):
    """Generate a daily cross-domain report with AI summary."""
    now = dt.now(timezone.utc)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)

    # Today's orders
    from app.models.sales import SalesOrder

    today_orders = (await db.execute(
        select(
            func.count(SalesOrder.id),
            func.coalesce(func.sum(SalesOrder.total_amount), 0),
        ).where(
            SalesOrder.deleted_at.is_(None),
            SalesOrder.created_at >= today_start,
        )
    )).first()
    orders_count = today_orders[0] if today_orders else 0
    orders_amount = float(today_orders[1]) if today_orders else 0.0

    # New customers today
    from app.models.customer import Customer

    new_cust = (await db.execute(
        select(func.count(Customer.id)).where(
            Customer.deleted_at.is_(None),
            Customer.created_at >= today_start,
        )
    )).scalar() or 0

    # Inventory summary
    from app.models.product import Inventory

    low_stock = (await db.execute(
        select(func.count(Inventory.id)).where(
            Inventory.deleted_at.is_(None),
            Inventory.quantity <= Inventory.safety_stock,
            Inventory.quantity > 0,
        )
    )).scalar() or 0
    out_of_stock = (await db.execute(
        select(func.count(Inventory.id)).where(
            Inventory.deleted_at.is_(None),
            Inventory.quantity <= 0,
        )
    )).scalar() or 0

    # Payments today
    from app.models.transaction import Payment

    today_payments = (await db.execute(
        select(func.count(Payment.id), func.coalesce(func.sum(Payment.amount), 0)).where(
            Payment.deleted_at.is_(None),
            Payment.created_at >= today_start,
        )
    )).first()
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

    # AI summary
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
                {"role": "system", "content": "你是一个ERP日报助手，擅长用简洁的语言总结每日经营状况。"},
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

    return ok(report)
