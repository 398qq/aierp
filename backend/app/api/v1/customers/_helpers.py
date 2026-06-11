"""Customer internal helpers — short_name / code generation and audit logging.

These functions are imported by ``crud.py``, ``list.py``, and
``bulk.py``. They are intentionally module-private (underscore prefix
and a leading underscore module name) so consumers always reach them
through the re-exports in ``crud.py``.
"""

from __future__ import annotations

import re
import unicodedata
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.customer import Customer, CustomerLog


# --- Constants shared with crud.py / bulk.py ---

_FORBIDDEN_FILENAME_CHARS = re.compile(r"[/\\\x00\r\n]")
_CODE_NUMBER_RE = re.compile(r"\d+")
COMPANY_SUFFIXES = (
    "有限责任公司",
    "股份有限公司",
    "集团有限公司",
    "控股有限公司",
    "有限公司",
    "责任公司",
    "股份公司",
    "控股集团",
    "集团",
    "公司",
)


def _safe_filename(name: str) -> str:
    if not name:
        return "unnamed"
    name = _FORBIDDEN_FILENAME_CHARS.sub("", name)
    return name or "unnamed"


def _generate_short_name(name: str | None) -> str | None:
    if not name:
        return None
    value = unicodedata.normalize("NFKC", name.strip())
    value = re.sub(r"\s+", "", value)
    value = re.sub(r"\([^()]*\)", "", value)
    for suffix in COMPANY_SUFFIXES:
        if value.endswith(suffix) and len(value) > len(suffix):
            value = value[: -len(suffix)]
            break
    return value or None


def _short_name_with_suffix(base: str, suffix: str) -> str:
    return f"{base}{suffix}" if base else suffix


async def _short_name_exists(
    db: AsyncSession,
    short_name: str,
    exclude_id: int | None = None,
) -> bool:
    stmt = select(Customer.id).where(
        Customer.short_name == short_name,
        Customer.deleted_at.is_(None),
    )
    if exclude_id is not None:
        stmt = stmt.where(Customer.id != exclude_id)
    result = await db.execute(stmt)
    return result.scalar_one_or_none() is not None


async def _dedupe_auto_short_name(
    db: AsyncSession,
    base: str,
    exclude_id: int | None = None,
) -> str:
    if not base:
        base = "客户"
    candidate = base
    suffix = 1
    while await _short_name_exists(db, candidate, exclude_id=exclude_id):
        candidate = _short_name_with_suffix(base, str(suffix))
        suffix += 1
        if suffix > 99:
            break
    return candidate


def _extract_code_number(code: str | None) -> str | None:
    if not code:
        return None
    match = _CODE_NUMBER_RE.search(code)
    if not match:
        return None
    return match.group(0)


def _code_number_conflict_message(code: str, conflict_code: str | None) -> str:
    if conflict_code:
        return f"客户编码 {code} 与 {conflict_code} 编号段冲突"
    return f"客户编码 {code} 已存在"


async def _find_code_number_conflict(
    db: AsyncSession,
    number: str,
    region: str | None = None,
    exclude_id: int | None = None,
) -> Customer | None:

    stmt = select(Customer).where(
        Customer.deleted_at.is_(None),
    )
    if exclude_id is not None:
        stmt = stmt.where(Customer.id != exclude_id)
    rows = (await db.execute(stmt)).scalars().all()
    for row in rows:
        if not row.code:
            continue
        row_number = _extract_code_number(row.code)
        if (
            row_number
            and row_number == number
            and (not region or not row.region or row.region == region)
        ):
            return row
    return None


async def _generate_unique_code(
    db: AsyncSession,
    start_number: int,
    region: str | None,
    exclude_id: int | None = None,
) -> str:
    from app.api.v1.customers.crud import _generate_code  # local import to avoid cycle

    number = start_number
    while number < start_number + 10000:
        candidate = _generate_code(number, region)
        if not await _find_code_number_conflict(
            db, str(number), region=region, exclude_id=exclude_id
        ):
            return candidate
        number += 1
    return _generate_code(start_number, region)


async def _log(
    db: AsyncSession,
    customer_id: int,
    action: str,
    field_name: str | None = None,
    old_value: str | None = None,
    new_value: str | None = None,
    operator: str | None = None,
    details: str | None = None,
) -> None:
    log = CustomerLog(
        customer_id=customer_id,
        action=action,
        field_name=field_name,
        old_value=old_value,
        new_value=new_value,
        operator=operator,
        details=details,
        created_at=datetime.now(timezone.utc),
    )
    db.add(log)
    await db.flush()


__all__ = [
    "_FORBIDDEN_FILENAME_CHARS",
    "_CODE_NUMBER_RE",
    "COMPANY_SUFFIXES",
    "_safe_filename",
    "_generate_short_name",
    "_short_name_with_suffix",
    "_short_name_exists",
    "_dedupe_auto_short_name",
    "_extract_code_number",
    "_code_number_conflict_message",
    "_find_code_number_conflict",
    "_generate_unique_code",
    "_log",
]
