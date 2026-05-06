"""Product & inventory management API."""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.database import get_db
from app.models.product import Brand, Inventory, Product, Supplier, Warehouse
from app.schemas.common import fail, ok

router = APIRouter(prefix="/products", tags=["products"])


# --- Schemas ---

class ProductCreate(BaseModel):
    sku: str | None = None
    name: str = Field(min_length=1, max_length=255)
    brand_id: int | None = None
    category: str | None = None
    package_type: str | None = None
    specs: str | None = None
    unit: str | None = None
    notes: str | None = None
    image_url: str | None = None


class ProductUpdate(BaseModel):
    sku: str | None = None
    name: str | None = Field(None, min_length=1, max_length=255)
    brand_id: int | None = None
    category: str | None = None
    package_type: str | None = None
    specs: str | None = None
    unit: str | None = None
    notes: str | None = None
    image_url: str | None = None


def _product_row(p: Product) -> dict:
    return {
        "id": p.id, "sku": p.sku, "name": p.name, "brand_id": p.brand_id,
        "category": p.category, "package_type": p.package_type,
        "specs": p.specs, "unit": p.unit, "notes": p.notes,
        "image_url": p.image_url,
        "created_at": str(p.created_at),
    }


@router.get("")
async def list_products(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    q: str | None = None,
    category: str | None = None,
    brand_id: int | None = None,
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(get_current_user),
):
    base = select(Product).where(Product.deleted_at.is_(None))
    count_base = select(func.count(Product.id)).where(Product.deleted_at.is_(None))

    if q:
        like = f"%{q}%"
        base = base.where(or_(Product.name.ilike(like), Product.sku.ilike(like)))
        count_base = count_base.where(or_(Product.name.ilike(like), Product.sku.ilike(like)))
    if category:
        base = base.where(Product.category == category)
        count_base = count_base.where(Product.category == category)
    if brand_id:
        base = base.where(Product.brand_id == brand_id)
        count_base = count_base.where(Product.brand_id == brand_id)

    total = (await db.execute(count_base)).scalar() or 0
    rows = (await db.execute(
        base.order_by(Product.id.desc()).offset((page - 1) * page_size).limit(page_size)
    )).scalars().all()

    return ok({"list": [_product_row(p) for p in rows], "total": total, "page": page, "page_size": page_size})


@router.get("/{product_id}")
async def get_product(product_id: int, db: AsyncSession = Depends(get_db), _user: dict = Depends(get_current_user)):
    result = await db.execute(select(Product).where(Product.id == product_id, Product.deleted_at.is_(None)))
    product = result.scalar_one_or_none()
    if product is None:
        return fail("Product not found", 404)
    return ok(_product_row(product))


@router.post("", status_code=201)
async def create_product(body: ProductCreate, db: AsyncSession = Depends(get_db), _user: dict = Depends(get_current_user)):
    product = Product(**body.model_dump())
    db.add(product)
    await db.flush()
    return ok({"id": product.id, "name": product.name})


@router.put("/{product_id}")
async def update_product(product_id: int, body: ProductUpdate, db: AsyncSession = Depends(get_db), _user: dict = Depends(get_current_user)):
    result = await db.execute(select(Product).where(Product.id == product_id, Product.deleted_at.is_(None)))
    product = result.scalar_one_or_none()
    if product is None:
        return fail("Product not found", 404)
    for key, val in body.model_dump(exclude_unset=True).items():
        setattr(product, key, val)
    await db.flush()
    return ok({"id": product.id})


@router.delete("/{product_id}")
async def delete_product(product_id: int, db: AsyncSession = Depends(get_db), _user: dict = Depends(get_current_user)):
    result = await db.execute(select(Product).where(Product.id == product_id, Product.deleted_at.is_(None)))
    product = result.scalar_one_or_none()
    if product is None:
        return fail("Product not found", 404)
    product.deleted_at = datetime.now(timezone.utc)
    await db.flush()
    return ok(msg="deleted")


# --- Brands ---

brands_router = APIRouter(prefix="/brands", tags=["brands"])


class BrandCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    name_cn: str | None = None
    website: str | None = None
    category: str | None = None
    notes: str | None = None


@brands_router.get("")
async def list_brands(db: AsyncSession = Depends(get_db), _user: dict = Depends(get_current_user)):
    rows = (await db.execute(
        select(Brand).where(Brand.deleted_at.is_(None)).order_by(Brand.name)
    )).scalars().all()
    return ok([{"id": b.id, "name": b.name, "name_cn": b.name_cn, "website": b.website, "category": b.category} for b in rows])


