"""Product & inventory management API."""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.database import get_db
from app.models.product import Brand, Inventory, Product, Supplier, SupplierProduct, Warehouse
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
        "brand_name": p.brand.name_cn or p.brand.name if p.brand else None,
        "category": p.category, "package_type": p.package_type,
        "specs": p.specs, "unit": p.unit, "notes": p.notes,
        "image_url": p.image_url,
        "created_at": str(p.created_at) if p.created_at else None,
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
    from app.services.embedding_pipeline import after_product_save
    after_product_save(product.id)
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
    from app.services.embedding_pipeline import after_product_save
    after_product_save(product.id)
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


@router.get("/{product_id}/sales")
async def get_product_sales(
    product_id: int,
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(get_current_user),
):
    from app.models.sales import Quotation, QuotationItem, SalesOrder, SalesOrderItem, DeliveryNote, DeliveryNoteItem

    # Quotations
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

    # Sales Orders
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

    # Delivery Notes
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


# --- Brands ---

brands_router = APIRouter(prefix="/brands", tags=["brands"])


class BrandCreate(BaseModel):
    # 基础
    code: str | None = None
    name: str = Field(min_length=1, max_length=255)
    name_cn: str | None = None
    short_name: str | None = None
    logo: str | None = None
    brand_type: str | None = None
    status: str = "active"
    category: str | None = None
    description: str | None = None
    notes: str | None = None
    # 商业
    level: str | None = None
    positioning: str | None = None
    owner: str | None = None
    product_lines: str | None = None
    target_markets: str | None = None
    website: str | None = None
    # 供应链
    supplier_id: int | None = None
    manufacturer_name: str | None = None
    authorization_status: str | None = None
    lifecycle_stage: str | None = None
    is_automotive: bool = False
    moq: int | None = None
    lead_time_days: int | None = None
    risk_level: str | None = None
    rohs_status: str | None = None
    # AI
    ai_keywords: str | None = None
    risk_score: float | None = None
    alternative_brands: str | None = None


class BrandUpdate(BaseModel):
    # 基础
    code: str | None = None
    name: str | None = Field(None, min_length=1, max_length=255)
    name_cn: str | None = None
    short_name: str | None = None
    logo: str | None = None
    brand_type: str | None = None
    status: str | None = None
    category: str | None = None
    description: str | None = None
    notes: str | None = None
    # 商业
    level: str | None = None
    positioning: str | None = None
    owner: str | None = None
    product_lines: str | None = None
    target_markets: str | None = None
    website: str | None = None
    # 供应链
    supplier_id: int | None = None
    manufacturer_name: str | None = None
    authorization_status: str | None = None
    lifecycle_stage: str | None = None
    is_automotive: bool | None = None
    moq: int | None = None
    lead_time_days: int | None = None
    risk_level: str | None = None
    rohs_status: str | None = None
    # AI
    ai_keywords: str | None = None
    risk_score: float | None = None
    alternative_brands: str | None = None


def _brand_row(b: Brand) -> dict:
    return {
        "id": b.id,
        "code": b.code, "name": b.name, "name_cn": b.name_cn, "short_name": b.short_name,
        "logo": b.logo, "brand_type": b.brand_type, "status": b.status,
        "category": b.category, "description": b.description, "notes": b.notes,
        "level": b.level, "positioning": b.positioning, "owner": b.owner,
        "product_lines": b.product_lines, "target_markets": b.target_markets,
        "website": b.website,
        "supplier_id": b.supplier_id, "manufacturer_name": b.manufacturer_name,
        "authorization_status": b.authorization_status, "lifecycle_stage": b.lifecycle_stage,
        "is_automotive": b.is_automotive, "moq": b.moq, "lead_time_days": b.lead_time_days,
        "risk_level": b.risk_level, "rohs_status": b.rohs_status,
        "ai_keywords": b.ai_keywords, "risk_score": b.risk_score,
        "alternative_brands": b.alternative_brands,
        "created_at": str(b.created_at) if b.created_at else None,
        "updated_at": str(b.updated_at) if b.updated_at else None,
    }


