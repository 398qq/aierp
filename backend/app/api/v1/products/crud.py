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
from app.models.product import Product
from app.schemas.common import fail, ok
from app.services.cache_service import cache_bump_version

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/products", tags=["products"])

# Cache key version — bump to invalidate all entries after schema change
PRODUCTS_LIST_CACHE_VERSION = "v1"


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



@router.post("", status_code=201)
async def create_product(body: ProductCreate, db: AsyncSession = Depends(get_db), _user: dict = Depends(get_current_user)):
    product = Product(**body.model_dump())
    db.add(product)
    await db.flush()
    from app.services.embedding_pipeline import after_product_save
    after_product_save(product.id)
    await cache_bump_version("products:list")
    await cache_bump_version("dashboard:kpi")
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
    await cache_bump_version("products:list")
    await cache_bump_version("dashboard:kpi")
    return ok({"id": product.id})


@router.delete("/{product_id}")
async def delete_product(product_id: int, db: AsyncSession = Depends(get_db), _user: dict = Depends(get_current_user)):
    result = await db.execute(select(Product).where(Product.id == product_id, Product.deleted_at.is_(None)))
    product = result.scalar_one_or_none()
    if product is None:
        return fail("Product not found", 404)
    product.deleted_at = datetime.now(timezone.utc)
    await db.flush()
    await cache_bump_version("products:list")
    await cache_bump_version("dashboard:kpi")
    return ok(msg="deleted")


@router.post("/batch-delete")
async def batch_delete_products(body: dict, db: AsyncSession = Depends(get_db), _user: dict = Depends(get_current_user)):
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
async def batch_update_products(body: dict, db: AsyncSession = Depends(get_db), _user: dict = Depends(get_current_user)):
    ids: list[int] = body.get("ids", [])
    if not ids:
        return fail("No product IDs provided", 400)
    allowed = {"brand_id", "category", "package_type", "specs", "unit", "notes"}
    updates = {k: v for k, v in body.items() if k in allowed and v is not None}
    if not updates:
        return fail("No valid fields to update", 400)
    await db.execute(
        update(Product).where(Product.id.in_(ids), Product.deleted_at.is_(None)).values(**updates)
    )
    await cache_bump_version("products:list")
    await cache_bump_version("dashboard:kpi")
    return ok({"updated": len(ids), "fields": list(updates.keys())})



__all__ = ["router"]
