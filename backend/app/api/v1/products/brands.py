"""Brands CRUD API."""

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy import case, func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.database import get_db
from app.models.product import Brand, Product
from app.schemas.common import fail, ok

brands_router = APIRouter(prefix="/brands", tags=["brands"])


# --- Schemas ---


class BrandCreate(BaseModel):
    code: str | None = None
    name: str = Field(min_length=1, max_length=255)
    name_cn: str | None = None
    short_name: str | None = None
    logo: str | None = None
    brand_type: str | None = None
    status: str | None = None
    category: str | None = None
    description: str | None = None
    notes: str | None = None
    level: str | None = None
    positioning: str | None = None
    owner: str | None = None
    product_lines: str | None = None
    target_markets: str | None = None
    website: str | None = None
    supplier_id: int | None = None
    manufacturer_name: str | None = None
    authorization_status: str | None = None
    lifecycle_stage: str | None = None
    is_automotive: bool | None = None
    moq: int | None = None
    lead_time_days: int | None = None
    risk_level: str | None = None
    rohs_status: str | None = None
    ai_keywords: str | None = None
    risk_score: float | None = None
    alternative_brands: str | None = None


class BrandUpdate(BaseModel):
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
    level: str | None = None
    positioning: str | None = None
    owner: str | None = None
    product_lines: str | None = None
    target_markets: str | None = None
    website: str | None = None
    supplier_id: int | None = None
    manufacturer_name: str | None = None
    authorization_status: str | None = None
    lifecycle_stage: str | None = None
    is_automotive: bool | None = None
    moq: int | None = None
    lead_time_days: int | None = None
    risk_level: str | None = None
    rohs_status: str | None = None
    ai_keywords: str | None = None
    risk_score: float | None = None
    alternative_brands: str | None = None


class BrandBatchUpdate(BaseModel):
    ids: list[int] = Field(min_length=1)
    updates: BrandUpdate


class BrandBatchDelete(BaseModel):
    ids: list[int] = Field(min_length=1)


def _brand_completion(brand: Brand) -> tuple[int, list[str]]:
    fields = [
        ("编码", brand.code),
        ("中文名", brand.name_cn),
        ("类型", brand.brand_type),
        ("分类", brand.category),
        ("等级", brand.level),
        ("负责人", brand.owner),
        ("产品线", brand.product_lines),
        ("授权状态", brand.authorization_status),
        ("生命周期", brand.lifecycle_stage),
        ("风险等级", brand.risk_level),
        ("RoHS", brand.rohs_status),
    ]
    completed = sum(1 for _, value in fields if value not in (None, ""))
    missing = [label for label, value in fields if value in (None, "")]
    return round(completed / len(fields) * 100), missing


def _brand_incomplete_clause():
    return or_(
        Brand.code.is_(None),
        Brand.code == "",
        Brand.name_cn.is_(None),
        Brand.name_cn == "",
        Brand.brand_type.is_(None),
        Brand.brand_type == "",
        Brand.category.is_(None),
        Brand.category == "",
        Brand.level.is_(None),
        Brand.level == "",
        Brand.owner.is_(None),
        Brand.owner == "",
        Brand.product_lines.is_(None),
        Brand.product_lines == "",
        Brand.authorization_status.is_(None),
        Brand.authorization_status == "",
        Brand.lifecycle_stage.is_(None),
        Brand.lifecycle_stage == "",
        Brand.risk_level.is_(None),
        Brand.risk_level == "",
        Brand.rohs_status.is_(None),
        Brand.rohs_status == "",
    )


def _product_count_subquery():
    return (
        select(Product.brand_id, func.count(Product.id).label("product_count"))
        .where(Product.deleted_at.is_(None))
        .group_by(Product.brand_id)
        .subquery()
    )


