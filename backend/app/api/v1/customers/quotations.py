from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.permissions import require_perm
from app.database import get_db
from app.models.customer import Customer
from app.models.sales import Quotation
from app.schemas.common import fail, ok

router = APIRouter(prefix="/customers", tags=["customers"])


def _money(value) -> float:
    return float(value or 0)


@router.get("/{customer_id:int}/quotation-history")
async def get_customer_quotation_history(
    customer_id: int,
    status: str | None = Query(None),
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(require_perm("customers", "read")),
):
    customer_exists = await db.scalar(
        select(func.count(Customer.id)).where(Customer.id == customer_id, Customer.deleted_at.is_(None))
    )
    if not customer_exists:
        return fail("客户不存在", 404)

    conditions = [Quotation.customer_id == customer_id, Quotation.deleted_at.is_(None)]
    if status:
        conditions.append(Quotation.status == status)

    rows = (
        await db.execute(
            select(Quotation)
            .where(*conditions)
            .options(selectinload(Quotation.items))
            .order_by(Quotation.created_at.desc(), Quotation.id.desc())
        )
    ).scalars().all()

    quotations = []
    for quote in rows:
        items = [
            {
                "id": item.id,
                "product_id": item.product_id,
                "product_name": item.product_name,
                "quantity": item.quantity,
                "unit_price": _money(item.unit_price),
                "total_price": _money(item.total_price),
            }
            for item in quote.items
            if item.deleted_at is None
        ]
        quotations.append(
            {
                "id": quote.id,
                "quotation_no": quote.quotation_no or f"#{quote.id}",
                "status": quote.status,
                "total_amount": _money(quote.total_amount),
                "valid_until": quote.valid_until,
                "notes": quote.notes,
                "created_at": quote.created_at,
                "items": items,
            }
        )

    total = len(quotations)
    won = sum(1 for quote in rows if quote.status == "won")
    lost = sum(1 for quote in rows if quote.status == "lost")
    pending = sum(1 for quote in rows if quote.status not in {"won", "lost"})
    total_won_amount = sum(_money(quote.total_amount) for quote in rows if quote.status == "won")
    conversion_rate = round(won / total * 100, 1) if total else 0

    return ok(
        {
            "quotations": quotations,
            "total": total,
            "stats": {
                "won": won,
                "lost": lost,
                "pending": pending,
                "conversion_rate": conversion_rate,
                "total_won_amount": total_won_amount,
            },
        }
    )
