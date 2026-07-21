from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.responses import JSONResponse

from app.api.deps import get_current_user
from app.database import get_db
from app.schemas.common import APIResponse, ok, fail
from app.schemas.uom import UomDictCreate, UomDictResponse, UomDictUpdate
from app.services.uom_service import UomService

router = APIRouter(prefix="/uoms", tags=["UOM"])
svc = UomService()


@router.get("", response_model=APIResponse[list[UomDictResponse]])
async def list_uoms(
    uom_type: Literal["count", "package"] | None = Query(
        None, description="count / package"
    ),
    db: AsyncSession = Depends(get_db),
) -> dict:
    uoms = await svc.list(db, uom_type=uom_type)
    return ok([UomDictResponse.model_validate(u) for u in uoms])


@router.get("/{code}", response_model=APIResponse[UomDictResponse])
async def get_uom(
    code: str,
    db: AsyncSession = Depends(get_db),
) -> dict:
    uom = await svc.get_by_code(db, code)
    if not uom:
        raise HTTPException(status_code=404, detail=f"UOM '{code}' not found")
    return ok(UomDictResponse.model_validate(uom))


@router.post("", response_model=APIResponse[UomDictResponse])
async def create_uom(
    body: UomDictCreate,
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(get_current_user),
) -> dict | JSONResponse:
    existing = await svc.get_by_code(db, body.code)
    if existing:
        return fail(msg=f"UOM code '{body.code}' already exists", code=409)
    uom = await svc.create(db, body)
    return ok(UomDictResponse.model_validate(uom))


@router.put("/{code}", response_model=APIResponse[UomDictResponse])
async def update_uom(
    code: str,
    body: UomDictUpdate,
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(get_current_user),
) -> dict:
    uom = await svc.get_by_code(db, code)
    if not uom:
        raise HTTPException(status_code=404, detail=f"UOM '{code}' not found")
    uom = await svc.update(db, uom, body)
    return ok(UomDictResponse.model_validate(uom))


@router.delete("/{code}", response_model=APIResponse[None])
async def delete_uom(
    code: str,
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(get_current_user),
) -> dict:
    uom = await svc.get_by_code(db, code)
    if not uom:
        raise HTTPException(status_code=404, detail=f"UOM '{code}' not found")
    await svc.soft_delete(db, uom)
    return ok(msg=f"UOM '{code}' deleted")
