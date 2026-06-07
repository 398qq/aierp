"""BOM — Bill of Materials API (CRUD)."""

from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.database import get_db
from app.models.product import BOM, BOMLine, Product
from app.schemas.common import fail, ok

bom_router = APIRouter(prefix="/boms", tags=["bom"])


class BOMCreate(BaseModel):
    product_id: int
    name: str = Field(min_length=1, max_length=255)
    version: str = "1.0"
    status: str = "draft"
    revision_notes: str | None = None


class BOMUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=255)
    version: str | None = None
    status: str | None = None
    revision_notes: str | None = None


class BOMLineCreate(BaseModel):
    child_product_id: int
    quantity: float = Field(1, gt=0)
    unit: str | None = None
    reference_designator: str | None = None
    position: int = 0
    is_critical: bool = False
    notes: str | None = None


class BOMLineUpdate(BaseModel):
    quantity: float | None = Field(None, gt=0)
    unit: str | None = None
    reference_designator: str | None = None
    position: int | None = None
    is_critical: bool | None = None
    notes: str | None = None


def _bom_row(
    bom: BOM, product: Product | None = None, line_count: int | None = None
) -> dict:
    return {
        "id": bom.id,
        "product_id": bom.product_id,
        "name": bom.name,
        "version": bom.version,
        "status": bom.status,
        "revision_notes": bom.revision_notes,
        "product_name": product.name if product else None,
        "product_sku": product.sku if product else None,
        "line_count": line_count,
        "created_at": str(bom.created_at) if bom.created_at else None,
        "updated_at": str(bom.updated_at) if bom.updated_at else None,
    }


def _bom_line_row(line: BOMLine, child_product: Product | None = None) -> dict:
    return {
        "id": line.id,
        "bom_id": line.bom_id,
        "child_product_id": line.child_product_id,
        "quantity": float(line.quantity),
        "unit": line.unit,
        "reference_designator": line.reference_designator,
        "position": line.position,
        "is_critical": line.is_critical,
        "notes": line.notes,
        "child_product_name": child_product.name if child_product else None,
        "child_product_sku": child_product.sku if child_product else None,
        "child_product_mpn": child_product.mpn if child_product else None,
    }


def _resolve_products(db_result, ids: set[int]) -> dict[int, Product]:
    if not ids:
        return {}
    products = db_result.scalars().all()
    return {p.id: p for p in products}


# ── BOM CRUD ──────────────────────────────────────────────────────────────


@bom_router.get("")
async def list_boms(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    product_id: int | None = None,
    status: str | None = None,
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(get_current_user),
):
    base = select(BOM).where(BOM.deleted_at.is_(None))
    if product_id:
        base = base.where(BOM.product_id == product_id)
    if status:
        base = base.where(BOM.status == status)

    count_q = select(func.count()).select_from(base.subquery())
    total = (await db.execute(count_q)).scalar() or 0

    rows = (
        (
            await db.execute(
                base.order_by(BOM.created_at.desc())
                .offset((page - 1) * page_size)
                .limit(page_size)
            )
        )
        .scalars()
        .all()
    )

    product_ids = {b.product_id for b in rows}
    prod_result = (
        await db.execute(select(Product).where(Product.id.in_(product_ids)))
        if product_ids
        else None
    )
    products = _resolve_products(prod_result, product_ids) if prod_result else {}

    line_counts: dict[int, int] = {}
    if rows:
        bom_ids = [b.id for b in rows]
        lc_rows = (
            await db.execute(
                select(BOMLine.bom_id, func.count(BOMLine.id))
                .where(BOMLine.bom_id.in_(bom_ids), BOMLine.deleted_at.is_(None))
                .group_by(BOMLine.bom_id)
            )
        ).all()
        line_counts = {bid: int(cnt) for bid, cnt in lc_rows}

    items = [
        _bom_row(b, products.get(b.product_id), line_counts.get(b.id, 0)) for b in rows
    ]
    return ok({"list": items, "total": total, "page": page, "page_size": page_size})


