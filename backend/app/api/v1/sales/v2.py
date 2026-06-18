"""Sales API v2 — uses application-layer use cases with UoW.

This router demonstrates the new architecture:
- Thin HTTP adapters (validate input, return response)
- All business logic in use cases
- Explicit UoW dependency for transaction boundaries
- Domain events tracked on the UoW for after-commit dispatch

Routes are namespaced under /sales-v2 to avoid colliding with the
existing /sales router during migration. The legacy router can be
deprecated once the v2 router is feature-complete.

Lives inside ``app/api/v1/sales/`` subpackage since the sales.py
split (daf3a96). The aggregator in ``sales/__init__.py`` re-exports
this router so ``app.api.v1.router`` can still mount it.
"""

import logging
from decimal import Decimal

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.api.deps import get_current_user, get_uow
from app.application.sales import (
    CancelSalesOrderUseCase,
    ConfirmSalesOrderUseCase,
    ConvertQuotationToOrderUseCase,
)
from app.application.uow import UnitOfWork
from app.domain.sales.quotation import Quotation, QuotationLine
from app.models.sales import Quotation as QuotationModel
from app.models.sales import QuotationItem
from app.schemas.common import fail, ok

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/sales-v2", tags=["sales-v2"])


# ── Request/Response schemas ────────────────────────────────────────────────


class QuotationLineIn(BaseModel):
    product_id: int
    product_name: str = ""
    quantity: int = Field(gt=0)
    unit_price: float = Field(ge=0)
    cost_price: float | None = None


class QuotationCreateIn(BaseModel):
    customer_id: int
    title: str | None = None
    opportunity_id: int | None = None
    valid_until: str | None = None
    notes: str | None = None
    lines: list[QuotationLineIn]


class QuotationSendIn(BaseModel):
    pass


# ── Quotation routes ───────────────────────────────────────────────────────


@router.post("/quotations")
async def create_quotation(
    body: QuotationCreateIn,
    uow: UnitOfWork = Depends(get_uow),
    user: dict = Depends(get_current_user),
):
    """Create a draft quotation in the new domain architecture."""
    from datetime import datetime
    from app.services.docno import generate_doc_no

    valid_until = None
    if body.valid_until:
        valid_until = datetime.fromisoformat(body.valid_until)

    domain_lines = [
        QuotationLine(
            product_id=line.product_id,
            product_name=line.product_name,
            quantity=line.quantity,
            unit_price=Decimal(str(line.unit_price)),
            cost_price=Decimal(str(line.cost_price)) if line.cost_price else None,
        )
        for line in body.lines
    ]

    # 1. Generate doc no (uses session)
    quotation_no = await generate_doc_no(
        uow.session, "QT", QuotationModel, "quotation_no"
    )

    # 2. Build ORM
    quote_orm = QuotationModel(
        customer_id=body.customer_id,
        quotation_no=quotation_no,
        title=body.title,
        status="draft",
        valid_until=valid_until,
        notes=body.notes,
        total_amount=0,
    )
    uow.session.add(quote_orm)
    await uow.session.flush()

    total = Decimal("0")
    for line in domain_lines:
        uow.session.add(
            QuotationItem(
                quotation_id=quote_orm.id,
                product_id=line.product_id,
                product_name=line.product_name,
                quantity=line.quantity,
                unit_price=line.unit_price,
                cost_price=line.cost_price,
                total_price=line.subtotal,
            )
        )
        total += line.subtotal

    quote_orm.total_amount = float(total)
    await uow.session.flush()
    return ok(
        {
            "id": quote_orm.id,
            "quotation_no": quote_orm.quotation_no,
            "total": float(total),
        }
    )


@router.post("/quotations/{quotation_id}/send")
async def send_quotation(
    quotation_id: int,
    body: QuotationSendIn,
    uow: UnitOfWork = Depends(get_uow),
    user: dict = Depends(get_current_user),
):
    """Send a quotation — uses domain aggregate to validate transition."""
    from app.domain.sales.quotation import QuotationStatus

    stmt = (
        select(QuotationModel)
        .where(QuotationModel.id == quotation_id, QuotationModel.deleted_at.is_(None))
        .options(selectinload(QuotationModel.items))
    )
    result = await uow.session.execute(stmt)
    quote_orm = result.scalar_one_or_none()
    if quote_orm is None:
        return fail("报价单不存在", 404)

    domain = Quotation(
        id=quote_orm.id,
        customer_id=quote_orm.customer_id,
        quotation_no=quote_orm.quotation_no,
        status=QuotationStatus(quote_orm.status)
        if quote_orm.status
        else QuotationStatus.DRAFT,
        valid_until=quote_orm.valid_until,
        notes=quote_orm.notes,
        lines=[
            QuotationLine(
                product_id=item.product_id,
                product_name=item.product_name or "",
                quantity=item.quantity,
                unit_price=Decimal(str(item.unit_price or 0)),
                cost_price=Decimal(str(item.cost_price)) if item.cost_price else None,
            )
            for item in quote_orm.items
        ],
    )
    domain.send()  # Raises InvalidStateTransition / BusinessRuleViolation

    quote_orm.status = domain.status.value
    for event in domain.collect_events():
        uow.track_event(event)
    return ok({"id": quote_orm.id, "status": domain.status.value})


@router.post("/quotations/{quotation_id}/convert-to-order")
async def convert_quotation_to_order(
    quotation_id: int,
    uow: UnitOfWork = Depends(get_uow),
    user: dict = Depends(get_current_user),
):
    """Convert a quotation to a sales order."""
    use_case = ConvertQuotationToOrderUseCase(uow.session, user_id=user["user_id"])
    domain_order = await use_case.execute(quotation_id)
    return ok(
        {
            "quotation_id": quotation_id,
            "lines": len(domain_order.lines),
            "total": float(domain_order.total),
        }
    )


