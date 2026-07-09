"""Sales API — flow conversions across bounded contexts.

Each conversion is a multi-aggregate operation:
- quotation → sales order (crosses quotation + sales-order aggregates)
- sales order → delivery note (crosses sales-order + delivery-note + inventory)

These endpoints are prime candidates for the use-case refactor
documented in ``docs/architecture/001-design-audit-2026-06-03.md`` §1.5
— the cross-aggregate orchestration is exactly the work use cases
should encapsulate.
"""

import logging

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_uow
from app.application.sales import ConvertQuotationToOrderUseCase
from app.application.uow import UnitOfWork
from app.database import get_db
from app.domain.shared.errors import InvalidStateTransition, NotFoundError
from app.schemas.common import fail, ok
from app.schemas.sales import ConversionValidation, ConvertResponse
from app.services import sales_service as svc
from app.services.cache_service import cache_bump_version

logger = logging.getLogger(__name__)

router = APIRouter(tags=["sales:conversion"])


@router.post("/quotations/{quote_id}/convert-to-order")
async def convert_quote_to_order(
    quote_id: int,
    uow: UnitOfWork = Depends(get_uow),
    user: dict = Depends(get_current_user),
):
    use_case = ConvertQuotationToOrderUseCase(
        uow.session,
        user_id=user["user_id"],
        allow_legacy_draft=True,
        final_quotation_status="won",
    )
    try:
        order = await use_case.execute(quote_id)
    except NotFoundError:
        return fail("报价单不存在", 404)
    except InvalidStateTransition:
        return fail("报价单已转换或状态不允许转换", 400)

    await uow.commit()

    from app.services.sales_ai_pipeline import validate_quote_to_order

    validation = None
    try:
        quote = await svc.get_quotation(uow.session, quote_id)
        ai_result = await validate_quote_to_order(uow.session, quote) if quote else None
        if ai_result:
            validation = ConversionValidation(**ai_result)
    except Exception:
        pass
    await cache_bump_version("quotations:list")
    await cache_bump_version("quotations:stats")
    await cache_bump_version("dashboard:overview")
    await cache_bump_version("dashboard:kpi")
    await cache_bump_version("reports:predefined:sales")
    return ok(
        ConvertResponse(
            id=order.id or 0,
            document_no=order.order_no or "",
            msg="报价单已转换为销售订单",
            ai_validation=validation,
        )
    )


@router.post("/sales-orders/{order_id}/convert-to-delivery")
async def convert_order_to_delivery(
    order_id: int,
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(get_current_user),
):
    order = await svc.get_sales_order(db, order_id)
    if not order:
        return fail("销售订单不存在", 404)
    note = await svc.convert_order_to_delivery(db, order)
    if not note:
        return fail("订单已转换", 409)
    from app.services.sales_ai_pipeline import validate_order_to_delivery

    validation = None
    try:
        ai_result = await validate_order_to_delivery(db, order)
        if ai_result:
            validation = ConversionValidation(**ai_result)
    except Exception:
        pass
    return ok(
        ConvertResponse(
            id=note.id,
            document_no=note.delivery_no or "",
            msg="销售订单已转换为发货单",
            ai_validation=validation,
        )
    )


@router.post("/delivery-notes/{note_id}/convert-to-invoice")
async def convert_delivery_to_invoice(
    note_id: int,
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(get_current_user),
):
    """Convert a delivered delivery note into an invoice.

    Guards: delivery must be shipped/delivered, no duplicate invoice per order.
    """
    from app.models.sales import DeliveryNote as DeliveryNoteModel

    note = await db.get(DeliveryNoteModel, note_id)
    if not note or note.deleted_at:
        return fail("发货单不存在", 404)
    inv = await svc.convert_delivery_to_invoice(db, note)
    if not inv:
        return fail("发货单状态不允许转换或已存在对应发票", 409)
    await cache_bump_version("invoices:list")
    await cache_bump_version("dashboard:overview")
    await cache_bump_version("dashboard:kpi")
    return ok(
        ConvertResponse(
            id=inv.id,
            document_no=inv.invoice_no or "",
            msg="发货单已转换为发票",
        )
    )


@router.post("/delivery-notes/{note_id}/convert-to-return")
async def convert_delivery_to_return(
    note_id: int,
    reason: str = Query(""),
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(get_current_user),
):
    """Create a return note from a delivered/shipped delivery note."""
    from app.models.sales import DeliveryNote as DNModel

    note = await db.get(DNModel, note_id)
    if not note or note.deleted_at:
        return fail("发货单不存在", 404)
    rn = await svc.convert_delivery_to_return(db, note, reason)
    if not rn:
        return fail("发货单状态不允许退货或已存在退货单", 409)
    return ok(
        ConvertResponse(
            id=rn.id,
            document_no=rn.return_no or "",
            msg="发货单已转换为退货单",
        )
    )


@router.post("/return-notes/{return_id}/complete")
async def complete_return(
    return_id: int,
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(get_current_user),
):
    """Complete a return note — transitions to completed + auto-generates credit note."""
    result = await svc.complete_return_note(db, return_id)
    if not result:
        return fail("退货单不存在或未审批", 409)
    return ok(result)


@router.post("/delivery-notes/batch-convert-to-invoice")
async def batch_convert_to_invoice(
    body: dict,
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(get_current_user),
):
    """Batch convert multiple delivery notes to invoices."""
    from app.models.sales import DeliveryNote

    ids = body.get("ids", [])
    if not ids or not isinstance(ids, list):
        return fail("ids 必须为非空列表", 400)

    succeeded, failed = 0, []
    for note_id in ids:
        note = await db.get(DeliveryNote, int(note_id))
        if not note or note.deleted_at or note.status not in ("shipped", "delivered"):
            failed.append({"id": note_id, "error": "状态不允许或不存在"})
            continue
        result = await svc.convert_delivery_to_invoice(db, note)
        if result:
            succeeded += 1
        else:
            failed.append({"id": note_id, "error": "转换失败"})

    return ok({"succeeded": succeeded, "failed": len(failed), "details": failed})


@router.post("/sales-orders/batch-confirm")
async def batch_confirm_orders(
    body: dict,
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(get_current_user),
):
    """Batch confirm multiple pending sales orders."""
    from app.models.sales import SalesOrder
    from app.domain.states import assert_can_transition_sales_order

    ids = body.get("ids", [])
    if not ids or not isinstance(ids, list):
        return fail("ids 必须为非空列表", 400)

    succeeded, failed = 0, []
    for oid in ids:
        order = await db.get(SalesOrder, int(oid))
        if not order or order.deleted_at:
            failed.append({"id": oid, "error": "订单不存在"})
            continue
        try:
            assert_can_transition_sales_order(order.status, "confirmed")
        except Exception:
            failed.append({"id": oid, "error": f"状态 {order.status} 不允许确认"})
            continue
        order.status = "confirmed"
        succeeded += 1

    await db.commit()
    return ok({"succeeded": succeeded, "failed": len(failed), "details": failed})
