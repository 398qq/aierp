"""Products — read paths (list, stats, detail, sales).

Holds the catalog browse experience:
- /products                  — paginated list with filters & sort
- /products/stats/summary    — dashboard KPIs (in-stock, stale, etc.)
- /products/{id}             — single product detail
- /products/{id}/sales       — cross-document sales history

Write paths (create / update / delete / batch) live in ``crud.py``;
bulk price import lives in ``pricing.py``.
"""
from __future__ import annotations

import hashlib
import json
import logging
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, Query
from fastapi.responses import JSONResponse
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.database import get_db
from app.models.product import Brand, Inventory, Product, SupplierProduct
from app.schemas.common import fail, ok
from app.services.cache_service import cache_get_versioned, cache_set_versioned

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/products", tags=["products"])

# Cache TTL for /products list (5 minutes — list view tolerates slight staleness)
PRODUCTS_LIST_CACHE_TTL = 300
# Cache key version — bump to invalidate all entries after schema change
PRODUCTS_LIST_CACHE_VERSION = "v1"


def _inventory_metrics_subquery():
    available_expr = Inventory.quantity - func.coalesce(Inventory.locked_quantity, 0)
    return (
        select(
            Inventory.product_id.label("product_id"),
            func.count(Inventory.id).label("inventory_location_count"),
            func.coalesce(func.sum(Inventory.quantity), 0).label("quantity"),
            func.coalesce(func.sum(Inventory.locked_quantity), 0).label("locked_quantity"),
            func.coalesce(func.sum(available_expr), 0).label("available"),
            func.min(Inventory.safety_stock).label("safety_stock"),
            func.max(Inventory.unit_price).label("unit_price"),
            func.max(Inventory.updated_at).label("inventory_updated_at"),
        )
        .where(Inventory.deleted_at.is_(None))
        .group_by(Inventory.product_id)
        .subquery()
    )


def _supplier_metrics_subquery():
    return (
        select(
            SupplierProduct.product_id.label("product_id"),
            func.count(SupplierProduct.supplier_id).label("supplier_count"),
        )
        .where(SupplierProduct.deleted_at.is_(None))
        .group_by(SupplierProduct.product_id)
        .subquery()
    )


def _sales_metrics_subquery():
    from app.models.sales import SalesOrderItem

    return (
        select(
            SalesOrderItem.product_id.label("product_id"),
            func.max(SalesOrderItem.created_at).label("last_sale_at"),
        )
        .where(SalesOrderItem.deleted_at.is_(None), SalesOrderItem.product_id.is_not(None))
        .group_by(SalesOrderItem.product_id)
        .subquery()
    )


def _product_completion(p: Product) -> tuple[int, list[str]]:
    fields = [
        ("SKU", p.sku),
        ("品牌", p.brand_id),
        ("分类", p.category),
        ("封装", p.package_type),
        ("规格", p.specs),
        ("单位", p.unit),
    ]
    completed = sum(1 for _, value in fields if value not in (None, ""))
    missing = [label for label, value in fields if value in (None, "")]
    return round(completed / len(fields) * 100), missing


def _stock_status(available: int | None, safety_stock: int | None) -> str:
    available_qty = available or 0
    if available_qty <= 0:
        return "out_of_stock"
    if available_qty <= (safety_stock or 0):
        return "low_stock"
    return "in_stock"


def _product_row(
    p: Product,
    inventory_location_count: int | None = None,
    quantity: int | None = None,
    available: int | None = None,
    locked_quantity: int | None = None,
    safety_stock: int | None = None,
    unit_price: float | None = None,
    supplier_count: int | None = None,
    last_sale_at=None,
    inventory_updated_at=None,
) -> dict:
    completion_score, missing_fields = _product_completion(p)
    brand_name = None
    if p.brand:
        brand_name = p.brand.name or p.brand.short_name or p.brand.name_cn
    return {
        "id": p.id, "sku": p.sku, "name": p.name, "brand_id": p.brand_id,
        "brand_name": brand_name,
        "category": p.category, "package_type": p.package_type,
        "specs": p.specs, "unit": p.unit, "notes": p.notes,
        "image_url": p.image_url,
        "quantity": int(quantity or 0),
        "available": int(available or 0),
        "locked_quantity": int(locked_quantity or 0),
        "safety_stock": int(safety_stock) if safety_stock is not None else None,
        "unit_price": float(unit_price) if unit_price is not None else None,
        "stock_status": _stock_status(available, safety_stock),
        "inventory_location_count": int(inventory_location_count or 0),
        "supplier_count": int(supplier_count or 0),
        "completion_score": completion_score,
        "missing_fields": missing_fields,
        "last_sale_at": str(last_sale_at) if last_sale_at else None,
        "inventory_updated_at": str(inventory_updated_at) if inventory_updated_at else None,
        "created_at": str(p.created_at) if p.created_at else None,
    }


