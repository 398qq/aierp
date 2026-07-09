"""Sales Dashboard API — funnel, trends, AI alerts, widgets, KPI."""

import hashlib
import json
import logging
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, Query
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.database import get_db
from app.models.customer import Customer
from app.models.document import DashboardWidget
from app.models.finance import Invoice
from app.models.product import Inventory, Product
from app.models.sales import Opportunity, SalesOrder
from app.models.transaction import PurchaseOrder
from app.schemas.common import ok
from app.services.cache_service import (
    cache_bump_version,
    cache_get_versioned,
    cache_set_versioned,
)

router = APIRouter(tags=["sales-dashboard"])

logger = logging.getLogger(__name__)

# Cache TTLs (seconds). Dashboard stats can be slightly stale.
DASHBOARD_OVERVIEW_CACHE_TTL = 300  # 5min
DASHBOARD_TRENDS_CACHE_TTL = 600  # 10min
DASHBOARD_ALERTS_CACHE_TTL = 60  # 1min (alerts need fresh data)
DASHBOARD_WIDGETS_CACHE_TTL = 600  # 10min
DASHBOARD_KPI_CACHE_TTL = 120  # 2min (KPI needs to be fresh)
DASHBOARD_LIFECYCLE_CACHE_TTL = 300  # 5min (lifecycle metrics can be slightly stale)


def _dashboard_cache_key(**parts: object) -> str:
    canonical = json.dumps(parts, sort_keys=True, default=str)
    digest = hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:16]
    return f"dashboard:{digest}"


@router.get("/sales/dashboard/overview")
async def dashboard_overview(
    response: JSONResponse,
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(get_current_user),
):
    from app.models.sales import Opportunity, Quotation, SalesOrder, DeliveryNote

    cache_key = _dashboard_cache_key(endpoint="overview")
    cached = await cache_get_versioned("dashboard:overview", cache_key)
    if cached is not None:
        response.headers["X-Cache"] = "HIT"
        return ok(json.loads(cached))
    response.headers["X-Cache"] = "MISS"

    # Funnel counts
    opp_count = (
        await db.execute(
            select(func.count(Opportunity.id)).where(Opportunity.deleted_at.is_(None))
        )
    ).scalar() or 0
    opp_open = (
        await db.execute(
            select(func.count(Opportunity.id)).where(
                Opportunity.deleted_at.is_(None), Opportunity.status == "active"
            )
        )
    ).scalar() or 0
    opp_won = (
        await db.execute(
            select(func.count(Opportunity.id)).where(
                Opportunity.deleted_at.is_(None), Opportunity.status == "won"
            )
        )
    ).scalar() or 0
    opp_amount = (
        await db.execute(
            select(func.coalesce(func.sum(Opportunity.amount), 0)).where(
                Opportunity.deleted_at.is_(None)
            )
        )
    ).scalar() or 0

    quote_count = (
        await db.execute(
            select(func.count(Quotation.id)).where(Quotation.deleted_at.is_(None))
        )
    ).scalar() or 0
    quote_amount = (
        await db.execute(
            select(func.coalesce(func.sum(Quotation.total_amount), 0)).where(
                Quotation.deleted_at.is_(None)
            )
        )
    ).scalar() or 0

    order_count = (
        await db.execute(
            select(func.count(SalesOrder.id)).where(SalesOrder.deleted_at.is_(None))
        )
    ).scalar() or 0
    order_amount = (
        await db.execute(
            select(func.coalesce(func.sum(SalesOrder.total_amount), 0)).where(
                SalesOrder.deleted_at.is_(None)
            )
        )
    ).scalar() or 0

    delivery_count = (
        await db.execute(
            select(func.count(DeliveryNote.id)).where(DeliveryNote.deleted_at.is_(None))
        )
    ).scalar() or 0

    # Conversion rates
    quote_to_order = round(order_count / quote_count * 100, 1) if quote_count > 0 else 0
    opp_to_quote = round(quote_count / opp_count * 100, 1) if opp_count > 0 else 0

    result = {
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
    }
    await cache_set_versioned(
        "dashboard:overview",
        cache_key,
        json.dumps(result, default=str),
        DASHBOARD_OVERVIEW_CACHE_TTL,
    )
    return ok(result)


