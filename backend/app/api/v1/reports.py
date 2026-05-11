"""Reports — templates, execution, predefined reports, export."""

import datetime
import io

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.permissions import require_perm, write_audit_log
from app.database import get_db
from app.models.customer import Customer
from app.models.finance import Invoice, PaymentRecord
from app.models.product import Inventory, Product
from app.models.report import ReportTemplate
from app.models.sales import Quotation, SalesOrder, SalesOrderItem
from app.models.transaction import PurchaseOrder
from app.schemas.common import fail, ok, paginated_ok

router = APIRouter(prefix="/reports", tags=["reports"])


# ---------------------------------------------------------------------------
# Templates
# ---------------------------------------------------------------------------
@router.get("/templates")
async def list_templates(
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(require_perm("reports", "read")),
):
    result = await db.execute(
        select(ReportTemplate).where(
            ReportTemplate.deleted_at.is_(None),
        ).order_by(ReportTemplate.id.desc())
    )
    temps = result.scalars().all()
    return ok([{
        "id": t.id, "name": t.name, "type": t.type, "config": t.config,
        "is_public": t.is_public, "created_by": t.created_by,
        "created_at": str(t.created_at),
    } for t in temps])


class TemplateCreate(BaseModel):
    name: str
    type: str
    config: dict = {}
    is_public: bool = False


@router.post("/templates", status_code=201)
async def create_template(
    body: TemplateCreate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_perm("reports", "write")),
):
    t = ReportTemplate(
        name=body.name, type=body.type, config=body.config,
        created_by=current_user["user_id"], is_public=body.is_public,
    )
    db.add(t)
    await db.commit()
    return ok({"id": t.id}, msg="模板创建成功")


@router.put("/templates/{template_id}")
async def update_template(template_id: int, body: TemplateCreate,
                          db: AsyncSession = Depends(get_db),
                          _user: dict = Depends(require_perm("reports", "write"))):
    t = (await db.execute(
        select(ReportTemplate).where(ReportTemplate.id == template_id, ReportTemplate.deleted_at.is_(None))
    )).scalar_one_or_none()
    if not t:
        return fail("模板不存在")
    t.name = body.name
    t.type = body.type
    t.config = body.config
    t.is_public = body.is_public
    await db.commit()
    return ok(msg="模板更新成功")


@router.delete("/templates/{template_id}")
async def delete_template(template_id: int,
                          db: AsyncSession = Depends(get_db),
                          _user: dict = Depends(require_perm("reports", "write"))):
    t = (await db.execute(
        select(ReportTemplate).where(ReportTemplate.id == template_id, ReportTemplate.deleted_at.is_(None))
    )).scalar_one_or_none()
    if not t:
        return fail("模板不存在")
    t.deleted_at = datetime.datetime.now(datetime.timezone.utc)
    await db.commit()
    return ok(msg="模板已删除")


# ---------------------------------------------------------------------------
# Predefined Reports
# ---------------------------------------------------------------------------
@router.get("/predefined/sales")
async def sales_report(
    months: int = Query(12, ge=1, le=36),
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(require_perm("reports", "read")),
):
    """Sales analysis — monthly quotation/order/delivery counts and amounts."""
    from datetime import datetime, timedelta, timezone
    cutoff = datetime.now(timezone.utc) - timedelta(days=months * 30)

    so_month = func.to_char(SalesOrder.created_at, "YYYY-MM")
    orders = (await db.execute(
        select(
            so_month.label("month"),
            func.count(SalesOrder.id),
            func.coalesce(func.sum(SalesOrder.total_amount), 0),
        ).where(
            SalesOrder.deleted_at.is_(None),
            SalesOrder.created_at >= cutoff,
        ).group_by(so_month).order_by(so_month)
    )).all()

    q_month = func.to_char(Quotation.created_at, "YYYY-MM")
    quotes = (await db.execute(
        select(
            q_month.label("month"),
            func.count(Quotation.id),
            func.coalesce(func.sum(Quotation.total_amount), 0),
        ).where(
            Quotation.deleted_at.is_(None),
            Quotation.created_at >= cutoff,
        ).group_by(q_month).order_by(q_month)
    )).all()

    # Top products by order count
    top_products = (await db.execute(
        select(Product.name, Product.sku, func.count(SalesOrder.id).label("cnt"))
        .select_from(SalesOrder)
        .join(SalesOrderItem, SalesOrder.id == SalesOrderItem.order_id)
        .join(Product, SalesOrderItem.product_id == Product.id)
        .where(SalesOrder.deleted_at.is_(None))
        .group_by(Product.id, Product.name, Product.sku)
        .order_by(func.count(SalesOrder.id).desc()).limit(10)
    )).all()

    return ok({
        "monthly_orders": [{"month": m, "count": c, "amount": float(a)} for m, c, a in orders],
        "monthly_quotations": [{"month": m, "count": c, "amount": float(a)} for m, c, a in quotes],
        "top_products": [{"name": n, "sku": s, "order_count": c} for n, s, c in top_products],
    })


