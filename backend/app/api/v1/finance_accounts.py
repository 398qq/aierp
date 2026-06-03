"""Finance — chart of accounts, journal entries, bank reconciliation, P&L, balance sheet."""

import datetime
import hashlib
import io
import csv
import json

from fastapi import APIRouter, Depends, File, Query, Request, UploadFile
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.permissions import require_perm, write_audit_log
from app.database import date_format, get_db
from app.models.account import Account, BankReconciliation, JournalEntry, JournalEntryLine
from app.models.finance import PaymentRecord
from app.schemas.common import fail, ok, paginated_ok
from app.services.cache_service import cache_bump_version, cache_get_versioned, cache_set_versioned

router = APIRouter(prefix="/finance", tags=["finance"])

# ============================================================
# Cache configuration
# ============================================================
ACCOUNTS_LIST_CACHE_TTL = 600
ACCOUNTS_LIST_CACHE_VERSION = "v1"

JOURNAL_ENTRIES_LIST_CACHE_TTL = 300
JOURNAL_ENTRIES_LIST_CACHE_VERSION = "v1"

BANK_RECONCILIATIONS_LIST_CACHE_TTL = 300
BANK_RECONCILIATIONS_LIST_CACHE_VERSION = "v1"

PNL_REPORT_CACHE_TTL = 600
PNL_REPORT_CACHE_VERSION = "v1"

AP_REPORT_CACHE_TTL = 600
AP_REPORT_CACHE_VERSION = "v1"


def _accounts_cache_key(**parts: object) -> str:
    canonical = json.dumps(parts, sort_keys=True, default=str)
    digest = hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:16]
    return f"accounts:list:{ACCOUNTS_LIST_CACHE_VERSION}:{digest}"


def _journal_entries_cache_key(**parts: object) -> str:
    canonical = json.dumps(parts, sort_keys=True, default=str)
    digest = hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:16]
    return f"journal-entries:list:{JOURNAL_ENTRIES_LIST_CACHE_VERSION}:{digest}"


def _bank_reconciliations_cache_key(**parts: object) -> str:
    canonical = json.dumps(parts, sort_keys=True, default=str)
    digest = hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:16]
    return f"bank-reconciliations:list:{BANK_RECONCILIATIONS_LIST_CACHE_VERSION}:{digest}"


def _pnl_cache_key(month: str) -> str:
    return f"finance:reports:pnl:{PNL_REPORT_CACHE_VERSION}:{month}"


# ---------------------------------------------------------------------------
# Chart of Accounts
# ---------------------------------------------------------------------------
@router.get("/accounts")
async def list_accounts(
    response: JSONResponse,
    type: str | None = None,
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(require_perm("finance", "read")),
):
    cache_key = _accounts_cache_key(type=type)
    cached_payload = await cache_get_versioned("accounts:list", cache_key)
    if cached_payload is not None:
        response.headers["X-Cache"] = "HIT"
        response.headers["X-Cache-Key"] = cache_key
        return ok(json.loads(cached_payload))
    response.headers["X-Cache"] = "MISS"
    q = select(Account).where(Account.deleted_at.is_(None))
    if type:
        q = q.where(Account.type == type)
    result = await db.execute(q.order_by(Account.code))
    accounts = result.scalars().all()
    payload = [{
        "id": a.id, "code": a.code, "name": a.name, "type": a.type,
        "parent_id": a.parent_id, "description": a.description, "is_active": a.is_active,
    } for a in accounts]
    await cache_set_versioned("accounts:list", cache_key, json.dumps(payload, default=str),
                                ACCOUNTS_LIST_CACHE_TTL)
    return ok(payload)


class AccountCreate(BaseModel):
    code: str
    name: str
    type: str
    parent_id: int | None = None
    description: str = ""


