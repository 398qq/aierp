"""Shared document number generator with advisory lock for concurrency safety."""

from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession


async def generate_doc_no(db: AsyncSession, prefix: str, model, column_name: str) -> str:
    """Generate a date-based document number like QT202605110001.

    Uses PostgreSQL advisory lock to prevent duplicates under concurrency.
    Automatically skips the lock on SQLite (tests).
    """
    now = datetime.now(timezone.utc)
    date_part = now.strftime("%Y%m%d")
    col = getattr(model, column_name)

    if db.get_bind().dialect.name == "postgresql":
        lock_key = hash(f"{model.__tablename__}_{date_part}") & 0x7FFFFFFF
        await db.execute(select(func.pg_advisory_xact_lock(lock_key)))

    result = await db.execute(
        select(func.count()).where(col.like(f"{prefix}{date_part}%"))
    )
    seq = (result.scalar() or 0) + 1
    return f"{prefix}{date_part}{seq:04d}"
