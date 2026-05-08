"""Sales Targets API."""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.database import get_db
from app.schemas.common import fail, ok
from app.schemas.sales import TargetCreate, TargetUpdate
from app.services import sales_service as svc

router = APIRouter(prefix="/sales/targets", tags=["targets"])


@router.get("")
async def list_targets(
    page: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db), _user: dict = Depends(get_current_user),
):
    result = await svc.list_targets(db, page=page, page_size=page_size)
    return ok(result)


@router.get("/summary")
async def summary(
    db: AsyncSession = Depends(get_db), _user: dict = Depends(get_current_user),
):
    return ok(await svc.get_target_summary(db))


@router.get("/{target_id}")
async def get_target(
    target_id: int,
    db: AsyncSession = Depends(get_db), _user: dict = Depends(get_current_user),
):
    target = await svc.get_target(db, target_id)
    if not target:
        return fail("目标不存在", 404)
    return ok(target)


@router.post("", status_code=201)
async def create_target(
    body: TargetCreate,
    db: AsyncSession = Depends(get_db), _user: dict = Depends(get_current_user),
):
    target = await svc.create_target(db, body.model_dump())
    return ok(target)


@router.put("/{target_id}")
async def update_target(
    target_id: int, body: TargetUpdate,
    db: AsyncSession = Depends(get_db), _user: dict = Depends(get_current_user),
):
    target = await svc.get_target(db, target_id)
    if not target:
        return fail("目标不存在", 404)
    target = await svc.update_target(db, target, body.model_dump(exclude_none=True))
    return ok(target)


@router.delete("/{target_id}")
async def delete_target(
    target_id: int,
    db: AsyncSession = Depends(get_db), _user: dict = Depends(get_current_user),
):
    target = await svc.get_target(db, target_id)
    if not target:
        return fail("目标不存在", 404)
    await svc.delete_target(db, target)
    return ok({"deleted": target_id})
