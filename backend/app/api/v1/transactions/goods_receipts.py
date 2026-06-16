"""Goods Receipt API — record physical receipt + auto-create inventory batches."""

import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.database import get_db
from app.models.transaction import GoodsReceipt, GoodsReceiptItem, PurchaseOrder
from app.schemas.common import fail, ok
from app.services.inventory_batch_service import inventory_batch_service
from app.services.docno import generate_doc_no

logger = logging.getLogger(__name__)

gr_router = APIRouter(prefix="/goods-receipts", tags=["transactions:goods-receipt"])


class ReceiptItemIn(BaseModel):
    product_id: int
    quantity_received: int = Field(gt=0)
    unit_cost: float = Field(gt=0)
    batch_no: str | None = None


class GoodsReceiptIn(BaseModel):
    purchase_order_id: int
    warehouse_id: int = 1
    items: list[ReceiptItemIn]
    notes: str | None = None


@gr_router.get("")
async def list_receipts(
    page: int = 1,
    page_size: int = 20,
    purchase_order_id: int | None = None,
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(get_current_user),
):
    from sqlalchemy import func

    base = select(GoodsReceipt).where(GoodsReceipt.deleted_at.is_(None))
    if purchase_order_id:
        base = base.where(GoodsReceipt.purchase_order_id == purchase_order_id)
    total = (
        await db.execute(select(func.count()).select_from(base.subquery()))
    ).scalar() or 0
    rows = (
        (
            await db.execute(
                base.order_by(GoodsReceipt.id.desc())
                .offset((page - 1) * page_size)
                .limit(page_size)
            )
        )
        .scalars()
        .all()
    )

    return ok(
        {
            "list": [
                {
                    "id": r.id,
                    "receipt_no": r.receipt_no,
                    "purchase_order_id": r.purchase_order_id,
                    "status": r.status,
                    "received_date": str(r.received_date) if r.received_date else None,
                    "notes": r.notes,
                }
                for r in rows
            ],
            "total": total,
            "page": page,
            "page_size": page_size,
        }
    )


@gr_router.post("", status_code=201)
async def create_receipt(
    body: GoodsReceiptIn,
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(get_current_user),
):
    """Record goods receipt and auto-create inventory batches with actual costs."""
    # Validate PO exists
    po = (
        await db.execute(
            select(PurchaseOrder).where(
                PurchaseOrder.id == body.purchase_order_id,
                PurchaseOrder.deleted_at.is_(None),
            )
        )
    ).scalar_one_or_none()
    if not po:
        return fail("采购订单不存在", 404)

    receipt_no = await generate_doc_no(db, "GR", GoodsReceipt, "receipt_no")
    receipt = GoodsReceipt(
        receipt_no=receipt_no,
        purchase_order_id=body.purchase_order_id,
        supplier_id=po.supplier_id,
        received_date=datetime.now(timezone.utc),
        status="received",
        notes=body.notes,
    )
    db.add(receipt)
    await db.flush()

    for item_in in body.items:
        gr_item = GoodsReceiptItem(
            receipt_id=receipt.id,
            product_id=item_in.product_id,
            quantity_received=item_in.quantity_received,
            unit_cost=item_in.unit_cost,
            amount=item_in.quantity_received * item_in.unit_cost,
            batch_no=item_in.batch_no or f"{receipt_no}-{item_in.product_id}",
        )
        db.add(gr_item)

        # Auto-create inventory batch with actual cost
        await inventory_batch_service.create_batches_from_receipt(
            db,
            product_id=item_in.product_id,
            warehouse_id=body.warehouse_id,
            batch_no=item_in.batch_no or f"{receipt_no}-{item_in.product_id}",
            quantity=item_in.quantity_received,
            unit_cost=item_in.unit_cost,
            supplier_id=po.supplier_id,
            received_date=datetime.now(timezone.utc),
            notes=f"PO #{body.purchase_order_id} 收货",
        )

    await db.commit()
    await db.refresh(receipt)
    logger.info(
        "Goods receipt %s created with %d items + batches", receipt_no, len(body.items)
    )
    return ok(
        {"id": receipt.id, "receipt_no": receipt_no, "batches_created": len(body.items)}
    )
