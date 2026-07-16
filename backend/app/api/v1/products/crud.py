"""Products — write paths (create, update, delete, batch).

Read paths (list, stats, detail, sales) live in ``list.py``; bulk price
import lives in ``pricing.py``. The split keeps each module under the
500-line AGENTS.md limit and groups endpoints by mutation direction.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.database import get_db
from app.models.audit import FieldChangeLog, StatusTransitionLog
from app.models.product import Product
from app.schemas.common import fail, ok
from app.services.cache_service import cache_bump_version

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/products", tags=["products"])

# Cache key version — bump to invalidate all entries after schema change
PRODUCTS_LIST_CACHE_VERSION = "v3"
PRODUCT_STATUS_TRANSITIONS = {
    "draft": {"active", "inactive"},
    "active": {"frozen", "inactive"},
    "frozen": {"active", "inactive"},
    "inactive": {"active"},
}


# --- Schemas ---


class ProductCreate(BaseModel):
    # 基础标识
    sku: str | None = None
    name: str = Field(min_length=1, max_length=255)
    status: str = "active"
    product_type: str = "finished_good"
    owner: str | None = None
    mpn: str | None = None
    datecode: str | None = Field(None, max_length=100)
    barcode: str | None = None
    hs_code: str | None = None
    origin_country: str | None = None
    # 归属
    brand_id: int | None = None
    category: str | None = None
    package_type: str | None = None
    # 电子属性
    package_case: str | None = None
    pin_count: int | None = None
    voltage_rating: str | None = None
    tolerance_pct: str | None = None
    temperature_range: str | None = None
    power_rating: str | None = None
    # 规格
    specs: str | None = None
    unit: str | None = None
    default_warehouse_id: int | None = None
    batch_control: bool = False
    serial_control: bool = False
    shelf_life_control: bool = False
    # 物理属性
    length_mm: float | None = None
    width_mm: float | None = None
    height_mm: float | None = None
    gross_weight_g: float | None = None
    net_weight_g: float | None = None
    # 商务属性
    tax_rate: float | None = None
    currency: str = "CNY"
    standard_cost: float | None = None
    list_price: float | None = None
    wholesale_price: float | None = None
    minimum_sale_price: float | None = None
    price_valid_from: str | None = None
    price_valid_to: str | None = None
    latest_purchase_cost: float | None = None
    weighted_avg_cost: float | None = None
    cost_updated_at: str | None = None
    # 生命周期与合规
    lifecycle_status: str | None = None
    eol_date: str | None = None
    alternative_mpn: str | None = None
    rohs_compliant: bool = True
    reach_compliant: bool = False
    esd_sensitive: bool = False
    msl_level: str | None = None
    # 文档
    datasheet_url: str | None = None
    rohs_cert_url: str | None = None
    reach_cert_url: str | None = None
    # 备注
    notes: str | None = None
    image_url: str | None = None


class ProductUpdate(BaseModel):
    # 基础标识
    sku: str | None = None
    name: str | None = Field(None, min_length=1, max_length=255)
    status: str | None = None
    product_type: str | None = None
    owner: str | None = None
    mpn: str | None = None
    datecode: str | None = Field(None, max_length=100)
    barcode: str | None = None
    hs_code: str | None = None
    origin_country: str | None = None
    # 归属
    brand_id: int | None = None
    category: str | None = None
    package_type: str | None = None
    # 电子属性
    package_case: str | None = None
    pin_count: int | None = None
    voltage_rating: str | None = None
    tolerance_pct: str | None = None
    temperature_range: str | None = None
    power_rating: str | None = None
    # 规格
    specs: str | None = None
    unit: str | None = None
    default_warehouse_id: int | None = None
    batch_control: bool | None = None
    serial_control: bool | None = None
    shelf_life_control: bool | None = None
    # 物理属性
    length_mm: float | None = None
    width_mm: float | None = None
    height_mm: float | None = None
    gross_weight_g: float | None = None
    net_weight_g: float | None = None
    # 商务属性
    tax_rate: float | None = None
    currency: str | None = None
    standard_cost: float | None = None
    list_price: float | None = None
    wholesale_price: float | None = None
    minimum_sale_price: float | None = None
    price_valid_from: str | None = None
    price_valid_to: str | None = None
    latest_purchase_cost: float | None = None
    weighted_avg_cost: float | None = None
    cost_updated_at: str | None = None
    # 生命周期与合规
    lifecycle_status: str | None = None
    eol_date: str | None = None
    alternative_mpn: str | None = None
    rohs_compliant: bool | None = None
    reach_compliant: bool | None = None
    esd_sensitive: bool | None = None
    msl_level: str | None = None
    # 文档
    datasheet_url: str | None = None
    rohs_cert_url: str | None = None
    reach_cert_url: str | None = None
    # 备注
    notes: str | None = None
    image_url: str | None = None


@router.post("", status_code=201)
async def create_product(
    body: ProductCreate,
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(get_current_user),
):
    if body.status not in {"draft", "active", "frozen", "inactive"}:
        return fail("产品状态无效", 422)
    product = Product(**body.model_dump())
    db.add(product)
    await db.flush()
    from app.services.embedding_pipeline import after_product_save

    after_product_save(product.id)
    await cache_bump_version("products:list")
    await cache_bump_version("dashboard:kpi")
    return ok(
        {
            "id": product.id,
            "name": product.name,
            "sku": product.sku,
            "datecode": product.datecode,
        }
    )


@router.put("/{product_id}")
async def update_product(
    product_id: int,
    body: ProductUpdate,
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(get_current_user),
):
    result = await db.execute(
        select(Product).where(Product.id == product_id, Product.deleted_at.is_(None))
    )
    product = result.scalar_one_or_none()
    if product is None:
        return fail("Product not found", 404)
    data = body.model_dump(exclude_unset=True)
    if "status" in data and data["status"] not in {
        "draft",
        "active",
        "frozen",
        "inactive",
    }:
        return fail("产品状态无效", 422)
    old_status = product.status
    if "status" in data and data["status"] != old_status:
        if data["status"] not in PRODUCT_STATUS_TRANSITIONS.get(old_status, set()):
            return fail(f"产品状态转换非法: {old_status} → {data['status']}", 409)
    actor = str(_user.get("username") or _user.get("user_id") or "system")
    changes = [
        FieldChangeLog(
            table_name="products",
            record_id=product.id,
            field_name=key,
            old_value=str(getattr(product, key))
            if getattr(product, key) is not None
            else None,
            new_value=str(val) if val is not None else None,
            actor=actor,
        )
        for key, val in data.items()
        if getattr(product, key, None) != val
    ]
    for key, val in data.items():
        setattr(product, key, val)
    db.add_all(changes)
    if "status" in data and data["status"] != old_status:
        db.add(
            StatusTransitionLog(
                aggregate_type="product",
                aggregate_id=product.id,
                aggregate_no=product.sku,
                status_before=old_status,
                status_after=data["status"],
                action="status_change",
                actor=actor,
            )
        )
    await db.flush()
    from app.services.embedding_pipeline import after_product_save

    after_product_save(product.id)
    await cache_bump_version("products:list")
    await cache_bump_version("dashboard:kpi")
    return ok({"id": product.id})


@router.delete("/{product_id}")
async def delete_product(
    product_id: int,
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(get_current_user),
):
    result = await db.execute(
        select(Product).where(Product.id == product_id, Product.deleted_at.is_(None))
    )
    product = result.scalar_one_or_none()
    if product is None:
        return fail("Product not found", 404)
    product.deleted_at = datetime.now(timezone.utc)
    await db.flush()
    await cache_bump_version("products:list")
    await cache_bump_version("dashboard:kpi")
    return ok(msg="deleted")


@router.post("/batch-delete")
async def batch_delete_products(
    body: dict,
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(get_current_user),
):
    ids: list[int] = body.get("ids", [])
    if not ids:
        return fail("No product IDs provided", 400)
    now = datetime.now(timezone.utc)
    result = await db.execute(
        update(Product)
        .where(Product.id.in_(ids), Product.deleted_at.is_(None))
        .values(deleted_at=now)
    )
    await cache_bump_version("products:list")
    await cache_bump_version("dashboard:kpi")
    return ok({"deleted": result.rowcount or 0})


@router.patch("/batch")
async def batch_update_products(
    body: dict,
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(get_current_user),
):
    ids: list[int] = body.get("ids", [])
    if not ids:
        return fail("No product IDs provided", 400)
    allowed = {
        "brand_id",
        "category",
        "package_type",
        "package_case",
        "pin_count",
        "specs",
        "unit",
        "notes",
        "mpn",
        "barcode",
        "hs_code",
        "origin_country",
        "voltage_rating",
        "tolerance_pct",
        "temperature_range",
        "power_rating",
        "length_mm",
        "width_mm",
        "height_mm",
        "gross_weight_g",
        "net_weight_g",
        "tax_rate",
        "currency",
        "standard_cost",
        "list_price",
        "wholesale_price",
        "lifecycle_status",
        "eol_date",
        "alternative_mpn",
        "rohs_compliant",
        "reach_compliant",
        "esd_sensitive",
        "msl_level",
        "datasheet_url",
        "rohs_cert_url",
        "reach_cert_url",
    }
    updates = {k: v for k, v in body.items() if k in allowed and v is not None}
    if not updates:
        return fail("No valid fields to update", 400)
    await db.execute(
        update(Product)
        .where(Product.id.in_(ids), Product.deleted_at.is_(None))
        .values(**updates)
    )
    await cache_bump_version("products:list")
    await cache_bump_version("dashboard:kpi")
    return ok({"updated": len(ids), "fields": list(updates.keys())})


__all__ = ["router"]