def _brand_row(brand: Brand, product_count: int | None = None) -> dict:
    completion_score, missing_fields = _brand_completion(brand)
    if product_count is None:
        product_count = getattr(brand, "product_count", None)
    return {
        "id": brand.id,
        "code": brand.code,
        "name": brand.name,
        "name_cn": brand.name_cn,
        "short_name": brand.short_name,
        "logo": brand.logo,
        "brand_type": brand.brand_type,
        "status": brand.status,
        "category": brand.category,
        "description": brand.description,
        "notes": brand.notes,
        "level": brand.level,
        "positioning": brand.positioning,
        "owner": brand.owner,
        "product_lines": brand.product_lines,
        "target_markets": brand.target_markets,
        "website": brand.website,
        "supplier_id": brand.supplier_id,
        "manufacturer_name": brand.manufacturer_name,
        "authorization_status": brand.authorization_status,
        "lifecycle_stage": brand.lifecycle_stage,
        "is_automotive": brand.is_automotive,
        "moq": brand.moq,
        "lead_time_days": brand.lead_time_days,
        "risk_level": brand.risk_level,
        "rohs_status": brand.rohs_status,
        "ai_keywords": brand.ai_keywords,
        "alternative_brands": brand.alternative_brands,
        "risk_score": brand.risk_score,
        "product_count": product_count,
        "has_products": product_count is None or product_count > 0,
        "completion_score": completion_score,
        "missing_fields": missing_fields,
        "created_at": brand.created_at,
        "updated_at": brand.updated_at,
    }


async def _count_by(db: AsyncSession, column, key: str) -> list[dict]:
    rows = (
        await db.execute(
            select(column, func.count(Brand.id))
            .where(Brand.deleted_at.is_(None))
            .group_by(column)
            .order_by(func.count(Brand.id).desc())
        )
    ).all()
    return [{key: value or "unknown", "count": count} for value, count in rows]


async def _brand_product_count(db: AsyncSession, brand_id: int) -> int:
    return (
        await db.execute(
            select(func.count(Product.id)).where(
                Product.brand_id == brand_id,
                Product.deleted_at.is_(None),
            )
        )
    ).scalar() or 0


# --- CRUD ---


@brands_router.get("/")
async def list_brands(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=200),
    keyword: str | None = None,
    q: str | None = None,
    status: str | None = None,
    level: str | None = None,
    brand_type: str | None = None,
    category: str | None = None,
    lifecycle_stage: str | None = None,
    risk_level: str | None = None,
    scene: str | None = Query(
        None,
        description="high_risk | eol_nrnd | pending_completion | no_products | automotive | unauthorized",
    ),
    sort: str | None = Query(
        None,
        description="created_at_desc | name_asc | name_desc | risk_score_desc | product_count_desc",
    ),
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
) -> dict:
    keyword = keyword or q
    product_count_subq = _product_count_subquery()
    product_count_expr = func.coalesce(product_count_subq.c.product_count, 0)
    query = (
        select(Brand, product_count_expr.label("product_count"))
        .outerjoin(product_count_subq, Brand.id == product_count_subq.c.brand_id)
        .where(Brand.deleted_at.is_(None))
    )
    if keyword:
        pattern = f"%{keyword}%"
        query = query.where(
            or_(
                Brand.name.ilike(pattern),
                Brand.name_cn.ilike(pattern),
                Brand.code.ilike(pattern),
                Brand.short_name.ilike(pattern),
                Brand.category.ilike(pattern),
                Brand.manufacturer_name.ilike(pattern),
                Brand.product_lines.ilike(pattern),
                Brand.ai_keywords.ilike(pattern),
            )
        )
    if status:
        query = query.where(Brand.status == status)
    if level:
        query = query.where(Brand.level == level)
    if brand_type:
        query = query.where(Brand.brand_type == brand_type)
    if category:
        query = query.where(Brand.category == category)
    if lifecycle_stage:
        query = query.where(Brand.lifecycle_stage == lifecycle_stage)
    if risk_level:
        query = query.where(Brand.risk_level == risk_level)

    if scene == "high_risk":
        query = query.where(
            or_(Brand.risk_score >= 70, Brand.risk_level.in_(("high", "critical")))
        )
    elif scene == "eol_nrnd":
        query = query.where(Brand.lifecycle_stage.in_(("eol", "nrnd")))
    elif scene == "pending_completion":
        query = query.where(_brand_incomplete_clause())
    elif scene == "no_products":
        query = query.where(product_count_expr == 0)
    elif scene == "automotive":
        query = query.where(Brand.is_automotive.is_(True))
    elif scene == "unauthorized":
        query = query.where(Brand.authorization_status == "unauthorized")

    count_q = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_q)).scalar() or 0

    if sort == "name_asc":
        query = query.order_by(Brand.name.asc(), Brand.id.desc())
    elif sort == "name_desc":
        query = query.order_by(Brand.name.desc(), Brand.id.desc())
    elif sort == "risk_score_desc":
        query = query.order_by(
            case((Brand.risk_score.is_(None), 1), else_=0),
            Brand.risk_score.desc(),
            Brand.id.desc(),
        )
    elif sort == "product_count_desc":
        query = query.order_by(product_count_expr.desc(), Brand.id.desc())
    else:
        query = query.order_by(Brand.created_at.desc(), Brand.id.desc())
    query = query.offset((page - 1) * page_size).limit(page_size)
    rows = (await db.execute(query)).all()

    items = []
    for brand, product_count in rows:
        item = _brand_row(brand, product_count=int(product_count or 0))
        items.append(item)

    return ok({"list": items, "total": total, "page": page, "page_size": page_size})