@router.get("/stats/summary")
async def products_stats_summary(
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(get_current_user),
):
    inv_subq = _inventory_metrics_subquery()
    sales_subq = _sales_metrics_subquery()

    base = (
        select(
            Product.id,
            Product.brand_id,
            Product.category,
            Product.package_type,
            Product.specs,
            Product.unit,
            inv_subq.c.available,
            inv_subq.c.safety_stock,
            sales_subq.c.last_sale_at,
        )
        .outerjoin(inv_subq, Product.id == inv_subq.c.product_id)
        .outerjoin(sales_subq, Product.id == sales_subq.c.product_id)
        .where(Product.deleted_at.is_(None))
        .subquery()
    )

    cutoff_30d = datetime.now(timezone.utc) - timedelta(days=30)

    total = (await db.execute(select(func.count()).select_from(base))).scalar() or 0
    in_stock_count = (await db.execute(
        select(func.count()).select_from(base).where(base.c.available > 0)
    )).scalar() or 0
    out_of_stock_count = (await db.execute(
        select(func.count()).select_from(base).where((base.c.available <= 0) | (base.c.available.is_(None)))
    )).scalar() or 0
    low_stock_count = (await db.execute(
        select(func.count()).select_from(base).where(
            base.c.available > 0,
            base.c.available <= func.coalesce(base.c.safety_stock, 0),
        )
    )).scalar() or 0
    pending_completion_count = (await db.execute(
        select(func.count()).select_from(base).where(
            or_(
                base.c.brand_id.is_(None),
                base.c.category.is_(None),
                base.c.category == "",
                base.c.package_type.is_(None),
                base.c.package_type == "",
                base.c.specs.is_(None),
                base.c.specs == "",
                base.c.unit.is_(None),
                base.c.unit == "",
            )
        )
    )).scalar() or 0
    stale_30d_count = (await db.execute(
        select(func.count()).select_from(base).where(
            (base.c.last_sale_at.is_(None)) | (base.c.last_sale_at < cutoff_30d)
        )
    )).scalar() or 0

    return ok({
        "total": total,
        "in_stock_count": in_stock_count,
        "out_of_stock_count": out_of_stock_count,
        "low_stock_count": low_stock_count,
        "pending_completion_count": pending_completion_count,
        "stale_30d_count": stale_30d_count,
        "generated_at": datetime.now(timezone.utc).isoformat(),
    })