@brands_router.get("")
async def list_brands(
    q: str | None = None,
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(get_current_user),
):
    base = select(Brand).where(Brand.deleted_at.is_(None))
    if q:
        base = base.where(Brand.name.ilike(f"%{q}%"))
    rows = (await db.execute(base.order_by(Brand.name))).scalars().all()
    return ok([_brand_row(b) for b in rows])


@brands_router.get("/{brand_id}")
async def get_brand(brand_id: int, db: AsyncSession = Depends(get_db), _user: dict = Depends(get_current_user)):
    brand = (await db.execute(
        select(Brand).where(Brand.id == brand_id, Brand.deleted_at.is_(None))
    )).scalar_one_or_none()
    if brand is None:
        return fail("Brand not found", 404)

    # Count products under this brand
    product_count = (await db.execute(
        select(func.count(Product.id)).where(
            Product.brand_id == brand_id, Product.deleted_at.is_(None)
        )
    )).scalar() or 0

    return ok({
        **_brand_row(brand),
        "product_count": product_count,
    })


@brands_router.post("", status_code=201)
async def create_brand(body: BrandCreate, db: AsyncSession = Depends(get_db), _user: dict = Depends(get_current_user)):
    brand = Brand(**body.model_dump())
    db.add(brand)
    await db.flush()
    return ok({"id": brand.id, "name": brand.name})


@brands_router.put("/{brand_id}")
async def update_brand(brand_id: int, body: BrandUpdate, db: AsyncSession = Depends(get_db), _user: dict = Depends(get_current_user)):
    brand = (await db.execute(
        select(Brand).where(Brand.id == brand_id, Brand.deleted_at.is_(None))
    )).scalar_one_or_none()
    if brand is None:
        return fail("Brand not found", 404)
    for key, val in body.model_dump(exclude_unset=True).items():
        setattr(brand, key, val)
    await db.flush()
    return ok({"id": brand.id})


@brands_router.delete("/{brand_id}")
async def delete_brand(brand_id: int, db: AsyncSession = Depends(get_db), _user: dict = Depends(get_current_user)):
    brand = (await db.execute(
        select(Brand).where(Brand.id == brand_id, Brand.deleted_at.is_(None))
    )).scalar_one_or_none()
    if brand is None:
        return fail("Brand not found", 404)
    brand.deleted_at = datetime.now(timezone.utc)
    await db.flush()
    return ok(msg="deleted")


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
    supplier_type: str | None = None
    certifications: str | None = None
    payment_terms: str | None = None
    region: str | None = None
    website: str | None = None
    financial_rating: str | None = None


class SupplierUpdate(BaseModel):
    name: str | None = None
    contact_person: str | None = None
    phone: str | None = None
    email: str | None = None
    address: str | None = None
    product_lines: str | None = None
    notes: str | None = None
    supplier_type: str | None = None
    certifications: str | None = None
    payment_terms: str | None = None
    region: str | None = None
    website: str | None = None
    financial_rating: str | None = None


def _supplier_to_dict(s: Supplier) -> dict:
    return {
        "id": s.id, "name": s.name, "contact_person": s.contact_person,
        "phone": s.phone, "email": s.email, "address": s.address,
        "product_lines": s.product_lines, "notes": s.notes,
        "supplier_type": s.supplier_type, "certifications": s.certifications,
        "payment_terms": s.payment_terms, "region": s.region,
        "website": s.website, "financial_rating": s.financial_rating,
        "created_at": str(s.created_at) if s.created_at else None,
        "updated_at": str(s.updated_at) if s.updated_at else None,
    }


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
        "list": [_supplier_to_dict(s) for s in rows],
        "total": total, "page": page, "page_size": page_size,
    })


