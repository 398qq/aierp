"""Suppliers CRUD API."""

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy import and_, func, or_, select
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
    status: str = "active"
    certifications: str | None = None
    payment_terms: str | None = None
    payment_method: str | None = None
    currency: str = "CNY"
    incoterms: str | None = None
    region: str | None = None
    website: str | None = None
    financial_rating: str | None = None
    rating_score: float | None = None
    lead_time_days: int | None = None
    min_order_value: float | None = None


class SupplierUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=255)
    contact_person: str | None = None
    phone: str | None = None
    email: str | None = None
    address: str | None = None
    product_lines: str | None = None
    notes: str | None = None
    supplier_type: str | None = None
    status: str | None = None
    certifications: str | None = None
    payment_terms: str | None = None
    payment_method: str | None = None
    currency: str | None = None
    incoterms: str | None = None
    region: str | None = None
    website: str | None = None
    financial_rating: str | None = None
    rating_score: float | None = None
    lead_time_days: int | None = None
    min_order_value: float | None = None


def _supplier_to_dict(s: Supplier) -> dict:
    supplier_type = _normalize_supplier_type(s.supplier_type)
    return {
        "id": s.id,
        "name": s.name,
        "contact_person": s.contact_person,
        "phone": s.phone,
        "email": s.email,
        "address": s.address,
        "product_lines": s.product_lines,
        "notes": s.notes,
        "supplier_type": None if supplier_type == "未维护" else supplier_type,
        "status": s.status,
        "certifications": s.certifications,
        "payment_terms": s.payment_terms,
        "payment_method": s.payment_method,
        "currency": s.currency,
        "incoterms": s.incoterms,
        "region": s.region,
        "website": s.website,
        "financial_rating": s.financial_rating,
        "rating_score": float(s.rating_score) if s.rating_score is not None else None,
        "lead_time_days": s.lead_time_days,
        "min_order_value": float(s.min_order_value)
        if s.min_order_value is not None
        else None,
        "last_audit_date": str(s.last_audit_date) if s.last_audit_date else None,
        "created_at": s.created_at,
        "updated_at": s.updated_at,
    }


def _normalize_supplier_type(value: str | None) -> str:
    if not value:
        return "未维护"
    value_map = {
        "agency": "代理商",
        "agent": "代理商",
        "factory": "原厂",
        "manufacturer": "原厂",
        "trader": "贸易商",
        "trade": "贸易商",
    }
    return value_map.get(value.lower(), value)


def _supplier_type_filter_values(value: str) -> list[str]:
    aliases = {
        "代理商": ["代理商", "agency", "agent"],
        "原厂": ["原厂", "factory", "manufacturer"],
        "贸易商": ["贸易商", "trader", "trade"],
    }
    return aliases.get(value, [value])


def _merge_supplier_type_counts(rows: list[dict]) -> list[dict]:
    counts: dict[str, int] = {}
    for row in rows:
        key = _normalize_supplier_type(row.get("type"))
        counts[key] = counts.get(key, 0) + int(row["count"])
    return [
        {"type": key, "count": count}
        for key, count in sorted(counts.items(), key=lambda item: item[1], reverse=True)
    ]


def _filled(column):
    return and_(column.is_not(None), func.trim(column) != "")


def _empty(column):
    return or_(column.is_(None), func.trim(column) == "")


async def _count_suppliers(db: AsyncSession, *conditions) -> int:
    query = (
        select(func.count())
        .select_from(Supplier)
        .where(Supplier.deleted_at.is_(None), *conditions)
    )
    return (await db.execute(query)).scalar() or 0


async def _count_by_supplier_field(db: AsyncSession, column, label: str) -> list[dict]:
    grouped_value = func.coalesce(column, "未维护")
    query = (
        select(grouped_value.label(label), func.count().label("count"))
        .select_from(Supplier)
        .where(Supplier.deleted_at.is_(None))
        .group_by(grouped_value)
        .order_by(func.count().desc())
    )
    rows = (await db.execute(query)).all()
    return [{label: value or "未维护", "count": count} for value, count in rows]


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
        query = query.where(
            Supplier.supplier_type.in_(_supplier_type_filter_values(supplier_type))
        )

    count_q = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_q)).scalar() or 0

    query = query.order_by(Supplier.created_at.desc())
    query = query.offset((page - 1) * page_size).limit(page_size)
    rows = (await db.execute(query)).scalars().all()

    return ok(
        {
            "list": [_supplier_to_dict(r) for r in rows],
            "total": total,
            "page": page,
            "page_size": page_size,
        }
    )


