"""Products CRUD + price import endpoints."""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy import case, func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.database import get_db
from app.models.product import Inventory, Product
from app.schemas.common import fail, ok

router = APIRouter(prefix="/products", tags=["products"])


# --- Price Import ---


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


def _product_row(p: Product) -> dict:
    return {
        "id": p.id, "sku": p.sku, "name": p.name, "brand_id": p.brand_id,
        "brand_name": p.brand.name_cn or p.brand.name if p.brand else None,
        "category": p.category, "package_type": p.package_type,
        "specs": p.specs, "unit": p.unit, "notes": p.notes,
        "image_url": p.image_url,
        "created_at": str(p.created_at) if p.created_at else None,
    }


@router.get("")
async def list_products(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    q: str | None = None,
    category: str | None = None,
    brand_id: int | None = None,
    stock_status: str | None = Query(None, description="in_stock | out_of_stock | low_stock"),
    sort: str | None = Query(None, description="name_asc | name_desc | created_at_asc | created_at_desc"),
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(get_current_user),
):
    base = select(Product).where(Product.deleted_at.is_(None))
    count_base = select(func.count(Product.id)).where(Product.deleted_at.is_(None))

    if q:
        like = f"%{q}%"
        base = base.where(or_(Product.name.ilike(like), Product.sku.ilike(like)))
        count_base = count_base.where(or_(Product.name.ilike(like), Product.sku.ilike(like)))
    if category:
        base = base.where(Product.category == category)
        count_base = count_base.where(Product.category == category)
    if brand_id:
        base = base.where(Product.brand_id == brand_id)
        count_base = count_base.where(Product.brand_id == brand_id)

    if stock_status:
        avail_expr = case(
            (Inventory.quantity.is_(None), None),
            else_=Inventory.quantity - Inventory.locked_quantity,
        )
        inv_subq = (
            select(
                Inventory.product_id,
                func.sum(avail_expr).label("available"),
                func.min(Inventory.safety_stock).label("safety_stock"),
            )
            .where(Inventory.deleted_at.is_(None))
            .group_by(Inventory.product_id)
            .subquery()
        )

        base = base.outerjoin(inv_subq, Product.id == inv_subq.c.product_id)
        count_base = count_base.outerjoin(inv_subq, Product.id == inv_subq.c.product_id)

        if stock_status == "in_stock":
            base = base.where(inv_subq.c.available > 0)
            count_base = count_base.where(inv_subq.c.available > 0)
        elif stock_status == "out_of_stock":
            base = base.where((inv_subq.c.available == 0) | (inv_subq.c.available.is_(None)))
            count_base = count_base.where((inv_subq.c.available == 0) | (inv_subq.c.available.is_(None)))
        elif stock_status == "low_stock":
            base = base.where(inv_subq.c.available > 0, inv_subq.c.available <= inv_subq.c.safety_stock)
            count_base = count_base.where(inv_subq.c.available > 0, inv_subq.c.available <= inv_subq.c.safety_stock)

    if sort == "name_asc":
        order_col = Product.name.asc()
    elif sort == "name_desc":
        order_col = Product.name.desc()
    elif sort == "created_at_asc":
        order_col = Product.created_at.asc()
    else:
        order_col = Product.created_at.desc()

    total = (await db.execute(count_base)).scalar() or 0
    rows = (await db.execute(
        base.order_by(order_col, Product.id.desc()).offset((page - 1) * page_size).limit(page_size)
    )).scalars().all()

    return ok({"list": [_product_row(p) for p in rows], "total": total, "page": page, "page_size": page_size})


@router.get("/{product_id}")
async def get_product(product_id: int, db: AsyncSession = Depends(get_db), _user: dict = Depends(get_current_user)):
    result = await db.execute(select(Product).where(Product.id == product_id, Product.deleted_at.is_(None)))
    product = result.scalar_one_or_none()
    if product is None:
        return fail("Product not found", 404)
    return ok(_product_row(product))


@router.post("", status_code=201)
async def create_product(body: ProductCreate, db: AsyncSession = Depends(get_db), _user: dict = Depends(get_current_user)):
    product = Product(**body.model_dump())
    db.add(product)
    await db.flush()
    from app.services.embedding_pipeline import after_product_save
    after_product_save(product.id)
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
    return ok({"id": product.id})


@router.delete("/{product_id}")
async def delete_product(product_id: int, db: AsyncSession = Depends(get_db), _user: dict = Depends(get_current_user)):
    result = await db.execute(select(Product).where(Product.id == product_id, Product.deleted_at.is_(None)))
    product = result.scalar_one_or_none()
    if product is None:
        return fail("Product not found", 404)
    product.deleted_at = datetime.now(timezone.utc)
    await db.flush()
    return ok(msg="deleted")


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
    return ok({"updated": len(ids), "fields": list(updates.keys())})


@router.get("/{product_id}/sales")
async def get_product_sales(product_id: int, db: AsyncSession = Depends(get_db), _user: dict = Depends(get_current_user)):
    from app.models.sales import Quotation, QuotationItem, SalesOrder, SalesOrderItem, DeliveryNote, DeliveryNoteItem

    qi_rows = (await db.execute(
        select(QuotationItem, Quotation).join(Quotation, QuotationItem.quotation_id == Quotation.id)
        .where(QuotationItem.product_id == product_id, Quotation.deleted_at.is_(None), QuotationItem.deleted_at.is_(None))
        .order_by(Quotation.id.desc()).limit(5)
    )).all()
    quotations = [{
        "id": q.id, "quotation_no": q.quotation_no, "customer_id": q.customer_id,
        "status": q.status, "total_amount": float(q.total_amount),
        "quantity": qi.quantity, "unit_price": float(qi.unit_price) if qi.unit_price else None,
        "created_at": str(q.created_at),
    } for qi, q in qi_rows]

    soi_rows = (await db.execute(
        select(SalesOrderItem, SalesOrder).join(SalesOrder, SalesOrderItem.order_id == SalesOrder.id)
        .where(SalesOrderItem.product_id == product_id, SalesOrder.deleted_at.is_(None), SalesOrderItem.deleted_at.is_(None))
        .order_by(SalesOrder.id.desc()).limit(5)
    )).all()
    orders = [{
        "id": o.id, "order_no": o.order_no, "customer_id": o.customer_id,
        "status": o.status, "total_amount": float(o.total_amount),
        "quantity": soi.quantity, "unit_price": float(soi.unit_price) if soi.unit_price else None,
        "created_at": str(o.created_at),
    } for soi, o in soi_rows]

    dni_rows = (await db.execute(
        select(DeliveryNoteItem, DeliveryNote).join(DeliveryNote, DeliveryNoteItem.delivery_note_id == DeliveryNote.id)
        .where(DeliveryNoteItem.product_id == product_id, DeliveryNote.deleted_at.is_(None), DeliveryNoteItem.deleted_at.is_(None))
        .order_by(DeliveryNote.id.desc()).limit(5)
    )).all()
    deliveries = [{
        "id": d.id, "delivery_no": d.delivery_no, "customer_id": d.customer_id,
        "status": d.status, "quantity": dni.quantity,
        "created_at": str(d.created_at),
    } for dni, d in dni_rows]

    return ok({"quotations": quotations, "orders": orders, "deliveries": deliveries})