@suppliers_router.get("/{supplier_id}")
async def get_supplier(supplier_id: int, db: AsyncSession = Depends(get_db), _user: dict = Depends(get_current_user)):
    result = await db.execute(select(Supplier).where(Supplier.id == supplier_id, Supplier.deleted_at.is_(None)))
    supplier = result.scalar_one_or_none()
    if supplier is None:
        return fail("Supplier not found", 404)
    return ok(_supplier_to_dict(supplier))


@suppliers_router.post("", status_code=201)
async def create_supplier(body: SupplierCreate, db: AsyncSession = Depends(get_db), _user: dict = Depends(get_current_user)):
    supplier = Supplier(**body.model_dump())
    db.add(supplier)
    await db.flush()
    from app.services.embedding_pipeline import after_supplier_save
    after_supplier_save(supplier.id)
    return ok({"id": supplier.id, "name": supplier.name})


@suppliers_router.put("/{supplier_id}")
async def update_supplier(supplier_id: int, body: SupplierUpdate, db: AsyncSession = Depends(get_db), _user: dict = Depends(get_current_user)):
    result = await db.execute(select(Supplier).where(Supplier.id == supplier_id, Supplier.deleted_at.is_(None)))
    supplier = result.scalar_one_or_none()
    if supplier is None:
        return fail("Supplier not found", 404)
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(supplier, field, value)
    await db.flush()
    await db.refresh(supplier)
    from app.services.embedding_pipeline import after_supplier_save
    after_supplier_save(supplier.id)
    return ok(_supplier_to_dict(supplier))



@suppliers_router.delete("/{supplier_id}")
async def delete_supplier(supplier_id: int, db: AsyncSession = Depends(get_db), _user: dict = Depends(get_current_user)):
    from datetime import datetime, timezone
    result = await db.execute(select(Supplier).where(Supplier.id == supplier_id, Supplier.deleted_at.is_(None)))
    supplier = result.scalar_one_or_none()
    if supplier is None:
        return fail("Supplier not found", 404)
    supplier.deleted_at = datetime.now(timezone.utc)
    await db.flush()
    return ok(msg="deleted")


@suppliers_router.get("/stats/summary")
async def supplier_stats(db: AsyncSession = Depends(get_db), _user: dict = Depends(get_current_user)):
    """Supplier dashboard statistics."""
    total = (await db.execute(select(func.count(Supplier.id)).where(Supplier.deleted_at.is_(None)))).scalar() or 0

    # By type
    type_rows = (await db.execute(
        select(Supplier.supplier_type, func.count(Supplier.id))
        .where(Supplier.deleted_at.is_(None), Supplier.supplier_type.is_not(None))
        .group_by(Supplier.supplier_type)
    )).all()
    by_type = [{"type": t or "未知", "count": c} for t, c in type_rows]

    # By region
    region_rows = (await db.execute(
        select(Supplier.region, func.count(Supplier.id))
        .where(Supplier.deleted_at.is_(None), Supplier.region.is_not(None))
        .group_by(Supplier.region)
    )).all()
    by_region = [{"region": r or "未知", "count": c} for r, c in region_rows]

    # By financial rating
    rating_rows = (await db.execute(
        select(Supplier.financial_rating, func.count(Supplier.id))
        .where(Supplier.deleted_at.is_(None), Supplier.financial_rating.is_not(None))
        .group_by(Supplier.financial_rating)
    )).all()
    by_rating = [{"rating": r or "未评级", "count": c} for r, c in rating_rows]

    # With certifications
    cert_count = (await db.execute(
        select(func.count(Supplier.id)).where(
            Supplier.deleted_at.is_(None),
            Supplier.certifications.is_not(None),
            Supplier.certifications != "",
        )
    )).scalar() or 0

    # Recent suppliers (last 30 days)
    from datetime import timedelta
    thirty_days_ago = datetime.now(timezone.utc) - timedelta(days=30)
    recent_count = (await db.execute(
        select(func.count(Supplier.id)).where(
            Supplier.deleted_at.is_(None),
            Supplier.created_at >= thirty_days_ago,
        )
    )).scalar() or 0

    # Top suppliers by product count
    top_rows = (await db.execute(
        select(Supplier.id, Supplier.name, func.count(SupplierProduct.product_id).label("pc"))
        .join(SupplierProduct, Supplier.id == SupplierProduct.supplier_id, isouter=True)
        .where(Supplier.deleted_at.is_(None))
        .group_by(Supplier.id)
        .order_by(func.count(SupplierProduct.product_id).desc())
        .limit(10)
    )).all()
    top_suppliers = [{"id": r.id, "name": r.name, "product_count": r.pc} for r in top_rows]

    return ok({
        "total": total,
        "certified": cert_count,
        "recent_30d": recent_count,
        "by_type": by_type,
        "by_region": by_region,
        "by_rating": by_rating,
        "top_suppliers": top_suppliers,
    })


