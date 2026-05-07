"""Contracts API."""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.database import get_db
from app.models.finance import Contract, Invoice, PaymentRecord
from app.models.sales import SalesOrder
from app.schemas.common import fail, ok
from app.schemas.finance import ContractCreate, ContractUpdate

router = APIRouter(prefix="/sales/contracts", tags=["contracts"])


def _parse_date(value: str | None) -> datetime | None:
    if value:
        return datetime.fromisoformat(value)
    return None


def _serialize_dt(dt: datetime | None) -> str | None:
    return str(dt) if dt else None


def _contract_row(c: Contract) -> dict:
    return {
        "id": c.id, "contract_no": c.contract_no, "customer_id": c.customer_id,
        "sales_order_id": c.sales_order_id, "title": c.title,
        "amount": float(c.amount), "signed_date": _serialize_dt(c.signed_date),
        "expire_date": _serialize_dt(c.expire_date), "status": c.status,
        "file_url": c.file_url, "notes": c.notes, "created_at": str(c.created_at),
    }


@router.get("")
async def list_contracts(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    customer_id: int | None = None,
    status: str | None = None,
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(get_current_user),
):
    base = select(Contract).where(Contract.deleted_at.is_(None))
    count_base = select(func.count(Contract.id)).where(Contract.deleted_at.is_(None))

    if customer_id:
        base = base.where(Contract.customer_id == customer_id)
        count_base = count_base.where(Contract.customer_id == customer_id)
    if status:
        base = base.where(Contract.status == status)
        count_base = count_base.where(Contract.status == status)

    total = (await db.execute(count_base)).scalar() or 0
    rows = (await db.execute(
        base.order_by(Contract.id.desc()).offset((page - 1) * page_size).limit(page_size)
    )).scalars().all()

    return ok({
        "list": [_contract_row(c) for c in rows],
        "total": total, "page": page, "page_size": page_size,
    })


@router.get("/{contract_id}")
async def get_contract(contract_id: int, db: AsyncSession = Depends(get_db), _user: dict = Depends(get_current_user)):
    result = await db.execute(
        select(Contract).where(Contract.id == contract_id, Contract.deleted_at.is_(None))
    )
    contract = result.scalar_one_or_none()
    if contract is None:
        return fail("Contract not found", 404)
    data = _contract_row(contract)

    # related orders
    if contract.sales_order_id:
        so_result = await db.execute(
            select(SalesOrder).where(SalesOrder.id == contract.sales_order_id, SalesOrder.deleted_at.is_(None))
        )
        so = so_result.scalar_one_or_none()
        if so:
            data["sales_order"] = {"id": so.id, "order_no": so.order_no, "status": so.status, "total_amount": float(so.total_amount)}

    # related invoices
    inv_result = await db.execute(
        select(Invoice).where(Invoice.sales_order_id == contract.sales_order_id, Invoice.deleted_at.is_(None))
    )
    data["invoices"] = [{"id": i.id, "invoice_no": i.invoice_no, "amount": float(i.amount), "status": i.status} for i in inv_result.scalars().all()]

    # related payments
    pay_result = await db.execute(
        select(PaymentRecord).where(PaymentRecord.sales_order_id == contract.sales_order_id, PaymentRecord.deleted_at.is_(None))
    )
    data["payments"] = [{"id": p.id, "amount": float(p.amount), "payment_method": p.payment_method, "status": p.status} for p in pay_result.scalars().all()]

    return ok(data)


@router.post("", status_code=201)
async def create_contract(body: ContractCreate, db: AsyncSession = Depends(get_db), _user: dict = Depends(get_current_user)):
    data = body.model_dump()
    for field in ("signed_date", "expire_date"):
        if data.get(field):
            data[field] = _parse_date(data[field])
    contract = Contract(**data)
    db.add(contract)
    await db.flush()
    return ok({"id": contract.id, "contract_no": contract.contract_no})


@router.put("/{contract_id}")
async def update_contract(contract_id: int, body: ContractUpdate, db: AsyncSession = Depends(get_db), _user: dict = Depends(get_current_user)):
    result = await db.execute(
        select(Contract).where(Contract.id == contract_id, Contract.deleted_at.is_(None))
    )
    contract = result.scalar_one_or_none()
    if contract is None:
        return fail("Contract not found", 404)
    data = body.model_dump(exclude_unset=True)
    for field in ("signed_date", "expire_date"):
        if data.get(field):
            data[field] = _parse_date(data[field])
    for key, val in data.items():
        setattr(contract, key, val)
    await db.flush()
    return ok({"id": contract.id})


@router.delete("/{contract_id}")
async def delete_contract(contract_id: int, db: AsyncSession = Depends(get_db), _user: dict = Depends(get_current_user)):
    result = await db.execute(
        select(Contract).where(Contract.id == contract_id, Contract.deleted_at.is_(None))
    )
    contract = result.scalar_one_or_none()
    if contract is None:
        return fail("Contract not found", 404)
    contract.deleted_at = datetime.now(timezone.utc)
    await db.flush()
    return ok(msg="deleted")
