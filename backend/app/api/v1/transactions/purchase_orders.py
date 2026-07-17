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
from datetime import datetime, timezone

from app.api.deps import get_current_user
from app.database import get_db
from app.domain.shared.errors import BusinessRuleViolation, NotFoundError
from app.domain.states import assert_can_transition_purchase_order
from app.models.transaction import PurchaseOrder
from app.schemas.common import ok
from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

logger = logging.getLogger(__name__)

po_router = APIRouter(prefix="/purchase-orders", tags=["transactions:purchase-order"])


class POItemCreate(BaseModel):
    product_id: int
    sales_order_id: int | None = None
    supplier_mpn: str | None = None
    product_sku: str | None = None
    product_name: str | None = None
    brand_name: str | None = None
    package_type: str | None = None
    quantity: int = Field(1, gt=0)
    unit: str = "pcs"
    min_pack_qty: int | None = Field(None, gt=0)
    min_pack_unit: str | None = None
    date_code_requirement: str = "不限"
    tax_rate: float = Field(13, ge=0, le=100)
    unit_price: float = Field(0, ge=0)
    amount: float = 0
    customer_name: str | None = None
    notes: str | None = None


class POCreate(BaseModel):
    order_no: str | None = None
    supplier_id: int
    status: str = "draft"
    sales_order_id: int | None = None
    supplier_contact: str | None = None
    payment_terms: str | None = None
    currency: str = "CNY"
    incoterms: str | None = None
    delivery_address: str | None = None
    tax_rate: float = Field(13, ge=0, le=100)
    expected_date: str | None = None
    allow_partial_delivery: bool = False
    contract_terms_version: str = "v3.4"
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
    q: str | None = None,
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
            PurchaseOrder.supplier_confirmation_status,
            PurchaseOrder.sales_order_id,
            PurchaseOrder.large_order_confirmed,
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
    if q and q.strip():
        keyword = f"%{q.strip()}%"
        search_filter = or_(
            PurchaseOrder.order_no.ilike(keyword),
            Supplier.name.ilike(keyword),
        )
        base = base.where(search_filter)
        count_base = count_base.join(
            Supplier, PurchaseOrder.supplier_id == Supplier.id, isouter=True
        ).where(search_filter)

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
                    "supplier_confirmation_status": r[7],
                    "sales_order_id": r[8],
                    "large_order_confirmed": r[9],
                    "notes": r[10],
                    "created_at": str(r[11]) if r[11] else None,
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
    from app.models.product import Supplier
    from app.models.transaction import PurchaseOrderItem

    data = body.model_dump()
    items_data = data.pop("items", None)
    if data.get("expected_date"):
        data["expected_date"] = datetime.fromisoformat(data["expected_date"])

    if not data.get("order_no"):
        from app.services.docno import generate_doc_no

        data["order_no"] = await generate_doc_no(db, "PO", PurchaseOrder, "order_no")

    supplier = await db.get(Supplier, body.supplier_id)
    if supplier is None or supplier.deleted_at is not None:
        raise NotFoundError("供应商不存在")
    data["supplier_contact"] = data.get("supplier_contact") or supplier.contact_person
    data["payment_terms"] = data.get("payment_terms") or supplier.payment_terms
    data.pop("status", None)
    order = PurchaseOrder(**data, status="draft")
    db.add(order)
    await db.flush()

    if items_data:
        total = 0.0
        for item in items_data:
            item["amount"] = round(item["quantity"] * item["unit_price"], 6)
            poi = PurchaseOrderItem(order_id=order.id, **item)
            db.add(poi)
            total += item["amount"]
        order.total_amount = total
        order.subtotal = round(total / (1 + float(order.tax_rate) / 100), 6)
        order.tax_amount = round(total - float(order.subtotal), 6)

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
    sales_order_id: int | None = None
    supplier_contact: str | None = None
    payment_terms: str | None = None
    currency: str | None = None
    incoterms: str | None = None
    delivery_address: str | None = None
    tax_rate: float | None = Field(None, ge=0, le=100)
    expected_date: str | None = None
    allow_partial_delivery: bool | None = None
    notes: str | None = None
    items: list[POItemCreate] | None = None