@router.get("")
async def list_products(
    response: JSONResponse,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    q: str | None = None,
    category: str | None = None,
    brand_id: int | None = None,
    scene: str | None = Query(None, description="all | in_stock | out_of_stock | low_stock | pending_completion | stale_30d"),
    stock_status: str | None = Query(None, description="in_stock | out_of_stock | low_stock"),
    sort: str | None = Query(None, description="name_asc | name_desc | created_at_asc | created_at_desc"),
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(get_current_user),
):
    effective_stock_status = stock_status
    if not effective_stock_status and scene in {"in_stock", "out_of_stock", "low_stock"}:
        effective_stock_status = scene

    cache_key = _products_cache_key(
        page=page, page_size=page_size, q=q, category=category,
        brand_id=brand_id, scene=scene, stock_status=effective_stock_status,
        sort=sort,
    )
    cached_payload = await cache_get_versioned("products:list", cache_key)
    if cached_payload is not None:
        # Re-wrap the cached inner payload in the standard
        # {code, msg, data} envelope. The cache stores the raw
        # {"list":..., "total":...} dict (line ~436) for compactness;
        # the non-cached path returns ok(payload) which wraps it.
        # The frontend reads resp.data.data.list, so cache hits
        # must return the same wrapped shape.
        return JSONResponse(
            content=ok(json.loads(cached_payload)),
            headers={"X-Cache": "HIT", "X-Cache-Key": cache_key},
        )

    response.headers["X-Cache"] = "MISS"

    inv_subq = _inventory_metrics_subquery()
    sales_subq = _sales_metrics_subquery()
    supplier_subq = _supplier_metrics_subquery()

    base = (
        select(
            Product,
            inv_subq.c.inventory_location_count,
            inv_subq.c.quantity,
            inv_subq.c.available,
            inv_subq.c.locked_quantity,
            inv_subq.c.safety_stock,
            inv_subq.c.unit_price,
            inv_subq.c.inventory_updated_at,
            supplier_subq.c.supplier_count,
            sales_subq.c.last_sale_at,
        )
        .outerjoin(inv_subq, Product.id == inv_subq.c.product_id)
        .outerjoin(supplier_subq, Product.id == supplier_subq.c.product_id)
        .outerjoin(sales_subq, Product.id == sales_subq.c.product_id)
        .where(Product.deleted_at.is_(None))
    )

    if q:
        like = f"%{q}%"
        base = base.outerjoin(Brand, Product.brand_id == Brand.id).where(
            or_(
                Product.name.ilike(like),
                Product.sku.ilike(like),
                Product.category.ilike(like),
                Product.package_type.ilike(like),
                Product.specs.ilike(like),
                Brand.name.ilike(like),
                Brand.name_cn.ilike(like),
            )
        )
    if category:
        base = base.where(Product.category == category)
    if brand_id:
        base = base.where(Product.brand_id == brand_id)

    if effective_stock_status == "in_stock":
        base = base.where(inv_subq.c.available > 0)
    elif effective_stock_status == "out_of_stock":
        base = base.where((inv_subq.c.available <= 0) | (inv_subq.c.available.is_(None)))
    elif effective_stock_status == "low_stock":
        base = base.where(
            inv_subq.c.available > 0,
            inv_subq.c.available <= func.coalesce(inv_subq.c.safety_stock, 0),
        )

    if scene == "pending_completion":
        base = base.where(
            or_(
                Product.brand_id.is_(None),
                Product.category.is_(None),
                Product.category == "",
                Product.package_type.is_(None),
                Product.package_type == "",
                Product.specs.is_(None),
                Product.specs == "",
                Product.unit.is_(None),
                Product.unit == "",
            )
        )
    elif scene == "stale_30d":
        cutoff_30d = datetime.now(timezone.utc) - timedelta(days=30)
        base = base.where((sales_subq.c.last_sale_at.is_(None)) | (sales_subq.c.last_sale_at < cutoff_30d))

    if sort == "name_asc":
        order_col = Product.name.asc()
    elif sort == "name_desc":
        order_col = Product.name.desc()
    elif sort == "created_at_asc":
        order_col = Product.created_at.asc()
    else:
        order_col = Product.created_at.desc()

    total = (await db.execute(select(func.count()).select_from(base.subquery()))).scalar() or 0
    rows = (await db.execute(
        base.order_by(order_col, Product.id.desc()).offset((page - 1) * page_size).limit(page_size)
    )).all()

    items = [
        _product_row(
            p,
            inventory_location_count=inventory_location_count,
            quantity=quantity,
            available=available,
            locked_quantity=locked_quantity,
            safety_stock=safety_stock,
            unit_price=unit_price,
            supplier_count=supplier_count,
            last_sale_at=last_sale_at,
            inventory_updated_at=inventory_updated_at,
        )
        for (
            p,
            inventory_location_count,
            quantity,
            available,
            locked_quantity,
            safety_stock,
            unit_price,
            inventory_updated_at,
            supplier_count,
            last_sale_at,
        ) in rows
    ]
    payload = {"list": items, "total": total, "page": page, "page_size": page_size}
    await cache_set_versioned("products:list", cache_key, json.dumps(payload, default=str), PRODUCTS_LIST_CACHE_TTL)
    return ok(payload)


def _products_cache_key(**parts: object) -> str:
    """Stable cache key derived from all query parameters."""
    canonical = json.dumps(parts, sort_keys=True, default=str)
    digest = hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:16]
    return f"products:list:{PRODUCTS_LIST_CACHE_VERSION}:{digest}"


