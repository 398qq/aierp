"""Finance CRUD service — invoices, payments, contracts, targets."""

from datetime import datetime, timezone
from decimal import Decimal
from typing import Any

from app.domain.shared.errors import BusinessRuleViolation, NotFoundError
from app.domain.states import (
    assert_can_transition_commission,
    assert_can_transition_contract,
    assert_can_transition_invoice,
    assert_can_transition_payment,
)
from app.models.customer import Customer
from app.models.finance import Commission, Contract, Invoice, PaymentRecord, SalesTarget
from app.models.sales import SalesOrder
from app.services.docno import generate_doc_no
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

_DATE_FIELDS = {
    "invoice_date",
    "due_date",
    "payment_date",
    "signed_date",
    "expire_date",
}

CONTRACT_STATUSES = {"draft", "signed", "active", "expired", "terminated", "cancelled"}
CONTRACT_INITIAL_STATUSES = {"draft", "signed"}
CONTRACT_LOCKED_EDITABLE_FIELDS = {"status", "file_url", "notes"}
DEFAULT_INVOICE_TAX_RATE = Decimal("0.13")


def _calculate_invoice_tax(amount: Any) -> Decimal:
    return (Decimal(str(amount or 0)) * DEFAULT_INVOICE_TAX_RATE).quantize(
        Decimal("0.01")
    )


def _parse_dates(data: dict) -> dict:
    """Convert ISO date strings → datetime for SQLAlchemy. Mutates and returns data."""
    for field in _DATE_FIELDS:
        raw = data.get(field)
        if raw and isinstance(raw, str):
            try:
                data[field] = datetime.fromisoformat(raw.replace("Z", "+00:00"))
            except ValueError:
                pass  # leave as-is; DB will reject invalid values
    return data


async def _apply_sales_order_customer(db: AsyncSession, data: dict) -> None:
    sales_order_id = data.get("sales_order_id")
    if not sales_order_id:
        return

    result = await db.execute(
        select(SalesOrder.customer_id).where(
            SalesOrder.id == sales_order_id, SalesOrder.deleted_at.is_(None)
        )
    )
    customer_id = result.scalar_one_or_none()
    if customer_id:
        data["customer_id"] = customer_id


# ============================================================
# Invoice CRUD
# ============================================================


async def list_invoices(
    db: AsyncSession,
    *,
    page: int = 1,
    page_size: int = 20,
    customer_id: int | None = None,
    status: str | None = None,
    sales_order_id: int | None = None,
    sort_by: str = "id",
    sort_order: str = "desc",
) -> dict:
    base = select(Invoice).where(Invoice.deleted_at.is_(None))
    cnt = select(func.count(Invoice.id)).where(Invoice.deleted_at.is_(None))
    for col_name, val in [
        ("customer_id", customer_id),
        ("status", status),
        ("sales_order_id", sales_order_id),
    ]:
        if val is not None:
            col = getattr(Invoice, col_name)
            base = base.where(col == val)
            cnt = cnt.where(col == val)
    total = (await db.execute(cnt)).scalar() or 0
    sort_col = getattr(Invoice, sort_by, Invoice.id)
    base = base.order_by(sort_col.desc() if sort_order == "desc" else sort_col.asc())
    rows = (
        (await db.execute(base.offset((page - 1) * page_size).limit(page_size)))
        .scalars()
        .all()
    )
    return {"list": rows, "total": total, "page": page, "page_size": page_size}


async def get_invoice(db: AsyncSession, inv_id: int) -> Invoice | None:
    result = await db.execute(
        select(Invoice).where(Invoice.id == inv_id, Invoice.deleted_at.is_(None))
    )
    return result.scalar_one_or_none()


async def create_invoice(db: AsyncSession, data: dict) -> Invoice:
    _parse_dates(data)
    await _apply_sales_order_customer(db, data)
    if data.get("tax_amount") is None:
        data["tax_amount"] = _calculate_invoice_tax(data.get("amount"))
    if not data.get("invoice_no"):
        data["invoice_no"] = await generate_doc_no(db, "INV", Invoice, "invoice_no")
    inv = Invoice(**data)
    db.add(inv)
    await db.commit()
    await db.refresh(inv)
    return inv


