"""Products — bulk price import endpoint.

Used by the front-end "PriceImport" page to push batch unit-price and
quantity updates keyed by SKU + warehouse. Kept separate from the main
products CRUD so the import pipeline (validation, error reporting) can
evolve independently of the basic create/update flows.
"""
from __future__ import annotations

import logging

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.database import get_db
from app.models.product import Inventory, Product
from app.schemas.common import ok

logger = logging.getLogger(__name__)


router = APIRouter(prefix="/products", tags=["products"])


class PriceImportItem(BaseModel):
    sku: str
    warehouse_id: int
    unit_price: float | None = None
    quantity: int | None = None


class PriceImportBody(BaseModel):
    items: list[PriceImportItem] = Field(min_length=1, max_length=5000)


@router.post("/price-import")
async def price_import(
    body: PriceImportBody,
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(get_current_user),
):
    errors: list[str] = []
    success_count = 0

    for item in body.items:
        result = await db.execute(
            select(Product).where(Product.sku == item.sku, Product.deleted_at.is_(None))
        )
        product = result.scalar_one_or_none()
        if product is None:
            errors.append(f"SKU不存在: {item.sku}")
            continue

        inv_result = await db.execute(
            select(Inventory).where(
                Inventory.product_id == product.id,
                Inventory.warehouse_id == item.warehouse_id,
                Inventory.deleted_at.is_(None),
            )
        )
        inv = inv_result.scalar_one_or_none()
        if inv is None:
            errors.append(f"库存记录不存在: SKU={item.sku} 仓库ID={item.warehouse_id}")
            continue

        if item.unit_price is not None:
            inv.unit_price = item.unit_price
        if item.quantity is not None:
            inv.quantity = item.quantity

        success_count += 1

    await db.commit()
    return ok({
        "success": success_count,
        "failed": len(errors),
        "errors": errors,
    })


__all__ = ["router", "PriceImportItem", "PriceImportBody", "price_import"]
