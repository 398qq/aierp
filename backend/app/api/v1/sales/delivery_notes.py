"""Sales API — delivery note bounded context.

Routes for the delivery note lifecycle:
- list / get / create / update / delete
- mark-paid (idempotent PaymentRecord creation)
- batch delete

The mark-paid endpoint crosses into the finance domain (creates a
``PaymentRecord``); this is a candidate for a future use-case
extraction (see ``docs/architecture/001-design-audit-2026-06-03.md`` §1.5).
"""

import logging

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import get_current_user
from app.database import get_db
from app.models.sales import DeliveryNote as DeliveryNoteModel
from app.schemas.common import fail, ok
from app.schemas.sales import (
    BatchDeleteRequest,
    DeliveryNoteCreate,
    DeliveryNoteMarkPaidIn,
    DeliveryNoteUpdate,
)
from app.services import sales_service as svc

logger = logging.getLogger(__name__)

router = APIRouter(tags=["sales:delivery-note"])


@router.get("/delivery-notes")
async def list_delivery_notes(
    page: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=100),
    customer_id: int | None = None, status: str | None = None,
    sales_order_id: int | None = None,
    q: str | None = Query(None, description="Search customer, delivery no, order no, notes, product line"),
    include_ai: bool = Query(False),
    sort_by: str = "id", sort_order: str = "desc",
    db: AsyncSession = Depends(get_db), _user: dict = Depends(get_current_user),
):
    result = await svc.list_delivery_notes(
        db, page=page, page_size=page_size, customer_id=customer_id,
        status=status, sales_order_id=sales_order_id, q=q,
        sort_by=sort_by, sort_order=sort_order,
    )
    if include_ai and result["list"]:
        from app.services.sales_ai_service import enrich_delivery_list
        ai_map = await enrich_delivery_list(db, result["list"])
        result["ai"] = ai_map
    return ok(result)


@router.get("/delivery-notes/{note_id}")
async def get_delivery_note(
    note_id: int,
    include_ai: bool = Query(False),
    db: AsyncSession = Depends(get_db), _user: dict = Depends(get_current_user),
):
    note = await svc.get_delivery_note(db, note_id)
    if not note:
        return fail("发货单不存在", 404)
    if include_ai:
        from app.services.sales_ai_service import enrich_delivery_note
        ai_data = await enrich_delivery_note(db, note)
        from app.schemas.sales import DeliveryNoteResponse
        ai_result: dict = DeliveryNoteResponse.model_validate(note).model_dump()
        ai_result["ai"] = ai_data
        return ok(ai_result)
    return ok(note)


@router.post("/delivery-notes", status_code=201)
async def create_delivery_note(
    body: DeliveryNoteCreate,
    db: AsyncSession = Depends(get_db), _user: dict = Depends(get_current_user),
):
    data = body.model_dump()
    items_data = data.pop("items", [])
    note = await svc.create_delivery_note(db, data, items_data)
    return ok(note)


@router.put("/delivery-notes/{note_id}")
async def update_delivery_note(
    note_id: int, body: DeliveryNoteUpdate,
    db: AsyncSession = Depends(get_db), _user: dict = Depends(get_current_user),
):
    note = await svc.get_delivery_note(db, note_id)
    if not note:
        return fail("发货单不存在", 404)
    note = await svc.update_delivery_note(db, note, body.model_dump(exclude_none=True))
    return ok(note)


@router.delete("/delivery-notes/{note_id}")
async def delete_delivery_note(
    note_id: int,
    db: AsyncSession = Depends(get_db), _user: dict = Depends(get_current_user),
):
    note = await svc.get_delivery_note(db, note_id)
    if not note:
        return fail("发货单不存在", 404)
    await svc.delete_delivery_note(db, note)
    return ok({"deleted": note_id})


@router.post("/delivery-notes/{note_id}/mark-paid")
async def mark_delivery_note_paid(
    note_id: int,
    body: DeliveryNoteMarkPaidIn,
    db: AsyncSession = Depends(get_db), _user: dict = Depends(get_current_user),
):
    """Create a PaymentRecord for a delivery note and mark it received.

    Idempotent — returns the existing payment if one already exists.
    Defaults amount to the order total when not provided.
    """
    stmt = (
        select(DeliveryNoteModel)
        .where(DeliveryNoteModel.id == note_id, DeliveryNoteModel.deleted_at.is_(None))
        .options(selectinload(DeliveryNoteModel.items))
    )
    result = await db.execute(stmt)
    note = result.scalar_one_or_none()
    if not note:
        return fail("发货单不存在", 404)

    paid_result = await svc.mark_delivery_note_paid(
        db, note,
        amount=body.amount,
        payment_method=body.payment_method,
        payment_date=body.payment_date,
        notes=body.notes,
    )
    return ok({
        "created": paid_result["created"],
        "payment": {
            "id": paid_result["payment"].id,
            "amount": float(paid_result["payment"].amount),
            "status": paid_result["payment"].status,
            "method": paid_result["payment"].payment_method,
            "date": paid_result["payment"].payment_date.isoformat() if paid_result["payment"].payment_date else None,
        },
        "delivery_note": {
            "id": note.id,
            "status": note.status,
            "received_date": note.received_date.isoformat() if note.received_date else None,
        },
    })


@router.post("/delivery-notes/batch-delete")
async def batch_delete_delivery_notes(
    body: BatchDeleteRequest,
    db: AsyncSession = Depends(get_db), _user: dict = Depends(get_current_user),
):
    for nid in body.ids:
        note = await svc.get_delivery_note(db, nid)
        if note:
            await svc.delete_delivery_note(db, note)
    return ok({"deleted": len(body.ids)})