async def update_invoice(db: AsyncSession, inv: Invoice, data: dict) -> Invoice:
    _parse_dates(data)
    if "amount" in data and "tax_amount" not in data:
        data["tax_amount"] = _calculate_invoice_tax(data["amount"])
    if "status" in data and data["status"] != inv.status:
        assert_can_transition_invoice(inv.status, data["status"])
    await _apply_sales_order_customer(db, data)
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
    db: AsyncSession,
    *,
    page: int = 1,
    page_size: int = 20,
    customer_id: int | None = None,
    status: str | None = None,
    sales_order_id: int | None = None,
    delivery_note_id: int | None = None,
    invoice_id: int | None = None,
    sort_by: str = "id",
    sort_order: str = "desc",
) -> dict:
    base = select(PaymentRecord).where(PaymentRecord.deleted_at.is_(None))
    cnt = select(func.count(PaymentRecord.id)).where(PaymentRecord.deleted_at.is_(None))
    for col_name, val in [
        ("customer_id", customer_id),
        ("status", status),
        ("sales_order_id", sales_order_id),
        ("delivery_note_id", delivery_note_id),
        ("invoice_id", invoice_id),
    ]:
        if val is not None:
            col = getattr(PaymentRecord, col_name)
            base = base.where(col == val)
            cnt = cnt.where(col == val)
    total = (await db.execute(cnt)).scalar() or 0
    sort_col = getattr(PaymentRecord, sort_by, PaymentRecord.id)
    base = base.order_by(sort_col.desc() if sort_order == "desc" else sort_col.asc())
    rows = (
        (await db.execute(base.offset((page - 1) * page_size).limit(page_size)))
        .scalars()
        .all()
    )
    return {"list": rows, "total": total, "page": page, "page_size": page_size}


async def get_payment(db: AsyncSession, pay_id: int) -> PaymentRecord | None:
    result = await db.execute(
        select(PaymentRecord).where(
            PaymentRecord.id == pay_id, PaymentRecord.deleted_at.is_(None)
        )
    )
    return result.scalar_one_or_none()


async def create_payment(db: AsyncSession, data: dict) -> PaymentRecord:
    _parse_dates(data)
    await _apply_sales_order_customer(db, data)
    pay = PaymentRecord(**data)
    db.add(pay)
    await db.commit()
    await db.refresh(pay)

    # Auto-reconcile linked invoice when payment is completed on creation
    if pay.status == "completed" and pay.invoice_id:
        await _reconcile_invoice_if_fully_paid(db, pay.invoice_id)

    return pay


async def update_payment(
    db: AsyncSession, pay: PaymentRecord, data: dict
) -> PaymentRecord:
    _parse_dates(data)
    if "status" in data and data["status"] != pay.status:
        assert_can_transition_payment(pay.status, data["status"])
    await _apply_sales_order_customer(db, data)
    for k, v in data.items():
        if v is not None:
            setattr(pay, k, v)
    await db.commit()
    await db.refresh(pay)

    # Auto-reconcile linked invoice when payment completes
    if pay.status == "completed" and pay.invoice_id:
        await _reconcile_invoice_if_fully_paid(db, pay.invoice_id)

    return pay


async def _reconcile_invoice_if_fully_paid(db: AsyncSession, invoice_id: int) -> None:
    """Mark invoice as paid when all linked payments are completed."""
    from app.models.finance import Invoice
    from app.services.commission_listener import on_invoice_paid

    inv = await db.scalar(
        select(Invoice).where(Invoice.id == invoice_id, Invoice.deleted_at.is_(None))
    )
    if inv is None or inv.status == "paid":
        return

    total_paid = await db.scalar(
        select(func.coalesce(func.sum(PaymentRecord.amount), 0)).where(
            PaymentRecord.invoice_id == invoice_id,
            PaymentRecord.status == "completed",
            PaymentRecord.deleted_at.is_(None),
        )
    )
    if total_paid and total_paid >= inv.amount:
        inv.status = "paid"
        await db.commit()
        # Stage 7: auto-create draft commission (no-op if already exists)
        await on_invoice_paid(db, invoice_id)


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


