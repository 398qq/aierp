"""Finance accounts API — bank reconciliation bounded context.

Routes:
- /bank/reconcile        : heavy CSV upload + auto-match against payments
- /bank/reconciliations  : paginated list of past reconciliations
"""

import csv
import datetime
import io
import json
import logging

from fastapi import APIRouter, Depends, File, Query, UploadFile
from fastapi.responses import JSONResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.permissions import require_perm
from app.database import get_db
from app.models.account import BankReconciliation
from app.models.finance import PaymentRecord
from app.schemas.common import fail, ok, paginated_ok
from app.api.v1.finance_accounts._shared import (
    BANK_RECONCILIATIONS_LIST_CACHE_TTL,
    _bank_reconciliations_cache_key,
)
from app.services.cache_service import (
    cache_bump_version,
    cache_get_versioned,
    cache_set_versioned,
)

logger = logging.getLogger(__name__)

router = APIRouter(tags=["finance-account:bank"])


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

        match = None
        for p in payments:
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
