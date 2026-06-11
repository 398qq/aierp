"""AI-powered procurement intelligence endpoints."""

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.permissions import require_perm
from app.database import date_format, get_db
from app.models.product import Inventory, Product, Supplier, SupplierProduct
from app.models.transaction import PurchaseOrder
from app.schemas.common import ok

router = APIRouter(prefix="/ai/procurement", tags=["procurement-ai"])


@router.get("/restock-suggest")
async def restock_suggest(
    warehouse_id: int | None = None,
    top_k: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(require_perm("purchases", "read")),
):
    """Scan inventory below safety stock and suggest restock quantities."""
    q = (
        select(
            Inventory,
            Product.name,
            Product.sku,
        )
        .join(Product, Inventory.product_id == Product.id)
        .where(
            Inventory.deleted_at.is_(None),
            Product.deleted_at.is_(None),
            Inventory.quantity <= Inventory.safety_stock,
            Inventory.safety_stock > 0,
        )
    )
    if warehouse_id:
        q = q.where(Inventory.warehouse_id == warehouse_id)
    q = q.order_by((Inventory.safety_stock - Inventory.quantity).desc()).limit(top_k)

    result = await db.execute(q)
    rows = result.all()
    suggestions = []
    for inv, prod_name, sku in rows:
        gap = max(0, (inv.safety_stock or 0) - (inv.quantity or 0))
        # Find best supplier
        sp = (
            await db.execute(
                select(SupplierProduct, Supplier.name)
                .join(Supplier, SupplierProduct.supplier_id == Supplier.id)
                .where(
                    SupplierProduct.product_id == inv.product_id,
                    SupplierProduct.deleted_at.is_(None),
                    Supplier.deleted_at.is_(None),
                )
                .order_by(SupplierProduct.cost_price.asc().nulls_last())
                .limit(1)
            )
        ).first()

        suggestions.append(
            {
                "product_id": inv.product_id,
                "product_name": prod_name,
                "sku": sku,
                "warehouse_id": inv.warehouse_id,
                "current_qty": inv.quantity,
                "safety_stock": inv.safety_stock,
                "gap": gap,
                "suggested_order": max(
                    gap, int(inv.safety_stock * 0.5) if inv.safety_stock else 10
                ),
                "best_supplier": {
                    "id": sp[0].supplier_id,
                    "name": sp[1],
                    "cost_price": float(sp[0].cost_price or 0),
                }
                if sp
                else None,
            }
        )
    return ok({"suggestions": suggestions, "total": len(suggestions)})


@router.get("/supplier-recommend")
async def supplier_recommend(
    product_ids: str = Query(""),  # comma-separated
    quantity: int = 1,
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(require_perm("purchases", "read")),
):
    """Recommend best supplier for given products."""
    ids = [int(x) for x in product_ids.split(",") if x.strip().isdigit()]
    if not ids:
        return ok({"recommendations": []})

    recommendations = []
    for pid in ids:
        product = (
            await db.execute(
                select(Product.name, Product.sku).where(
                    Product.id == pid, Product.deleted_at.is_(None)
                )
            )
        ).first()
        if not product:
            continue

        suppliers = (
            await db.execute(
                select(SupplierProduct, Supplier)
                .join(Supplier, SupplierProduct.supplier_id == Supplier.id)
                .where(
                    SupplierProduct.product_id == pid,
                    SupplierProduct.deleted_at.is_(None),
                    Supplier.deleted_at.is_(None),
                )
            )
        ).all()

        options = []
        for sp, sup in suppliers:
            score = 0
            if sp.cost_price and sp.cost_price > 0:
                score += 30
            if sp.lead_time_days and sp.lead_time_days <= 7:
                score += 20
            elif sp.lead_time_days and sp.lead_time_days <= 14:
                score += 10
            if sp.is_preferred:
                score += 25
            if sp.moq and sp.moq <= quantity:
                score += 15
            RATING_ORDER = ["D", "C", "B", "A", "AAA"]
            sup_rating = sup.financial_rating.upper() if sup.financial_rating else None
            if (
                sup_rating
                and sup_rating in RATING_ORDER
                and RATING_ORDER.index(sup_rating) >= RATING_ORDER.index("B")
            ):
                score += 10
            options.append(
                {
                    "supplier_id": sup.id,
                    "supplier_name": sup.name,
                    "cost_price": float(sp.cost_price) if sp.cost_price else None,
                    "lead_time_days": sp.lead_time_days,
                    "moq": sp.moq,
                    "is_preferred": sp.is_preferred,
                    "score": score,
                }
            )

        options.sort(key=lambda x: x["score"], reverse=True)
        recommendations.append(
            {
                "product_id": pid,
                "product_name": product[0],
                "sku": product[1],
                "options": options[:5],
            }
        )

    return ok({"recommendations": recommendations})


