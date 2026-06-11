"""Inventory transactions (ledger) API."""

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.database import get_db
from app.models.product import InventoryTransaction, Product, Warehouse
from app.schemas.common import ok

router = APIRouter(prefix="/inventory-transactions", tags=["inventory_transactions"])


@router.get("")
async def list_inventory_transactions(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    warehouse_id: int | None = Query(None),
    product_id: int | None = Query(None),
    type: str | None = Query(
        None, description="Transaction type: stock_in, stock_out, adjust, transfer"
    ),
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(get_current_user),
):
    """
    Paginated inventory transaction ledger.
    Returns transactions with joined product_name and warehouse_name.
    Ordered by created_at DESC.
    """
    base = (
        select(
            InventoryTransaction.id,
            InventoryTransaction.product_id,
            InventoryTransaction.warehouse_id,
            InventoryTransaction.type,
            InventoryTransaction.quantity,
            InventoryTransaction.before_qty,
            InventoryTransaction.after_qty,
            InventoryTransaction.reference_type,
            InventoryTransaction.reference_id,
            InventoryTransaction.notes,
            InventoryTransaction.created_at,
            Product.name.label("product_name"),
            Warehouse.name.label("warehouse_name"),
        )
        .select_from(InventoryTransaction)
        .join(Product, InventoryTransaction.product_id == Product.id)
        .join(Warehouse, InventoryTransaction.warehouse_id == Warehouse.id)
        .where(
            InventoryTransaction.deleted_at.is_(None),
            Product.deleted_at.is_(None),
            Warehouse.deleted_at.is_(None),
        )
    )

    count_base = select(func.count(InventoryTransaction.id)).where(
        InventoryTransaction.deleted_at.is_(None)
    )

    if warehouse_id:
        base = base.where(InventoryTransaction.warehouse_id == warehouse_id)
        count_base = count_base.where(InventoryTransaction.warehouse_id == warehouse_id)
    if product_id:
        base = base.where(InventoryTransaction.product_id == product_id)
        count_base = count_base.where(InventoryTransaction.product_id == product_id)
    if type:
        base = base.where(InventoryTransaction.type == type)
        count_base = count_base.where(InventoryTransaction.type == type)

    total = (await db.execute(count_base)).scalar() or 0
    rows = (
        await db.execute(
            base.order_by(InventoryTransaction.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
    ).all()

    return ok(
        {
            "list": [
                {
                    "id": r[0],
                    "product_id": r[1],
                    "warehouse_id": r[2],
                    "type": r[3],
                    "quantity": r[4],
                    "before_qty": r[5],
                    "after_qty": r[6],
                    "reference_type": r[7],
                    "reference_id": r[8],
                    "notes": r[9],
                    "created_at": str(r[10]) if r[10] else None,
                    "product_name": r[11],
                    "warehouse_name": r[12],
                }
                for r in rows
            ],
            "total": total,
            "page": page,
            "page_size": page_size,
        }
    )
