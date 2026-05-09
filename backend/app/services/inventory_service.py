"""Inventory intelligence — predictive restock, dead stock detection, shortage matching."""

import logging
from collections import defaultdict
from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.product import Brand, Inventory, InventoryTransaction, Product, SupplierProduct
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


async def _ensure_inventory(db: AsyncSession, product_id: int, warehouse_id: int) -> Inventory:
    """Get or create an inventory record."""
    result = await db.execute(
        select(Inventory).where(
            Inventory.product_id == product_id,
            Inventory.warehouse_id == warehouse_id,
            Inventory.deleted_at.is_(None),
        )
    )
    inv = result.scalar_one_or_none()
    if inv is None:
        inv = Inventory(product_id=product_id, warehouse_id=warehouse_id, quantity=0, safety_stock=0, locked_quantity=0)
        db.add(inv)
        await db.flush()
    return inv


async def receive_po_item(
    db: AsyncSession,
    product_id: int,
    warehouse_id: int,
    quantity: int,
    po_id: int,
) -> dict:
    """Auto-receive stock when a purchase order item is received."""
    inv = await _ensure_inventory(db, product_id, warehouse_id)
    before = inv.quantity
    inv.quantity += quantity
    after = inv.quantity

    txn = InventoryTransaction(
        product_id=product_id,
        warehouse_id=warehouse_id,
        type="stock_in",
        quantity=quantity,
        before_qty=before,
        after_qty=after,
        reference_type="purchase",
        reference_id=po_id,
        notes=f"采购入库: PO#{po_id} +{quantity}",
    )
    db.add(txn)
    await db.flush()
    return {"product_id": product_id, "before": before, "after": after, "transaction_id": txn.id}


async def deduct_for_delivery(
    db: AsyncSession,
    product_id: int,
    warehouse_id: int,
    quantity: int,
    delivery_id: int,
) -> dict:
    """Deduct stock (and release lock) when a delivery note item is shipped."""
    inv = await _ensure_inventory(db, product_id, warehouse_id)

    release_qty = min(quantity, inv.locked_quantity)
    if release_qty > 0:
        inv.locked_quantity -= release_qty

    before = inv.quantity
    inv.quantity = max(0, inv.quantity - quantity)
    after = inv.quantity

    txn = InventoryTransaction(
        product_id=product_id,
        warehouse_id=warehouse_id,
        type="stock_out",
        quantity=-quantity,
        before_qty=before,
        after_qty=after,
        reference_type="sales_delivery",
        reference_id=delivery_id,
        notes=f"销售出库: DN#{delivery_id} -{quantity}" + (f" (释放锁定{release_qty})" if release_qty > 0 else ""),
    )
    db.add(txn)
    await db.flush()
    return {"product_id": product_id, "before": before, "after": after, "transaction_id": txn.id}


async def lock_for_sales_order(
    db: AsyncSession,
    product_id: int,
    warehouse_id: int,
    quantity: int,
    order_id: int,
) -> dict:
    """Lock stock when a sales order is confirmed."""
    inv = await _ensure_inventory(db, product_id, warehouse_id)

    lockable = min(quantity, max(0, inv.quantity - inv.locked_quantity))
    if lockable > 0:
        inv.locked_quantity += lockable

    txn = InventoryTransaction(
        product_id=product_id,
        warehouse_id=warehouse_id,
        type="adjust",
        quantity=0,
        before_qty=inv.quantity,
        after_qty=inv.quantity,
        reference_type="sales_order_lock",
        reference_id=order_id,
        notes=f"订单锁定: SO#{order_id} 锁定{lockable}/{quantity}" + (" (部分锁定)" if lockable < quantity else ""),
    )
    db.add(txn)
    await db.flush()
    return {"product_id": product_id, "locked": lockable, "requested": quantity, "transaction_id": txn.id}


