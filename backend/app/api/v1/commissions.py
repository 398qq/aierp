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
    result = svc._commission_to_dict(obj)
    await db.commit()
    await cache_bump_version("commissions")
    return ok(result)


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
    result = svc._commission_to_dict(obj)
    await db.commit()
    await cache_bump_version("commissions")
    return ok(result)


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

    Emits a `commission_status_changed` event in notes (Stage 10 Day 2 hook
    for Telegram notification). Bumps commissions cache.
    """
    target = payload.get("to")
    if not target:
        return fail("missing 'to'", 400)
    obj = await svc.get_commission(db, commission_id)
    if not obj:
        return fail("commission not found", 404)

    previous_status = obj.status
    data = {
        "status": target,
        "notes": (obj.notes or "")
        + f"\n[{datetime.utcnow().isoformat()}] {user.get('username')}: {previous_status} \u2192 {target} | {payload.get('reason', '')}",
    }
    if target == "approved":
        data["approved_by"] = user.get("user_id") or user.get("id")
    # paid_at + paid_amount now set by finance_service.update_commission (Stage 10 Day 1)
    await svc.update_commission(db, obj, data)
    result = svc._commission_to_dict(obj)
    await db.commit()
    await cache_bump_version("commissions")
    # Stage 10 Day 2: fire-and-forget notification hook
    try:
        from app.services.commission_notifier import on_commission_status_changed

        await on_commission_status_changed(
            db=db,
            commission=obj,
            previous_status=previous_status,
            new_status=target,
            actor=user.get("username", "system"),
        )
    except Exception:
        pass  # never fail the transition
    return ok(result)


# ── Stage 10 Day 1: RESTful state-machine shortcuts ──────────


@router.post("/{commission_id}/submit")
async def submit_for_approval(
    commission_id: int,
    payload: dict = {},
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """Submit a draft commission for approval (draft \u2192 pending_approval)."""
    payload["to"] = "pending_approval"
    return await transition(commission_id, payload, db, user)


@router.post("/{commission_id}/approve")
async def approve_commission(
    commission_id: int,
    payload: dict = {},
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """Approve a pending commission (pending_approval \u2192 approved)."""
    payload["to"] = "approved"
    return await transition(commission_id, payload, db, user)


@router.post("/{commission_id}/reject")
async def reject_commission(
    commission_id: int,
    payload: dict = {},
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """Reject a pending commission (pending_approval \u2192 rejected)."""
    payload["to"] = "rejected"
    return await transition(commission_id, payload, db, user)


@router.post("/{commission_id}/pay")
async def mark_paid(
    commission_id: int,
    payload: dict = {},
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """Mark an approved commission as paid (approved \u2192 paid)."""
    payload["to"] = "paid"
    return await transition(commission_id, payload, db, user)


@router.post("/batch-transition")
async def batch_transition(
    payload: dict,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """Transition multiple commissions in one call (Stage 11 Day 2).

    Body:
    {
        "ids": [1, 2, 3, ...],
        "to": "approved" | "rejected" | "paid" | "cancelled" | "pending_approval",
        "notes": "optional shared note",
        "paid_amount": 100.0  # required when to=paid
    }

    Returns:
    {
        "ok": true,
        "succeeded": [{"id": 1, "to": "approved"}],
        "failed":    [{"id": 2, "error": "Invalid transition"}],
        "summary":   {"total": 3, "succeeded": 1, "failed": 1}
    }
    """
    ids = payload.get("ids", [])
    to = payload.get("to")
    notes = payload.get("notes", "")
    paid_amount = payload.get("paid_amount")

    if not isinstance(ids, list) or not ids:
        return fail("ids must be a non-empty list", code=400)
    if to not in ("approved", "rejected", "paid", "cancelled", "pending_approval"):
        return fail(f"unsupported to={to}", code=400)

    succeeded = []
    failed = []
    for cid in ids:
        try:
            sub_payload = {"to": to, "notes": notes}
            if paid_amount is not None:
                sub_payload["paid_amount"] = paid_amount
            # Run transition logic inline (don't depend on FastAPI endpoint function
            # signature with `payload: dict` default). Stage 11 Day 2: direct call.
            from app.services.finance_service import get_commission, update_commission
            from app.domain.states.finance import assert_can_transition_commission

            obj = await get_commission(db, cid)
            if not obj:
                failed.append({"id": cid, "error": "commission not found"})
                continue
            try:
                assert_can_transition_commission(obj.status, to)
            except Exception:  # noqa: BLE001
                failed.append(
                    {"id": cid, "error": f"invalid transition: {obj.status} → {to}"}
                )
                continue
            previous_status = obj.status
            data = {
                "status": to,
                "notes": (obj.notes or "")
                + f"\n[batch {datetime.utcnow().isoformat()}] {user.get('username')}: {previous_status} → {to} | {notes}",
            }
            if to == "approved":
                data["approved_by"] = user.get("user_id") or user.get("id")
            if to == "paid":
                data["paid_at"] = datetime.utcnow()
                if paid_amount is not None:
                    data["paid_amount"] = paid_amount
            try:
                await update_commission(db, obj, data)
                await db.commit()
            except Exception as exc:  # noqa: BLE001
                await db.rollback()
                failed.append({"id": cid, "error": f"db error: {exc}"})
                continue
            succeeded.append({"id": cid, "from": previous_status, "to": to})
            # Fire-and-forget notification (Stage 10 Day 2)
            try:
                from app.services.commission_notifier import (
                    on_commission_status_changed,
                )

                await on_commission_status_changed(
                    db=db,
                    commission=obj,
                    previous_status=previous_status,
                    new_status=to,
                    actor=user.get("username", "system"),
                )
            except Exception:  # noqa: BLE001
                pass
        except Exception as exc:  # noqa: BLE001
            failed.append({"id": cid, "error": f"unexpected: {exc}"})

    # Bump cache once at the end (not per-id)
    try:
        from app.services.cache_service import cache_bump_version

        await cache_bump_version("commissions")
    except Exception as exc:  # noqa: BLE001
        # never fail the batch
        import logging

        logging.getLogger(__name__).debug("cache_bump_version failed: %s", exc)

    return ok(
        {
            "ok": True,
            "succeeded": succeeded,
            "failed": failed,
            "summary": {
                "total": len(ids),
                "succeeded": len(succeeded),
                "failed": len(failed),
            },
        }
    )
