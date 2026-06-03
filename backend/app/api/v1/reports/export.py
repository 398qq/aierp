"""Reports API — export bounded context.

Heavy read-only endpoints that stream data (CSV). Per-call cost is
dominated by the streaming serialization, not the DB scan, so they
are NOT cached.
"""

import io
import logging
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.permissions import require_perm
from app.database import date_format, get_db
from app.models.sales import SalesOrder

logger = logging.getLogger(__name__)

router = APIRouter(tags=["report:export"])


@router.post("/export/sales")
async def export_sales_excel(
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(require_perm("reports", "read")),
):
    """Export monthly sales data as CSV."""
    cutoff = datetime.now(timezone.utc) - timedelta(days=365)

    exp_month = date_format(SalesOrder.created_at, "YYYY-MM")
    orders = (await db.execute(
        select(
            exp_month.label("month"),
            func.count(SalesOrder.id),
            func.coalesce(func.sum(SalesOrder.total_amount), 0),
        ).where(
            SalesOrder.deleted_at.is_(None),
            SalesOrder.created_at >= cutoff,
        ).group_by(exp_month).order_by(exp_month)
    )).all()

    csv = "月份,订单数,金额\n" + "\n".join(
        f"{m},{c},{float(a):.2f}" for m, c, a in orders
    )
    return StreamingResponse(
        io.BytesIO(csv.encode("utf-8-sig")),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=sales_report_{datetime.now().strftime('%Y%m%d')}.csv"},
    )
