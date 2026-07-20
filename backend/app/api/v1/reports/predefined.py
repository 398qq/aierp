"""Reports API — predefined analytics reports bounded context.

All four endpoints run heavy multi-table GROUP BY aggregations. They
are read-only and cached for 5-10 minutes; cache invalidation happens
on the upstream write paths (sales-order / invoice / inventory / PO).
"""

import json
import logging
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, Query
from fastapi.responses import JSONResponse
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.permissions import require_perm
from app.database import date_format, get_db
from app.models.customer import Customer
from app.models.finance import Invoice
from app.models.product import Inventory, Product
from app.models.sales import Quotation, SalesOrder, SalesOrderItem
from app.models.transaction import PurchaseOrder
from app.schemas.common import ok
from app.api.v1.reports._shared import (
    PREDEFINED_AR_CACHE_TTL,
    PREDEFINED_INVENTORY_CACHE_TTL,
    PREDEFINED_PROCUREMENT_CACHE_TTL,
    PREDEFINED_SALES_CACHE_TTL,
    _predefined_ar_cache_key,
    _predefined_inventory_cache_key,
    _predefined_procurement_cache_key,
    _predefined_sales_cache_key,
)
from app.services.cache_service import (
    cache_get_versioned,
    cache_set_versioned,
)

logger = logging.getLogger(__name__)

router = APIRouter(tags=["report:predefined"])


@router.get("/predefined/sales")
async def sales_report(
    response: JSONResponse,
    months: int = Query(12, ge=1, le=36),
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(require_perm("reports", "read")),
):
    """Sales analysis — monthly quotation/order/delivery counts and amounts."""
    cache_key = _predefined_sales_cache_key(months)
    cached_payload = await cache_get_versioned("reports:predefined:sales", cache_key)
    if cached_payload is not None:
        response.headers["X-Cache"] = "HIT"
        response.headers["X-Cache-Key"] = cache_key
        return ok(json.loads(cached_payload))
    response.headers["X-Cache"] = "MISS"
    cutoff = datetime.now(timezone.utc) - timedelta(days=months * 30)

    so_month = date_format(SalesOrder.created_at, "YYYY-MM")
    orders = (
        await db.execute(
            select(
                so_month.label("month"),
                func.count(SalesOrder.id),
                func.coalesce(func.sum(SalesOrder.total_amount), 0),
            )
            .where(
                SalesOrder.deleted_at.is_(None),
                SalesOrder.created_at >= cutoff,
            )
            .group_by(so_month)
            .order_by(so_month)
        )
    ).all()

    q_month = date_format(Quotation.created_at, "YYYY-MM")
    quotes = (
        await db.execute(
            select(
                q_month.label("month"),
                func.count(Quotation.id),
                func.coalesce(func.sum(Quotation.total_amount), 0),
            )
            .where(
                Quotation.deleted_at.is_(None),
                Quotation.created_at >= cutoff,
            )
            .group_by(q_month)
            .order_by(q_month)
        )
    ).all()

    top_products = (
        await db.execute(
            select(Product.name, Product.sku, func.count(SalesOrder.id).label("cnt"))
            .select_from(SalesOrder)
            .join(SalesOrderItem, SalesOrder.id == SalesOrderItem.order_id)
            .join(Product, SalesOrderItem.product_id == Product.id)
            .where(SalesOrder.deleted_at.is_(None))
            .group_by(Product.id, Product.name, Product.sku)
            .order_by(func.count(SalesOrder.id).desc())
            .limit(10)
        )
    ).all()

    payload = {
        "monthly_orders": [
            {"month": m, "count": c, "amount": float(a)} for m, c, a in orders
        ],
        "monthly_quotations": [
            {"month": m, "count": c, "amount": float(a)} for m, c, a in quotes
        ],
        "top_products": [
            {"name": n, "sku": s, "order_count": c} for n, s, c in top_products
        ],
    }
    await cache_set_versioned(
        "reports:predefined:sales",
        cache_key,
        json.dumps(payload, default=str),
        PREDEFINED_SALES_CACHE_TTL,
    )
    return ok(payload)


