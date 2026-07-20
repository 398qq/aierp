"""Finance accounts API — aggregation reports bounded context.

Routes:
- /reports/pnl  : monthly Profit & Loss statement (per-month cache key)
- /reports/ap   : Accounts Payable aging — outstanding POs (single global key)

Both endpoints run heavy multi-table aggregations; cache TTLs are long
(10 min) because stale data is acceptable for finance dashboards.
"""

import datetime
import json
import logging

from fastapi import APIRouter, Depends, Query
from fastapi.responses import JSONResponse
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.permissions import require_perm
from app.database import date_format, get_db
from app.models.account import Account, JournalEntry, JournalEntryLine
from app.schemas.common import ok
from app.api.v1.finance_accounts._shared import (
    AP_REPORT_CACHE_TTL,
    AP_REPORT_CACHE_VERSION,
    PNL_REPORT_CACHE_TTL,
    _pnl_cache_key,
)
from app.services.cache_service import (
    cache_get_versioned,
    cache_set_versioned,
)

logger = logging.getLogger(__name__)

router = APIRouter(tags=["finance-account:report"])


@router.get("/reports/pnl")
async def profit_and_loss(
    response: JSONResponse,
    month: str = Query(..., description="YYYY-MM"),
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(require_perm("reports", "read")),
):
    """Monthly Profit & Loss statement."""
    cache_key = _pnl_cache_key(month)
    cached_payload = await cache_get_versioned("finance:reports:pnl", cache_key)
    if cached_payload is not None:
        response.headers["X-Cache"] = "HIT"
        response.headers["X-Cache-Key"] = cache_key
        return ok(json.loads(cached_payload))
    response.headers["X-Cache"] = "MISS"
    month_expr = date_format(JournalEntry.entry_date, "YYYY-MM")

    lines = (
        await db.execute(
            select(
                Account.type,
                func.sum(JournalEntryLine.debit).label("debit"),
                func.sum(JournalEntryLine.credit).label("credit"),
            )
            .select_from(JournalEntryLine)
            .join(JournalEntry, JournalEntryLine.entry_id == JournalEntry.id)
            .join(Account, JournalEntryLine.account_id == Account.id)
            .where(
                JournalEntry.status == "posted",
                month_expr == month,
                JournalEntry.deleted_at.is_(None),
                JournalEntryLine.deleted_at.is_(None),
            )
            .group_by(Account.type)
        )
    ).all()

    totals = {
        row[0]: {"debit": float(row[1] or 0), "credit": float(row[2] or 0)}
        for row in lines
    }

    income = totals.get("income", {"debit": 0, "credit": 0})
    expense = totals.get("expense", {"debit": 0, "credit": 0})

    revenue = income["credit"] - income["debit"]
    cost = expense["debit"] - expense["credit"]
    net_profit = revenue - cost

    payload = {
        "month": month,
        "revenue": round(revenue, 2),
        "cost_of_goods": round(cost, 2),
        "gross_profit": round(revenue - cost, 2),
        "net_profit": round(net_profit, 2),
        "details": {
            k: {"debit": v["debit"], "credit": v["credit"]} for k, v in totals.items()
        },
    }
    await cache_set_versioned(
        "finance:reports:pnl",
        cache_key,
        json.dumps(payload, default=str),
        PNL_REPORT_CACHE_TTL,
    )
    return ok(payload)


@router.get("/reports/ap")
async def accounts_payable(
    response: JSONResponse,
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(require_perm("reports", "read")),
):
    """Accounts Payable aging — outstanding purchase orders."""
    cache_key = f"finance:reports:ap:{AP_REPORT_CACHE_VERSION}:global"
    cached_payload = await cache_get_versioned("finance:reports:ap", cache_key)
    if cached_payload is not None:
        response.headers["X-Cache"] = "HIT"
        response.headers["X-Cache-Key"] = cache_key
        return ok(json.loads(cached_payload))
    response.headers["X-Cache"] = "MISS"
    from app.models.transaction import PurchaseOrder
    from app.models.product import Supplier

    from app.domain.states import PURCHASE_ORDER_PAYABLE_STATUSES

    pos = (
        await db.execute(
            select(PurchaseOrder, Supplier.name)
            .join(Supplier, PurchaseOrder.supplier_id == Supplier.id)
            .where(
                PurchaseOrder.deleted_at.is_(None),
                PurchaseOrder.status.in_(PURCHASE_ORDER_PAYABLE_STATUSES),
            )
        )
    ).all()

    now = datetime.datetime.now(datetime.timezone.utc)
    items = []
    total_ap = 0.0
    for po, sup_name in pos:
        age_days = (now - po.created_at).days if po.created_at else 0
        total_ap += float(po.total_amount)
        items.append(
            {
                "po_id": po.id,
                "order_no": po.order_no,
                "supplier": sup_name,
                "amount": float(po.total_amount),
                "status": po.status,
                "age_days": age_days,
            }
        )

    payload = {"total_ap": round(total_ap, 2), "items": items}
    await cache_set_versioned(
        "finance:reports:ap",
        cache_key,
        json.dumps(payload, default=str),
        AP_REPORT_CACHE_TTL,
    )
    return ok(payload)