# --- Supplier-Product Linkage ---


class SupplierProductLink(BaseModel):
    product_id: int
    cost_price: float | None = None
    lead_time_days: int | None = None
    moq: int | None = None
    spq: int | None = None
    is_preferred: bool = False
    notes: str | None = None


@suppliers_router.get("/{supplier_id}/products")
async def list_supplier_products(supplier_id: int, db: AsyncSession = Depends(get_db), _user: dict = Depends(get_current_user)):
    rows = (await db.execute(
        select(
            SupplierProduct.id, SupplierProduct.product_id, SupplierProduct.cost_price,
            SupplierProduct.lead_time_days, SupplierProduct.moq, SupplierProduct.spq,
            SupplierProduct.is_preferred, SupplierProduct.notes,
            Product.sku, Product.name, Product.category, Product.package_type,
            Brand.name_cn, Brand.name,
        )
        .join(Product, SupplierProduct.product_id == Product.id)
        .outerjoin(Brand, Product.brand_id == Brand.id)
        .where(
            SupplierProduct.supplier_id == supplier_id,
            SupplierProduct.deleted_at.is_(None),
            Product.deleted_at.is_(None),
        )
        .order_by(SupplierProduct.is_preferred.desc(), SupplierProduct.id.desc())
    )).all()
    return ok([{
        "id": r[0], "product_id": r[1], "cost_price": float(r[2]) if r[2] else None,
        "lead_time_days": r[3], "moq": r[4], "spq": r[5],
        "is_preferred": r[6], "notes": r[7],
        "sku": r[8], "product_name": r[9], "category": r[10], "package_type": r[11],
        "brand_name": r[12] or r[13],
    } for r in rows])


@suppliers_router.post("/{supplier_id}/products", status_code=201)
async def link_supplier_product(supplier_id: int, body: SupplierProductLink, db: AsyncSession = Depends(get_db), _user: dict = Depends(get_current_user)):
    # Check for duplicate
    existing = (await db.execute(
        select(SupplierProduct).where(
            SupplierProduct.supplier_id == supplier_id,
            SupplierProduct.product_id == body.product_id,
            SupplierProduct.deleted_at.is_(None),
        )
    )).scalar_one_or_none()
    if existing:
        return fail("Product already linked to this supplier", 409)

    sp = SupplierProduct(supplier_id=supplier_id, **body.model_dump())
    db.add(sp)
    await db.flush()
    return ok({"id": sp.id})


@suppliers_router.put("/{supplier_id}/products/{product_id}")
async def update_supplier_product(supplier_id: int, product_id: int, body: SupplierProductLink, db: AsyncSession = Depends(get_db), _user: dict = Depends(get_current_user)):
    result = await db.execute(
        select(SupplierProduct).where(
            SupplierProduct.supplier_id == supplier_id,
            SupplierProduct.product_id == product_id,
            SupplierProduct.deleted_at.is_(None),
        )
    )
    sp = result.scalar_one_or_none()
    if sp is None:
        return fail("Linkage not found", 404)
    for key, val in body.model_dump(exclude_unset=True).items():
        setattr(sp, key, val)
    await db.flush()
    return ok({"id": sp.id})


