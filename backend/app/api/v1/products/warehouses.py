"""Warehouses and inventory management API."""

import json
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Query
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.database import get_db
from app.models.product import Inventory, Product, Warehouse
from app.schemas.common import fail, ok
from app.services.cache_service import cache_get_versioned, cache_set_versioned
from app.services.inventory_service import get_inventory_overview

warehouses_router = APIRouter(prefix="/warehouses", tags=["warehouses"])
inventory_router = APIRouter(prefix="/inventory", tags=["inventory"])


# --- Warehouse Schemas ---


class WarehouseCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    location: str | None = None
    description: str | None = None
    warehouse_type: str | None = None  # main / transit / returns / quarantine
    is_active: bool = True


class WarehouseUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=100)
    location: str | None = None
    description: str | None = None
    warehouse_type: str | None = None
    is_active: bool | None = None


# --- Inventory Schemas ---


class BatchAdjustItem(BaseModel):
    product_id: int
    warehouse_id: int
    quantity: int
    notes: str | None = None


class BatchAdjustBody(BaseModel):
    items: list[BatchAdjustItem]
    reason: str | None = None


# --- Warehouse CRUD ---


@warehouses_router.get("/")
async def list_warehouses(
    page: int = Query(1, ge=1),
    page_size: int = Query(100, ge=1, le=200),
    keyword: str | None = None,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
) -> dict:
    query = select(Warehouse).where(Warehouse.deleted_at.is_(None))
    if keyword:
        pattern = f"%{keyword}%"
        query = query.where(
            or_(
                Warehouse.name.ilike(pattern),
                Warehouse.location.ilike(pattern),
            )
        )

    count_q = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_q)).scalar() or 0

    query = query.order_by(Warehouse.created_at.desc())
    query = query.offset((page - 1) * page_size).limit(page_size)
    rows = (await db.execute(query)).scalars().all()

    items = [
        {
            "id": r.id,
            "name": r.name,
            "location": r.location,
            "description": r.description,
            "warehouse_type": r.warehouse_type,
            "is_active": r.is_active,
        }
        for r in rows
    ]
    return ok({"list": items, "total": total, "page": page, "page_size": page_size})


@warehouses_router.post("/")
async def create_warehouse(
    data: WarehouseCreate,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
) -> dict:
    warehouse = Warehouse(**data.model_dump(), created_by=current_user["user_id"])
    db.add(warehouse)
    await db.commit()
    await db.refresh(warehouse)
    return ok(
        {
            "id": warehouse.id,
            "name": warehouse.name,
            "location": warehouse.location,
            "warehouse_type": warehouse.warehouse_type,
            "is_active": warehouse.is_active,
        }
    )


@warehouses_router.get("/{warehouse_id}")
async def get_warehouse(
    warehouse_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
) -> dict:
    row = await db.get(Warehouse, warehouse_id)
    if not row or row.deleted_at is not None:
        return fail("Warehouse not found", 404)
    return ok(
        {
            "id": row.id,
            "name": row.name,
            "location": row.location,
            "description": row.description,
            "warehouse_type": row.warehouse_type,
            "is_active": row.is_active,
        }
    )


@warehouses_router.put("/{warehouse_id}")
async def update_warehouse(
    warehouse_id: int,
    data: WarehouseUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
) -> dict:
    warehouse = await db.get(Warehouse, warehouse_id)
    if not warehouse or warehouse.deleted_at is not None:
        return fail("Warehouse not found", 404)
    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(warehouse, key, value)
    warehouse.updated_by = current_user["user_id"]
    await db.commit()
    await db.refresh(warehouse)
    return ok(
        {
            "id": warehouse.id,
            "name": warehouse.name,
            "location": warehouse.location,
            "warehouse_type": warehouse.warehouse_type,
            "is_active": warehouse.is_active,
        }
    )


