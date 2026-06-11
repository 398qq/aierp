"""Commissions API — sales commission tracking + state machine.

State machine:
    draft → pending_approval → approved → paid
                              ↘ rejected → draft (retry)
                              ↘ cancelled (terminal from any non-paid)
"""

from datetime import datetime

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.database import get_db
from app.schemas.common import fail, ok
from app.services import finance_service as svc
from app.services.cache_service import cache_bump_version

router = APIRouter(prefix="/finance/commissions", tags=["commissions"])


@router.get("")
async def list_commissions(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: str | None = None,
    sales_user_id: int | None = None,
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(get_current_user),
):
    return ok(
        await svc.list_commissions(
            db,
            page=page,
            page_size=page_size,
            status=status,
            sales_user_id=sales_user_id,
        )
    )


@router.get("/{commission_id}")
async def get_commission(
    commission_id: int,
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(get_current_user),
):
    obj = await svc.get_commission(db, commission_id)
    if not obj:
        return fail("commission not found", 404)
    return ok(svc._commission_to_dict(obj))


@router.post("")
async def create_commission(
    payload: dict,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    obj = await svc.create_commission(db, payload)
    await db.commit()
    await cache_bump_version("commissions")
    return ok(svc._commission_to_dict(obj))


@router.patch("/{commission_id}")
async def update_commission(
    commission_id: int,
    payload: dict,
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(get_current_user),
):
    obj = await svc.get_commission(db, commission_id)
    if not obj:
        return fail("commission not found", 404)
    await svc.update_commission(db, obj, payload)
    await db.commit()
    await cache_bump_version("commissions")
    return ok(svc._commission_to_dict(obj))


@router.delete("/{commission_id}")
async def delete_commission(
    commission_id: int,
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(get_current_user),
):
    obj = await svc.get_commission(db, commission_id)
    if not obj:
        return fail("commission not found", 404)
    await svc.delete_commission(db, obj)
    await db.commit()
    await cache_bump_version("commissions")
    return ok({"id": commission_id, "deleted": True})


@router.post("/{commission_id}/transition")
async def transition(
    commission_id: int,
    payload: dict,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """Explicit state-machine transition with reason.

    Body: { "to": "approved" | "rejected" | "paid" | "cancelled" | "pending_approval",
            "reason": "..." }
    """
    target = payload.get("to")
    if not target:
        return fail("missing 'to'", 400)
    obj = await svc.get_commission(db, commission_id)
    if not obj:
        return fail("commission not found", 404)
    data = {
        "status": target,
        "notes": (obj.notes or "")
        + f"\n[{datetime.utcnow().isoformat()}] {user.get('username')} → {target}: {payload.get('reason', '')}",
    }
    if target == "approved":
        data["approved_by"] = user.get("user_id") or user.get("id")
    await svc.update_commission(db, obj, data)
    await db.commit()
    return ok(svc._commission_to_dict(obj))