@brands_router.get("/stats/summary")
async def brand_stats_summary(
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
) -> dict:
    now = datetime.now(timezone.utc)
    recent_since = now - timedelta(days=30)

    total = (
        await db.execute(select(func.count(Brand.id)).where(Brand.deleted_at.is_(None)))
    ).scalar() or 0
    recent_30d = (
        await db.execute(
            select(func.count(Brand.id)).where(
                Brand.deleted_at.is_(None),
                Brand.created_at >= recent_since,
            )
        )
    ).scalar() or 0
    eol_nrnd_count = (
        await db.execute(
            select(func.count(Brand.id)).where(
                Brand.deleted_at.is_(None),
                Brand.lifecycle_stage.in_(("eol", "nrnd")),
            )
        )
    ).scalar() or 0
    automotive_count = (
        await db.execute(
            select(func.count(Brand.id)).where(
                Brand.deleted_at.is_(None),
                Brand.is_automotive.is_(True),
            )
        )
    ).scalar() or 0
    high_risk_count = (
        await db.execute(
            select(func.count(Brand.id)).where(
                Brand.deleted_at.is_(None),
                or_(Brand.risk_score >= 70, Brand.risk_level.in_(("high", "critical"))),
            )
        )
    ).scalar() or 0
    completion_base = (
        select(Brand)
        .where(
            Brand.deleted_at.is_(None),
            _brand_incomplete_clause(),
        )
        .subquery()
    )
    pending_completion_count = (
        await db.execute(select(func.count()).select_from(completion_base))
    ).scalar() or 0

    product_count_subq = _product_count_subquery()
    no_product_count = (
        await db.execute(
            select(func.count(Brand.id))
            .outerjoin(product_count_subq, Brand.id == product_count_subq.c.brand_id)
            .where(
                Brand.deleted_at.is_(None),
                func.coalesce(product_count_subq.c.product_count, 0) == 0,
            )
        )
    ).scalar() or 0

    top_risk_rows = (
        (
            await db.execute(
                select(Brand)
                .where(Brand.deleted_at.is_(None))
                .order_by(
                    case((Brand.risk_score.is_(None), 1), else_=0),
                    Brand.risk_score.desc(),
                )
                .limit(5)
            )
        )
        .scalars()
        .all()
    )

    eol_alert_rows = (
        await db.execute(
            select(
                Brand.id,
                Brand.name,
                Brand.lifecycle_stage,
                Brand.risk_level,
                Brand.risk_score,
            )
            .where(
                Brand.deleted_at.is_(None),
                Brand.lifecycle_stage.in_(("eol", "nrnd")),
            )
            .order_by(
                case((Brand.risk_score.is_(None), 1), else_=0),
                Brand.risk_score.desc(),
                Brand.updated_at.desc(),
            )
            .limit(10)
        )
    ).all()

    return ok(
        {
            "total": total,
            "total_count": total,
            "recent_30d": recent_30d,
            "eol_nrnd_count": eol_nrnd_count,
            "automotive_count": automotive_count,
            "high_risk_count": high_risk_count,
            "pending_completion_count": pending_completion_count,
            "no_product_count": no_product_count,
            "by_status": await _count_by(db, Brand.status, "status"),
            "by_level": await _count_by(db, Brand.level, "level"),
            "by_type": await _count_by(db, Brand.brand_type, "type"),
            "by_brand_type": await _count_by(db, Brand.brand_type, "brand_type"),
            "by_lifecycle": await _count_by(db, Brand.lifecycle_stage, "stage"),
            "by_lifecycle_stage": await _count_by(db, Brand.lifecycle_stage, "stage"),
            "by_authorization": await _count_by(
                db, Brand.authorization_status, "status"
            ),
            "by_authorization_status": await _count_by(
                db, Brand.authorization_status, "status"
            ),
            "by_category": await _count_by(db, Brand.category, "category"),
            "by_risk": await _count_by(db, Brand.risk_level, "level"),
            "top_risk_brands": [
                {
                    "id": brand.id,
                    "name": brand.name,
                    "risk_score": brand.risk_score or 0,
                    "risk_level": brand.risk_level,
                    "lifecycle_stage": brand.lifecycle_stage,
                }
                for brand in top_risk_rows
            ],
            "recent_eol_alerts": [
                {
                    "brand_id": brand_id,
                    "brand_name": name,
                    "lifecycle_stage": lifecycle_stage,
                    "risk_level": risk_level,
                    "risk_score": risk_score or 0,
                }
                for brand_id, name, lifecycle_stage, risk_level, risk_score in eol_alert_rows
            ],
        }
    )


