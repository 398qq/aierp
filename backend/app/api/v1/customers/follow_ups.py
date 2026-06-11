from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.permissions import require_perm
from app.database import get_db
from app.models.customer import Customer, CustomerFollowUp
from app.schemas.common import fail, ok

from .crud import FollowUpCreate, FollowUpUpdate

router = APIRouter(prefix="/customers", tags=["customers"])


@router.get("/{customer_id}/follow-ups")
async def list_followups(
    customer_id: int,
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(require_perm("customers", "read")),
):
    rows = (await db.execute(
        select(CustomerFollowUp).where(
            CustomerFollowUp.customer_id == customer_id,
            CustomerFollowUp.deleted_at.is_(None),
        )
    )).scalars().all()
    return ok([{
        "id": f.id, "method": f.method, "status": f.status,
        "content": f.content, "result": f.result,
        "planned_at": str(f.planned_at) if f.planned_at else None,
        "completed_at": str(f.completed_at) if f.completed_at else None,
        "priority": f.priority, "assigned_to": f.assigned_to,
        "created_at": str(f.created_at) if f.created_at else None,
    } for f in rows])


@router.post("/{customer_id}/follow-ups", status_code=201)
async def create_followup(
    customer_id: int,
    body: FollowUpCreate,
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(require_perm("customers", "write")),
):
    try:
        data = body.model_dump()
        for date_field in ("planned_at", "completed_at"):
            if data.get(date_field):
                data[date_field] = datetime.fromisoformat(data[date_field])
        if data.get("completed_at") and not data.get("status"):
            data["status"] = "completed"
        followup = CustomerFollowUp(customer_id=customer_id, **data)
        db.add(followup)
        with db.no_autoflush:
            result = await db.execute(select(Customer).where(Customer.id == customer_id))
            cust = result.scalar_one_or_none()
            if cust:
                cust.last_contacted_at = datetime.now(timezone.utc)
                # Trigger customer state machine transition (inactive/churned -> active)
                from app.services.customer_state_service import on_re_engage
                await on_re_engage(db, customer_id)
            await db.flush()
            followup_id = followup.id
        return ok({"id": followup_id})
    except Exception as e:
        import traceback
        traceback.print_exc()
        return fail(str(e), 500)


@router.put("/{customer_id}/follow-ups/{followup_id}")
async def update_followup(
    customer_id: int,
    followup_id: int,
    body: FollowUpUpdate,
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(require_perm("customers", "write")),
):
    result = await db.execute(
        select(CustomerFollowUp).where(
            CustomerFollowUp.id == followup_id,
            CustomerFollowUp.customer_id == customer_id,
            CustomerFollowUp.deleted_at.is_(None),
        )
    )
    followup = result.scalar_one_or_none()
    if followup is None:
        return fail("Follow-up not found", 404)
    data = body.model_dump(exclude_unset=True)
    for date_field in ("planned_at", "completed_at"):
        if date_field in data and data.get(date_field) is None:
            del data[date_field]
        elif data.get(date_field):
            data[date_field] = datetime.fromisoformat(data[date_field])
    if data.get("completed_at") and not data.get("status"):
        data["status"] = "completed"
    for key, val in data.items():
        setattr(followup, key, val)
    await db.flush()
    return ok({"id": followup.id})


@router.delete("/{customer_id}/follow-ups/{followup_id}")
async def delete_followup(
    customer_id: int,
    followup_id: int,
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(require_perm("customers", "delete")),
):
    result = await db.execute(
        select(CustomerFollowUp).where(
            CustomerFollowUp.id == followup_id,
            CustomerFollowUp.customer_id == customer_id,
            CustomerFollowUp.deleted_at.is_(None),
        )
    )
    followup = result.scalar_one_or_none()
    if followup is None:
        return fail("Follow-up not found", 404)
    followup.deleted_at = datetime.now(timezone.utc)
    await db.flush()
    return ok(msg="deleted")
