"""Shared pagination helper for list endpoints.

Usage::

    result = await paginate(db, query, page, page_size)
    # result = {"list": [...], "total": 42, "page": 1, "page_size": 20}
"""

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession


async def paginate(
    db: AsyncSession,
    base_query,
    *,
    page: int = 1,
    page_size: int = 20,
) -> dict:
    """Execute a query with pagination and return {list, total, page, page_size}."""
    total = (await db.scalar(
        select(func.count()).select_from(base_query.subquery())
    )) or 0

    offset = (page - 1) * page_size
    rows = (await db.execute(
        base_query.offset(offset).limit(page_size)
    )).scalars().all()

    return {
        "list": rows,
        "total": total,
        "page": page,
        "page_size": page_size,
    }