# ── Sales Order routes (domain-driven) ────────────────────────────────────


@router.post("/orders/{order_id}/confirm")
async def confirm_order(
    order_id: int,
    uow: UnitOfWork = Depends(get_uow),
    user: dict = Depends(get_current_user),
):
    """Confirm a draft order — uses ConfirmSalesOrderUseCase.

    This replaces the legacy /sales/orders/{id} PATCH path with a
    domain-driven implementation that emits OrderConfirmed events.
    """
    use_case = ConfirmSalesOrderUseCase(
        uow.session,
        user_id=user["user_id"],
    )
    domain_order = await use_case.execute(order_id)
    for event in domain_order.collect_events():
        uow.track_event(event)
    return ok(
        {
            "id": domain_order.id,
            "status": domain_order.status.value,
            "total": float(domain_order.total),
        }
    )


@router.post("/orders/{order_id}/cancel")
async def cancel_order(
    order_id: int,
    reason: str = Query(..., min_length=1),
    uow: UnitOfWork = Depends(get_uow),
    user: dict = Depends(get_current_user),
):
    """Cancel a sales order — uses CancelSalesOrderUseCase.

    Emits OrderCancelled; the event bus subscriber releases reserved
    stock automatically.
    """
    use_case = CancelSalesOrderUseCase(uow.session, user_id=user["user_id"])
    domain_order = await use_case.execute(order_id, reason=reason)
    for event in domain_order.collect_events():
        uow.track_event(event)
    return ok(
        {
            "id": domain_order.id,
            "status": domain_order.status.value,
        }
    )


# ── Delivery Note routes (domain-driven) ──────────────────────────────────


@router.post("/orders/{order_id}/convert-to-delivery")
async def convert_order_to_delivery_v2(
    order_id: int,
    uow: UnitOfWork = Depends(get_uow),
    user: dict = Depends(get_current_user),
):
    """Convert a sales order to a delivery note (v2 — UoW pattern).

    Auto-transitions order pending→confirmed on first delivery creation.
    """
    from app.models.sales import DeliveryNote, DeliveryNoteItem, SalesOrder
    from app.services.docno import generate_doc_no

    order = await uow.session.get(SalesOrder, order_id)
    if not order or order.deleted_at:
        return fail("销售订单不存在", 404)
    if order.status in ("completed", "cancelled"):
        return fail("订单已完成或已取消", 409)

    # Guard against duplicate delivery
    from sqlalchemy import func

    count = (
        await uow.session.execute(
            select(func.count()).where(
                DeliveryNote.sales_order_id == order.id,
                DeliveryNote.deleted_at.is_(None),
            )
        )
    ).scalar() or 0
    if count > 0:
        return fail("订单已生成发货单", 409)

    delivery_no = await generate_doc_no(uow.session, "DN", DeliveryNote, "delivery_no")
    note = DeliveryNote(
        delivery_no=delivery_no,
        sales_order_id=order.id,
        customer_id=order.customer_id,
        status="pending",
    )
    uow.session.add(note)
    await uow.session.flush()

    for soi in order.items:
        uow.session.add(
            DeliveryNoteItem(
                delivery_note_id=note.id,
                product_id=soi.product_id,
                product_name=soi.product_name,
                quantity=soi.quantity,
            )
        )

    if order.status in ("pending", "draft"):
        order.status = "confirmed"

    await uow.session.flush()
    return ok({"id": note.id, "delivery_no": note.delivery_no})


@router.post("/delivery-notes/{note_id}/convert-to-invoice")
async def convert_delivery_to_invoice_v2(
    note_id: int,
    uow: UnitOfWork = Depends(get_uow),
    user: dict = Depends(get_current_user),
):
    """Convert a delivery note to an invoice (v2 — UoW pattern)."""
    from app.models.finance import Invoice, InvoiceLine
    from app.models.sales import DeliveryNote as DNModel, SalesOrder
    from app.services.docno import generate_doc_no

    note = await uow.session.get(DNModel, note_id)
    if not note or note.deleted_at:
        return fail("发货单不存在", 404)
    if note.status not in ("shipped", "delivered"):
        return fail("发货单状态不允许转换", 409)

    # Guard duplicate
    from sqlalchemy import func

    count = (
        await uow.session.execute(
            select(func.count()).where(
                Invoice.sales_order_id == note.sales_order_id,
                Invoice.deleted_at.is_(None),
            )
        )
    ).scalar() or 0
    if count > 0:
        return fail("已存在对应发票", 409)

    order = (
        await uow.session.get(SalesOrder, note.sales_order_id)
        if note.sales_order_id
        else None
    )
    invoice_no = await generate_doc_no(uow.session, "INV", Invoice, "invoice_no")

    inv = Invoice(
        invoice_no=invoice_no,
        sales_order_id=note.sales_order_id,
        customer_id=note.customer_id,
        amount=order.total_amount if order else 0,
        tax_amount=round((order.total_amount if order else 0) * 0.13, 4),
        status="draft",
    )
    uow.session.add(inv)
    await uow.session.flush()

    for dni in note.items:
        uow.session.add(
            InvoiceLine(
                invoice_id=inv.id,
                product_id=dni.product_id,
                product_name=dni.product_name,
                quantity=dni.quantity,
            )
        )

    await uow.session.flush()
    return ok({"id": inv.id, "invoice_no": inv.invoice_no})
