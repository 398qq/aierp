"""Finance CRUD service — invoices, payments, contracts, targets."""

from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.finance import Contract, Invoice, PaymentRecord, SalesTarget


# ============================================================
# Document Number Generation
# ============================================================

async def _gen_no(db: AsyncSession, prefix: str, model) -> str:
    now = datetime.now(timezone.utc)
    date_part = now.strftime("%Y%m%d")
    col = getattr(model, list(model.__table__.columns.keys())[1])
    result = await db.execute(
        select(func.count()).where(col.like(f"{prefix}{date_part}%"))
    )
    seq = (result.scalar() or 0) + 1
    return f"{prefix}{date_part}{seq:04d}"


# ============================================================
# Invoice CRUD
# ============================================================

async def list_invoices(
    db: AsyncSession, *, page: int = 1, page_size: int = 20,
    customer_id: int | None = None, status: str | None = None,
    sales_order_id: int | None = None,
    sort_by: str = "id", sort_order: str = "desc",
) -> dict:
    base = select(Invoice).where(Invoice.deleted_at.is_(None))
    cnt = select(func.count(Invoice.id)).where(Invoice.deleted_at.is_(None))
    for col_name, val in [("customer_id", customer_id), ("status", status), ("sales_order_id", sales_order_id)]:
        if val is not None:
            col = getattr(Invoice, col_name)
            base = base.where(col == val)
            cnt = cnt.where(col == val)
    total = (await db.execute(cnt)).scalar() or 0
    sort_col = getattr(Invoice, sort_by, Invoice.id)
    base = base.order_by(sort_col.desc() if sort_order == "desc" else sort_col.asc())
    rows = (await db.execute(base.offset((page - 1) * page_size).limit(page_size))).scalars().all()
    return {"list": rows, "total": total, "page": page, "page_size": page_size}


async def get_invoice(db: AsyncSession, inv_id: int) -> Invoice | None:
    result = await db.execute(
        select(Invoice).where(Invoice.id == inv_id, Invoice.deleted_at.is_(None))
    )
    return result.scalar_one_or_none()


async def create_invoice(db: AsyncSession, data: dict) -> Invoice:
    if not data.get("invoice_no"):
        data["invoice_no"] = await _gen_no(db, "INV", Invoice)
    inv = Invoice(**data)
    db.add(inv)
    await db.commit()
    await db.refresh(inv)
    return inv


async def update_invoice(db: AsyncSession, inv: Invoice, data: dict) -> Invoice:
    for k, v in data.items():
        if v is not None:
            setattr(inv, k, v)
    await db.commit()
    await db.refresh(inv)
    return inv


async def delete_invoice(db: AsyncSession, inv: Invoice) -> None:
    inv.deleted_at = datetime.now(timezone.utc)
    await db.commit()


# ============================================================
# Payment CRUD
# ============================================================

async def list_payments(
    db: AsyncSession, *, page: int = 1, page_size: int = 20,
    customer_id: int | None = None, status: str | None = None,
    sales_order_id: int | None = None,
    sort_by: str = "id", sort_order: str = "desc",
) -> dict:
    base = select(PaymentRecord).where(PaymentRecord.deleted_at.is_(None))
    cnt = select(func.count(PaymentRecord.id)).where(PaymentRecord.deleted_at.is_(None))
    for col_name, val in [("customer_id", customer_id), ("status", status), ("sales_order_id", sales_order_id)]:
        if val is not None:
            col = getattr(PaymentRecord, col_name)
            base = base.where(col == val)
            cnt = cnt.where(col == val)
    total = (await db.execute(cnt)).scalar() or 0
    sort_col = getattr(PaymentRecord, sort_by, PaymentRecord.id)
    base = base.order_by(sort_col.desc() if sort_order == "desc" else sort_col.asc())
    rows = (await db.execute(base.offset((page - 1) * page_size).limit(page_size))).scalars().all()
    return {"list": rows, "total": total, "page": page, "page_size": page_size}


async def get_payment(db: AsyncSession, pay_id: int) -> PaymentRecord | None:
    result = await db.execute(
        select(PaymentRecord).where(PaymentRecord.id == pay_id, PaymentRecord.deleted_at.is_(None))
    )
    return result.scalar_one_or_none()


async def create_payment(db: AsyncSession, data: dict) -> PaymentRecord:
    pay = PaymentRecord(**data)
    db.add(pay)
    await db.commit()
    await db.refresh(pay)
    return pay


async def update_payment(db: AsyncSession, pay: PaymentRecord, data: dict) -> PaymentRecord:
    for k, v in data.items():
        if v is not None:
            setattr(pay, k, v)
    await db.commit()
    await db.refresh(pay)
    return pay


async def delete_payment(db: AsyncSession, pay: PaymentRecord) -> None:
    pay.deleted_at = datetime.now(timezone.utc)
    await db.commit()


