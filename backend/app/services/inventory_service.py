"""Inventory intelligence — predictive restock, dead stock detection, shortage matching."""

import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.product import Brand, Inventory, InventoryTransaction, Product
from app.models.sales import SalesOrder, SalesOrderItem

logger = logging.getLogger(__name__)


async def get_inventory_overview(db: AsyncSession) -> dict:
    """High-level inventory summary with AI context."""
    total_qty = (await db.execute(
        select(func.coalesce(func.sum(Inventory.quantity), 0))
        .where(Inventory.deleted_at.is_(None))
    )).scalar() or 0

    low_stock_count = (await db.execute(
        select(func.count(Inventory.id)).where(
            Inventory.deleted_at.is_(None),
            Inventory.quantity <= Inventory.safety_stock,
        )
    )).scalar() or 0

    dead_stock = await _detect_dead_stock(db)
    restock = await _predict_restock(db)

    return {
        "total_quantity": total_qty,
        "low_stock_items": low_stock_count,
        "dead_stock_items": len(dead_stock),
        "dead_stock": dead_stock[:10],
        "restock_suggestions": restock[:10],
    }


async def _detect_dead_stock(db: AsyncSession, days_threshold: int = 180) -> list[dict]:
    """Find items with no sales in the past N days."""
    threshold_date = datetime.now(timezone.utc) - timedelta(days=days_threshold)

    # Products with stock but no recent sales
    result = await db.execute(
        select(
            Product.id, Product.sku, Product.name, Product.category,
            Inventory.quantity, Inventory.warehouse_id,
        )
        .join(Inventory, Product.id == Inventory.product_id)
        .where(
            Inventory.deleted_at.is_(None),
            Product.deleted_at.is_(None),
            Inventory.quantity > 0,
            ~Product.id.in_(
                select(SalesOrderItem.product_id).join(
                    SalesOrder, SalesOrderItem.order_id == SalesOrder.id
                ).where(
                    SalesOrder.created_at >= threshold_date,
                    SalesOrder.deleted_at.is_(None),
                    SalesOrderItem.deleted_at.is_(None),
                )
            ),
        )
        .order_by(Inventory.quantity.desc())
        .limit(30)
    )
    rows = result.all()
    return [
        {
            "product_id": r[0], "sku": r[1], "name": r[2], "category": r[3],
            "quantity": r[4], "warehouse_id": r[5],
            "days_untouched": days_threshold,
            "suggestion": "建议促销或联系供应商退货",
        }
        for r in rows
    ]


async def _predict_restock(db: AsyncSession) -> list[dict]:
    """Predict restock needs based on recent sales velocity."""
    now = datetime.now(timezone.utc)
    d90 = now - timedelta(days=90)

    # Sales velocity for each product in last 90 days
    result = await db.execute(
        select(
            Product.id, Product.sku, Product.name, Product.category,
            func.coalesce(func.sum(SalesOrderItem.quantity), 0).label("sold_qty"),
            Inventory.quantity,
            Inventory.safety_stock,
        )
        .join(SalesOrderItem, Product.id == SalesOrderItem.product_id)
        .join(SalesOrder, SalesOrderItem.order_id == SalesOrder.id)
        .outerjoin(Inventory, Product.id == Inventory.product_id)
        .where(
            SalesOrder.created_at >= d90,
            SalesOrder.deleted_at.is_(None),
            SalesOrderItem.deleted_at.is_(None),
            Product.deleted_at.is_(None),
        )
        .group_by(Product.id, Inventory.quantity, Inventory.safety_stock)
        .having(func.coalesce(func.sum(SalesOrderItem.quantity), 0) > 0)
    )
    rows = result.all()

    suggestions = []
    for r in rows:
        sold_90d = r[4] or 0
        current_qty = r[5] or 0
        safety = r[6] or 0
        monthly_rate = sold_90d / 3  # per month

        if monthly_rate <= 0:
            continue

        months_remaining = current_qty / monthly_rate if monthly_rate > 0 else 999
        target_qty = max(safety, int(monthly_rate * 3))  # 3 months coverage

        if current_qty < target_qty and months_remaining < 3:
            suggestions.append({
                "product_id": r[0], "sku": r[1], "name": r[2], "category": r[3],
                "sold_90d": sold_90d, "current_qty": current_qty,
                "safety_stock": safety, "monthly_rate": round(monthly_rate, 1),
                "months_remaining": round(months_remaining, 1),
                "suggested_order": target_qty - current_qty,
                "urgency": "紧急" if months_remaining < 1 else "建议" if months_remaining < 2 else "计划",
            })

    suggestions.sort(key=lambda x: x["months_remaining"])
    return suggestions


async def adjust_inventory(
    db: AsyncSession,
    product_id: int,
    warehouse_id: int,
    adjustment: int,
    reason: str = "manual",
) -> dict:
    """Adjust inventory quantity and log the transaction."""
    result = await db.execute(
        select(Inventory).where(
            Inventory.product_id == product_id,
            Inventory.warehouse_id == warehouse_id,
            Inventory.deleted_at.is_(None),
        )
    )
    inv = result.scalar_one_or_none()
    if inv is None:
        # Auto-create inventory record if needed
        inv = Inventory(product_id=product_id, warehouse_id=warehouse_id, quantity=0, safety_stock=0)
        db.add(inv)
        await db.flush()

    before = inv.quantity
    inv.quantity = max(0, inv.quantity + adjustment)
    after = inv.quantity

    txn = InventoryTransaction(
        product_id=product_id,
        warehouse_id=warehouse_id,
        type="adjust" if reason == "manual" else "stock_in" if adjustment > 0 else "stock_out",
        quantity=adjustment,
        before_qty=before,
        after_qty=after,
        reference_type=reason,
        notes=f"{reason}: {adjustment:+d}",
    )
    db.add(txn)
    await db.flush()

    return {
        "product_id": product_id, "warehouse_id": warehouse_id,
        "before": before, "after": after, "adjustment": adjustment,
        "transaction_id": txn.id,
    }


async def find_substitutes_for_stockout(
    db: AsyncSession,
    product_id: int,
    limit: int = 5,
) -> list[dict]:
    """Find in-stock similar products as substitutes for a low-stock item."""

    prod = (await db.execute(
        select(Product).where(Product.id == product_id, Product.deleted_at.is_(None))
    )).scalar_one_or_none()
    if prod is None or prod.embedding is None:
        return []

    result = await db.execute(
        select(
            Product.id, Product.sku, Product.name, Product.category,
            Product.package_type, Inventory.quantity, Brand.name,
            Product.embedding.cosine_distance(prod.embedding).label("distance"),
        )
        .join(Inventory, Product.id == Inventory.product_id)
        .outerjoin(Brand, Product.brand_id == Brand.id)
        .where(
            Inventory.deleted_at.is_(None),
            Product.deleted_at.is_(None),
            Product.id != product_id,
            Inventory.quantity > 0,
            Product.embedding.isnot(None),
        )
        .order_by(Product.embedding.cosine_distance(prod.embedding))
        .limit(limit)
    )
    rows = result.all()
    return [
        {
            "id": r[0], "sku": r[1], "name": r[2], "category": r[3],
            "package_type": r[4], "in_stock": r[5], "brand": r[6],
            "similarity": round(1 - float(r[7]), 4),
        }
        for r in rows
    ]
