"""Transactions API — payment (non-finance) bounded context.

Generic payment records that bridge customer/supplier ledgers. Note
that this is distinct from ``app.api.v1.finance.payments`` which
specifically handles the ``PaymentRecord`` (回款) domain. This router
is for the broader ``Payment`` model used in transaction tracking.
"""

import logging
from datetime import datetime

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.database import get_db
from app.models.transaction import Payment
from app.schemas.common import ok

logger = logging.getLogger(__name__)

pay_router = APIRouter(prefix="/payments", tags=["transactions:payment"])


class PaymentCreate(BaseModel):
    payment_no: str | None = None
    customer_id: int | None = None
    supplier_id: int | None = None
    type: str = "receipt"
    amount: float
    method: str | None = None
    paid_at: str | None = None
    notes: str | None = None


@pay_router.get("")
async def list_payments(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    type: str | None = None,
    customer_id: int | None = None,
    supplier_id: int | None = None,
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(get_current_user),
):
    base = select(Payment).where(Payment.deleted_at.is_(None))
    count_base = select(func.count(Payment.id)).where(Payment.deleted_at.is_(None))

    if type:
        base = base.where(Payment.type == type)
        count_base = count_base.where(Payment.type == type)
    if customer_id:
        base = base.where(Payment.customer_id == customer_id)
        count_base = count_base.where(Payment.customer_id == customer_id)
    if supplier_id:
        base = base.where(Payment.supplier_id == supplier_id)
        count_base = count_base.where(Payment.supplier_id == supplier_id)

    total = (await db.execute(count_base)).scalar() or 0
    rows = (await db.execute(
        base.order_by(Payment.id.desc()).offset((page - 1) * page_size).limit(page_size)
    )).scalars().all()

    return ok({
        "list": [{"id": p.id, "payment_no": p.payment_no, "customer_id": p.customer_id,
                  "supplier_id": p.supplier_id, "type": p.type, "amount": float(p.amount),
                  "method": p.method, "paid_at": str(p.paid_at) if p.paid_at else None,
                  "notes": p.notes, "created_at": str(p.created_at)} for p in rows],
        "total": total, "page": page, "page_size": page_size,
    })


@pay_router.post("", status_code=201)
async def create_payment(body: PaymentCreate, db: AsyncSession = Depends(get_db), _user: dict = Depends(get_current_user)):
    data = body.model_dump()
    if data.get("paid_at"):
        data["paid_at"] = datetime.fromisoformat(data["paid_at"])
    payment = Payment(**data)
    db.add(payment)
    await db.flush()
    return ok({"id": payment.id, "payment_no": payment.payment_no})
