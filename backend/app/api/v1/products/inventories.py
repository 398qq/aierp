"""Inventory management API."""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from app.api.deps import get_current_user
from app.database import get_db
from app.models.product import Inventory, Product, Warehouse
from app.schemas.common import fail, ok

inventories_router = APIRouter(prefix="/inventories", tags=["inventories"])


# ============================================================
# Schemas
# ============================================================


class InventoryCreate(BaseModel):
    product_id: int
    warehouse_id: int
    quantity: int | None = None
    safety_stock: int | None = None
    locked_quantity: int | None = None
    unit_price: float | None = None
    location_code: str | None = None
    reorder_point: int = 0
    max_stock: int | None = None
    abc_class: str | None = None
    costing_method: str = "moving_avg"
    count_cycle_days: int | None = None


class InventoryUpdate(BaseModel):
    quantity: int | None = None
    safety_stock: int | None = None
    locked_quantity: int | None = None
    unit_price: float | None = None
    location_code: str | None = None
    reorder_point: int | None = None
    max_stock: int | None = None
    abc_class: str | None = None
    costing_method: str | None = None
    last_counted_at: str | None = None
    count_cycle_days: int | None = None


# ============================================================
# Helpers
# ============================================================


def _inventory_row(inv: Inventory, prod: Product, wh: Warehouse) -> dict:
    return {
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
        "available_quantity": inv.quantity - (inv.locked_quantity or 0),
        "location_code": inv.location_code,
        "reorder_point": inv.reorder_point,
        "max_stock": inv.max_stock,
        "abc_class": inv.abc_class,
        "costing_method": inv.costing_method,
        "last_counted_at": str(inv.last_counted_at) if inv.last_counted_at else None,
        "count_cycle_days": inv.count_cycle_days,
        "created_at": inv.created_at,
        "updated_at": inv.updated_at,
    }


# ============================================================
# Inventory CRUD
# ============================================================


@inventories_router.get("/")
async def list_inventories(
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

    items = [_inventory_row(inv, prod, wh) for inv, prod, wh in rows]
    return ok({"list": items, "total": total, "page": page, "page_size": page_size})


@inventories_router.get("/{inventory_id}")
async def get_inventory(
    inventory_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
) -> dict:
    result = await db.execute(
        select(Inventory, Product, Warehouse)
        .join(Product, Inventory.product_id == Product.id)
        .join(Warehouse, Inventory.warehouse_id == Warehouse.id)
        .where(Inventory.id == inventory_id)
    )
    row = result.first()
    if not row or row[0].deleted_at is not None:
        return fail("Inventory not found", 404)
    inv, prod, wh = row
    return ok(_inventory_row(inv, prod, wh))


@inventories_router.post("/", status_code=201)
async def create_inventory(
    data: InventoryCreate,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
) -> dict:
    existing = await db.execute(
        select(Inventory).where(
            Inventory.product_id == data.product_id,
            Inventory.warehouse_id == data.warehouse_id,
        )
    )
    if existing.scalar_one_or_none():
        return fail(
            "Inventory record already exists for this product and warehouse", 400
        )

    inventory = Inventory(
        **data.model_dump(exclude_unset=True),
        created_by=current_user["user_id"],
    )
    db.add(inventory)
    await db.commit()
    await db.refresh(inventory)

    product = await db.get(Product, data.product_id)
    warehouse = await db.get(Warehouse, data.warehouse_id)
    if product and warehouse:
        return ok(_inventory_row(inventory, product, warehouse))
    return ok({"id": inventory.id})


@inventories_router.put("/{inventory_id}")
async def update_inventory(
    inventory_id: int,
    data: InventoryUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
) -> dict:
    inventory = await db.get(Inventory, inventory_id)
    if not inventory or inventory.deleted_at is not None:
        return fail("Inventory not found", 404)

    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(inventory, key, value)
    inventory.updated_by = current_user["user_id"]
    await db.commit()
    await db.refresh(inventory)

    product = await db.get(Product, inventory.product_id)
    warehouse = await db.get(Warehouse, inventory.warehouse_id)
    if product and warehouse:
        return ok(_inventory_row(inventory, product, warehouse))
    return ok({"id": inventory.id})


@inventories_router.delete("/{inventory_id}")
async def delete_inventory(
    inventory_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
) -> dict:
    inventory = await db.get(Inventory, inventory_id)
    if not inventory or inventory.deleted_at is not None:
        return fail("Inventory not found", 404)
    inventory.deleted_at = datetime.now(timezone.utc)
    inventory.updated_by = current_user["user_id"]
    await db.commit()
    return ok({"id": inventory_id})
