"""Base CRUD service — reusable list / get / create / update / soft-delete operations.

Extend this class and override `model` to get standard CRUD with pagination.
"""

from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession


class BaseCRUDService:
    model: type = None  # Set in subclass

    # ── list ──────────────────────────────────────────────────────────

    async def list(
        self,
        db: AsyncSession,
        *,
        page: int = 1,
        page_size: int = 20,
        filters: list | None = None,
        sort_by: str = "id",
        sort_order: str = "desc",
    ) -> dict:
        """Paginated list with optional filters and sorting.

        filters: list of SQLAlchemy where-clauses, e.g. ``[Model.status == "active"]``
        """
        base = select(self.model).where(self.model.deleted_at.is_(None))
        if filters:
            base = base.where(*filters)

        total = (await db.scalar(
            select(func.count()).select_from(base.subquery())
        )) or 0

        sort_col = getattr(self.model, sort_by, self.model.id)
        base = base.order_by(sort_col.desc() if sort_order == "desc" else sort_col.asc())
        offset = (page - 1) * page_size
        rows = (await db.execute(base.offset(offset).limit(page_size))).scalars().all()

        return {"list": rows, "total": total, "page": page, "page_size": page_size}

    # ── get by id ─────────────────────────────────────────────────────

    async def get(self, db: AsyncSession, obj_id: int) -> object | None:
        result = await db.execute(
            select(self.model).where(
                self.model.id == obj_id,
                self.model.deleted_at.is_(None),
            )
        )
        return result.scalar_one_or_none()

    # ── create ────────────────────────────────────────────────────────

    async def create(self, db: AsyncSession, data: dict) -> object:
        obj = self.model(**data)
        db.add(obj)
        await db.commit()
        await db.refresh(obj)
        return obj

    # ── update ────────────────────────────────────────────────────────

    async def update(self, db: AsyncSession, obj: object, data: dict) -> object:
        for k, v in data.items():
            if v is not None:
                setattr(obj, k, v)
        await db.commit()
        await db.refresh(obj)
        return obj

    # ── soft-delete ───────────────────────────────────────────────────

    async def delete(self, db: AsyncSession, obj: object) -> None:
        obj.deleted_at = datetime.now(timezone.utc)
        await db.commit()
