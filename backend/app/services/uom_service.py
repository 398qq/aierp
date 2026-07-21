from datetime import datetime, timezone
from typing import Literal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.uom import UomDict
from app.schemas.uom import UomDictCreate, UomDictUpdate


class UomService:

    async def list(
        self,
        db: AsyncSession,
        *,
        uom_type: Literal["count", "package"] | None = None,
    ) -> list[UomDict]:
        stmt = select(UomDict).where(UomDict.deleted_at.is_(None))
        if uom_type:
            stmt = stmt.where(UomDict.uom_type == uom_type)
        stmt = stmt.order_by(UomDict.sort_order, UomDict.code)
        result = await db.execute(stmt)
        return list(result.scalars().all())

    async def get_by_code(self, db: AsyncSession, code: str) -> UomDict | None:
        result = await db.execute(
            select(UomDict).where(
                UomDict.code == code, UomDict.deleted_at.is_(None)
            )
        )
        return result.scalar_one_or_none()

    async def create(self, db: AsyncSession, data: UomDictCreate) -> UomDict:
        obj = UomDict(**data.model_dump())
        db.add(obj)
        await db.commit()
        await db.refresh(obj)
        return obj

    async def update(
        self, db: AsyncSession, obj: UomDict, data: UomDictUpdate
    ) -> UomDict:
        changed = False
        for k, v in data.model_dump(exclude_unset=True).items():
            if v is not None:
                setattr(obj, k, v)
                changed = True
        if changed:
            obj.updated_at = datetime.now(timezone.utc)
        await db.commit()
        await db.refresh(obj)
        return obj

    async def soft_delete(self, db: AsyncSession, obj: UomDict) -> None:
        obj.deleted_at = datetime.now(timezone.utc)
        await db.commit()
