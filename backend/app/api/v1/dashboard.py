"""Sales Dashboard API — funnel, trends, AI alerts, widgets, KPI."""

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, Query
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
            ~Notification.is_read,
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


# ---------------------------------------------------------------------------
# Dashboard Widgets
# ---------------------------------------------------------------------------
@router.get("/dashboard/widgets")
async def list_widgets(
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    result = await db.execute(
        select(DashboardWidget).where(
            DashboardWidget.user_id == current_user["user_id"],
            DashboardWidget.deleted_at.is_(None),
        ).order_by(DashboardWidget.position_y, DashboardWidget.position_x)
    )
    widgets = result.scalars().all()
    return ok([{
        "id": w.id, "widget_type": w.widget_type, "title": w.title,
        "config": w.config, "position_x": w.position_x, "position_y": w.position_y,
        "width": w.width, "height": w.height, "enabled": w.enabled,
    } for w in widgets])


class WidgetSave(BaseModel):
    widgets: list[dict]


@router.put("/dashboard/widgets")
async def save_widgets(
    body: WidgetSave,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    # Delete existing
    existing = (await db.execute(
        select(DashboardWidget).where(
            DashboardWidget.user_id == current_user["user_id"],
            DashboardWidget.deleted_at.is_(None),
        )
    )).scalars().all()
    for w in existing:
        w.deleted_at = datetime.now(timezone.utc)

    # Insert new
    for wi in body.widgets:
        db.add(DashboardWidget(
            user_id=current_user["user_id"],
            widget_type=wi.get("widget_type", "kpi_card"),
            title=wi.get("title", ""),
            config=wi.get("config", {}),
            position_x=wi.get("position_x", 0),
            position_y=wi.get("position_y", 0),
            width=wi.get("width", 3),
            height=wi.get("height", 2),
            enabled=wi.get("enabled", True),
        ))

    await db.commit()
    return ok(msg="仪表板已保存")


@router.get("/dashboard/kpi")
async def dashboard_kpi(
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(get_current_user),
):
    now = datetime.now(timezone.utc)
    month_start = datetime(now.year, now.month, 1, tzinfo=timezone.utc)

    # Revenue this month
    month_revenue = (await db.execute(
        select(func.coalesce(func.sum(SalesOrder.total_amount), 0)).where(
            SalesOrder.deleted_at.is_(None),
            SalesOrder.created_at >= month_start,
        )
    )).scalar() or 0

    # New customers this month
    new_customers = (await db.execute(
        select(func.count(Customer.id)).where(
            Customer.deleted_at.is_(None),
            Customer.created_at >= month_start,
        )
    )).scalar() or 0

    # Open opportunities
    open_opps = (await db.execute(
        select(func.count(Opportunity.id)).where(
            Opportunity.deleted_at.is_(None),
            Opportunity.status == "active",
        )
    )).scalar() or 0

    # Pending purchase orders
    pending_pos = (await db.execute(
        select(func.count(PurchaseOrder.id)).where(
            PurchaseOrder.deleted_at.is_(None),
            PurchaseOrder.status.in_(["draft", "submitted", "approved"]),
        )
    )).scalar() or 0

    # Outstanding AR
    outstanding_ar = (await db.execute(
        select(func.coalesce(func.sum(Invoice.amount), 0)).where(
            Invoice.deleted_at.is_(None),
            Invoice.status.in_(["sent", "overdue", "partial"]),
        )
    )).scalar() or 0

    # Low stock products
    low_stock = (await db.execute(
        select(func.count(Inventory.id)).where(
            Inventory.deleted_at.is_(None),
            Inventory.quantity <= Inventory.safety_stock,
            Inventory.safety_stock > 0,
        )
    )).scalar() or 0

    # Total products
    total_products = (await db.execute(
        select(func.count(Product.id)).where(Product.deleted_at.is_(None))
    )).scalar() or 0

    # Total customers
    total_customers = (await db.execute(
        select(func.count(Customer.id)).where(Customer.deleted_at.is_(None))
    )).scalar() or 0

    return ok({
        "month_revenue": float(month_revenue),
        "new_customers": new_customers,
        "open_opportunities": open_opps,
        "pending_purchase_orders": pending_pos,
        "outstanding_ar": float(outstanding_ar),
        "low_stock_items": low_stock,
        "total_products": total_products,
        "total_customers": total_customers,
    })