@router.get("/predefined/ar")
async def ar_report(
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(require_perm("reports", "read")),
):
    """Accounts Receivable aging report."""
    from datetime import datetime, timezone
    now = datetime.now(timezone.utc)

    # Outstanding invoices
    invoices = (await db.execute(
        select(Invoice, Customer.name, Customer.code)
        .join(Customer, Invoice.customer_id == Customer.id)
        .where(
            Invoice.deleted_at.is_(None),
            Customer.deleted_at.is_(None),
            Invoice.status.in_(["sent", "overdue", "partial"]),
        )
    )).all()

    aging = {"current": [], "1_30": [], "31_60": [], "61_90": [], "over_90": []}
    total_ar = 0.0

    for inv, cust_name, cust_code in invoices:
        age_days = (now - inv.created_at).days if inv.created_at else 0
        amount = float(inv.amount)
        total_ar += amount
        entry = {"invoice_id": inv.id, "invoice_no": inv.invoice_no, "customer": cust_name,
                 "customer_code": cust_code, "amount": amount, "age_days": age_days,
                 "status": inv.status, "invoice_date": str(inv.invoice_date) if inv.invoice_date else None}

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

    return ok({
        "total_ar": total_ar,
        "aging": {
            "current": {"count": len(aging["current"]), "amount": sum(e["amount"] for e in aging["current"])},
            "1_30": {"count": len(aging["1_30"]), "amount": sum(e["amount"] for e in aging["1_30"])},
            "31_60": {"count": len(aging["31_60"]), "amount": sum(e["amount"] for e in aging["31_60"])},
            "61_90": {"count": len(aging["61_90"]), "amount": sum(e["amount"] for e in aging["61_90"])},
            "over_90": {"count": len(aging["over_90"]), "amount": sum(e["amount"] for e in aging["over_90"])},
        },
        "details": aging,
    })


@router.get("/predefined/inventory")
async def inventory_report(
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(require_perm("reports", "read")),
):
    """Inventory turnover and stock health report."""
    # Products with highest/lowest stock
    stock_levels = (await db.execute(
        select(
            Product.name, Product.sku,
            func.coalesce(func.sum(Inventory.quantity), 0).label("total_qty"),
            func.coalesce(func.sum(Inventory.safety_stock), 0).label("total_safety"),
        ).join(Inventory, Product.id == Inventory.product_id)
        .where(Product.deleted_at.is_(None), Inventory.deleted_at.is_(None))
        .group_by(Product.id, Product.name, Product.sku)
    )).all()

    # Build summary
    total_products = len(stock_levels)
    low_stock = sum(1 for _, _, qty, safety in stock_levels if qty <= safety and safety > 0)
    out_of_stock = sum(1 for _, _, qty, _ in stock_levels if qty <= 0)
    total_inventory_value = 0.0

    items = []
    for name, sku, qty, safety in stock_levels:
        status = "正常"
        if qty <= 0:
            status = "缺货"
        elif safety > 0 and qty <= safety:
            status = "低库存"
        items.append({"name": name, "sku": sku, "quantity": int(qty),
                       "safety_stock": int(safety), "status": status})

    items.sort(key=lambda x: x["quantity"])

    return ok({
        "summary": {"total_products": total_products, "low_stock": low_stock,
                     "out_of_stock": out_of_stock},
        "items": items,
    })


@router.get("/predefined/procurement")
async def procurement_report(
    months: int = Query(12, ge=1, le=36),
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(require_perm("reports", "read")),
):
    """Procurement analysis report."""
    from datetime import datetime, timedelta, timezone
    cutoff = datetime.now(timezone.utc) - timedelta(days=months * 30)

    # Monthly procurement
    po_month = func.to_char(PurchaseOrder.created_at, "YYYY-MM")
    monthly = (await db.execute(
        select(
            po_month.label("month"),
            func.count(PurchaseOrder.id),
            func.coalesce(func.sum(PurchaseOrder.total_amount), 0),
        ).where(
            PurchaseOrder.deleted_at.is_(None),
            PurchaseOrder.created_at >= cutoff,
        ).group_by(po_month).order_by(po_month)
    )).all()

    # PO status summary
    status_summary = (await db.execute(
        select(PurchaseOrder.status, func.count(PurchaseOrder.id))
        .where(PurchaseOrder.deleted_at.is_(None))
        .group_by(PurchaseOrder.status)
    )).all()

    return ok({
        "monthly": [{"month": m, "count": c, "amount": float(a)} for m, c, a in monthly],
        "status_summary": [{"status": s, "count": c} for s, c in status_summary],
    })


# ---------------------------------------------------------------------------
# Export
# ---------------------------------------------------------------------------
@router.post("/export/sales")
async def export_sales_excel(
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(require_perm("reports", "read")),
):
    """Export monthly sales data as CSV."""
    from datetime import datetime, timedelta, timezone
    cutoff = datetime.now(timezone.utc) - timedelta(days=365)

    exp_month = func.to_char(SalesOrder.created_at, "YYYY-MM")
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