@warehouses_router.delete("/{warehouse_id}")
async def delete_warehouse(
    warehouse_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
) -> dict:
    warehouse = await db.get(Warehouse, warehouse_id)
    if not warehouse or warehouse.deleted_at is not None:
        return fail("Warehouse not found", 404)
    warehouse.deleted_at = datetime.now(timezone.utc)
    warehouse.updated_by = current_user["user_id"]
    await db.commit()
    return ok({"id": warehouse_id})


# --- Inventory ---


@inventory_router.get("/")
async def list_inventory(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=200),
    warehouse_id: int | None = None,
    product_id: int | None = None,
    low_stock: bool | None = None,
    keyword: str | None = None,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
) -> dict:
    query = (
        select(Inventory, Product, Warehouse)
        .join(Product, Inventory.product_id == Product.id)
        .join(Warehouse, Inventory.warehouse_id == Warehouse.id)
        .where(
            Product.deleted_at.is_(None),
            Warehouse.deleted_at.is_(None),
        )
    )
    if warehouse_id:
        query = query.where(Inventory.warehouse_id == warehouse_id)
    if product_id:
        query = query.where(Inventory.product_id == product_id)
    if low_stock:
        query = query.where(Inventory.quantity <= Inventory.safety_stock)
    if keyword:
        pattern = f"%{keyword}%"
        query = query.where(
            or_(
                Product.name.ilike(pattern),
                Product.sku.ilike(pattern),
            )
        )

    count_q = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_q)).scalar() or 0

    query = query.order_by(Warehouse.name, Product.name)
    query = query.offset((page - 1) * page_size).limit(page_size)
    rows = (await db.execute(query)).all()

    items = []
    for inv, prod, wh in rows:
        items.append(
            {
                "id": inv.id,
                "product_id": inv.product_id,
                "product_name": prod.name,
                "product_sku": prod.sku,
                "mpn": prod.mpn,
                "warehouse_id": inv.warehouse_id,
                "warehouse_name": wh.name,
                "warehouse_type": wh.warehouse_type,
                "quantity": inv.quantity,
                "safety_stock": inv.safety_stock,
                "locked_quantity": inv.locked_quantity,
                "unit_price": inv.unit_price,
                "available_quantity": inv.quantity - inv.locked_quantity,
                "location_code": inv.location_code,
                "reorder_point": inv.reorder_point,
                "max_stock": inv.max_stock,
                "abc_class": inv.abc_class,
                "costing_method": inv.costing_method,
                "last_counted_at": str(inv.last_counted_at)
                if inv.last_counted_at
                else None,
                "count_cycle_days": inv.count_cycle_days,
            }
        )
    return ok({"list": items, "total": total, "page": page, "page_size": page_size})


@inventory_router.get("/overview")
async def inventory_overview(
    response: JSONResponse,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
) -> dict:
    """Inventory KPI snapshot. Cached 60s (changes on every stock txn)."""
    cache_key = "overview:v2"
    cached_payload = await cache_get_versioned("inventory:overview", cache_key)
    if cached_payload is not None:
        response.headers["X-Cache"] = "HIT"
        return ok(json.loads(cached_payload))
    response.headers["X-Cache"] = "MISS"

    total_value_q = select(
        func.coalesce(func.sum(Inventory.quantity * Inventory.unit_price), 0)
    ).where(Inventory.deleted_at.is_(None))
    total_value = (await db.execute(total_value_q)).scalar() or 0

    low_stock_q = select(func.count()).where(
        Inventory.deleted_at.is_(None),
        Inventory.quantity <= Inventory.safety_stock
    )
    low_stock_count = (await db.execute(low_stock_q)).scalar() or 0

    out_of_stock_q = select(func.count()).where(
        Inventory.deleted_at.is_(None), Inventory.quantity <= 0
    )
    out_of_stock_count = (await db.execute(out_of_stock_q)).scalar() or 0

    product_count_q = select(func.count(func.distinct(Inventory.product_id))).where(
        Inventory.deleted_at.is_(None)
    )
    product_count = (await db.execute(product_count_q)).scalar() or 0

    operational_overview = await get_inventory_overview(db)
    payload = {
        **operational_overview,
        "total_value": float(total_value),
        "low_stock_count": low_stock_count,
        "out_of_stock_count": out_of_stock_count,
        "product_count": product_count,
    }
    await cache_set_versioned(
        "inventory:overview", cache_key, json.dumps(payload, default=str), ttl=60
    )
    return ok(payload)