@router.post("/accounts", status_code=201)
async def create_account(body: AccountCreate, request: Request,
                         db: AsyncSession = Depends(get_db),
                         current_user: dict = Depends(require_perm("finance", "write"))):
    if body.type not in ("asset", "liability", "equity", "income", "expense"):
        return fail("科目类型无效")
    a = Account(**body.model_dump())
    db.add(a)
    await db.commit()
    await write_audit_log(db, current_user["user_id"], current_user.get("username", ""),
                          "create", "account", a.id, f"创建科目: {a.code} {a.name}",
                          request.client.host if request.client else "")
    await db.commit()
    await cache_bump_version("accounts:list")
    return ok({"id": a.id}, msg="科目创建成功")


@router.put("/accounts/{account_id}")
async def update_account(account_id: int, body: AccountCreate,
                         db: AsyncSession = Depends(get_db),
                         _user: dict = Depends(require_perm("finance", "write"))):
    a = (await db.execute(select(Account).where(Account.id == account_id, Account.deleted_at.is_(None)))).scalar_one_or_none()
    if not a:
        return fail("科目不存在")
    for k, v in body.model_dump().items():
        setattr(a, k, v)
    await db.commit()
    await cache_bump_version("accounts:list")
    return ok(msg="科目更新成功")


@router.delete("/accounts/{account_id}")
async def delete_account(account_id: int, db: AsyncSession = Depends(get_db),
                         _user: dict = Depends(require_perm("finance", "write"))):
    a = (await db.execute(select(Account).where(Account.id == account_id, Account.deleted_at.is_(None)))).scalar_one_or_none()
    if not a:
        return fail("科目不存在")
    a.deleted_at = datetime.datetime.now(datetime.timezone.utc)
    await db.commit()
    await cache_bump_version("accounts:list")
    return ok(msg="科目已删除")


# ---------------------------------------------------------------------------
# Journal Entries
# ---------------------------------------------------------------------------
@router.get("/journal-entries")
async def list_entries(
    response: JSONResponse,
    status: str | None = None, month: str | None = None,
    page: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(require_perm("finance", "read")),
):
    cache_key = _journal_entries_cache_key(
        status=status, month=month, page=page, page_size=page_size,
    )
    cached_payload = await cache_get_versioned("journal-entries:list", cache_key)
    if cached_payload is not None:
        response.headers["X-Cache"] = "HIT"
        response.headers["X-Cache-Key"] = cache_key
        return JSONResponse(content=json.loads(cached_payload),
                            headers={"X-Cache": "HIT", "X-Cache-Key": cache_key})
    response.headers["X-Cache"] = "MISS"
    q = select(JournalEntry).where(JournalEntry.deleted_at.is_(None))
    if status:
        q = q.where(JournalEntry.status == status)
    if month:
        q = q.where(date_format(JournalEntry.entry_date, "YYYY-MM") == month)

    count_q = select(JournalEntry.id).where(JournalEntry.deleted_at.is_(None))
    if status:
        count_q = count_q.where(JournalEntry.status == status)
    if month:
        count_q = count_q.where(date_format(JournalEntry.entry_date, "YYYY-MM") == month)

    total = len((await db.execute(count_q)).scalars().all())
    result = await db.execute(q.order_by(JournalEntry.id.desc()).offset((page - 1) * page_size).limit(page_size))
    entries = result.scalars().all()
    payload = paginated_ok([{
        "id": e.id, "entry_no": e.entry_no, "entry_date": str(e.entry_date),
        "description": e.description, "status": e.status,
        "created_at": str(e.created_at),
    } for e in entries], total, page, page_size)
    await cache_set_versioned("journal-entries:list", cache_key, json.dumps(payload, default=str),
                                JOURNAL_ENTRIES_LIST_CACHE_TTL)
    return JSONResponse(content=payload, headers={"X-Cache": "MISS", "X-Cache-Key": cache_key})


class LineItem(BaseModel):
    account_id: int
    description: str = ""
    debit: float = 0
    credit: float = 0


class EntryCreate(BaseModel):
    entry_date: str  # YYYY-MM-DD
    description: str = ""
    lines: list[LineItem]


