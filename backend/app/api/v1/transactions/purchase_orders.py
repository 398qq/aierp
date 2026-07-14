"""Transactions API — purchase order bounded context.

Routes for the purchase order lifecycle:
- list / get / create / update / delete
- receive (move PO items to inventory)
- create-from-restock (AI restock suggestion → PO)

The receive endpoint calls into ``inventory_service.receive_po_item`` to
move stock into a warehouse. The create-from-restock endpoint is
populated by the AI restock pipeline.
"""

import logging
from datetime import datetime

from app.api.deps import get_current_user
from app.database import get_db
from app.domain.shared.errors import BusinessRuleViolation, NotFoundError
from app.domain.states import assert_can_transition_purchase_order
from app.models.transaction import PurchaseOrder
from app.schemas.common import ok
from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

logger = logging.getLogger(__name__)

po_router = APIRouter(prefix="/purchase-orders", tags=["transactions:purchase-order"])


class POItemCreate(BaseModel):
    product_id: int
    quantity: int = 1
    unit_price: float = 0
    amount: float = 0


class POCreate(BaseModel):
    order_no: str | None = None
    supplier_id: int
    status: str = "draft"
    total_amount: float = 0
    expected_date: str | None = None
    notes: str | None = None
    items: list[POItemCreate] | None = None


class POBatchDelete(BaseModel):
    ids: list[int] = Field(min_length=1, max_length=100)