@inventory_router.post("/adjust")
async def inventory_adjust(
    product_id: int,
    warehouse_id: int,
    quantity: int,
    notes: str | None = None,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
) -> dict:
    inv = await db.execute(
        select(Inventory).where(
            Inventory.product_id == product_id,
            Inventory.warehouse_id == warehouse_id,
        )
    )
    inv = inv.scalar_one_or_none()
    if not inv:
        inv = Inventory(
            product_id=product_id,
            warehouse_id=warehouse_id,
            quantity=quantity,
            safety_stock=0,
            locked_quantity=0,
        )
        db.add(inv)
    else:
        new_qty = inv.quantity + quantity
        if new_qty < 0:
            return fail("Insufficient inventory", 400)
        inv.quantity = new_qty

    from app.models.product import InventoryTransaction

    tx = InventoryTransaction(
        product_id=product_id,
        warehouse_id=warehouse_id,
        type="adjust",
        quantity=quantity,
        before_qty=inv.quantity - quantity,
        after_qty=inv.quantity,
        notes=notes,
    )
    db.add(tx)
    await db.commit()
    await db.refresh(inv)
    return ok({"id": inv.id, "quantity": inv.quantity})


@inventory_router.post("/batch-adjust")
async def inventory_batch_adjust(
    body: BatchAdjustBody,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
) -> dict:
    results = []
    for item in body.items:
        inv = await db.execute(
            select(Inventory).where(
                Inventory.product_id == item.product_id,
                Inventory.warehouse_id == item.warehouse_id,
            )
        )
        inv = inv.scalar_one_or_none()
        if not inv:
            inv = Inventory(
                product_id=item.product_id,
                warehouse_id=item.warehouse_id,
                quantity=item.quantity,
                safety_stock=0,
                locked_quantity=0,
            )
            db.add(inv)
            new_qty = item.quantity
        else:
            new_qty = inv.quantity + item.quantity
            if new_qty < 0:
                return fail(
                    f"Insufficient inventory for product {item.product_id} in warehouse {item.warehouse_id}",
                    400,
                )
            inv.quantity = new_qty

        from app.models.product import InventoryTransaction

        tx = InventoryTransaction(
            product_id=item.product_id,
            warehouse_id=item.warehouse_id,
            type="adjust",
            quantity=item.quantity,
            before_qty=new_qty - item.quantity,
            after_qty=new_qty,
            notes=item.notes or body.reason,
        )
        db.add(tx)
        results.append(
            {
                "product_id": item.product_id,
                "warehouse_id": item.warehouse_id,
                "quantity": new_qty,
            }
        )

    await db.commit()
    return ok(results)


@inventory_router.get("/substitutes")
async def inventory_substitutes(
    product_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
) -> dict:
    product = await db.get(Product, product_id)
    if not product or product.deleted_at is not None:
        return fail("Product not found", 404)

    query = (
        select(Inventory, Product, Warehouse)
        .join(Product, Inventory.product_id == Product.id)
        .join(Warehouse, Inventory.warehouse_id == Warehouse.id)
        .where(
            Product.id != product_id,
            Product.deleted_at.is_(None),
            Product.category == product.category,
            Inventory.quantity > 0,
            Warehouse.deleted_at.is_(None),
        )
        .order_by(Inventory.quantity.desc())
        .limit(10)
    )
    rows = (await db.execute(query)).all()

    items = []
    for inv, prod, wh in rows:
        items.append(
            {
                "product_id": prod.id,
                "product_name": prod.name,
                "product_sku": prod.sku,
                "warehouse_id": wh.id,
                "warehouse_name": wh.name,
                "quantity": inv.quantity,
            }
        )
    return ok(items)
