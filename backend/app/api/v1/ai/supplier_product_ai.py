"""Supplier-product matching routes."""

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.database import get_db
from app.schemas.common import fail, ok

router = APIRouter(prefix="/ai", tags=["ai"])


@router.post("/suppliers/{supplier_id}/match-products")
async def ai_match_supplier_products(
    supplier_id: int,
    catalog_text: str | None = Query(None),
    auto_link: bool = Query(False),
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(get_current_user),
):
    """AI matches a supplier's product catalog to system products."""
    from app.models.product import SupplierProduct
    from app.services.pricing_service import match_supplier_to_products

    try:
        matches = await match_supplier_to_products(db, supplier_id, catalog_text)
    except ValueError as e:
        return fail(str(e), 404)

    if auto_link and matches:
        linked = 0
        for m in matches:
            pid = m.get("product_id")
            if not pid:
                continue
            exists = (
                await db.execute(
                    select(SupplierProduct).where(
                        SupplierProduct.supplier_id == supplier_id,
                        SupplierProduct.product_id == pid,
                        SupplierProduct.deleted_at.is_(None),
                    )
                )
            ).scalar_one_or_none()
            if not exists:
                sp = SupplierProduct(
                    supplier_id=supplier_id,
                    product_id=pid,
                    cost_price=m.get("cost_price"),
                    lead_time_days=m.get("lead_time_days"),
                    moq=m.get("moq"),
                )
                db.add(sp)
                linked += 1
        await db.commit()
        return ok({"matches": matches, "linked": linked})

    return ok({"matches": matches})