@po_router.get("/{po_id}")
async def get_purchase_order(
    po_id: int,
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(get_current_user),
):
    from app.models.customer import Customer
    from app.models.product import Product, Supplier
    from app.models.sales import SalesOrder
    from app.models.transaction import PurchaseOrderItem

    result = await db.execute(
        select(PurchaseOrder)
        .where(PurchaseOrder.id == po_id, PurchaseOrder.deleted_at.is_(None))
        .options(
            selectinload(PurchaseOrder.items)
            .selectinload(PurchaseOrderItem.product)
            .selectinload(Product.brand)
        )
    )
    po = result.scalar_one_or_none()
    if po is None:
        raise NotFoundError("采购订单不存在")

    supplier = None
    if po.supplier_id:
        supplier = await db.get(Supplier, po.supplier_id)
    sales_order_no = None
    customer_name = None
    if po.sales_order_id:
        so_row = (
            await db.execute(
                select(SalesOrder.order_no, Customer.name)
                .join(Customer, SalesOrder.customer_id == Customer.id)
                .where(SalesOrder.id == po.sales_order_id)
            )
        ).one_or_none()
        if so_row:
            sales_order_no, customer_name = so_row

    return ok(
        {
            "id": po.id,
            "order_no": po.order_no,
            "supplier_id": po.supplier_id,
            "supplier_name": supplier.name if supplier else f"#{po.supplier_id}",
            "supplier_contact": po.supplier_contact,
            "sales_order_id": po.sales_order_id,
            "sales_order_no": sales_order_no,
            "customer_name": customer_name,
            "status": po.status,
            "currency": po.currency,
            "incoterms": po.incoterms,
            "payment_terms": po.payment_terms,
            "delivery_address": po.delivery_address,
            "tax_rate": float(po.tax_rate),
            "subtotal": float(po.subtotal),
            "tax_amount": float(po.tax_amount),
            "total_amount": float(po.total_amount),
            "expected_date": str(po.expected_date) if po.expected_date else None,
            "notes": po.notes,
            "allow_partial_delivery": po.allow_partial_delivery,
            "large_order_confirmed": po.large_order_confirmed,
            "large_order_confirmed_at": str(po.large_order_confirmed_at) if po.large_order_confirmed_at else None,
            "supplier_confirmation_status": po.supplier_confirmation_status,
            "supplier_confirmed_at": str(po.supplier_confirmed_at) if po.supplier_confirmed_at else None,
            "supplier_confirmation_method": po.supplier_confirmation_method,
            "supplier_confirmed_delivery_date": str(po.supplier_confirmed_delivery_date) if po.supplier_confirmed_delivery_date else None,
            "contract_terms_version": po.contract_terms_version,
            "sent_at": str(po.sent_at) if po.sent_at else None,
            "created_at": str(po.created_at),
            "updated_at": str(po.updated_at) if po.updated_at else None,
            "items": [
                {
                    "id": i.id,
                    "product_id": i.product_id,
                    "sales_order_id": i.sales_order_id,
                    "supplier_mpn": i.supplier_mpn or (i.product.mpn if i.product else None),
                    "product_name": i.product_name or (i.product.name if i.product else f"#{i.product_id}"),
                    "product_sku": i.product_sku or (i.product.sku if i.product else ""),
                    "brand_name": i.brand_name or (i.product.brand.name if i.product and i.product.brand else None),
                    "package_type": i.package_type or (i.product.package_type if i.product else None),
                    "quantity": i.quantity,
                    "unit": i.unit or "pcs",
                    "min_pack_qty": i.min_pack_qty,
                    "min_pack_unit": i.min_pack_unit,
                    "date_code_requirement": i.date_code_requirement or "不限",
                    "tax_rate": float(i.tax_rate) if i.tax_rate is not None else 13,
                    "unit_price": float(i.unit_price),
                    "amount": float(i.amount),
                    "customer_name": i.customer_name,
                    "notes": i.notes,
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

    for field in (
        "supplier_id", "sales_order_id", "supplier_contact", "payment_terms",
        "currency", "incoterms", "delivery_address", "tax_rate",
        "allow_partial_delivery", "notes",
    ):
        if field in data:
            setattr(po, field, data[field])
    if "expected_date" in data and data["expected_date"]:
        po.expected_date = datetime.fromisoformat(data["expected_date"])
    if items_data is not None:
        for item in po.items:
            await db.delete(item)
        total = 0.0
        for item in items_data:
            item["amount"] = round(item["quantity"] * item["unit_price"], 6)
            poi = PurchaseOrderItem(order_id=po.id, **item)
            db.add(poi)
            total += item.get("amount", 0) or 0
        po.total_amount = total
        po.subtotal = round(total / (1 + float(po.tax_rate) / 100), 6)
        po.tax_amount = round(total - float(po.subtotal), 6)

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


class POTransition(BaseModel):
    target_status: str


@po_router.post("/{po_id}/confirm-large-order")
async def confirm_large_purchase_order(
    po_id: int,
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(get_current_user),
):
    po = await db.get(PurchaseOrder, po_id)
    if po is None or po.deleted_at is not None:
        raise NotFoundError("采购订单不存在")
    if po.status != "draft":
        raise BusinessRuleViolation("只有草稿采购订单可以执行大额二次确认")
    po.large_order_confirmed = True
    po.large_order_confirmed_at = datetime.now(timezone.utc)
    await db.commit()
    return ok({"id": po.id, "large_order_confirmed": True})


@po_router.post("/{po_id}/transition")
async def transition_purchase_order(
    po_id: int,
    body: POTransition,
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(get_current_user),
):
    po = (
        await db.execute(
            select(PurchaseOrder)
            .where(PurchaseOrder.id == po_id, PurchaseOrder.deleted_at.is_(None))
            .options(selectinload(PurchaseOrder.items))
        )
    ).scalar_one_or_none()
    if po is None:
        raise NotFoundError("采购订单不存在")
    assert_can_transition_purchase_order(po.status, body.target_status)
    if body.target_status == "approved":
        if not po.items:
            raise BusinessRuleViolation("空采购订单不能审批")
        missing_headers = [
            label
            for value, label in (
                (po.supplier_contact, "供应商联系人"),
                (po.payment_terms, "付款方式"),
                (po.expected_date, "预计交期"),
                (po.delivery_address, "交货地址"),
            )
            if not value
        ]
        if missing_headers:
            raise BusinessRuleViolation(
                f"采购订单头信息不完整: {', '.join(missing_headers)}"
            )
        missing = [
            str(item.product_sku or item.product_id)
            for item in po.items
            if not all(
                (
                    item.supplier_mpn,
                    item.product_sku,
                    item.product_name,
                    item.brand_name,
                    item.package_type,
                    item.date_code_requirement,
                )
            )
        ]
        if missing:
            raise BusinessRuleViolation(
                f"以下明细缺少 MPN/SKU/品名/品牌/封装/生产批次: {', '.join(missing)}"
            )
        if float(po.total_amount) > 10000 and not po.large_order_confirmed:
            raise BusinessRuleViolation("采购金额超过 ¥10,000，须先完成二次确认")
    if body.target_status == "ordered":
        po.sent_at = datetime.now(timezone.utc)
        po.supplier_confirmation_status = "pending"
    po.status = body.target_status
    await db.commit()
    return ok({"id": po.id, "status": po.status})


class POSupplierConfirmation(BaseModel):
    method: str
    confirmed_delivery_date: str
    allow_partial_delivery: bool = False


@po_router.post("/{po_id}/supplier-confirmation")
async def record_supplier_confirmation(
    po_id: int,
    body: POSupplierConfirmation,
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(get_current_user),
):
    po = await db.get(PurchaseOrder, po_id)
    if po is None or po.deleted_at is not None:
        raise NotFoundError("采购订单不存在")
    if po.status not in {"ordered", "partially_received"}:
        raise BusinessRuleViolation("采购订单发送给供应商后才能记录确认")
    po.supplier_confirmation_status = "confirmed"
    po.supplier_confirmation_method = body.method
    po.supplier_confirmed_at = datetime.now(timezone.utc)
    po.supplier_confirmed_delivery_date = datetime.fromisoformat(
        body.confirmed_delivery_date
    )
    po.allow_partial_delivery = body.allow_partial_delivery
    await db.commit()
    return ok({"id": po.id, "supplier_confirmation_status": "confirmed"})


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

    if po.supplier_confirmation_status != "confirmed":
        raise BusinessRuleViolation("供应商尚未完成书面确认，不能收货")

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
