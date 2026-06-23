"""Customers — list endpoint (paginated search).

Read path for the catalog/CRM list view. Heavy cache integration
(``_customers_cache_key``) and row serializer (``_customer_row``)
come from ``crud.py`` to share the lookup/serialization logic with
the create/update endpoints.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Query
from fastapi.responses import JSONResponse
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.customers.crud import (
    SORTABLE_COLUMNS,
    _customer_row,
    _customers_cache_key,
)
from app.core.permissions import require_perm
from app.database import get_db
from app.models.customer import Customer
from app.models.sales import SalesOrder
from app.schemas.common import ok
from app.services.cache_service import cache_get_versioned, cache_set_versioned

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/customers", tags=["customers"])

# Cache TTL for /customers list (5 minutes — list view tolerates slight staleness)
CUSTOMERS_LIST_CACHE_TTL = 300
# Cache key version — bump to invalidate all entries after schema change
CUSTOMERS_LIST_CACHE_VERSION = "v2"


@router.get("")
@router.get("/")
async def list_customers(
    response: JSONResponse,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_perm("customers", "read")),
    keyword: str | None = None,
    q: str | None = None,
    level: str | None = None,
    industry: str | None = None,
    region: str | None = None,
    source: str | None = None,
    credit_level: str | None = None,
    status: str | None = None,
    is_deleted: str | None = None,
    tag_ids: str | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=500),
    sort_by: str = "id",
    sort_order: str = "desc",
):
    cache_key = _customers_cache_key(
        keyword=keyword,
        q=q,
        level=level,
        industry=industry,
        region=region,
        source=source,
        credit_level=credit_level,
        status=status,
        is_deleted=is_deleted,
        tag_ids=tag_ids,
        page=page,
        page_size=page_size,
        sort_by=sort_by,
        sort_order=sort_order,
    )
    cached_payload = await cache_get_versioned("customers:list", cache_key)
    if cached_payload is not None:
        # Re-wrap the cached inner payload in the standard
        # {code, msg, data} envelope. The cache stores the raw
        # {"list":..., "total":...} dict for compactness; the non-cached
        # path returns ok(payload) which wraps it. The frontend reads
        # resp.data.data.list, so cache hits must return the same
        # wrapped shape. (Mirrors the fix in products/crud.py.)
        response.headers["X-Cache"] = "HIT"
        response.headers["X-Cache-Key"] = cache_key
        return JSONResponse(
            content=ok(json.loads(cached_payload)),
            headers={"X-Cache": "HIT", "X-Cache-Key": cache_key},
        )

    response.headers["X-Cache"] = "MISS"
    order_totals = (
        select(
            SalesOrder.customer_id.label("customer_id"),
            func.coalesce(func.sum(SalesOrder.total_amount), 0).label("total_amount"),
        )
        .where(SalesOrder.deleted_at.is_(None))
        .group_by(SalesOrder.customer_id)
        .subquery()
    )
    stmt = select(Customer, func.coalesce(order_totals.c.total_amount, 0)).outerjoin(
        order_totals, order_totals.c.customer_id == Customer.id
    )
    conditions = []
    _keyword = keyword or q
    if _keyword:
        conditions.append(
            or_(
                Customer.name.ilike(f"%{_keyword}%"),
                Customer.code.ilike(f"%{_keyword}%"),
                Customer.short_name.ilike(f"%{_keyword}%"),
                Customer.contact_person.ilike(f"%{_keyword}%"),
                Customer.phone.ilike(f"%{_keyword}%"),
                Customer.tax_id.ilike(f"%{_keyword}%"),
                Customer.email.ilike(f"%{_keyword}%"),
            )
        )
    if level:
        conditions.append(Customer.level == level)
    if industry:
        conditions.append(Customer.industry == industry)
    if region:
        conditions.append(Customer.region == region)
    if source:
        conditions.append(Customer.source == source)
    if credit_level:
        conditions.append(Customer.credit_level == credit_level)
    if status:
        statuses = [s.strip() for s in status.split(",") if s.strip()]
        if len(statuses) == 1:
            conditions.append(Customer.status == statuses[0])
        elif len(statuses) > 1:
            conditions.append(Customer.status.in_(statuses))
    if is_deleted == "true":
        conditions.append(Customer.deleted_at.isnot(None))
    elif is_deleted == "false" or is_deleted is None:
        conditions.append(Customer.deleted_at.is_(None))
    if tag_ids:
        tag_id_list = [int(t) for t in tag_ids.split(",") if t.isdigit()]
        if tag_id_list:
            from app.models.customer import customer_tag_table

            tag_filter = select(customer_tag_table.c.customer_id).where(
                customer_tag_table.c.tag_id.in_(tag_id_list)
            )
            conditions.append(Customer.id.in_(tag_filter))
    for c in conditions:
        stmt = stmt.where(c)
    sort_col = SORTABLE_COLUMNS.get(sort_by, Customer.id)
    if sort_order == "desc":
        stmt = stmt.order_by(sort_col.desc())
    else:
        stmt = stmt.order_by(sort_col.asc())
    count_stmt = select(func.count()).select_from(stmt.subquery())
    total_result = await db.execute(count_stmt)
    total = total_result.scalar() or 0
    stmt = stmt.offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(stmt)
    customer_rows = result.all()
    now = datetime.now(timezone.utc)
    rows = [
        _customer_row(customer, now=now, total_amount=total_amount)
        for customer, total_amount in customer_rows
    ]
    payload = {"list": rows, "total": total, "page": page, "page_size": page_size}
    await cache_set_versioned(
        "customers:list",
        cache_key,
        json.dumps(payload, default=str),
        CUSTOMERS_LIST_CACHE_TTL,
    )
    return ok(payload)


__all__ = ["router"]