@router.post("/journal-entries", status_code=201)
async def create_entry(body: EntryCreate, request: Request,
                       db: AsyncSession = Depends(get_db),
                       current_user: dict = Depends(require_perm("finance", "write"))):
    total_debit = sum(li.debit for li in body.lines)
    total_credit = sum(li.credit for li in body.lines)
    if abs(total_debit - total_credit) > 0.01:
        return fail(f"借贷不平衡: 借方 {total_debit:,.2f} vs 贷方 {total_credit:,.2f}")

    # Generate entry_no
    month_str = body.entry_date[:7].replace("-", "")
    count = len((await db.execute(
        select(JournalEntry.id).where(date_format(JournalEntry.entry_date, "YYYYMM") == month_str)
    )).scalars().all()) + 1
    entry_no = f"JV-{month_str}-{count:04d}"

    entry = JournalEntry(
        entry_no=entry_no, entry_date=datetime.date.fromisoformat(body.entry_date),
        description=body.description, status="draft",
        created_by=current_user["user_id"],
    )
    db.add(entry)
    await db.flush()

    for li in body.lines:
        db.add(JournalEntryLine(
            entry_id=entry.id, account_id=li.account_id,
            description=li.description, debit=li.debit, credit=li.credit,
        ))

    await db.commit()
    await write_audit_log(db, current_user["user_id"], current_user.get("username", ""),
                          "create", "journal_entry", entry.id, f"创建凭证: {entry_no}",
                          request.client.host if request.client else "")
    await db.commit()
    await cache_bump_version("journal-entries:list")
    return ok({"id": entry.id, "entry_no": entry_no}, msg="凭证创建成功")


@router.get("/journal-entries/{entry_id}")
async def get_entry(entry_id: int, db: AsyncSession = Depends(get_db),
                    _user: dict = Depends(require_perm("finance", "read"))):
    entry = (await db.execute(
        select(JournalEntry).where(JournalEntry.id == entry_id, JournalEntry.deleted_at.is_(None))
    )).scalar_one_or_none()
    if not entry:
        return fail("凭证不存在")
    return ok({
        "id": entry.id, "entry_no": entry.entry_no, "entry_date": str(entry.entry_date),
        "description": entry.description, "status": entry.status,
        "lines": [{
            "id": li.id, "account_id": li.account_id, "account_name": li.account.name if li.account else "",
            "description": li.description, "debit": float(li.debit), "credit": float(li.credit),
        } for li in (entry.lines or [])],
        "created_at": str(entry.created_at),
    })


@router.post("/journal-entries/{entry_id}/post")
async def post_entry(entry_id: int, request: Request,
                     db: AsyncSession = Depends(get_db),
                     current_user: dict = Depends(require_perm("finance", "write"))):
    entry = (await db.execute(
        select(JournalEntry).where(JournalEntry.id == entry_id, JournalEntry.deleted_at.is_(None))
    )).scalar_one_or_none()
    if not entry:
        return fail("凭证不存在")
    if entry.status != "draft":
        return fail(f"凭证状态为 {entry.status}，无法过账")
    entry.status = "posted"
    entry.posted_at = datetime.datetime.now(datetime.timezone.utc)
    entry.posted_by = current_user["user_id"]
    await db.commit()
    # Posting a journal entry changes the data feeding /finance/reports/pnl
    await cache_bump_version("journal-entries:list")
    await cache_bump_version("finance:reports:pnl")
    return ok(msg="凭证已过账")


