"""Enhanced dashboard API."""

import time
from datetime import datetime, timezone, timedelta

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.database import get_db
from app.models.customer import Customer
from app.models.sales import Opportunity, SalesOrder, SalesOrderItem
from app.models.product import Product
from app.schemas.common import ok
from app.utils.cache import _cache

router = APIRouter(prefix="/sales/dashboard", tags=["dashboard"])
DASHBOARD_TTL = 30  # seconds


def _cached(key: str, ttl: int = DASHBOARD_TTL):
    """Check cache, return (is_hit, data)."""
    now = time.time()
    if key in _cache:
        expiry, value = _cache[key]
        if now < expiry:
            return True, value
        del _cache[key]
    return False, None


@router.get("/overview")
async def get_dashboard_overview(db: AsyncSession = Depends(get_db), _user: dict = Depends(get_current_user)):
    cache_key = "dashboard:overview"
    hit, cached = _cached(cache_key)
    if hit:
        return cached

    today = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    tomorrow = today + timedelta(days=1)

    today_orders = (await db.execute(
        select(func.count(SalesOrder.id), func.coalesce(func.sum(SalesOrder.total_amount), 0)).where(
            SalesOrder.deleted_at.is_(None), SalesOrder.created_at >= today, SalesOrder.created_at < tomorrow
        )
    )).first()

    today_opps = (await db.execute(
        select(func.count(Opportunity.id)).where(
            Opportunity.deleted_at.is_(None), Opportunity.created_at >= today, Opportunity.created_at < tomorrow
        )
    )).scalar() or 0

    active_opps = (await db.execute(
        select(func.count(Opportunity.id)).where(
            Opportunity.deleted_at.is_(None), Opportunity.stage.notin_(["won", "lost"])
        )
    )).scalar() or 0

    won_opps = (await db.execute(
        select(func.coalesce(func.sum(Opportunity.amount), 0)).where(
            Opportunity.deleted_at.is_(None), Opportunity.stage == "won"
        )
    )).scalar() or 0

    total_customers = (await db.execute(
        select(func.count(Customer.id)).where(Customer.deleted_at.is_(None))
    )).scalar() or 0

    result = ok({
        "today_orders": today_orders[0] or 0,
        "today_order_amount": float(today_orders[1]),
        "today_opportunities": today_opps,
        "active_opportunities": active_opps,
        "won_amount": float(won_opps),
        "total_customers": total_customers,
    })
    _cache[cache_key] = (time.time() + DASHBOARD_TTL, result)
    return result


@router.get("/realtime")
async def get_dashboard_realtime(db: AsyncSession = Depends(get_db), _user: dict = Depends(get_current_user)):
    cache_key = "dashboard:realtime"
    hit, cached = _cached(cache_key)
    if hit:
        return cached

    # Order status distribution
    order_status = (await db.execute(
        select(SalesOrder.status, func.count(SalesOrder.id), func.coalesce(func.sum(SalesOrder.total_amount), 0)).where(
            SalesOrder.deleted_at.is_(None)
        ).group_by(SalesOrder.status)
    )).all()

    # Top customers by order amount
    top_customers = (await db.execute(
        select(Customer.name, func.coalesce(func.sum(SalesOrder.total_amount), 0)).select_from(SalesOrder).join(
            Customer, SalesOrder.customer_id == Customer.id
        ).where(
            SalesOrder.deleted_at.is_(None), Customer.deleted_at.is_(None)
        ).group_by(Customer.name).order_by(func.sum(SalesOrder.total_amount).desc()).limit(10)
    )).all()

    # Top products by order count
    top_products = (await db.execute(
        select(Product.name, func.count(SalesOrderItem.id)).select_from(SalesOrder).join(
            SalesOrderItem, SalesOrder.id == SalesOrderItem.order_id
        ).join(
            Product, SalesOrderItem.product_id == Product.id
        ).where(SalesOrder.deleted_at.is_(None)).group_by(Product.name).order_by(func.count(SalesOrderItem.id).desc()).limit(10)
    )).all()

    result = ok({
        "order_status": [{"status": r[0], "count": r[1], "amount": float(r[2])} for r in order_status],
        "top_customers": [{"name": r[0], "amount": float(r[1])} for r in top_customers],
        "top_products": [{"name": r[0], "count": r[1]} for r in top_products],
    })
    _cache[cache_key] = (time.time() + DASHBOARD_TTL, result)
    return result