@suppliers_router.get("/stats/summary")
async def supplier_stats_summary(
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
) -> dict:
    del current_user

    total = await _count_suppliers(db)
    certified = await _count_suppliers(db, _filled(Supplier.certifications))
    rated = await _count_suppliers(db, _filled(Supplier.financial_rating))
    recent_30d = await _count_suppliers(
        db, Supplier.created_at >= datetime.now(timezone.utc) - timedelta(days=30)
    )
    missing_contact = await _count_suppliers(
        db,
        _empty(Supplier.contact_person),
        _empty(Supplier.phone),
        _empty(Supplier.email),
    )
    missing_profile = await _count_suppliers(
        db,
        or_(
            _empty(Supplier.contact_person),
            and_(_empty(Supplier.phone), _empty(Supplier.email)),
            _empty(Supplier.supplier_type),
            _empty(Supplier.product_lines),
            _empty(Supplier.region),
            _empty(Supplier.payment_terms),
            _empty(Supplier.financial_rating),
            _empty(Supplier.certifications),
        ),
    )
    overseas_terms = ["海外", "香港", "台湾", "新加坡", "美国", "欧洲", "日本", "韩国"]
    overseas = await _count_suppliers(
        db,
        or_(
            *[
                condition
                for term in overseas_terms
                for condition in (
                    Supplier.region.ilike(f"%{term}%"),
                    Supplier.address.ilike(f"%{term}%"),
                )
            ]
        ),
    )

    top_query = (
        select(
            Supplier.id,
            Supplier.name,
            func.count(SupplierProduct.id).label("product_count"),
        )
        .select_from(Supplier)
        .outerjoin(SupplierProduct, SupplierProduct.supplier_id == Supplier.id)
        .where(Supplier.deleted_at.is_(None))
        .group_by(Supplier.id, Supplier.name)
        .order_by(func.count(SupplierProduct.id).desc(), Supplier.created_at.desc())
        .limit(10)
    )
    top_rows = (await db.execute(top_query)).all()

    by_type = _merge_supplier_type_counts(
        await _count_by_supplier_field(db, Supplier.supplier_type, "type")
    )

    return ok(
        {
            "total": total,
            "certified": certified,
            "rated": rated,
            "recent_30d": recent_30d,
            "missing_contact": missing_contact,
            "missing_profile": missing_profile,
            "overseas": overseas,
            "by_type": by_type,
            "by_region": await _count_by_supplier_field(db, Supplier.region, "region"),
            "by_rating": await _count_by_supplier_field(
                db, Supplier.financial_rating, "rating"
            ),
            "top_suppliers": [
                {"id": supplier_id, "name": name, "product_count": product_count}
                for supplier_id, name, product_count in top_rows
            ],
        }
    )


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

    return ok(
        {
            "supplier_id": supplier_id,
            "product_count": product_count,
            "preferred_product_count": preferred_count,
        }
    )


# --- Supplier-Product links ---


class SupplierProductLink(BaseModel):
    product_id: int
    cost_price: float | None = None
    currency: str = "CNY"
    price_valid_from: str | None = None
    price_valid_to: str | None = None
    moq: int | None = None
    spq: int | None = None
    min_order_value: float | None = None
    lead_time_days: int | None = None
    supplier_sku: str | None = None
    is_preferred: bool = False
    is_active: bool = True
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
        items.append(
            {
                "id": sp.id,
                "product_id": sp.product_id,
                "product_name": prod.name,
                "product_sku": prod.sku,
                "product_mpn": prod.mpn,
                "cost_price": float(sp.cost_price) if sp.cost_price else None,
                "currency": sp.currency,
                "price_valid_from": str(sp.price_valid_from)
                if sp.price_valid_from
                else None,
                "price_valid_to": str(sp.price_valid_to) if sp.price_valid_to else None,
                "moq": sp.moq,
                "spq": sp.spq,
                "min_order_value": float(sp.min_order_value)
                if sp.min_order_value
                else None,
                "lead_time_days": sp.lead_time_days,
                "supplier_sku": sp.supplier_sku,
                "is_preferred": sp.is_preferred,
                "is_active": sp.is_active,
                "notes": sp.notes,
            }
        )
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
        currency=data.currency,
        price_valid_from=data.price_valid_from,
        price_valid_to=data.price_valid_to,
        lead_time_days=data.lead_time_days,
        moq=data.moq,
        spq=data.spq,
        min_order_value=data.min_order_value,
        supplier_sku=data.supplier_sku,
        is_preferred=data.is_preferred,
        is_active=data.is_active,
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