@bom_router.post("", status_code=201)
async def create_bom(
    data: BOMCreate,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    product = await db.get(Product, data.product_id)
    if not product or product.deleted_at is not None:
        return fail("Product not found", 404)

    bom = BOM(**data.model_dump(), created_by=current_user["user_id"])
    db.add(bom)
    await db.commit()
    await db.refresh(bom)
    return ok(_bom_row(bom, product, 0))


@bom_router.get("/{bom_id}")
async def get_bom(
    bom_id: int,
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(get_current_user),
):
    bom = await db.get(BOM, bom_id)
    if not bom or bom.deleted_at is not None:
        return fail("BOM not found", 404)

    product = await db.get(Product, bom.product_id)

    lines_result = (
        (
            await db.execute(
                select(BOMLine)
                .where(BOMLine.bom_id == bom_id, BOMLine.deleted_at.is_(None))
                .order_by(BOMLine.position)
            )
        )
        .scalars()
        .all()
    )

    child_ids = {line.child_product_id for line in lines_result}
    child_result = (
        await db.execute(select(Product).where(Product.id.in_(child_ids)))
        if child_ids
        else None
    )
    child_products = _resolve_products(child_result, child_ids) if child_result else {}

    return ok(
        {
            **_bom_row(bom, product, len(lines_result)),
            "lines": [
                _bom_line_row(line, child_products.get(line.child_product_id))
                for line in lines_result
            ],
        }
    )


@bom_router.put("/{bom_id}")
async def update_bom(
    bom_id: int,
    data: BOMUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    bom = await db.get(BOM, bom_id)
    if not bom or bom.deleted_at is not None:
        return fail("BOM not found", 404)

    for key, val in data.model_dump(exclude_unset=True).items():
        setattr(bom, key, val)
    bom.updated_by = current_user["user_id"]
    await db.commit()
    await db.refresh(bom)

    product = await db.get(Product, bom.product_id)
    return ok(_bom_row(bom, product))


@bom_router.delete("/{bom_id}")
async def delete_bom(
    bom_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    bom = await db.get(BOM, bom_id)
    if not bom or bom.deleted_at is not None:
        return fail("BOM not found", 404)
    now = datetime.now(timezone.utc)
    bom.deleted_at = now
    bom.updated_by = current_user["user_id"]
    await db.execute(
        update(BOMLine)
        .where(BOMLine.bom_id == bom_id, BOMLine.deleted_at.is_(None))
        .values(deleted_at=now)
    )
    await db.commit()
    return ok({"id": bom_id})


# ── BOM Line CRUD ────────────────────────────────────────────────────────


@bom_router.post("/{bom_id}/lines", status_code=201)
async def add_bom_line(
    bom_id: int,
    data: BOMLineCreate,
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(get_current_user),
):
    bom = await db.get(BOM, bom_id)
    if not bom or bom.deleted_at is not None:
        return fail("BOM not found", 404)

    child = await db.get(Product, data.child_product_id)
    if not child or child.deleted_at is not None:
        return fail("Child product not found", 404)

    line = BOMLine(bom_id=bom_id, **data.model_dump())
    db.add(line)
    await db.commit()
    await db.refresh(line)
    return ok(_bom_line_row(line, child))


@bom_router.put("/{bom_id}/lines/{line_id}")
async def update_bom_line(
    bom_id: int,
    line_id: int,
    data: BOMLineUpdate,
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(get_current_user),
):
    line = await db.get(BOMLine, line_id)
    if not line or line.deleted_at is not None or line.bom_id != bom_id:
        return fail("BOM line not found", 404)

    for key, val in data.model_dump(exclude_unset=True).items():
        setattr(line, key, val)
    await db.commit()
    await db.refresh(line)

    child = await db.get(Product, line.child_product_id)
    return ok(_bom_line_row(line, child))


@bom_router.delete("/{bom_id}/lines/{line_id}")
async def delete_bom_line(
    bom_id: int,
    line_id: int,
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(get_current_user),
):
    line = await db.get(BOMLine, line_id)
    if not line or line.deleted_at is not None or line.bom_id != bom_id:
        return fail("BOM line not found", 404)
    line.deleted_at = datetime.now(timezone.utc)
    await db.commit()
    return ok({"id": line_id})


# ── Product-scoped queries ──────────────────────────────────────────────


product_bom_router = APIRouter(prefix="/products", tags=["bom"])


@product_bom_router.get("/{product_id}/bom")
async def get_product_bom(
    product_id: int,
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(get_current_user),
):
    result = await db.execute(
        select(BOM)
        .where(
            BOM.product_id == product_id,
            BOM.status == "active",
            BOM.deleted_at.is_(None),
        )
        .order_by(BOM.created_at.desc())
        .limit(1)
    )
    bom = result.scalar_one_or_none()
    if not bom:
        return ok(None)

    lines_result = (
        (
            await db.execute(
                select(BOMLine)
                .where(BOMLine.bom_id == bom.id, BOMLine.deleted_at.is_(None))
                .order_by(BOMLine.position)
            )
        )
        .scalars()
        .all()
    )

    child_ids = {line.child_product_id for line in lines_result}
    child_result = (
        await db.execute(select(Product).where(Product.id.in_(child_ids)))
        if child_ids
        else None
    )
    child_products = _resolve_products(child_result, child_ids) if child_result else {}

    return ok(
        {
            **_bom_row(bom, None, len(lines_result)),
            "lines": [
                _bom_line_row(line, child_products.get(line.child_product_id))
                for line in lines_result
            ],
        }
    )


@product_bom_router.get("/{product_id}/where-used")
async def get_product_where_used(
    product_id: int,
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(get_current_user),
):
    lines_result = (
        (
            await db.execute(
                select(BOMLine).where(
                    BOMLine.child_product_id == product_id,
                    BOMLine.deleted_at.is_(None),
                )
            )
        )
        .scalars()
        .all()
    )

    if not lines_result:
        return ok([])

    bom_ids = {line.bom_id for line in lines_result}
    boms_result = await db.execute(
        select(BOM).where(BOM.id.in_(bom_ids), BOM.deleted_at.is_(None))
    )
    boms = {b.id: b for b in boms_result.scalars().all()}

    assembly_ids = {b.product_id for b in boms.values()}
    asm_result = (
        await db.execute(select(Product).where(Product.id.in_(assembly_ids)))
        if assembly_ids
        else None
    )
    assemblies = _resolve_products(asm_result, assembly_ids) if asm_result else {}

    items: list[dict] = []
    for line in lines_result:
        bom = boms.get(line.bom_id)
        if not bom:
            continue
        assembly = assemblies.get(bom.product_id)
        items.append(
            {
                "bom_id": bom.id,
                "bom_name": bom.name,
                "bom_status": bom.status,
                "assembly_product_id": bom.product_id,
                "assembly_product_name": assembly.name if assembly else None,
                "assembly_product_sku": assembly.sku if assembly else None,
                "quantity_per_assembly": float(line.quantity),
                "reference_designator": line.reference_designator,
            }
        )

    return ok(items)


__all__ = ["bom_router", "product_bom_router"]