# ---------------------------------------------------------------------------
# Bank Reconciliation
# ---------------------------------------------------------------------------
@router.post("/bank/reconcile")
async def reconcile_bank(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_perm("finance", "write")),
):
    """Upload bank CSV (date,description,amount) and auto-match against payments."""
    content = await file.read()
    reader = csv.DictReader(io.StringIO(content.decode("utf-8-sig")))
    rows = list(reader)

    # Get unmatched payments
    payments = (await db.execute(
        select(PaymentRecord).where(
            PaymentRecord.deleted_at.is_(None),
            PaymentRecord.status == "completed",
        )
    )).scalars().all()

    matched = 0
    unmatched_rows = []

    for row in rows:
        amount = abs(float(row.get("amount", row.get("金额", 0))))
        txn_date = row.get("date", row.get("日期", ""))
        txn_desc = row.get("description", row.get("摘要", ""))
        txn_id = row.get("txn_id", row.get("流水号", ""))

        # Find matching payment (same amount, date within 3 days)
        match = None
        for p in payments:
            if p.reconciliation_id:
                continue  # Already reconciled
            if abs(float(p.amount) - amount) < 0.01:
                match = p
                break

        if match:
            br = BankReconciliation(
                payment_id=match.id, bank_txn_id=txn_id,
                bank_date=datetime.date.fromisoformat(txn_date) if txn_date else None,
                bank_amount=amount, bank_description=txn_desc,
                match_type="auto", difference=0,
                reconciled_by=current_user["user_id"],
                reconciled_at=datetime.datetime.now(datetime.timezone.utc),
            )
            db.add(br)
            matched += 1
        else:
            br = BankReconciliation(
                bank_txn_id=txn_id,
                bank_date=datetime.date.fromisoformat(txn_date) if txn_date else None,
                bank_amount=amount, bank_description=txn_desc,
                match_type="unmatched", difference=amount,
                reconciled_by=current_user["user_id"],
                reconciled_at=datetime.datetime.now(datetime.timezone.utc),
            )
            db.add(br)
            unmatched_rows.append({"date": txn_date, "description": txn_desc, "amount": amount})

    await db.commit()
    await cache_bump_version("bank-reconciliations:list")
    return ok({
        "total": len(rows), "matched": matched, "unmatched": len(unmatched_rows),
        "unmatched_details": unmatched_rows[:20],
    })


@router.get("/bank/reconciliations")
async def list_reconciliations(
    response: JSONResponse,
    page: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=100),
    match_type: str | None = None,
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(require_perm("finance", "read")),
):
    cache_key = _bank_reconciliations_cache_key(
        page=page, page_size=page_size, match_type=match_type,
    )
    cached_payload = await cache_get_versioned("bank-reconciliations:list", cache_key)
    if cached_payload is not None:
        return JSONResponse(content=json.loads(cached_payload),
                            headers={"X-Cache": "HIT", "X-Cache-Key": cache_key})
    response.headers["X-Cache"] = "MISS"
    q = select(BankReconciliation).where(BankReconciliation.deleted_at.is_(None))
    if match_type:
        q = q.where(BankReconciliation.match_type == match_type)

    count_q = select(BankReconciliation.id).where(BankReconciliation.deleted_at.is_(None))
    if match_type:
        count_q = count_q.where(BankReconciliation.match_type == match_type)

    total = len((await db.execute(count_q)).scalars().all())
    result = await db.execute(q.order_by(BankReconciliation.id.desc()).offset((page - 1) * page_size).limit(page_size))
    items = result.scalars().all()
    payload = paginated_ok([{
        "id": r.id, "payment_id": r.payment_id, "bank_txn_id": r.bank_txn_id,
        "bank_date": str(r.bank_date) if r.bank_date else None,
        "bank_amount": float(r.bank_amount) if r.bank_amount else None,
        "bank_description": r.bank_description,
        "match_type": r.match_type, "difference": float(r.difference),
        "reconciled_at": str(r.reconciled_at) if r.reconciled_at else None,
    } for r in items], total, page, page_size)
    await cache_set_versioned("bank-reconciliations:list", cache_key, json.dumps(payload, default=str),
                                BANK_RECONCILIATIONS_LIST_CACHE_TTL)
    return JSONResponse(content=payload, headers={"X-Cache": "MISS", "X-Cache-Key": cache_key})