async def forecast_demand(db: AsyncSession, category: str | None = None, top_k: int = 20) -> list[dict]:
    """Enhanced demand forecasting with seasonality, trend, and lead-time detection.

    Returns list of dicts with monthly_forecast, trend, seasonal_factor, suggested_safety_stock, confidence.
    """
    now = datetime.now(timezone.utc)
    d365 = now - timedelta(days=365)
    d45 = now - timedelta(days=45)

    # Base query: products with sales history
    base_q = (
        select(
            Product.id, Product.sku, Product.name, Product.category,
            func.coalesce(func.sum(SalesOrderItem.quantity), 0).label("sold_365d"),
            func.coalesce(func.sum(SalesOrderItem.quantity * SalesOrderItem.unit_price), 0).label("revenue_365d"),
            func.max(SalesOrder.created_at).label("last_sold"),
        )
        .join(SalesOrderItem, Product.id == SalesOrderItem.product_id)
        .join(SalesOrder, SalesOrderItem.order_id == SalesOrder.id)
        .where(
            SalesOrder.created_at >= d365,
            SalesOrder.deleted_at.is_(None),
            SalesOrderItem.deleted_at.is_(None),
            Product.deleted_at.is_(None),
        )
        .group_by(Product.id)
    )
    if category:
        base_q = base_q.where(Product.category == category)

    base_q = base_q.order_by(func.sum(SalesOrderItem.quantity * SalesOrderItem.unit_price).desc()).limit(top_k)
    rows = (await db.execute(base_q)).all()

    results = []
    for r in rows:
        pid, sku, name, cat = r[0], r[1], r[2], r[3]
        sold_365 = r[4] or 0
        last_sold_str = str(r[6]) if r[6] else ""

        # Lead time from supplier linkage
        lead_time = (await db.execute(
            select(func.coalesce(func.min(SupplierProduct.lead_time_days), 21)).where(
                SupplierProduct.product_id == pid,
                SupplierProduct.deleted_at.is_(None),
            )
        )).scalar() or 21

        # Inventory on hand
        current_qty = (await db.execute(
            select(func.coalesce(func.sum(Inventory.quantity), 0)).where(
                Inventory.product_id == pid,
                Inventory.deleted_at.is_(None),
            )
        )).scalar() or 0

        safety_stock = (await db.execute(
            select(func.max(Inventory.safety_stock)).where(
                Inventory.product_id == pid,
                Inventory.deleted_at.is_(None),
            )
        )).scalar() or 0

        # Trend detection: compare first 45d vs last 45d velocity
        first_45d = (await db.execute(
            select(func.coalesce(func.sum(SalesOrderItem.quantity), 0)).select_from(SalesOrderItem)
            .join(SalesOrder, SalesOrderItem.order_id == SalesOrder.id)
            .where(
                SalesOrderItem.product_id == pid,
                SalesOrderItem.deleted_at.is_(None),
                SalesOrder.deleted_at.is_(None),
                SalesOrder.created_at.between(d365, d365 + timedelta(days=45)),
            )
        )).scalar() or 0

        last_45d = (await db.execute(
            select(func.coalesce(func.sum(SalesOrderItem.quantity), 0)).select_from(SalesOrderItem)
            .join(SalesOrder, SalesOrderItem.order_id == SalesOrder.id)
            .where(
                SalesOrderItem.product_id == pid,
                SalesOrderItem.deleted_at.is_(None),
                SalesOrder.deleted_at.is_(None),
                SalesOrder.created_at.between(d45, now),
            )
        )).scalar() or 0

        if first_45d > 0 and last_45d > 0:
            trend_direction = "上升" if last_45d > first_45d * 1.2 else "下降" if last_45d < first_45d * 0.8 else "持平"
            trend_score = round(last_45d / max(first_45d, 1), 2)
        elif last_45d > 0:
            trend_direction = "新增长"
            trend_score = 2.0
        elif sold_365 == 0:
            trend_direction = "无销售"
            trend_score = 0.0
        else:
            trend_direction = "衰退"
            trend_score = 0.3

        # Seasonality detection: monthly grouping over 12 months
        monthly_sales = defaultdict(float)
        monthly_q = (
            select(
                func.date_trunc("month", SalesOrder.created_at).label("month"),
                func.coalesce(func.sum(SalesOrderItem.quantity), 0),
            )
            .join(SalesOrderItem, SalesOrderItem.order_id == SalesOrder.id)
            .where(
                SalesOrderItem.product_id == pid,
                SalesOrderItem.deleted_at.is_(None),
                SalesOrder.deleted_at.is_(None),
                SalesOrder.created_at >= d365,
            )
            .group_by("month")
            .order_by("month")
        )
        month_rows = (await db.execute(monthly_q)).all()
        for mr in month_rows:
            monthly_sales[str(mr[0])] = float(mr[1])

        monthly_values = list(monthly_sales.values())
        if len(monthly_values) >= 6:
            avg_monthly = sum(monthly_values) / len(monthly_values)
            peak = max(monthly_values)
            min(monthly_values)
            seasonal_factor = round(peak / max(avg_monthly, 1), 2)  # > 1.5 = seasonal
        else:
            avg_monthly = sold_365 / max(len(monthly_values), 1)
            seasonal_factor = 1.0

        monthly_forecast = round(avg_monthly * trend_score if trend_score > 0 else avg_monthly, 1)

        # Suggested safety stock: base + lead time buffer + seasonal buffer
        lead_time_months = max(1, lead_time / 30.0)
        suggested_safety = round(monthly_forecast * lead_time_months * max(1, seasonal_factor), 0)

        results.append({
            "product_id": pid,
            "sku": sku or "",
            "name": name,
            "category": cat or "",
            "monthly_forecast": monthly_forecast,
            "trend": trend_direction,
            "trend_score": trend_score,
            "seasonal_factor": seasonal_factor,
            "suggested_safety_stock": int(suggested_safety),
            "current_safety_stock": int(safety_stock),
            "current_quantity": int(current_qty),
            "lead_time_days": lead_time,
            "confidence": "高" if len(monthly_values) >= 9 and trend_score >= 0.8 else "中" if len(monthly_values) >= 4 else "低",
            "last_sold": last_sold_str[:10] if last_sold_str else "",
            "monthly_history": {k[:10]: v for k, v in monthly_sales.items()},
        })

    results.sort(key=lambda x: x["monthly_forecast"], reverse=True)
    return results


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
