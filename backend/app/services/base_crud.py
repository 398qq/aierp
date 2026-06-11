"""Base CRUD service — reusable list / get / create / update / soft-delete operations.

Extend this class and override `model` to get standard CRUD with pagination.

Stage 7: update() now supports an optional `audit_actor` parameter that
records every changed field to `field_change_logs` (one row per field).
Pass `audit_actor="alice"` (or any string) to enable; omit to skip.
"""

from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit import FieldChangeLog


def _serialize(v) -> str:
    """Best-effort string snapshot for audit log."""
    if v is None:
        return None
    if isinstance(v, (str, int, float, bool)):
        return str(v)
    if isinstance(v, datetime):
        return v.isoformat()
    return repr(v)


class BaseCRUDService:
    model: type = None  # Set in subclass
    table_name: Optional[str] = None  # Override in subclass if != model.__tablename__

    @property
    def _table_name(self) -> str:
        return self.table_name or (
            self.model.__tablename__ if self.model else "unknown"
        )

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

        total = (
            await db.scalar(select(func.count()).select_from(base.subquery()))
        ) or 0

        sort_col = getattr(self.model, sort_by, self.model.id)
        base = base.order_by(
            sort_col.desc() if sort_order == "desc" else sort_col.asc()
        )
        offset = (page - 1) * page_size
        rows = (await db.execute(base.offset(offset).limit(page_size))).scalars().all()

        return {"list": rows, "total": total, "page": page, "page_size": page_size}

    # ── get by id ──────────────────────────────────────────────────────

    async def get(self, db: AsyncSession, obj_id: int) -> object | None:
        result = await db.execute(
            select(self.model).where(
                self.model.id == obj_id,
                self.model.deleted_at.is_(None),
            )
        )
        return result.scalar_one_or_none()

    # ── create ─────────────────────────────────────────────────────────

    async def create(self, db: AsyncSession, data: dict) -> object:
        obj = self.model(**data)
        db.add(obj)
        await db.commit()
        await db.refresh(obj)
        return obj

    # ── update ─────────────────────────────────────────────────────────

    async def update(
        self,
        db: AsyncSession,
        obj: object,
        data: dict,
        *,
        audit_actor: Optional[str] = None,
        audit_reason: Optional[str] = None,
    ) -> object:
        """Update fields on `obj`.

        Stage 7: if `audit_actor` is provided, every changed field is
        recorded to `field_change_logs` (one row per field). Existing
        rows that have the same value are not recorded (no-op filter).
        """
        changes: list[FieldChangeLog] = []
        for k, v in data.items():
            if v is None:
                continue  # PATCH semantics
            old = getattr(obj, k, None)
            if old == v:
                continue  # skip no-op
            setattr(obj, k, v)
            if audit_actor is not None:
                changes.append(
                    FieldChangeLog(
                        table_name=self._table_name,
                        record_id=obj.id,
                        field_name=k,
                        old_value=_serialize(old),
                        new_value=_serialize(v),
                        actor=audit_actor,
                        reason=audit_reason,
                    )
                )
        await db.commit()
        if changes:
            db.add_all(changes)
            await db.commit()
        await db.refresh(obj)
        return obj

    # ── soft-delete ────────────────────────────────────────────────────

    async def delete(self, db: AsyncSession, obj: object) -> None:
        obj.deleted_at = datetime.now(timezone.utc)
        await db.commit()