@brands_router.patch("/batch")
@brands_router.put("/batch")
async def batch_update_brands(
    data: BrandBatchUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
) -> dict:
    updates = data.updates.model_dump(exclude_unset=True)
    if not updates:
        return fail("No fields to update")

    allowed_fields = {
        "status",
        "level",
        "brand_type",
        "category",
        "lifecycle_stage",
        "risk_level",
        "authorization_status",
        "owner",
        "positioning",
        "rohs_status",
    }
    invalid_fields = sorted(set(updates) - allowed_fields)
    if invalid_fields:
        return fail(
            f"Fields not allowed for batch update: {', '.join(invalid_fields)}", 400
        )

    updates["updated_by"] = current_user["user_id"]
    result = await db.execute(
        update(Brand)
        .where(Brand.id.in_(data.ids), Brand.deleted_at.is_(None))
        .values(**updates)
    )
    await db.commit()
    return ok(
        {
            "updated": result.rowcount or 0,
            "fields": sorted(updates.keys() - {"updated_by"}),
        }
    )


@brands_router.post("/batch-delete")
@brands_router.delete("/batch")
async def batch_delete_brands(
    data: BrandBatchDelete,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
) -> dict:
    now = datetime.now(timezone.utc)
    result = await db.execute(
        update(Brand)
        .where(Brand.id.in_(data.ids), Brand.deleted_at.is_(None))
        .values(deleted_at=now, updated_by=current_user["user_id"])
    )
    await db.commit()
    return ok({"deleted": result.rowcount or 0})


@brands_router.get("/{brand_id}")
async def get_brand(
    brand_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
) -> dict:
    row = await db.get(Brand, brand_id)
    if not row or row.deleted_at is not None:
        return fail("Brand not found", 404)
    return ok(_brand_row(row, product_count=await _brand_product_count(db, brand_id)))


@brands_router.post("/")
async def create_brand(
    data: BrandCreate,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
) -> dict:
    brand = Brand(**data.model_dump(), created_by=current_user["user_id"])
    db.add(brand)
    await db.commit()
    await db.refresh(brand)
    return ok(_brand_row(brand, product_count=0))


@brands_router.put("/{brand_id}")
async def update_brand(
    brand_id: int,
    data: BrandUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
) -> dict:
    brand = await db.get(Brand, brand_id)
    if not brand or brand.deleted_at is not None:
        return fail("Brand not found", 404)
    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(brand, key, value)
    brand.updated_by = current_user["user_id"]
    await db.commit()
    await db.refresh(brand)
    return ok(_brand_row(brand, product_count=await _brand_product_count(db, brand_id)))


@brands_router.delete("/{brand_id}")
async def delete_brand(
    brand_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
) -> dict:
    brand = await db.get(Brand, brand_id)
    if not brand or brand.deleted_at is not None:
        return fail("Brand not found", 404)
    brand.deleted_at = datetime.now(timezone.utc)
    brand.updated_by = current_user["user_id"]
    await db.commit()
    return ok({"id": brand_id})


@brands_router.get("/{brand_id}/stats")
async def brand_stats(
    brand_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
) -> dict:
    brand = await db.get(Brand, brand_id)
    if not brand or brand.deleted_at is not None:
        return fail("Brand not found", 404)

    product_count_q = select(func.count()).where(
        Product.brand_id == brand_id,
        Product.deleted_at.is_(None),
    )
    product_count = (await db.execute(product_count_q)).scalar() or 0

    active_product_count_q = select(func.count()).where(
        Product.brand_id == brand_id,
        Product.deleted_at.is_(None),
    )
    active_product_count = (await db.execute(active_product_count_q)).scalar() or 0

    return ok(
        {
            "brand_id": brand_id,
            "product_count": product_count,
            "active_product_count": active_product_count,
            "risk_score": brand.risk_score,
        }
    )