@brands_router.post("", status_code=201)
async def create_brand(body: BrandCreate, db: AsyncSession = Depends(get_db), _user: dict = Depends(get_current_user)):
    brand = Brand(**body.model_dump())
    db.add(brand)
    await db.flush()
    return ok({"id": brand.id, "name": brand.name})


# --- Suppliers ---

suppliers_router = APIRouter(prefix="/suppliers", tags=["suppliers"])


class SupplierCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    contact_person: str | None = None
    phone: str | None = None
    email: str | None = None
    address: str | None = None
    product_lines: str | None = None
    notes: str | None = None


@suppliers_router.get("")
async def list_suppliers(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    q: str | None = None,
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(get_current_user),
):
    base = select(Supplier).where(Supplier.deleted_at.is_(None))
    count_base = select(func.count(Supplier.id)).where(Supplier.deleted_at.is_(None))

    if q:
        like = f"%{q}%"
        base = base.where(Supplier.name.ilike(like))
        count_base = count_base.where(Supplier.name.ilike(like))

    total = (await db.execute(count_base)).scalar() or 0
    rows = (await db.execute(
        base.order_by(Supplier.id.desc()).offset((page - 1) * page_size).limit(page_size)
    )).scalars().all()

    return ok({
        "list": [{"id": s.id, "name": s.name, "contact_person": s.contact_person,
                  "phone": s.phone, "email": s.email, "address": s.address,
                  "product_lines": s.product_lines, "notes": s.notes,
                  "created_at": str(s.created_at)} for s in rows],
        "total": total, "page": page, "page_size": page_size,
    })


@suppliers_router.get("/{supplier_id}")
async def get_supplier(supplier_id: int, db: AsyncSession = Depends(get_db), _user: dict = Depends(get_current_user)):
    result = await db.execute(select(Supplier).where(Supplier.id == supplier_id, Supplier.deleted_at.is_(None)))
    supplier = result.scalar_one_or_none()
    if supplier is None:
        return fail("Supplier not found", 404)
    return ok({"id": supplier.id, "name": supplier.name, "contact_person": supplier.contact_person,
               "phone": supplier.phone, "email": supplier.email, "address": supplier.address,
               "product_lines": supplier.product_lines, "notes": supplier.notes})


@suppliers_router.post("", status_code=201)
async def create_supplier(body: SupplierCreate, db: AsyncSession = Depends(get_db), _user: dict = Depends(get_current_user)):
    supplier = Supplier(**body.model_dump())
    db.add(supplier)
    await db.flush()
    return ok({"id": supplier.id, "name": supplier.name})


# --- Warehouses ---

warehouses_router = APIRouter(prefix="/warehouses", tags=["warehouses"])


@warehouses_router.get("")
async def list_warehouses(db: AsyncSession = Depends(get_db), _user: dict = Depends(get_current_user)):
    rows = (await db.execute(
        select(Warehouse).where(Warehouse.deleted_at.is_(None)).order_by(Warehouse.name)
    )).scalars().all()
    return ok([{"id": w.id, "name": w.name, "location": w.location, "description": w.description} for w in rows])


# --- Inventory ---

inventory_router = APIRouter(prefix="/inventory", tags=["inventory"])


@inventory_router.get("")
async def list_inventory(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    warehouse_id: int | None = None,
    product_id: int | None = None,
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(get_current_user),
):
    base = select(Inventory).where(Inventory.deleted_at.is_(None))
    count_base = select(func.count(Inventory.id)).where(Inventory.deleted_at.is_(None))

    if warehouse_id:
        base = base.where(Inventory.warehouse_id == warehouse_id)
        count_base = count_base.where(Inventory.warehouse_id == warehouse_id)
    if product_id:
        base = base.where(Inventory.product_id == product_id)
        count_base = count_base.where(Inventory.product_id == product_id)

    total = (await db.execute(count_base)).scalar() or 0
    rows = (await db.execute(
        base.order_by(Inventory.id.desc()).offset((page - 1) * page_size).limit(page_size)
    )).scalars().all()

    return ok({
        "list": [{"id": i.id, "product_id": i.product_id, "warehouse_id": i.warehouse_id,
                  "quantity": i.quantity, "safety_stock": i.safety_stock,
                  "created_at": str(i.created_at)} for i in rows],
        "total": total, "page": page, "page_size": page_size,
    })