@router.get("/dashboard")
async def procurement_dashboard(
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(require_perm("purchases", "read")),
):
    """Procurement dashboard overview."""
    # PO status distribution
    po_status = (
        await db.execute(
            select(PurchaseOrder.status, func.count(PurchaseOrder.id))
            .where(PurchaseOrder.deleted_at.is_(None))
            .group_by(PurchaseOrder.status)
        )
    ).all()

    # Monthly purchase amount (last 12 months)
    from datetime import datetime, timedelta, timezone

    year_ago = datetime.now(timezone.utc) - timedelta(days=365)
    to_char_expr = date_format(PurchaseOrder.created_at, "YYYY-MM")
    monthly = (
        await db.execute(
            select(
                to_char_expr.label("month"),
                func.count(PurchaseOrder.id),
                func.coalesce(func.sum(PurchaseOrder.total_amount), 0),
            )
            .where(
                PurchaseOrder.deleted_at.is_(None),
                PurchaseOrder.created_at >= year_ago,
            )
            .group_by(to_char_expr)
            .order_by(to_char_expr)
        )
    ).all()

    # Total stats
    total_po = sum(c for _, c in po_status)
    total_amount = (
        await db.execute(
            select(func.coalesce(func.sum(PurchaseOrder.total_amount), 0)).where(
                PurchaseOrder.deleted_at.is_(None)
            )
        )
    ).scalar() or 0

    # Supplier on-time delivery rate (last 90 days)
    d90 = datetime.now(timezone.utc) - timedelta(days=90)
    # Count POs received late vs on time
    late_pos = (
        await db.execute(
            select(func.count(PurchaseOrder.id)).where(
                PurchaseOrder.deleted_at.is_(None),
                PurchaseOrder.status.in_(["received", "completed"]),
                PurchaseOrder.updated_at >= d90,
                PurchaseOrder.expected_date.isnot(None),
                PurchaseOrder.updated_at > PurchaseOrder.expected_date,
            )
        )
    ).scalar() or 0
    ontime_pos = (
        await db.execute(
            select(func.count(PurchaseOrder.id)).where(
                PurchaseOrder.deleted_at.is_(None),
                PurchaseOrder.status.in_(["received", "completed"]),
                PurchaseOrder.updated_at >= d90,
                PurchaseOrder.expected_date.isnot(None),
                PurchaseOrder.updated_at <= PurchaseOrder.expected_date,
            )
        )
    ).scalar() or 0
    total_delivered = late_pos + ontime_pos
    ontime_rate = (
        round(ontime_pos / total_delivered * 100, 1) if total_delivered > 0 else 0
    )

    return ok(
        {
            "total_po": total_po,
            "total_amount": float(total_amount),
            "status_distribution": [{"status": s, "count": c} for s, c in po_status],
            "monthly_trend": [
                {"month": m, "count": c, "amount": float(a)} for m, c, a in monthly
            ],
            "on_time_delivery": {
                "rate": ontime_rate,
                "on_time": ontime_pos,
                "late": late_pos,
            },
        }
    )


@router.get("/po-calendar")
async def po_calendar(
    days: int = Query(30, ge=1, le=90),
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(require_perm("purchases", "read")),
):
    """Expected arrival calendar for POs."""
    from datetime import datetime, timedelta, timezone

    end = datetime.now(timezone.utc) + timedelta(days=days)

    pos = (
        (
            await db.execute(
                select(PurchaseOrder)
                .where(
                    PurchaseOrder.deleted_at.is_(None),
                    PurchaseOrder.status.in_(["approved", "in_transit", "partial"]),
                    PurchaseOrder.expected_date.isnot(None),
                    PurchaseOrder.expected_date >= datetime.now(timezone.utc),
                    PurchaseOrder.expected_date <= end,
                )
                .order_by(PurchaseOrder.expected_date)
            )
        )
        .scalars()
        .all()
    )

    return ok(
        [
            {
                "id": po.id,
                "order_no": po.order_no,
                "supplier_id": po.supplier_id,
                "total_amount": float(po.total_amount),
                "status": po.status,
                "expected_date": str(po.expected_date) if po.expected_date else None,
            }
            for po in pos
        ]
    )