@router.get("/sales/dashboard/trends")
async def dashboard_trends(
    response: JSONResponse,
    months: int = Query(12, ge=1, le=24),
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(get_current_user),
):
    from app.models.sales import Opportunity, SalesOrder

    cache_key = _dashboard_cache_key(endpoint="trends", months=months)
    cached = await cache_get_versioned("dashboard:trends", cache_key)
    if cached is not None:
        response.headers["X-Cache"] = "HIT"
        return ok(json.loads(cached))
    response.headers["X-Cache"] = "MISS"

    now = datetime.now(timezone.utc)
    trend = []
    for i in range(months - 1, -1, -1):
        month_start = datetime(now.year, now.month, 1, tzinfo=timezone.utc) - timedelta(
            days=30 * i
        )
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

        opp_created = (
            await db.execute(
                select(func.count(Opportunity.id)).where(
                    Opportunity.deleted_at.is_(None),
                    Opportunity.created_at >= month_start,
                    Opportunity.created_at <= month_end,
                )
            )
        ).scalar() or 0

        orders_created = (
            await db.execute(
                select(func.count(SalesOrder.id)).where(
                    SalesOrder.deleted_at.is_(None),
                    SalesOrder.created_at >= month_start,
                    SalesOrder.created_at <= month_end,
                )
            )
        ).scalar() or 0

        order_amount = (
            await db.execute(
                select(func.coalesce(func.sum(SalesOrder.total_amount), 0)).where(
                    SalesOrder.deleted_at.is_(None),
                    SalesOrder.created_at >= month_start,
                    SalesOrder.created_at <= month_end,
                )
            )
        ).scalar() or 0

        trend.append(
            {
                "month": label,
                "opportunities": opp_created,
                "orders": orders_created,
                "revenue": float(order_amount),
            }
        )
    result = {"trends": trend}
    await cache_set_versioned(
        "dashboard:trends",
        cache_key,
        json.dumps(result, default=str),
        DASHBOARD_TRENDS_CACHE_TTL,
    )
    return ok(result)


@router.get("/sales/dashboard/alerts")
async def dashboard_alerts(
    response: JSONResponse,
    limit: int = Query(10, ge=1, le=50),
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(get_current_user),
):
    from app.models.finance import Notification

    cache_key = _dashboard_cache_key(endpoint="alerts", limit=limit)
    cached = await cache_get_versioned("dashboard:alerts", cache_key)
    if cached is not None:
        response.headers["X-Cache"] = "HIT"
        return ok(json.loads(cached))
    response.headers["X-Cache"] = "MISS"

    alerts = (
        (
            await db.execute(
                select(Notification)
                .where(
                    Notification.deleted_at.is_(None),
                    ~Notification.is_read,
                    Notification.type.in_(
                        ["risk_alert", "overdue", "target_warning", "contract_expiry"]
                    ),
                )
                .order_by(Notification.id.desc())
                .limit(limit)
            )
        )
        .scalars()
        .all()
    )

    result = {
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
    }
    await cache_set_versioned(
        "dashboard:alerts",
        cache_key,
        json.dumps(result, default=str),
        DASHBOARD_ALERTS_CACHE_TTL,
    )
    return ok(result)