def _normalize_contract_data(data: dict) -> dict:
    for field in ("signed_date", "expire_date", "contract_no", "file_url", "notes"):
        if data.get(field) == "":
            data[field] = None
    if data.get("currency"):
        data["currency"] = str(data["currency"]).upper()
    return data


def _validate_contract_status(status: str | None) -> None:
    if status and status not in CONTRACT_STATUSES:
        raise BusinessRuleViolation(f"合同状态无效: {status}")


def _validate_contract_invariants(
    data: dict, *, existing: Contract | None = None
) -> None:
    merged: dict[str, Any] = {}
    if existing is not None:
        merged = {
            "status": existing.status,
            "amount": existing.amount,
            "currency": existing.currency,
            "signed_date": existing.signed_date,
            "expire_date": existing.expire_date,
        }
    merged.update(data)

    status = merged.get("status") or "draft"
    _validate_contract_status(status)

    amount = merged.get("amount")
    if amount is not None and float(amount) < 0:
        raise BusinessRuleViolation("合同金额不能为负")

    currency = merged.get("currency")
    if currency and (len(str(currency)) != 3 or not str(currency).isalpha()):
        raise BusinessRuleViolation("合同币种必须是 3 位字母代码")

    signed_date = merged.get("signed_date")
    expire_date = merged.get("expire_date")
    if signed_date and expire_date and expire_date < signed_date:
        raise BusinessRuleViolation("合同到期日期不能早于签署日期")

    if status in {"signed", "active"} and not signed_date:
        raise BusinessRuleViolation("已签署或履行中的合同必须填写签署日期")

    if status == "expired" and not expire_date:
        raise BusinessRuleViolation("已到期合同必须填写到期日期")


async def _assert_contract_no_available(
    db: AsyncSession, contract_no: str | None, *, exclude_id: int | None = None
) -> None:
    if not contract_no:
        return
    stmt = select(Contract.id).where(
        Contract.contract_no == contract_no,
        Contract.deleted_at.is_(None),
    )
    if exclude_id is not None:
        stmt = stmt.where(Contract.id != exclude_id)
    existing_id = await db.scalar(stmt)
    if existing_id is not None:
        raise BusinessRuleViolation(f"合同号已存在: {contract_no}")


async def _assert_customer_exists(db: AsyncSession, customer_id: int | None) -> None:
    if customer_id is None:
        return
    exists = await db.scalar(
        select(Customer.id).where(
            Customer.id == customer_id, Customer.deleted_at.is_(None)
        )
    )
    if exists is None:
        raise BusinessRuleViolation(f"客户不存在: {customer_id}")


