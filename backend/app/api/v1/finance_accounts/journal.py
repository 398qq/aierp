"""Finance accounts API — journal entry bounded context.

Routes for the journal entry lifecycle:
- list (with status / month filters)
- create (with auto-generated entry_no)
- get (with line details)
- post (draft → posted; bumps finance:reports:pnl)
"""

import datetime
import json
import logging

from fastapi import APIRouter, Depends, Query
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.requests import Request

from app.core.permissions import require_perm, write_audit_log
from app.database import date_format, get_db
from app.models.account import JournalEntry, JournalEntryLine
from app.schemas.common import fail, ok, paginated_ok
from app.api.v1.finance_accounts._shared import (
    JOURNAL_ENTRIES_LIST_CACHE_TTL,
    _journal_entries_cache_key,
)
from app.services.cache_service import (
    cache_bump_version,
    cache_get_versioned,
    cache_set_versioned,
)

logger = logging.getLogger(__name__)

router = APIRouter(tags=["finance-account:journal"])


@router.get("/journal-entries")
async def list_entries(
    response: JSONResponse,
    status: str | None = None,
    month: str | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(require_perm("finance", "read")),
):
    cache_key = _journal_entries_cache_key(
        status=status,
        month=month,
        page=page,
        page_size=page_size,
    )
    cached_payload = await cache_get_versioned("journal-entries:list", cache_key)
    if cached_payload is not None:
        return JSONResponse(
            content=json.loads(cached_payload),
            headers={"X-Cache": "HIT", "X-Cache-Key": cache_key},
        )
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
        count_q = count_q.where(
            date_format(JournalEntry.entry_date, "YYYY-MM") == month
        )

    total = len((await db.execute(count_q)).scalars().all())
    result = await db.execute(
        q.order_by(JournalEntry.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    entries = result.scalars().all()
    payload = paginated_ok(
        [
            {
                "id": e.id,
                "entry_no": e.entry_no,
                "entry_date": str(e.entry_date),
                "description": e.description,
                "status": e.status,
                "created_at": str(e.created_at),
            }
            for e in entries
        ],
        total,
        page,
        page_size,
    )
    await cache_set_versioned(
        "journal-entries:list",
        cache_key,
        json.dumps(payload, default=str),
        JOURNAL_ENTRIES_LIST_CACHE_TTL,
    )
    return JSONResponse(
        content=payload, headers={"X-Cache": "MISS", "X-Cache-Key": cache_key}
    )


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
async def create_entry(
    body: EntryCreate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_perm("finance", "write")),
):
    total_debit = sum(li.debit for li in body.lines)
    total_credit = sum(li.credit for li in body.lines)
    if abs(total_debit - total_credit) > 0.01:
        return fail(f"借贷不平衡: 借方 {total_debit:,.2f} vs 贷方 {total_credit:,.2f}")

    # Generate entry_no
    month_str = body.entry_date[:7].replace("-", "")
    count = (
        len(
            (
                await db.execute(
                    select(JournalEntry.id).where(
                        date_format(JournalEntry.entry_date, "YYYYMM") == month_str
                    )
                )
            )
            .scalars()
            .all()
        )
        + 1
    )
    entry_no = f"JV-{month_str}-{count:04d}"

    entry = JournalEntry(
        entry_no=entry_no,
        entry_date=datetime.date.fromisoformat(body.entry_date),
        description=body.description,
        status="draft",
        created_by=current_user["user_id"],
    )
    db.add(entry)
    await db.flush()

    for li in body.lines:
        db.add(
            JournalEntryLine(
                entry_id=entry.id,
                account_id=li.account_id,
                description=li.description,
                debit=li.debit,
                credit=li.credit,
            )
        )

    await db.commit()
    await write_audit_log(
        db,
        current_user["user_id"],
        current_user.get("username", ""),
        "create",
        "journal_entry",
        entry.id,
        f"创建凭证: {entry_no}",
        request.client.host if request.client else "",
    )
    await db.commit()
    await cache_bump_version("journal-entries:list")
    return ok({"id": entry.id, "entry_no": entry_no}, msg="凭证创建成功")


@router.get("/journal-entries/{entry_id}")
async def get_entry(
    entry_id: int,
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(require_perm("finance", "read")),
):
    entry = (
        await db.execute(
            select(JournalEntry).where(
                JournalEntry.id == entry_id, JournalEntry.deleted_at.is_(None)
            )
        )
    ).scalar_one_or_none()
    if not entry:
        return fail("凭证不存在")
    return ok(
        {
            "id": entry.id,
            "entry_no": entry.entry_no,
            "entry_date": str(entry.entry_date),
            "description": entry.description,
            "status": entry.status,
            "lines": [
                {
                    "id": li.id,
                    "account_id": li.account_id,
                    "account_name": li.account.name if li.account else "",
                    "description": li.description,
                    "debit": float(li.debit),
                    "credit": float(li.credit),
                }
                for li in (entry.lines or [])
            ],
            "created_at": str(entry.created_at),
        }
    )


@router.post("/journal-entries/{entry_id}/post")
async def post_entry(
    entry_id: int,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_perm("finance", "write")),
):
    entry = (
        await db.execute(
            select(JournalEntry).where(
                JournalEntry.id == entry_id, JournalEntry.deleted_at.is_(None)
            )
        )
    ).scalar_one_or_none()
    if not entry:
        return fail("凭证不存在")
    if entry.status != "draft":
        return fail(f"凭证状态为 {entry.status}，无法过账")
    entry.status = "posted"
    entry.posted_at = datetime.datetime.now(datetime.timezone.utc)  # type: ignore[assignment]
    entry.posted_by = current_user["user_id"]
    await db.commit()
    # Posting a journal entry changes the data feeding /finance/reports/pnl
    await cache_bump_version("journal-entries:list")
    await cache_bump_version("finance:reports:pnl")
    return ok(msg="凭证已过账")
