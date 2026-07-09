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
from app.api.v1.sales._serialize import (
    attach_customer_and_quotation,
    attach_sales_order,
    attach_items,
    serialize_delivery_note,
)
from app.database import get_db
from app.models.sales import DeliveryNote as DeliveryNoteModel
from app.models.sales import DeliveryNoteItem
from app.schemas.common import APIResponse, PageData, fail, ok
from app.schemas.sales import (
    DeliveryNoteResponse,
    BatchDeleteRequest,
    DeliveryNoteCreate,
    DeliveryNoteMarkPaidIn,
    DeliveryNoteUpdate,
)
from app.services import sales_service as svc

logger = logging.getLogger(__name__)

router = APIRouter(tags=["sales:delivery-note"])


async def _eager_load_for_response(db, note: DeliveryNoteModel) -> DeliveryNoteModel:
    await attach_customer_and_quotation(db, note, type(note))
    await attach_sales_order(db, note, "sales_order_id")
    await attach_items(db, note, DeliveryNoteItem, "delivery_note_id")
    return note


@router.get(
    "/delivery-notes", response_model=APIResponse[PageData[DeliveryNoteResponse]]
)
async def list_delivery_notes(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    customer_id: int | None = None,
    status: str | None = None,
    sales_order_id: int | None = None,
    q: str | None = Query(
        None, description="Search customer, delivery no, order no, notes, product line"
    ),
    include_ai: bool = Query(False),
    sort_by: str = "id",
    sort_order: str = "desc",
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(get_current_user),
):
    raw = await svc.list_delivery_notes(
        db,
        page=page,
        page_size=page_size,
        customer_id=customer_id,
        status=status,
        sales_order_id=sales_order_id,
        q=q,
        sort_by=sort_by,
        sort_order=sort_order,
    )
    notes = list(raw["list"])
    # Eager-load customer + sales_order + items in batch
    from app.models.customer import Customer
    from app.models.sales import SalesOrder

    custs: dict[int, Customer] = {}
    sos: dict[int, SalesOrder] = {}
    if notes:
        cust_ids = list({n.customer_id for n in notes if n.customer_id})
        so_ids = list({n.sales_order_id for n in notes if n.sales_order_id})
        if cust_ids:
            custs = {
                c.id: c
                for c in (
                    await db.execute(select(Customer).where(Customer.id.in_(cust_ids)))
                )
                .scalars()
                .all()
            }
        if so_ids:
            sos = {
                s.id: s
                for s in (
                    await db.execute(
                        select(SalesOrder).where(SalesOrder.id.in_(so_ids))
                    )
                )
                .scalars()
                .all()
            }
        item_rows = (
            (
                await db.execute(
                    select(DeliveryNoteItem).where(
                        DeliveryNoteItem.delivery_note_id.in_([n.id for n in notes]),
                        DeliveryNoteItem.deleted_at.is_(None),
                    )
                )
            )
            .scalars()
            .all()
        )
        items_by_n: dict[int, list[DeliveryNoteItem]] = {}
        for it in item_rows:
            items_by_n.setdefault(it.delivery_note_id, []).append(it)
        for n in notes:
            # Only assign non-None to many-to-one relationships to avoid
            # clearing NOT NULL FK columns when the related row is missing.
            if (c := custs.get(n.customer_id)) is not None:
                n.customer = c
            if (s := sos.get(n.sales_order_id)) is not None:
                n.sales_order = s
            n.items = items_by_n.get(n.id, [])
    serialized_list = [serialize_delivery_note(n) for n in notes]
    result = {**raw, "list": serialized_list}
    if include_ai and notes:
        from app.services.sales_ai_service import enrich_delivery_list

        ai_map = await enrich_delivery_list(db, notes)
        result["ai"] = ai_map
    return ok(result)


@router.get(
    "/delivery-notes/{note_id}", response_model=APIResponse[DeliveryNoteResponse]
)
async def get_delivery_note(
    note_id: int,
    include_ai: bool = Query(False),
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(get_current_user),
):
    note = await svc.get_delivery_note(db, note_id)
    if not note:
        return fail("发货单不存在", 404)
    await _eager_load_for_response(db, note)
    if include_ai:
        from app.services.sales_ai_service import enrich_delivery_note

        ai_data = await enrich_delivery_note(db, note)
        ai_result = serialize_delivery_note(note)
        ai_result["ai"] = ai_data
        return ok(ai_result)
    return ok(serialize_delivery_note(note))


@router.post(
    "/delivery-notes", status_code=201, response_model=APIResponse[DeliveryNoteResponse]
)
async def create_delivery_note(
    body: DeliveryNoteCreate,
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(get_current_user),
):
    data = body.model_dump()
    items_data = data.pop("items", [])
    note = await svc.create_delivery_note(db, data, items_data)
    await _eager_load_for_response(db, note)
    return ok(serialize_delivery_note(note))


@router.put(
    "/delivery-notes/{note_id}", response_model=APIResponse[DeliveryNoteResponse]
)
async def update_delivery_note(
    note_id: int,
    body: DeliveryNoteUpdate,
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(get_current_user),
):
    note = await svc.get_delivery_note(db, note_id)
    if not note:
        return fail("发货单不存在", 404)
    note = await svc.update_delivery_note(db, note, body.model_dump(exclude_none=True))
    await _eager_load_for_response(db, note)
    return ok(serialize_delivery_note(note))


@router.delete("/delivery-notes/{note_id}")
async def delete_delivery_note(
    note_id: int,
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(get_current_user),
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
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(get_current_user),
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
        db,
        note,
        amount=body.amount,
        payment_method=body.payment_method,
        payment_date=body.payment_date,
        notes=body.notes,
    )
    return ok(
        {
            "created": paid_result["created"],
            "payment": {
                "id": paid_result["payment"].id,
                "amount": float(paid_result["payment"].amount),
                "status": paid_result["payment"].status,
                "method": paid_result["payment"].payment_method,
                "date": paid_result["payment"].payment_date.isoformat()
                if paid_result["payment"].payment_date
                else None,
            },
            "delivery_note": {
                "id": note.id,
                "status": note.status,
                "received_date": note.received_date.isoformat()
                if note.received_date
                else None,
            },
        }
    )


@router.post("/delivery-notes/batch-delete")
async def batch_delete_delivery_notes(
    body: BatchDeleteRequest,
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(get_current_user),
):
    for nid in body.ids:
        note = await svc.get_delivery_note(db, nid)
        if note:
            await svc.delete_delivery_note(db, note)
    return ok({"deleted": len(body.ids)})
