"""Product packaging level API — three-level hierarchy (PCS → REEL → BOX)."""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.database import get_db
from app.models.product import Product
from app.models.uom import ProductPackLevel
from app.schemas.common import ok
from app.schemas.uom import ProductPackLevelUpsert, ProductPackLevelResponse

router = APIRouter(prefix="/products/{product_id}/pack-levels", tags=["products"])


@router.get("")
async def list_pack_levels(
    product_id: int,
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(get_current_user),
) -> dict:
    """Get all packaging levels for a product."""
    stmt = (
        select(ProductPackLevel)
        .where(
            ProductPackLevel.product_id == product_id,
            ProductPackLevel.deleted_at.is_(None),
        )
        .order_by(ProductPackLevel.pack_level)
    )
    result = await db.execute(stmt)
    levels = result.scalars().all()
    return ok([ProductPackLevelResponse.model_validate(pl) for pl in levels])


@router.put("")
async def upsert_pack_levels(
    product_id: int,
    body: list[ProductPackLevelUpsert],
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(get_current_user),
) -> dict:
    """Replace all packaging levels for a product (3 max)."""
    # Verify product exists
    prod = await db.get(Product, product_id)
    if not prod or prod.deleted_at is not None:
        raise HTTPException(404, "Product not found")

    if len(body) > 3:
        raise HTTPException(400, "Maximum 3 packaging levels (0/1/2)")

    levels = {b.pack_level for b in body}
    if 0 not in levels:
        raise HTTPException(400, "pack_level 0 (base unit) is required")

    # Soft-delete existing levels
    existing = await db.execute(
        select(ProductPackLevel).where(
            ProductPackLevel.product_id == product_id,
            ProductPackLevel.deleted_at.is_(None),
        )
    )
    for row in existing.scalars().all():
        row.deleted_at = datetime.now(timezone.utc)

    # Insert new levels
    for b in body:
        level = ProductPackLevel(
            product_id=product_id,
            pack_level=b.pack_level,
            uom_code=b.uom_code,
            qty_per_parent=b.qty_per_parent,
        )
        db.add(level)

    await db.commit()
    return ok({"updated": len(body)})