async def list_contracts(
    db: AsyncSession,
    *,
    page: int = 1,
    page_size: int = 20,
    customer_id: int | None = None,
    status: str | None = None,
    sort_by: str = "id",
    sort_order: str = "desc",
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
    rows = (
        (await db.execute(base.offset((page - 1) * page_size).limit(page_size)))
        .scalars()
        .all()
    )
    return {"list": rows, "total": total, "page": page, "page_size": page_size}


async def get_contract(db: AsyncSession, contract_id: int) -> Contract | None:
    result = await db.execute(
        select(Contract).where(
            Contract.id == contract_id, Contract.deleted_at.is_(None)
        )
    )
    return result.scalar_one_or_none()


async def create_contract(db: AsyncSession, data: dict) -> Contract:
    _normalize_contract_data(data)
    _parse_dates(data)
    status = data.get("status") or "draft"
    if status not in CONTRACT_INITIAL_STATUSES:
        raise BusinessRuleViolation(f"合同初始状态不能为 {status}")
    data["status"] = status
    _validate_contract_invariants(data)
    await _apply_sales_order_customer(db, data)
    await _assert_customer_exists(db, data.get("customer_id"))
    await _assert_contract_no_available(db, data.get("contract_no"))
    if not data.get("contract_no"):
        data["contract_no"] = await generate_doc_no(db, "CTR", Contract, "contract_no")
    contract = Contract(**data)
    db.add(contract)
    await db.commit()
    await db.refresh(contract)
    return contract


async def update_contract(db: AsyncSession, contract: Contract, data: dict) -> Contract:
    _normalize_contract_data(data)
    _parse_dates(data)
    if contract.status != "draft":
        locked_fields = set(data) - CONTRACT_LOCKED_EDITABLE_FIELDS
        if locked_fields:
            raise BusinessRuleViolation(
                "已签署或履行后的合同只能更新状态、文件和备注",
                fields=sorted(locked_fields),
            )
    if "status" in data and data["status"] != contract.status:
        assert_can_transition_contract(contract.status, data["status"])
    _validate_contract_invariants(data, existing=contract)
    await _apply_sales_order_customer(db, data)
    if "customer_id" in data:
        await _assert_customer_exists(db, data.get("customer_id"))
    if "contract_no" in data and data["contract_no"] != contract.contract_no:
        await _assert_contract_no_available(
            db, data.get("contract_no"), exclude_id=contract.id
        )
    for k, v in data.items():
        if v is not None:
            setattr(contract, k, v)
    await db.commit()
    await db.refresh(contract)
    return contract


async def delete_contract(db: AsyncSession, contract: Contract) -> None:
    if contract.status != "draft":
        raise BusinessRuleViolation("只能删除草稿合同；已签署合同请走取消或终止流程")
    contract.deleted_at = datetime.now(timezone.utc)
    await db.commit()


# ============================================================
# Sales Target CRUD
# ============================================================


async def list_targets(
    db: AsyncSession,
    *,
    page: int = 1,
    page_size: int = 20,
    user_id: int | None = None,
    status: str | None = None,
    target_type: str | None = None,
    sort_by: str = "id",
    sort_order: str = "desc",
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
    rows = (
        (await db.execute(base.offset((page - 1) * page_size).limit(page_size)))
        .scalars()
        .all()
    )
    return {"list": rows, "total": total, "page": page, "page_size": page_size}


async def get_target(db: AsyncSession, target_id: int) -> SalesTarget | None:
    result = await db.execute(
        select(SalesTarget).where(
            SalesTarget.id == target_id, SalesTarget.deleted_at.is_(None)
        )
    )
    return result.scalar_one_or_none()


async def create_target(db: AsyncSession, data: dict) -> SalesTarget:
    target = SalesTarget(**data)
    db.add(target)
    await db.commit()
    await db.refresh(target)
    return target


async def update_target(
    db: AsyncSession, target: SalesTarget, data: dict
) -> SalesTarget:
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
        "achievement_pct": round(total_actual / total_target * 100, 1)
        if total_target > 0
        else 0,
        "count": len(rows),
        "completed": sum(1 for t in rows if t.status == "completed"),
    }


# ============================================================
# Commission CRUD + state machine
# ============================================================
# State machine definitions imported from app.domain.states


def _compute_commission_amount(base: float, rate: float) -> float:
    """Commission = base * rate. Use Decimal internally to avoid float drift."""
    from decimal import ROUND_HALF_UP, Decimal

    return float(
        Decimal(str(base))
        * Decimal(str(rate)).quantize(Decimal("0.000001"), rounding=ROUND_HALF_UP)
    )


async def list_commissions(
    db: AsyncSession,
    page: int = 1,
    page_size: int = 20,
    status: str | None = None,
    sales_user_id: int | None = None,
) -> dict:
    stmt = select(Commission).where(Commission.deleted_at.is_(None))
    if status:
        stmt = stmt.where(Commission.status == status)
    if sales_user_id:
        stmt = stmt.where(Commission.sales_user_id == sales_user_id)
    stmt = stmt.order_by(Commission.created_at.desc())
    total = await db.scalar(select(func.count()).select_from(stmt.subquery()))
    stmt = stmt.offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(stmt)
    items = [
        c.to_dict() if hasattr(c, "to_dict") else _commission_to_dict(c)
        for c in result.scalars().all()
    ]
    return {"list": items, "total": total or 0, "page": page, "page_size": page_size}


async def get_commission(db: AsyncSession, commission_id: int) -> Commission | None:
    result = await db.execute(
        select(Commission).where(
            Commission.id == commission_id, Commission.deleted_at.is_(None)
        )
    )
    return result.scalar_one_or_none()


async def create_commission(db: AsyncSession, data: dict) -> Commission:
    from app.models.sales import SalesOrder

    so = await db.scalar(
        select(SalesOrder.customer_id).where(
            SalesOrder.id == data["sales_order_id"], SalesOrder.deleted_at.is_(None)
        )
    )
    if not so:
        raise NotFoundError(
            f"sales_order {data['sales_order_id']} not found",
            entity="sales_order",
            id=data["sales_order_id"],
        )
    data["customer_id"] = so

    # 013 scheme engine: resolve scheme-based commission if user & base available
    if data.get("sales_user_id") and data.get("base_amount") is not None:
        try:
            from app.services.commission_scheme_service import compute_commission

            result = await compute_commission(
                db,
                user_id=data["sales_user_id"],
                base_amount=Decimal(str(data["base_amount"])),
                product_category=data.get("product_category"),
                customer_level=None,
                period=data.get("period", ""),
            )
            if result.scheme_id:  # Scheme resolved
                data["rate"] = float(result.rate)
                data["commission_amount"] = float(result.amount)
                data["commission_scheme_id"] = result.scheme_id
                data["scheme_snapshot"] = result.scheme_snapshot
            else:
                # Fallback to hardcoded calculation
                data["commission_amount"] = _compute_commission_amount(
                    data.get("base_amount", 0), data.get("rate", 0)
                )
        except Exception:
            # Fallback if scheme engine fails (e.g. missing migration)
            data["commission_amount"] = _compute_commission_amount(
                data.get("base_amount", 0), data.get("rate", 0)
            )
    else:
        data["commission_amount"] = _compute_commission_amount(
            data.get("base_amount", 0), data.get("rate", 0)
        )

    data.setdefault(
        "commission_no", await generate_doc_no(db, "CM", Commission, "commission_no")
    )
    obj = Commission(**data)
    db.add(obj)
    await db.flush()
    return obj


async def update_commission(
    db: AsyncSession, comm: Commission, data: dict
) -> Commission:
    if "status" in data and data["status"] != comm.status:
        assert_can_transition_commission(comm.status, data["status"])
        if data["status"] == "approved":
            data["approved_at"] = datetime.now(timezone.utc)
        if data["status"] == "paid":
            # Stage 10 Day 1: set paid_at + default paid_amount to commission_amount
            data["paid_at"] = datetime.now(timezone.utc)
            if "paid_amount" not in data and comm.commission_amount is not None:
                data["paid_amount"] = comm.commission_amount
    for k, v in data.items():
        setattr(comm, k, v)
    if "base_amount" in data or "rate" in data:
        comm.commission_amount = _compute_commission_amount(
            comm.base_amount or 0, comm.rate or 0
        )
    await db.flush()
    await db.refresh(comm)
    return comm


async def delete_commission(db: AsyncSession, comm: Commission) -> None:
    comm.deleted_at = datetime.now(timezone.utc)
    await db.flush()


def _commission_to_dict(c) -> dict:
    return {
        "id": c.id,
        "commission_no": c.commission_no,
        "sales_order_id": c.sales_order_id,
        "sales_user_id": c.sales_user_id,
        "customer_id": c.customer_id,
        "base_amount": float(c.base_amount or 0),
        "rate": float(c.rate or 0),
        "commission_amount": float(c.commission_amount or 0),
        "paid_amount": float(c.paid_amount or 0),
        "status": c.status,
        "approved_by": c.approved_by,
        "approved_at": c.approved_at.isoformat() if c.approved_at else None,
        "paid_at": c.paid_at.isoformat() if c.paid_at else None,
        "period": c.period,
        "notes": c.notes,
        "created_at": c.created_at.isoformat() if c.created_at else None,
        "updated_at": c.updated_at.isoformat() if c.updated_at else None,
    }