@po_router.get("")
async def list_purchase_orders(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    supplier_id: int | None = None,
    status: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(get_current_user),
):
    from app.models.product import Supplier

    base = (
        select(
            PurchaseOrder.id,
            PurchaseOrder.order_no,
            PurchaseOrder.supplier_id,
            Supplier.name,
            PurchaseOrder.status,
            PurchaseOrder.total_amount,
            PurchaseOrder.expected_date,
            PurchaseOrder.notes,
            PurchaseOrder.created_at,
        )
        .outerjoin(Supplier, PurchaseOrder.supplier_id == Supplier.id)
        .where(PurchaseOrder.deleted_at.is_(None))
    )
    count_base = select(func.count(PurchaseOrder.id)).where(
        PurchaseOrder.deleted_at.is_(None)
    )

    if supplier_id:
        base = base.where(PurchaseOrder.supplier_id == supplier_id)
        count_base = count_base.where(PurchaseOrder.supplier_id == supplier_id)
    if status:
        base = base.where(PurchaseOrder.status == status)
        count_base = count_base.where(PurchaseOrder.status == status)
    if date_from:
        base = base.where(PurchaseOrder.created_at >= datetime.fromisoformat(date_from))
        count_base = count_base.where(
            PurchaseOrder.created_at >= datetime.fromisoformat(date_from)
        )
    if date_to:
        base = base.where(
            PurchaseOrder.created_at <= datetime.fromisoformat(date_to + "T23:59:59")
        )
        count_base = count_base.where(
            PurchaseOrder.created_at <= datetime.fromisoformat(date_to + "T23:59:59")
        )

    total = (await db.execute(count_base)).scalar() or 0
    rows = (
        await db.execute(
            base.order_by(PurchaseOrder.id.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
    ).all()

    return ok(
        {
            "list": [
                {
                    "id": r[0],
                    "order_no": r[1],
                    "supplier_id": r[2],
                    "supplier_name": r[3] or f"#{r[2]}",
                    "status": r[4],
                    "total_amount": float(r[5]),
                    "expected_date": str(r[6]) if r[6] else None,
                    "notes": r[7],
                    "created_at": str(r[8]) if r[8] else None,
                }
                for r in rows
            ],
            "total": total,
            "page": page,
            "page_size": page_size,
        }
    )


@po_router.post("/batch-delete")
async def batch_delete_purchase_orders(
    body: POBatchDelete,
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(get_current_user),
):
    orders = (
        await db.execute(
            select(PurchaseOrder).where(
                PurchaseOrder.id.in_(body.ids), PurchaseOrder.deleted_at.is_(None)
            )
        )
    ).scalars().all()
    non_draft = [po.order_no or f"#{po.id}" for po in orders if po.status != "draft"]
    if non_draft:
        raise BusinessRuleViolation(
            f"只能删除草稿状态的采购订单: {', '.join(non_draft)}"
        )

    deleted_at = datetime.utcnow()
    for po in orders:
        po.deleted_at = deleted_at
    await db.commit()
    return ok({"deleted": len(orders), "ids": [po.id for po in orders]})


@po_router.post("", status_code=201)
async def create_purchase_order(
    body: POCreate,
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(get_current_user),
):
    from app.models.transaction import PurchaseOrderItem

    data = body.model_dump()
    items_data = data.pop("items", None)
    if data.get("expected_date"):
        data["expected_date"] = datetime.fromisoformat(data["expected_date"])

    if not data.get("order_no"):
        from app.services.docno import generate_doc_no

        data["order_no"] = await generate_doc_no(db, "PO", PurchaseOrder, "order_no")

    order = PurchaseOrder(**data)
    db.add(order)
    await db.flush()

    if items_data:
        total = 0.0
        for item in items_data:
            poi = PurchaseOrderItem(order_id=order.id, **item)
            db.add(poi)
            total += item.get("amount", 0) or 0
        order.total_amount = total

    await db.commit()
    await db.refresh(order)
    return ok(
        {
            "id": order.id,
            "order_no": order.order_no,
            "items_count": len(items_data) if items_data else 0,
        }
    )


class POUpdate(BaseModel):
    supplier_id: int | None = None
    expected_date: str | None = None
    notes: str | None = None
    items: list[POItemCreate] | None = None


@po_router.get("/{po_id}")
async def get_purchase_order(
    po_id: int,
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(get_current_user),
):
    from app.models.product import Supplier
    from app.models.transaction import PurchaseOrderItem

    result = await db.execute(
        select(PurchaseOrder)
        .where(PurchaseOrder.id == po_id, PurchaseOrder.deleted_at.is_(None))
        .options(
            selectinload(PurchaseOrder.items).selectinload(PurchaseOrderItem.product)
        )
    )
    po = result.scalar_one_or_none()
    if po is None:
        raise NotFoundError("采购订单不存在")

    supplier_name = None
    if po.supplier_id:
        r = await db.execute(select(Supplier.name).where(Supplier.id == po.supplier_id))
        supplier_name = r.scalar()

    return ok(
        {
            "id": po.id,
            "order_no": po.order_no,
            "supplier_id": po.supplier_id,
            "supplier_name": supplier_name or f"#{po.supplier_id}",
            "status": po.status,
            "total_amount": float(po.total_amount),
            "expected_date": str(po.expected_date) if po.expected_date else None,
            "notes": po.notes,
            "created_at": str(po.created_at),
            "updated_at": str(po.updated_at) if po.updated_at else None,
            "items": [
                {
                    "id": i.id,
                    "product_id": i.product_id,
                    "product_name": i.product.name if i.product else f"#{i.product_id}",
                    "product_sku": i.product.sku if i.product and i.product.sku else "",
                    "quantity": i.quantity,
                    "unit_price": float(i.unit_price),
                    "amount": float(i.amount),
                }
                for i in po.items
            ],
        }
    )


@po_router.put("/{po_id}")
async def update_purchase_order(
    po_id: int,
    body: POUpdate,
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(get_current_user),
):
    from app.models.transaction import PurchaseOrderItem

    result = await db.execute(
        select(PurchaseOrder)
        .where(PurchaseOrder.id == po_id, PurchaseOrder.deleted_at.is_(None))
        .options(selectinload(PurchaseOrder.items))
    )
    po = result.scalar_one_or_none()
    if po is None:
        raise NotFoundError("采购订单不存在")
    if po.status != "draft":
        raise BusinessRuleViolation("只能编辑草稿状态的采购订单")

    data = body.model_dump(exclude_none=True)
    items_data = data.pop("items", None)

    if "supplier_id" in data:
        po.supplier_id = data["supplier_id"]
    if "expected_date" in data and data["expected_date"]:
        po.expected_date = datetime.fromisoformat(data["expected_date"])
    if "notes" in data:
        po.notes = data["notes"]

    if items_data is not None:
        for item in po.items:
            await db.delete(item)
        total = 0.0
        for item in items_data:
            poi = PurchaseOrderItem(order_id=po.id, **item)
            db.add(poi)
            total += item.get("amount", 0) or 0
        po.total_amount = total

    await db.commit()
    await db.refresh(po)
    return ok({"id": po.id, "order_no": po.order_no, "msg": "更新成功"})


@po_router.delete("/{po_id}")
async def delete_purchase_order(
    po_id: int,
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(get_current_user),
):
    result = await db.execute(
        select(PurchaseOrder).where(
            PurchaseOrder.id == po_id, PurchaseOrder.deleted_at.is_(None)
        )
    )
    po = result.scalar_one_or_none()
    if po is None:
        raise NotFoundError("采购订单不存在")
    if po.status != "draft":
        raise BusinessRuleViolation("只能删除草稿状态的采购订单")

    po.deleted_at = datetime.utcnow()
    await db.commit()
    return ok({"id": po.id, "msg": "删除成功"})


class POReceive(BaseModel):
    warehouse_id: int = 1


@po_router.post("/{po_id}/receive")
async def receive_purchase_order(
    po_id: int,
    body: POReceive = POReceive(),
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(get_current_user),
):
    from app.services.inventory_service import receive_po_item

    result = await db.execute(
        select(PurchaseOrder)
        .where(PurchaseOrder.id == po_id, PurchaseOrder.deleted_at.is_(None))
        .options(selectinload(PurchaseOrder.items))
    )
    po = result.scalar_one_or_none()
    if po is None:
        raise NotFoundError("采购订单不存在")
    if po.status == "received":
        raise BusinessRuleViolation("采购订单已收货")

    assert_can_transition_purchase_order(po.status, "received")

    received_items = []
    for item in po.items:
        if item.product_id and item.quantity > 0:
            try:
                r = await receive_po_item(
                    db, item.product_id, body.warehouse_id, item.quantity, po.id
                )
                received_items.append(r)
            except Exception as e:
                logger.error(
                    "PO receive failed PO#%s product#%s: %s", po.id, item.product_id, e
                )

    po.status = "received"
    await db.commit()

    return ok(
        {
            "po_id": po.id,
            "order_no": po.order_no,
            "status": po.status,
            "items_received": len(received_items),
            "details": received_items,
        }
    )


class RestockItem(BaseModel):
    product_id: int
    quantity: int


class PORestockCreate(BaseModel):
    supplier_id: int
    items: list[RestockItem] = Field(min_length=1, max_length=50)
    notes: str | None = None


@po_router.post("/from-restock", status_code=201)
async def create_po_from_restock(
    body: PORestockCreate,
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(get_current_user),
):
    """One-click restock: create a purchase order from restock suggestions."""
    from app.models.product import Supplier
    from app.models.transaction import PurchaseOrderItem
    from app.services.docno import generate_doc_no

    supplier = (
        await db.execute(
            select(Supplier).where(
                Supplier.id == body.supplier_id, Supplier.deleted_at.is_(None)
            )
        )
    ).scalar_one_or_none()
    if supplier is None:
        raise NotFoundError("供应商不存在")

    # Generate PO number
    po_no = await generate_doc_no(db, "PO", PurchaseOrder, "order_no")

    po = PurchaseOrder(
        order_no=po_no,
        supplier_id=body.supplier_id,
        status="draft",
        total_amount=0,
        notes=body.notes or "AI补货建议自动生成",
    )
    db.add(po)
    await db.flush()

    created = 0
    skipped = 0
    for item in body.items:
        if item.quantity <= 0:
            skipped += 1
            continue
        poi = PurchaseOrderItem(
            order_id=po.id,
            product_id=item.product_id,
            quantity=item.quantity,
            unit_price=0,
            amount=0,
        )
        db.add(poi)
        created += 1

    await db.commit()
    await db.refresh(po)

    return ok(
        {
            "po_id": po.id,
            "order_no": po.order_no,
            "supplier_id": po.supplier_id,
            "items_created": created,
            "items_skipped": skipped,
        }
    )