@suppliers_router.delete("/{supplier_id}/products/{product_id}")
async def unlink_supplier_product(supplier_id: int, product_id: int, db: AsyncSession = Depends(get_db), _user: dict = Depends(get_current_user)):
    result = await db.execute(
        select(SupplierProduct).where(
            SupplierProduct.supplier_id == supplier_id,
            SupplierProduct.product_id == product_id,
            SupplierProduct.deleted_at.is_(None),
        )
    )
    sp = result.scalar_one_or_none()
    if sp is None:
        return fail("Linkage not found", 404)
    from datetime import datetime, timezone
    sp.deleted_at = datetime.now(timezone.utc)
    await db.flush()
    return ok(msg="unlinked")


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
    from app.models.product import Brand

    base = select(
        Inventory.id, Inventory.product_id, Inventory.warehouse_id,
        Inventory.quantity, Inventory.safety_stock, Inventory.created_at,
        Product.sku, Product.name, Product.category,
        Brand.name_cn, Brand.name,
        Warehouse.name, Inventory.locked_quantity,
    ).select_from(Inventory).join(
        Product, Inventory.product_id == Product.id
    ).outerjoin(
        Brand, Product.brand_id == Brand.id
    ).join(
        Warehouse, Inventory.warehouse_id == Warehouse.id
    ).where(
        Inventory.deleted_at.is_(None), Product.deleted_at.is_(None)
    )

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
    )).all()

    return ok({
        "list": [{
            "id": r[0], "product_id": r[1], "warehouse_id": r[2],
            "quantity": r[3], "safety_stock": r[4], "created_at": str(r[5]) if r[5] else None,
            "sku": r[6], "product_name": r[7], "category": r[8],
            "brand_name": r[9] or r[10], "warehouse_name": r[11],
            "locked_quantity": r[12] or 0,
        } for r in rows],
        "total": total, "page": page, "page_size": page_size,
    })


@inventory_router.get("/overview")
async def inventory_overview(db: AsyncSession = Depends(get_db), _user: dict = Depends(get_current_user)):
    """Intelligent inventory overview: dead stock, restock predictions."""
    from app.services.inventory_service import get_inventory_overview
    result = await get_inventory_overview(db)
    return ok(result)


@inventory_router.post("/adjust")
async def inventory_adjust(
    product_id: int = Query(...),
    warehouse_id: int = Query(...),
    adjustment: int = Query(...),
    reason: str = Query("manual"),
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(get_current_user),
):
    """Adjust inventory quantity and log the transaction."""
    from app.services.inventory_service import adjust_inventory
    result = await adjust_inventory(db, product_id, warehouse_id, adjustment, reason)
    await db.commit()
    return ok(result)


class BatchAdjustItem(BaseModel):
    product_id: int
    warehouse_id: int = 1
    adjustment: int
    reason: str = "batch"


class BatchAdjustBody(BaseModel):
    items: list[BatchAdjustItem] = Field(min_length=1, max_length=100)


@inventory_router.post("/batch-adjust")
async def inventory_batch_adjust(
    body: BatchAdjustBody,
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(get_current_user),
):
    """Batch adjust inventory for multiple items."""
    from app.services.inventory_service import adjust_inventory

    results = []
    for item in body.items:
        r = await adjust_inventory(db, item.product_id, item.warehouse_id, item.adjustment, item.reason)
        results.append(r)
    await db.commit()
    return ok({"adjusted": len(results), "details": results})


@inventory_router.get("/{product_id}/substitutes")
async def inventory_substitutes(product_id: int, db: AsyncSession = Depends(get_db), _user: dict = Depends(get_current_user)):
    """Find in-stock substitutes for a low-stock product."""
    from app.services.inventory_service import find_substitutes_for_stockout
    result = await find_substitutes_for_stockout(db, product_id)
    return ok(result)
