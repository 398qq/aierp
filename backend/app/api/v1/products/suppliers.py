"""Suppliers CRUD API."""
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.database import get_db
from app.models.product import Product, Supplier, SupplierProduct
from app.schemas.common import fail, ok

suppliers_router = APIRouter(prefix="/suppliers", tags=["suppliers"])


# --- Schemas ---


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
    name: str | None = Field(None, min_length=1, max_length=255)
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
        "id": s.id,
        "name": s.name,
        "contact_person": s.contact_person,
        "phone": s.phone,
        "email": s.email,
        "address": s.address,
        "product_lines": s.product_lines,
        "notes": s.notes,
        "supplier_type": s.supplier_type,
        "certifications": s.certifications,
        "payment_terms": s.payment_terms,
        "region": s.region,
        "website": s.website,
        "financial_rating": s.financial_rating,
        "created_at": s.created_at,
        "updated_at": s.updated_at,
    }


# --- CRUD ---


@suppliers_router.get("/")
async def list_suppliers(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=200),
    keyword: str | None = None,
    region: str | None = None,
    supplier_type: str | None = None,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
) -> dict:
    query = select(Supplier).where(Supplier.deleted_at.is_(None))
    if keyword:
        pattern = f"%{keyword}%"
        query = query.where(
            or_(
                Supplier.name.ilike(pattern),
                Supplier.contact_person.ilike(pattern),
                Supplier.email.ilike(pattern),
            )
        )
    if region:
        query = query.where(Supplier.region == region)
    if supplier_type:
        query = query.where(Supplier.supplier_type == supplier_type)

    count_q = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_q)).scalar() or 0

    query = query.order_by(Supplier.created_at.desc())
    query = query.offset((page - 1) * page_size).limit(page_size)
    rows = (await db.execute(query)).scalars().all()

    return ok({"list": [_supplier_to_dict(r) for r in rows], "total": total, "page": page, "page_size": page_size})


@suppliers_router.get("/{supplier_id}")
async def get_supplier(
    supplier_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
) -> dict:
    row = await db.get(Supplier, supplier_id)
    if not row or row.deleted_at is not None:
        return fail("Supplier not found", 404)
    return ok(_supplier_to_dict(row))


@suppliers_router.post("/")
async def create_supplier(
    data: SupplierCreate,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
) -> dict:
    supplier = Supplier(**data.model_dump(), created_by=current_user["user_id"])
    db.add(supplier)
    await db.commit()
    await db.refresh(supplier)
    return ok(_supplier_to_dict(supplier))


@suppliers_router.put("/{supplier_id}")
async def update_supplier(
    supplier_id: int,
    data: SupplierUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
) -> dict:
    supplier = await db.get(Supplier, supplier_id)
    if not supplier or supplier.deleted_at is not None:
        return fail("Supplier not found", 404)
    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(supplier, key, value)
    supplier.updated_by = current_user["user_id"]
    await db.commit()
    await db.refresh(supplier)
    return ok(_supplier_to_dict(supplier))


@suppliers_router.delete("/{supplier_id}")
async def delete_supplier(
    supplier_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
) -> dict:
    supplier = await db.get(Supplier, supplier_id)
    if not supplier or supplier.deleted_at is not None:
        return fail("Supplier not found", 404)
    supplier.deleted_at = datetime.now(timezone.utc)
    supplier.updated_by = current_user["user_id"]
    await db.commit()
    return ok({"id": supplier_id})


@suppliers_router.get("/{supplier_id}/stats")
async def supplier_stats(
    supplier_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
) -> dict:
    supplier = await db.get(Supplier, supplier_id)
    if not supplier or supplier.deleted_at is not None:
        return fail("Supplier not found", 404)

    product_count_q = select(func.count()).where(
        SupplierProduct.supplier_id == supplier_id,
    )
    product_count = (await db.execute(product_count_q)).scalar() or 0

    preferred_count_q = select(func.count()).where(
        SupplierProduct.supplier_id == supplier_id,
        SupplierProduct.is_preferred.is_(True),
    )
    preferred_count = (await db.execute(preferred_count_q)).scalar() or 0

    return ok({
        "supplier_id": supplier_id,
        "product_count": product_count,
        "preferred_product_count": preferred_count,
    })


# --- Supplier-Product links ---


class SupplierProductLink(BaseModel):
    product_id: int
    cost_price: float | None = None
    lead_time_days: int | None = None
    moq: int | None = None
    spq: int | None = None
    is_preferred: bool = False
    notes: str | None = None


@suppliers_router.get("/{supplier_id}/products")
async def list_supplier_products(
    supplier_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
) -> dict:
    query = (
        select(SupplierProduct, Product)
        .join(Product, SupplierProduct.product_id == Product.id)
        .where(
            SupplierProduct.supplier_id == supplier_id,
            Product.deleted_at.is_(None),
        )
    )
    rows = (await db.execute(query)).all()
    items = []
    for sp, prod in rows:
        items.append({
            "id": sp.id,
            "product_id": sp.product_id,
            "product_name": prod.name,
            "product_sku": prod.sku,
            "cost_price": sp.cost_price,
            "lead_time_days": sp.lead_time_days,
            "moq": sp.moq,
            "spq": sp.spq,
            "is_preferred": sp.is_preferred,
            "notes": sp.notes,
        })
    return ok(items)


@suppliers_router.post("/{supplier_id}/products")
async def link_supplier_product(
    supplier_id: int,
    data: SupplierProductLink,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
) -> dict:
    existing = await db.execute(
        select(SupplierProduct).where(
            SupplierProduct.supplier_id == supplier_id,
            SupplierProduct.product_id == data.product_id,
        )
    )
    if existing.scalar_one_or_none():
        return fail("Product already linked to this supplier", 400)

    link = SupplierProduct(
        supplier_id=supplier_id,
        product_id=data.product_id,
        cost_price=data.cost_price,
        lead_time_days=data.lead_time_days,
        moq=data.moq,
        spq=data.spq,
        is_preferred=data.is_preferred,
        notes=data.notes,
        created_by=current_user["user_id"],
    )
    db.add(link)
    await db.commit()
    await db.refresh(link)
    return ok({"id": link.id})


@suppliers_router.put("/{supplier_id}/products/{product_id}")
async def update_supplier_product(
    supplier_id: int,
    product_id: int,
    data: SupplierProductLink,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
) -> dict:
    link = await db.execute(
        select(SupplierProduct).where(
            SupplierProduct.supplier_id == supplier_id,
            SupplierProduct.product_id == product_id,
        )
    )
    link = link.scalar_one_or_none()
    if not link:
        return fail("Supplier product link not found", 404)

    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(link, key, value)
    link.updated_by = current_user["user_id"]
    await db.commit()
    await db.refresh(link)
    return ok({"id": link.id})


@suppliers_router.delete("/{supplier_id}/products/{product_id}")
async def unlink_supplier_product(
    supplier_id: int,
    product_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
) -> dict:
    link = await db.execute(
        select(SupplierProduct).where(
            SupplierProduct.supplier_id == supplier_id,
            SupplierProduct.product_id == product_id,
        )
    )
    link = link.scalar_one_or_none()
    if not link:
        return fail("Supplier product link not found", 404)
    await db.delete(link)
    await db.commit()
    return ok({"id": product_id})
