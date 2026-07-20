"""ConvertQuotationToOrderUseCase — convert an accepted quotation into a sales order.

Cross-aggregate orchestration:
1. Load Quotation ORM
2. Convert to domain Quotation
3. Validate state (must be SENT or ACCEPTED)
4. Build a new domain SalesOrder from quotation lines
5. Mark the quotation as CONVERTED
6. Persist both ORM records

The use case returns both the new order and any tracked events so the
caller can dispatch them on the event bus.
"""

import logging
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.domain.sales.entities import OrderLine, OrderStatus, SalesOrder
from app.domain.sales.quotation import Quotation, QuotationStatus
from app.domain.shared.errors import InvalidStateTransition, NotFoundError
from app.domain.states import assert_can_transition_quotation
from app.models.sales import (
    Quotation as QuotationModel,
    QuotationItem,
    SalesOrder as SalesOrderModel,
    SalesOrderItem,
)
from app.services.docno import generate_doc_no

logger = logging.getLogger(__name__)


class ConvertQuotationToOrderUseCase:
    """Convert a quotation into a sales order.

    The new order inherits the quotation's lines and customer. Pricing
    (unit_price) is copied verbatim — discounts should already be baked
    into the quotation when it was sent.
    """

    def __init__(
        self,
        session: AsyncSession,
        user_id: int,
        *,
        allow_legacy_draft: bool = False,
        final_quotation_status: str = "converted",
    ) -> None:
        self._session = session
        self._user_id = user_id
        self._allow_legacy_draft = allow_legacy_draft
        self._final_quotation_status = final_quotation_status

    async def execute(self, quotation_id: int) -> SalesOrder:
        # 1. Load quotation with items
        stmt = (
            select(QuotationModel)
            .where(
                QuotationModel.id == quotation_id,
                QuotationModel.deleted_at.is_(None),
            )
            .options(selectinload(QuotationModel.items))
            .with_for_update()
        )
        result = await self._session.execute(stmt)
        quote_orm = result.scalar_one_or_none()
        if quote_orm is None:
            raise NotFoundError(
                f"报价单 {quotation_id} 不存在",
                quotation_id=quotation_id,
            )

        existing_order = await self._session.scalar(
            select(SalesOrderModel).where(
                SalesOrderModel.quotation_id == quotation_id,
                SalesOrderModel.deleted_at.is_(None),
            )
        )
        if existing_order is not None:
            raise InvalidStateTransition(
                f"报价单已转换为销售订单 {existing_order.order_no or existing_order.id}"
            )

        # 2. Build domain quotation
        domain_quote = Quotation(
            id=quote_orm.id,
            customer_id=quote_orm.customer_id,
            quotation_no=quote_orm.quotation_no,
            title=quote_orm.title,
            status=_quotation_status(quote_orm.status, quote_orm.id),
            valid_until=quote_orm.valid_until,
            notes=quote_orm.notes,
            lines=[
                # QuotationItem doesn't have cost_price in ORM; pass None
                # for cost in the domain line, which is fine for conversion.
                _quote_line_from_orm(item)
                for item in quote_orm.items
            ],
        )

        # 3. Validate conversion state before creating downstream documents.
        # The canonical domain model uses "converted"; the legacy HTTP route
        # still exposes the older "won" status, so keep that compatibility here
        # instead of duplicating conversion rules in route adapters.
        if self._final_quotation_status == "won":
            assert_can_transition_quotation(quote_orm.status, "won")
        elif (
            self._allow_legacy_draft
            and domain_quote.status == QuotationStatus.DRAFT
            and self._final_quotation_status == "converted"
        ):
            pass
        else:
            domain_quote.convert_to_order()

        # 4. Build domain SalesOrder from quotation lines
        domain_order = SalesOrder(
            customer_id=domain_quote.customer_id,
            quotation_id=domain_quote.id,
            status=OrderStatus.DRAFT,
            lines=[
                OrderLine(
                    product_id=line.product_id or 0,
                    product_name=line.product_name,
                    quantity=line.quantity,
                    unit_price=line.unit_price,
                )
                for line in domain_quote.lines
            ],
        )

        # 5. Persist new order
        order_no = await generate_doc_no(
            self._session,
            "SO",
            SalesOrderModel,
            "order_no",
        )
        new_order_orm = SalesOrderModel(
            order_no=order_no,
            customer_id=domain_quote.customer_id,
            quotation_id=domain_quote.id,
            total_amount=float(domain_order.total),
            status=domain_order.status.value,
            currency=quote_orm.currency,
            incoterms=quote_orm.incoterms,
            payment_terms=quote_orm.payment_terms,
            discount_rate=quote_orm.discount_rate,
            discount_amount=quote_orm.discount_amount,
            subtotal=quote_orm.subtotal,
        )
        self._session.add(new_order_orm)
        await self._session.flush()
        domain_order.id = new_order_orm.id
        domain_order.order_no = new_order_orm.order_no

        source_lines = list(quote_orm.items)
        for line, source_line in zip(domain_order.lines, source_lines, strict=True):
            self._session.add(
                SalesOrderItem(
                    order_id=new_order_orm.id,
                    product_id=source_line.product_id,
                    product_name=line.product_name,
                    customer_part_no=source_line.customer_part_no,
                    customer_product_name=source_line.customer_product_name,
                    quantity=line.quantity,
                    unit=source_line.unit,
                    unit_price=line.unit_price,
                    total_price=line.subtotal,
                    tax_rate=source_line.tax_rate,
                    discount_rate=source_line.discount_rate,
                )
            )

        # 6. Mark source quotation as converted / won according to the adapter.
        quote_orm.status = self._final_quotation_status

        logger.info(
            "Converted quotation Q#%s to order SO#%s by user#%s (%d lines)",
            quotation_id,
            order_no,
            self._user_id,
            len(domain_order.lines),
        )

        await self._session.flush()
        return domain_order


def _quote_line_from_orm(item: QuotationItem):
    """Build a domain QuotationLine from a QuotationItem ORM row.

    Defined here (not in domain) to avoid importing ORM models from the
    domain layer.
    """
    from app.domain.sales.quotation import QuotationLine

    return QuotationLine(
        product_id=item.product_id,
        product_name=item.product_name or "",
        quantity=item.quantity,
        unit_price=Decimal(str(item.unit_price or 0)),
        cost_price=Decimal(str(item.cost_price)) if item.cost_price else None,
    )


def _quotation_status(
    raw_status: str | None, quotation_id: int | None
) -> QuotationStatus:
    if not raw_status:
        return QuotationStatus.DRAFT
    try:
        return QuotationStatus(raw_status)
    except ValueError as exc:
        raise InvalidStateTransition(
            f"报价单 {quotation_id}: {raw_status} 状态不允许转换为订单"
        ) from exc