# ---------------------------------------------------------------------------
# Dashboard Widgets
# ---------------------------------------------------------------------------
@router.get("/dashboard/widgets")
async def list_widgets(
    response: JSONResponse,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    user_id = current_user["user_id"]
    cache_key = _dashboard_cache_key(endpoint="widgets", user_id=user_id)
    cached = await cache_get_versioned("dashboard:widgets", cache_key)
    if cached is not None:
        response.headers["X-Cache"] = "HIT"
        return ok(json.loads(cached))
    response.headers["X-Cache"] = "MISS"

    result = await db.execute(
        select(DashboardWidget)
        .where(
            DashboardWidget.user_id == user_id,
            DashboardWidget.deleted_at.is_(None),
        )
        .order_by(DashboardWidget.position_y, DashboardWidget.position_x)
    )
    widgets = result.scalars().all()
    payload = [
        {
            "id": w.id,
            "widget_type": w.widget_type,
            "title": w.title,
            "config": w.config,
            "position_x": w.position_x,
            "position_y": w.position_y,
            "width": w.width,
            "height": w.height,
            "enabled": w.enabled,
        }
        for w in widgets
    ]
    await cache_set_versioned(
        "dashboard:widgets",
        cache_key,
        json.dumps(payload, default=str),
        DASHBOARD_WIDGETS_CACHE_TTL,
    )
    return ok(payload)


class WidgetSave(BaseModel):
    widgets: list[dict]


@router.put("/dashboard/widgets")
async def save_widgets(
    body: WidgetSave,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    # Delete existing
    existing = (
        (
            await db.execute(
                select(DashboardWidget).where(
                    DashboardWidget.user_id == current_user["user_id"],
                    DashboardWidget.deleted_at.is_(None),
                )
            )
        )
        .scalars()
        .all()
    )
    for w in existing:
        w.deleted_at = datetime.now(timezone.utc)

    # Insert new
    for wi in body.widgets:
        db.add(
            DashboardWidget(
                user_id=current_user["user_id"],
                widget_type=wi.get("widget_type", "kpi_card"),
                title=wi.get("title", ""),
                config=wi.get("config", {}),
                position_x=wi.get("position_x", 0),
                position_y=wi.get("position_y", 0),
                width=wi.get("width", 3),
                height=wi.get("height", 2),
                enabled=wi.get("enabled", True),
            )
        )

    await db.commit()
    await cache_bump_version("dashboard:widgets")
    return ok(msg="仪表板已保存")


@router.get("/dashboard/kpi")
async def dashboard_kpi(
    response: JSONResponse,
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(get_current_user),
):
    cache_key = _dashboard_cache_key(endpoint="kpi")
    cached = await cache_get_versioned("dashboard:kpi", cache_key)
    if cached is not None:
        response.headers["X-Cache"] = "HIT"
        return ok(json.loads(cached))
    response.headers["X-Cache"] = "MISS"

    now = datetime.now(timezone.utc)
    month_start = datetime(now.year, now.month, 1, tzinfo=timezone.utc)

    # Revenue this month
    month_revenue = (
        await db.execute(
            select(func.coalesce(func.sum(SalesOrder.total_amount), 0)).where(
                SalesOrder.deleted_at.is_(None),
                SalesOrder.created_at >= month_start,
            )
        )
    ).scalar() or 0

    # New customers this month
    new_customers = (
        await db.execute(
            select(func.count(Customer.id)).where(
                Customer.deleted_at.is_(None),
                Customer.created_at >= month_start,
            )
        )
    ).scalar() or 0

    # Open opportunities
    open_opps = (
        await db.execute(
            select(func.count(Opportunity.id)).where(
                Opportunity.deleted_at.is_(None),
                Opportunity.status == "active",
            )
        )
    ).scalar() or 0

    # Pending purchase orders
    pending_pos = (
        await db.execute(
            select(func.count(PurchaseOrder.id)).where(
                PurchaseOrder.deleted_at.is_(None),
                PurchaseOrder.status.in_(["draft", "submitted", "approved"]),
            )
        )
    ).scalar() or 0

    # Outstanding AR
    outstanding_ar = (
        await db.execute(
            select(func.coalesce(func.sum(Invoice.amount), 0)).where(
                Invoice.deleted_at.is_(None),
                Invoice.status.in_(["sent", "overdue", "partial"]),
            )
        )
    ).scalar() or 0

    # Low stock products
    low_stock = (
        await db.execute(
            select(func.count(Inventory.id)).where(
                Inventory.deleted_at.is_(None),
                Inventory.quantity <= Inventory.safety_stock,
                Inventory.safety_stock > 0,
            )
        )
    ).scalar() or 0

    # Total products
    total_products = (
        await db.execute(
            select(func.count(Product.id)).where(Product.deleted_at.is_(None))
        )
    ).scalar() or 0

    # Total customers
    total_customers = (
        await db.execute(
            select(func.count(Customer.id)).where(Customer.deleted_at.is_(None))
        )
    ).scalar() or 0

    result = {
        "month_revenue": float(month_revenue),
        "new_customers": new_customers,
        "open_opportunities": open_opps,
        "pending_purchase_orders": pending_pos,
        "outstanding_ar": float(outstanding_ar),
        "low_stock_items": low_stock,
        "total_products": total_products,
        "total_customers": total_customers,
    }
    await cache_set_versioned(
        "dashboard:kpi",
        cache_key,
        json.dumps(result, default=str),
        DASHBOARD_KPI_CACHE_TTL,
    )
    return ok(result)


# ===========================================================================
# Stage 7: 跟单全流程关键指标
# ===========================================================================


@router.get("/sales/lifecycle-metrics")
async def sales_lifecycle_metrics(
    days_back: int = Query(30, ge=1, le=365),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """三个关键指标 — 让老板一眼看出健康度。

    1. avg_time_to_confirm (avg_time_to_confirm_hours):
       从 PENDING → CONFIRMED 的平均停留小时数。
       越短越健康（订单响应快）；越长说明销售响应慢。

    2. cancellation_rate (cancellation_rate_pct):
       cancelled / (completed + cancelled) 的百分比。
       越低越健康；>30% 说明报价质量差或客户匹配错。

    3. stage_conversion (stage_conversion_pct):
       PENDING → COMPLETED 的端到端转化率。
       越高越好；<20% 说明漏斗流失严重。

    Cached: 5 min (DASHBOARD_LIFECYCLE_CACHE_TTL). Bust on OrderConfirmed
    / OrderCancelled / OrderCompleted via cache_bump_version (Stage 8 Day 3).
    """
    cache_key = _dashboard_cache_key("lifecycle", days_back=days_back)
    cached = await cache_get_versioned("dashboard:lifecycle", cache_key)
    if cached:
        from app.schemas.common import ok
        return JSONResponse(
            content=ok(json.loads(cached)),
        )

    from app.models.audit import StatusTransitionLog

    cutoff = datetime.now(timezone.utc) - timedelta(days=days_back)

    # 1. avg_time_to_confirm
    # Find PENDING → CONFIRMED transitions in the time window
    pending_to_confirmed = (
        (
            await db.execute(
                select(StatusTransitionLog).where(
                    StatusTransitionLog.action == "confirm",
                    StatusTransitionLog.transitioned_at >= cutoff,
                )
            )
        )
        .scalars()
        .all()
    )

    confirm_hours = []
    for log in pending_to_confirmed:
        # Find the corresponding PENDING entry (same aggregate, just before)
        prev = await db.scalar(
            select(StatusTransitionLog).where(
                StatusTransitionLog.aggregate_type == log.aggregate_type,
                StatusTransitionLog.aggregate_id == log.aggregate_id,
                StatusTransitionLog.status_before.is_(None),  # initial creation
            )
        )
        if prev:
            delta = (log.transitioned_at - prev.transitioned_at).total_seconds() / 3600
            confirm_hours.append(delta)
    avg_time_to_confirm_hours = (
        round(sum(confirm_hours) / len(confirm_hours), 1) if confirm_hours else None
    )

    # 2. cancellation_rate (within window)
    cancelled_count = (
        await db.scalar(
            select(func.count(StatusTransitionLog.id)).where(
                StatusTransitionLog.action == "cancel",
                StatusTransitionLog.transitioned_at >= cutoff,
            )
        )
    ) or 0
    completed_count = (
        await db.scalar(
            select(func.count(StatusTransitionLog.id)).where(
                StatusTransitionLog.action == "complete",
                StatusTransitionLog.transitioned_at >= cutoff,
            )
        )
    ) or 0
    total_outcomes = cancelled_count + completed_count
    cancellation_rate_pct = (
        round(cancelled_count / total_outcomes * 100, 1) if total_outcomes > 0 else None
    )

    # 3. stage_conversion
    # Count distinct orders that reached PENDING, then COMPLETED
    pending_orders = (
        await db.execute(
            select(func.count(func.distinct(StatusTransitionLog.aggregate_id))).where(
                StatusTransitionLog.action == "create",  # initial
                StatusTransitionLog.transitioned_at >= cutoff,
            )
        )
    ).scalar() or 0
    completed_orders = (
        await db.scalar(
            select(func.count(func.distinct(StatusTransitionLog.aggregate_id))).where(
                StatusTransitionLog.action == "complete",
                StatusTransitionLog.transitioned_at >= cutoff,
            )
        )
    ).scalar() or 0
    stage_conversion_pct = (
        round(completed_orders / pending_orders * 100, 1)
        if pending_orders > 0
        else None
    )

    result = {
        "window_days": days_back,
        "avg_time_to_confirm_hours": avg_time_to_confirm_hours,
        "cancellation_rate_pct": cancellation_rate_pct,
        "stage_conversion_pct": stage_conversion_pct,
        "sample_counts": {
            "confirm_transitions": len(confirm_hours),
            "cancelled": cancelled_count,
            "completed": completed_count,
            "pending_orders": pending_orders,
            "completed_orders": completed_orders,
        },
    }
    await cache_set_versioned(
        "dashboard:lifecycle", cache_key,
        json.dumps(result, default=str), DASHBOARD_LIFECYCLE_CACHE_TTL,
    )
    return ok(result)
