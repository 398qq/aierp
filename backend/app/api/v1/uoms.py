"""UOM (Unit of Measure) dictionary API — read-only reference data."""

from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.uom import UomDict
from app.schemas.common import ok

router = APIRouter(prefix="/uoms", tags=["UOM"])


@router.get("")
async def list_uoms(
    uom_type: Literal["count", "package"] | None = Query(
        None, description="count / package"
    ),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Get all UOM entries, optionally filtered by type."""
    stmt = select(UomDict).where(UomDict.deleted_at.is_(None))
    if uom_type:
        stmt = stmt.where(UomDict.uom_type == uom_type)
    stmt = stmt.order_by(UomDict.sort_order, UomDict.code)
    result = await db.execute(stmt)
    return ok([_to_dict(u) for u in result.scalars().all()])


@router.get("/{code}")
async def get_uom(
    code: str,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Get a single UOM entry by code."""
    stmt = select(UomDict).where(UomDict.code == code, UomDict.deleted_at.is_(None))
    result = await db.execute(stmt)
    uom = result.scalar_one_or_none()
    if not uom:
        raise HTTPException(status_code=404, detail=f"UOM '{code}' not found")
    return ok(_to_dict(uom))


def _to_dict(uom: UomDict) -> dict:
    return {
        "code": uom.code,
        "name": uom.name,
        "uom_type": uom.uom_type,
        "category": uom.category,
        "sort_order": uom.sort_order,
    }
