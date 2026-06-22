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

from app.api.deps import get_current_user
from app.database import get_db
from app.schemas.common import fail, ok
from app.schemas.sales import ConversionValidation, ConvertResponse
from app.services import sales_service as svc
from app.services.cache_service import cache_bump_version

logger = logging.getLogger(__name__)

router = APIRouter(tags=["sales:conversion"])


@router.post("/quotations/{quote_id}/convert-to-order")
async def convert_quote_to_order(
    quote_id: int,
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(get_current_user),
):
    quote = await svc.get_quotation(db, quote_id)
    if not quote:
        return fail("报价单不存在", 404)
    if quote.status == "won":
        return fail("报价单已转换", 400)
    order = await svc.convert_quotation_to_order(db, quote)
    from app.services.sales_ai_pipeline import validate_quote_to_order

    validation = None
    try:
        ai_result = await validate_quote_to_order(db, quote)
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
            id=order.id,
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
