"""Sales Dashboard API — funnel, trends, AI alerts."""

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.database import get_db
from app.schemas.common import ok

router = APIRouter(tags=["sales-dashboard"])


@router.get("/sales/dashboard/overview")
async def dashboard_overview(
    db: AsyncSession = Depends(get_db), _user: dict = Depends(get_current_user),
):
    from app.models.sales import Opportunity, Quotation, SalesOrder, DeliveryNote

    # Funnel counts
    opp_count = (await db.execute(
        select(func.count(Opportunity.id)).where(Opportunity.deleted_at.is_(None))
    )).scalar() or 0
    opp_open = (await db.execute(
        select(func.count(Opportunity.id)).where(
            Opportunity.deleted_at.is_(None), Opportunity.status == "active"
        )
    )).scalar() or 0
    opp_won = (await db.execute(
        select(func.count(Opportunity.id)).where(
            Opportunity.deleted_at.is_(None), Opportunity.status == "won"
        )
    )).scalar() or 0
    opp_amount = (await db.execute(
        select(func.coalesce(func.sum(Opportunity.amount), 0)).where(
            Opportunity.deleted_at.is_(None)
        )
    )).scalar() or 0

    quote_count = (await db.execute(
        select(func.count(Quotation.id)).where(Quotation.deleted_at.is_(None))
    )).scalar() or 0
    quote_amount = (await db.execute(
        select(func.coalesce(func.sum(Quotation.total_amount), 0)).where(
            Quotation.deleted_at.is_(None)
        )
    )).scalar() or 0

    order_count = (await db.execute(
        select(func.count(SalesOrder.id)).where(SalesOrder.deleted_at.is_(None))
    )).scalar() or 0
    order_amount = (await db.execute(
        select(func.coalesce(func.sum(SalesOrder.total_amount), 0)).where(
            SalesOrder.deleted_at.is_(None)
        )
    )).scalar() or 0

    delivery_count = (await db.execute(
        select(func.count(DeliveryNote.id)).where(DeliveryNote.deleted_at.is_(None))
    )).scalar() or 0

    # Conversion rates
    quote_to_order = round(order_count / quote_count * 100, 1) if quote_count > 0 else 0
    opp_to_quote = round(quote_count / opp_count * 100, 1) if opp_count > 0 else 0

    return ok({
        "funnel": [
            {"stage": "商机", "count": opp_count, "amount": float(opp_amount)},
            {"stage": "报价", "count": quote_count, "amount": float(quote_amount)},
            {"stage": "订单", "count": order_count, "amount": float(order_amount)},
            {"stage": "发货", "count": delivery_count, "amount": float(order_amount)},
        ],
        "open_opportunities": opp_open,
        "won_opportunities": opp_won,
        "total_pipeline": float(opp_amount),
        "quote_to_order_rate": quote_to_order,
        "opp_to_quote_rate": opp_to_quote,
    })


@router.get("/sales/dashboard/trends")
async def dashboard_trends(
    months: int = Query(12, ge=1, le=24),
    db: AsyncSession = Depends(get_db), _user: dict = Depends(get_current_user),
):
    from app.models.sales import Opportunity, SalesOrder

    now = datetime.now(timezone.utc)
    trend = []
    for i in range(months - 1, -1, -1):
        month_start = datetime(now.year, now.month, 1, tzinfo=timezone.utc) - timedelta(days=30 * i)
        if i == 0:
            month_end = now
        else:
            if now.month - i <= 0:
                y = now.year - 1
                m = now.month - i + 12
            else:
                y = now.year
                m = now.month - i
            import calendar
            last_day = calendar.monthrange(y, m)[1]
            month_end = datetime(y, m, last_day, 23, 59, 59, tzinfo=timezone.utc)
            month_start = datetime(y, m, 1, tzinfo=timezone.utc)

        label = month_start.strftime("%Y-%m")

        opp_created = (await db.execute(
            select(func.count(Opportunity.id)).where(
                Opportunity.deleted_at.is_(None),
                Opportunity.created_at >= month_start,
                Opportunity.created_at <= month_end,
            )
        )).scalar() or 0

        orders_created = (await db.execute(
            select(func.count(SalesOrder.id)).where(
                SalesOrder.deleted_at.is_(None),
                SalesOrder.created_at >= month_start,
                SalesOrder.created_at <= month_end,
            )
        )).scalar() or 0

        order_amount = (await db.execute(
            select(func.coalesce(func.sum(SalesOrder.total_amount), 0)).where(
                SalesOrder.deleted_at.is_(None),
                SalesOrder.created_at >= month_start,
                SalesOrder.created_at <= month_end,
            )
        )).scalar() or 0

        trend.append({
            "month": label,
            "opportunities": opp_created,
            "orders": orders_created,
            "revenue": float(order_amount),
        })
    return ok({"trends": trend})


@router.get("/sales/dashboard/alerts")
async def dashboard_alerts(
    limit: int = Query(10, ge=1, le=50),
    db: AsyncSession = Depends(get_db), _user: dict = Depends(get_current_user),
):
    from app.models.finance import Notification

    alerts = (await db.execute(
        select(Notification).where(
            Notification.deleted_at.is_(None),
            not Notification.is_read,
            Notification.type.in_(["risk_alert", "overdue", "target_warning", "contract_expiry"]),
        ).order_by(Notification.id.desc()).limit(limit)
    )).scalars().all()

    return ok({
        "alerts": [
            {
                "id": a.id,
                "type": a.type,
                "title": a.title,
                "content": a.content,
                "created_at": a.created_at.isoformat() if a.created_at else None,
            }
            for a in alerts
        ],
    })