async def payment_stats(db: AsyncSession) -> dict:
    base = select(PaymentRecord).where(PaymentRecord.deleted_at.is_(None))
    rows = (await db.execute(base)).scalars().all()
    total_received = sum(p.amount for p in rows if p.status == "completed")
    total_pending = sum(p.amount for p in rows if p.status == "pending")
    total_overdue = sum(p.amount for p in rows if p.status == "overdue")
    by_method: dict[str, float] = {}
    for p in rows:
        m = p.payment_method or "other"
        by_method[m] = by_method.get(m, 0) + p.amount
    return {
        "total_received": total_received,
        "total_pending": total_pending,
        "total_overdue": total_overdue,
        "by_method": by_method,
        "monthly": [],
    }


# ============================================================
# Contract CRUD
# ============================================================

async def list_contracts(
    db: AsyncSession, *, page: int = 1, page_size: int = 20,
    customer_id: int | None = None, status: str | None = None,
    sort_by: str = "id", sort_order: str = "desc",
) -> dict:
    base = select(Contract).where(Contract.deleted_at.is_(None))
    cnt = select(func.count(Contract.id)).where(Contract.deleted_at.is_(None))
    if customer_id:
        base = base.where(Contract.customer_id == customer_id)
        cnt = cnt.where(Contract.customer_id == customer_id)
    if status:
        base = base.where(Contract.status == status)
        cnt = cnt.where(Contract.status == status)
    total = (await db.execute(cnt)).scalar() or 0
    sort_col = getattr(Contract, sort_by, Contract.id)
    base = base.order_by(sort_col.desc() if sort_order == "desc" else sort_col.asc())
    rows = (await db.execute(base.offset((page - 1) * page_size).limit(page_size))).scalars().all()
    return {"list": rows, "total": total, "page": page, "page_size": page_size}


async def get_contract(db: AsyncSession, contract_id: int) -> Contract | None:
    result = await db.execute(
        select(Contract).where(Contract.id == contract_id, Contract.deleted_at.is_(None))
    )
    return result.scalar_one_or_none()


async def create_contract(db: AsyncSession, data: dict) -> Contract:
    if not data.get("contract_no"):
        data["contract_no"] = await _gen_no(db, "CTR", Contract)
    contract = Contract(**data)
    db.add(contract)
    await db.commit()
    await db.refresh(contract)
    return contract


async def update_contract(db: AsyncSession, contract: Contract, data: dict) -> Contract:
    for k, v in data.items():
        if v is not None:
            setattr(contract, k, v)
    await db.commit()
    await db.refresh(contract)
    return contract


async def delete_contract(db: AsyncSession, contract: Contract) -> None:
    contract.deleted_at = datetime.now(timezone.utc)
    await db.commit()


# ============================================================
# Sales Target CRUD
# ============================================================

async def list_targets(
    db: AsyncSession, *, page: int = 1, page_size: int = 20,
    user_id: int | None = None, status: str | None = None,
    target_type: str | None = None,
    sort_by: str = "id", sort_order: str = "desc",
) -> dict:
    base = select(SalesTarget).where(SalesTarget.deleted_at.is_(None))
    cnt = select(func.count(SalesTarget.id)).where(SalesTarget.deleted_at.is_(None))
    if user_id:
        base = base.where(SalesTarget.user_id == user_id)
        cnt = cnt.where(SalesTarget.user_id == user_id)
    if status:
        base = base.where(SalesTarget.status == status)
        cnt = cnt.where(SalesTarget.status == status)
    if target_type:
        base = base.where(SalesTarget.target_type == target_type)
        cnt = cnt.where(SalesTarget.target_type == target_type)
    total = (await db.execute(cnt)).scalar() or 0
    sort_col = getattr(SalesTarget, sort_by, SalesTarget.id)
    base = base.order_by(sort_col.desc() if sort_order == "desc" else sort_col.asc())
    rows = (await db.execute(base.offset((page - 1) * page_size).limit(page_size))).scalars().all()
    return {"list": rows, "total": total, "page": page, "page_size": page_size}


async def get_target(db: AsyncSession, target_id: int) -> SalesTarget | None:
    result = await db.execute(
        select(SalesTarget).where(SalesTarget.id == target_id, SalesTarget.deleted_at.is_(None))
    )
    return result.scalar_one_or_none()


async def create_target(db: AsyncSession, data: dict) -> SalesTarget:
    target = SalesTarget(**data)
    db.add(target)
    await db.commit()
    await db.refresh(target)
    return target


async def update_target(db: AsyncSession, target: SalesTarget, data: dict) -> SalesTarget:
    for k, v in data.items():
        if v is not None:
            setattr(target, k, v)
    await db.commit()
    await db.refresh(target)
    return target


async def delete_target(db: AsyncSession, target: SalesTarget) -> None:
    target.deleted_at = datetime.now(timezone.utc)
    await db.commit()


async def target_stats(db: AsyncSession) -> dict:
    base = select(SalesTarget).where(SalesTarget.deleted_at.is_(None))
    rows = (await db.execute(base)).scalars().all()
    total_target = sum(t.target_amount for t in rows)
    total_actual = sum(t.actual_amount for t in rows)
    return {
        "total_target": total_target,
        "total_actual": total_actual,
        "achievement_pct": round(total_actual / total_target * 100, 1) if total_target > 0 else 0,
        "count": len(rows),
        "completed": sum(1 for t in rows if t.status == "completed"),
    }