@router.get("/predefined/ar")
async def ar_report(
    response: JSONResponse,
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(require_perm("reports", "read")),
):
    """Accounts Receivable aging report."""
    cache_key = _predefined_ar_cache_key()
    cached_payload = await cache_get_versioned("reports:predefined:ar", cache_key)
    if cached_payload is not None:
        response.headers["X-Cache"] = "HIT"
        response.headers["X-Cache-Key"] = cache_key
        return ok(json.loads(cached_payload))
    response.headers["X-Cache"] = "MISS"
    now = datetime.now(timezone.utc)

    from app.domain.states import INVOICE_OUTSTANDING_STATUSES

    invoices = (
        await db.execute(
            select(Invoice, Customer.name, Customer.code)
            .join(Customer, Invoice.customer_id == Customer.id)
            .where(
                Invoice.deleted_at.is_(None),
                Customer.deleted_at.is_(None),
                Invoice.status.in_(INVOICE_OUTSTANDING_STATUSES),
            )
        )
    ).all()

    aging: dict[str, list[dict]] = {
        "current": [],
        "1_30": [],
        "31_60": [],
        "61_90": [],
        "over_90": [],
    }
    total_ar = 0.0

    for inv, cust_name, cust_code in invoices:
        age_days = (now - inv.created_at).days if inv.created_at else 0
        amount = float(inv.amount)
        total_ar += amount
        entry = {
            "invoice_id": inv.id,
            "invoice_no": inv.invoice_no,
            "customer": cust_name,
            "customer_code": cust_code,
            "amount": amount,
            "age_days": age_days,
            "status": inv.status,
            "invoice_date": str(inv.invoice_date) if inv.invoice_date else None,
        }

        if age_days <= 30:
            aging["current"].append(entry)
        elif age_days <= 60:
            aging["1_30"].append(entry)
        elif age_days <= 90:
            aging["31_60"].append(entry)
        elif age_days <= 120:
            aging["61_90"].append(entry)
        else:
            aging["over_90"].append(entry)

    payload = {
        "total_ar": total_ar,
        "aging": {
            "current": {
                "count": len(aging["current"]),
                "amount": sum(e["amount"] for e in aging["current"]),
            },
            "1_30": {
                "count": len(aging["1_30"]),
                "amount": sum(e["amount"] for e in aging["1_30"]),
            },
            "31_60": {
                "count": len(aging["31_60"]),
                "amount": sum(e["amount"] for e in aging["31_60"]),
            },
            "61_90": {
                "count": len(aging["61_90"]),
                "amount": sum(e["amount"] for e in aging["61_90"]),
            },
            "over_90": {
                "count": len(aging["over_90"]),
                "amount": sum(e["amount"] for e in aging["over_90"]),
            },
        },
        "details": aging,
    }
    await cache_set_versioned(
        "reports:predefined:ar",
        cache_key,
        json.dumps(payload, default=str),
        PREDEFINED_AR_CACHE_TTL,
    )
    return ok(payload)


@router.get("/predefined/inventory")
async def inventory_report(
    response: JSONResponse,
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(require_perm("reports", "read")),
):
    """Inventory turnover and stock health report."""
    cache_key = _predefined_inventory_cache_key()
    cached_payload = await cache_get_versioned(
        "reports:predefined:inventory", cache_key
    )
    if cached_payload is not None:
        response.headers["X-Cache"] = "HIT"
        response.headers["X-Cache-Key"] = cache_key
        return ok(json.loads(cached_payload))
    response.headers["X-Cache"] = "MISS"
    stock_levels = (
        await db.execute(
            select(
                Product.name,
                Product.sku,
                func.coalesce(func.sum(Inventory.quantity), 0).label("total_qty"),
                func.coalesce(func.sum(Inventory.safety_stock), 0).label(
                    "total_safety"
                ),
            )
            .join(Inventory, Product.id == Inventory.product_id)
            .where(Product.deleted_at.is_(None), Inventory.deleted_at.is_(None))
            .group_by(Product.id, Product.name, Product.sku)
        )
    ).all()

    total_products = len(stock_levels)
    low_stock = sum(
        1 for _, _, qty, safety in stock_levels if qty <= safety and safety > 0
    )
    out_of_stock = sum(1 for _, _, qty, _ in stock_levels if qty <= 0)

    items = []
    for name, sku, qty, safety in stock_levels:
        status = "正常"
        if qty <= 0:
            status = "缺货"
        elif safety > 0 and qty <= safety:
            status = "低库存"
        items.append(
            {
                "name": name,
                "sku": sku,
                "quantity": int(qty),
                "safety_stock": int(safety),
                "status": status,
            }
        )

    items.sort(key=lambda x: x["quantity"])

    payload = {
        "summary": {
            "total_products": total_products,
            "low_stock": low_stock,
            "out_of_stock": out_of_stock,
        },
        "items": items,
    }
    await cache_set_versioned(
        "reports:predefined:inventory",
        cache_key,
        json.dumps(payload, default=str),
        PREDEFINED_INVENTORY_CACHE_TTL,
    )
    return ok(payload)


@router.get("/predefined/procurement")
async def procurement_report(
    response: JSONResponse,
    months: int = Query(12, ge=1, le=36),
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(require_perm("reports", "read")),
):
    """Procurement analysis report."""
    cache_key = _predefined_procurement_cache_key(months)
    cached_payload = await cache_get_versioned(
        "reports:predefined:procurement", cache_key
    )
    if cached_payload is not None:
        response.headers["X-Cache"] = "HIT"
        response.headers["X-Cache-Key"] = cache_key
        return ok(json.loads(cached_payload))
    response.headers["X-Cache"] = "MISS"
    cutoff = datetime.now(timezone.utc) - timedelta(days=months * 30)

    po_month = date_format(PurchaseOrder.created_at, "YYYY-MM")
    monthly = (
        await db.execute(
            select(
                po_month.label("month"),
                func.count(PurchaseOrder.id),
                func.coalesce(func.sum(PurchaseOrder.total_amount), 0),
            )
            .where(
                PurchaseOrder.deleted_at.is_(None),
                PurchaseOrder.created_at >= cutoff,
            )
            .group_by(po_month)
            .order_by(po_month)
        )
    ).all()

    status_summary = (
        await db.execute(
            select(PurchaseOrder.status, func.count(PurchaseOrder.id))
            .where(PurchaseOrder.deleted_at.is_(None))
            .group_by(PurchaseOrder.status)
        )
    ).all()

    payload = {
        "monthly": [
            {"month": m, "count": c, "amount": float(a)} for m, c, a in monthly
        ],
        "status_summary": [{"status": s, "count": c} for s, c in status_summary],
    }
    await cache_set_versioned(
        "reports:predefined:procurement",
        cache_key,
        json.dumps(payload, default=str),
        PREDEFINED_PROCUREMENT_CACHE_TTL,
    )
    return ok(payload)