@router.get("/{product_id}")
async def get_product(product_id: int, db: AsyncSession = Depends(get_db), _user: dict = Depends(get_current_user)):
    inv_subq = _inventory_metrics_subquery()
    sales_subq = _sales_metrics_subquery()
    supplier_subq = _supplier_metrics_subquery()
    result = await db.execute(
        select(
            Product,
            inv_subq.c.inventory_location_count,
            inv_subq.c.quantity,
            inv_subq.c.available,
            inv_subq.c.locked_quantity,
            inv_subq.c.safety_stock,
            inv_subq.c.unit_price,
            inv_subq.c.inventory_updated_at,
            supplier_subq.c.supplier_count,
            sales_subq.c.last_sale_at,
        )
        .outerjoin(inv_subq, Product.id == inv_subq.c.product_id)
        .outerjoin(supplier_subq, Product.id == supplier_subq.c.product_id)
        .outerjoin(sales_subq, Product.id == sales_subq.c.product_id)
        .where(Product.id == product_id, Product.deleted_at.is_(None))
    )
    row = result.one_or_none()
    if row is None:
        return fail("Product not found", 404)
    (
        product,
        inventory_location_count,
        quantity,
        available,
        locked_quantity,
        safety_stock,
        unit_price,
        inventory_updated_at,
        supplier_count,
        last_sale_at,
    ) = row
    return ok(_product_row(
        product,
        inventory_location_count=inventory_location_count,
        quantity=quantity,
        available=available,
        locked_quantity=locked_quantity,
        safety_stock=safety_stock,
        unit_price=unit_price,
        supplier_count=supplier_count,
        last_sale_at=last_sale_at,
        inventory_updated_at=inventory_updated_at,
    ))


@router.get("/{product_id}/sales")
async def get_product_sales(product_id: int, db: AsyncSession = Depends(get_db), _user: dict = Depends(get_current_user)):
    from app.models.sales import Quotation, QuotationItem, SalesOrder, SalesOrderItem, DeliveryNote, DeliveryNoteItem

    qi_rows = (await db.execute(
        select(QuotationItem, Quotation).join(Quotation, QuotationItem.quotation_id == Quotation.id)
        .where(QuotationItem.product_id == product_id, Quotation.deleted_at.is_(None), QuotationItem.deleted_at.is_(None))
        .order_by(Quotation.id.desc()).limit(5)
    )).all()
    quotations = [{
        "id": q.id, "quotation_no": q.quotation_no, "customer_id": q.customer_id,
        "status": q.status, "total_amount": float(q.total_amount),
        "quantity": qi.quantity, "unit_price": float(qi.unit_price) if qi.unit_price else None,
        "created_at": str(q.created_at),
    } for qi, q in qi_rows]

    soi_rows = (await db.execute(
        select(SalesOrderItem, SalesOrder).join(SalesOrder, SalesOrderItem.order_id == SalesOrder.id)
        .where(SalesOrderItem.product_id == product_id, SalesOrder.deleted_at.is_(None), SalesOrderItem.deleted_at.is_(None))
        .order_by(SalesOrder.id.desc()).limit(5)
    )).all()
    orders = [{
        "id": o.id, "order_no": o.order_no, "customer_id": o.customer_id,
        "status": o.status, "total_amount": float(o.total_amount),
        "quantity": soi.quantity, "unit_price": float(soi.unit_price) if soi.unit_price else None,
        "created_at": str(o.created_at),
    } for soi, o in soi_rows]

    dni_rows = (await db.execute(
        select(DeliveryNoteItem, DeliveryNote).join(DeliveryNote, DeliveryNoteItem.delivery_note_id == DeliveryNote.id)
        .where(DeliveryNoteItem.product_id == product_id, DeliveryNote.deleted_at.is_(None), DeliveryNoteItem.deleted_at.is_(None))
        .order_by(DeliveryNote.id.desc()).limit(5)
    )).all()
    deliveries = [{
        "id": d.id, "delivery_no": d.delivery_no, "customer_id": d.customer_id,
        "status": d.status, "quantity": dni.quantity,
        "created_at": str(d.created_at),
    } for dni, d in dni_rows]

    return ok({"quotations": quotations, "orders": orders, "deliveries": deliveries})


__all__ = ["router"]