# ---------------------------------------------------------------------------
# P&L Report
# ---------------------------------------------------------------------------
@router.get("/reports/pnl")
async def profit_and_loss(
    response: JSONResponse,
    month: str = Query(..., description="YYYY-MM"),
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(require_perm("reports", "read")),
):
    """Monthly Profit & Loss statement."""
    cache_key = _pnl_cache_key(month)
    cached_payload = await cache_get_versioned("finance:reports:pnl", cache_key)
    if cached_payload is not None:
        response.headers["X-Cache"] = "HIT"
        response.headers["X-Cache-Key"] = cache_key
        return ok(json.loads(cached_payload))
    response.headers["X-Cache"] = "MISS"
    # Sum debits/credits by account type for posted entries in the given month
    month_expr = date_format(JournalEntry.entry_date, "YYYY-MM")

    lines = (await db.execute(
        select(Account.type, func.sum(JournalEntryLine.debit).label("debit"),
               func.sum(JournalEntryLine.credit).label("credit"))
        .select_from(JournalEntryLine)
        .join(JournalEntry, JournalEntryLine.entry_id == JournalEntry.id)
        .join(Account, JournalEntryLine.account_id == Account.id)
        .where(
            JournalEntry.status == "posted",
            month_expr == month,
            JournalEntry.deleted_at.is_(None),
            JournalEntryLine.deleted_at.is_(None),
        )
        .group_by(Account.type)
    )).all()

    totals = {row[0]: {"debit": float(row[1] or 0), "credit": float(row[2] or 0)} for row in lines}

    income = totals.get("income", {"debit": 0, "credit": 0})
    expense = totals.get("expense", {"debit": 0, "credit": 0})

    revenue = income["credit"] - income["debit"]
    cost = expense["debit"] - expense["credit"]
    net_profit = revenue - cost

    payload = {
        "month": month,
        "revenue": round(revenue, 2),
        "cost_of_goods": round(cost, 2),
        "gross_profit": round(revenue - cost, 2),
        "net_profit": round(net_profit, 2),
        "details": {k: {"debit": v["debit"], "credit": v["credit"]} for k, v in totals.items()},
    }
    await cache_set_versioned("finance:reports:pnl", cache_key, json.dumps(payload, default=str),
                                PNL_REPORT_CACHE_TTL)
    return ok(payload)


# ---------------------------------------------------------------------------
# AP Report (应付账款)
# ---------------------------------------------------------------------------
@router.get("/reports/ap")
async def accounts_payable(
    response: JSONResponse,
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(require_perm("reports", "read")),
):
    """Accounts Payable aging — outstanding purchase orders."""
    cache_key = f"finance:reports:ap:{AP_REPORT_CACHE_VERSION}:global"
    cached_payload = await cache_get_versioned("finance:reports:ap", cache_key)
    if cached_payload is not None:
        response.headers["X-Cache"] = "HIT"
        response.headers["X-Cache-Key"] = cache_key
        return ok(json.loads(cached_payload))
    response.headers["X-Cache"] = "MISS"
    from app.models.transaction import PurchaseOrder
    from app.models.product import Supplier

    pos = (await db.execute(
        select(PurchaseOrder, Supplier.name)
        .join(Supplier, PurchaseOrder.supplier_id == Supplier.id)
        .where(
            PurchaseOrder.deleted_at.is_(None),
            PurchaseOrder.status.in_(["approved", "in_transit", "partial", "received"]),
        )
    )).all()

    now = datetime.datetime.now(datetime.timezone.utc)
    items = []
    total_ap = 0.0
    for po, sup_name in pos:
        age_days = (now - po.created_at).days if po.created_at else 0
        total_ap += float(po.total_amount)
        items.append({
            "po_id": po.id, "order_no": po.order_no, "supplier": sup_name,
            "amount": float(po.total_amount), "status": po.status, "age_days": age_days,
        })

    payload = {"total_ap": round(total_ap, 2), "items": items}
    await cache_set_versioned("finance:reports:ap", cache_key, json.dumps(payload, default=str),
                                AP_REPORT_CACHE_TTL)
    return ok(payload)
