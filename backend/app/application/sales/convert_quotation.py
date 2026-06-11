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
from app.domain.shared.errors import NotFoundError
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

    def __init__(self, session: AsyncSession, user_id: int) -> None:
        self._session = session
        self._user_id = user_id

    async def execute(self, quotation_id: int) -> SalesOrder:
        # 1. Load quotation with items
        stmt = (
            select(QuotationModel)
            .where(
                QuotationModel.id == quotation_id,
                QuotationModel.deleted_at.is_(None),
            )
            .options(selectinload(QuotationModel.items))
        )
        result = await self._session.execute(stmt)
        quote_orm = result.scalar_one_or_none()
        if quote_orm is None:
            raise NotFoundError(
                f"报价单 {quotation_id} 不存在",
                quotation_id=quotation_id,
            )

        # 2. Build domain quotation
        domain_quote = Quotation(
            id=quote_orm.id,
            customer_id=quote_orm.customer_id,
            quotation_no=quote_orm.quotation_no,
            title=quote_orm.title,
            status=QuotationStatus(quote_orm.status)
            if quote_orm.status
            else QuotationStatus.DRAFT,
            valid_until=quote_orm.valid_until,
            notes=quote_orm.notes,
            lines=[
                # QuotationItem doesn't have cost_price in ORM; pass None
                # for cost in the domain line, which is fine for conversion.
                _quote_line_from_orm(item)
                for item in quote_orm.items
            ],
        )

        # 3. Build domain SalesOrder from quotation lines
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
                if line.product_id is not None
            ],
        )

        # 4. Persist new order
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
        )
        self._session.add(new_order_orm)
        await self._session.flush()

        for line in domain_order.lines:
            self._session.add(
                SalesOrderItem(
                    order_id=new_order_orm.id,
                    product_id=line.product_id,
                    product_name=line.product_name,
                    quantity=line.quantity,
                    unit_price=line.unit_price,
                    total_price=line.subtotal,
                )
            )

        # 5. Mark quotation as CONVERTED
        domain_quote.convert_to_order()  # Validates transition
        quote_orm.status = domain_quote.status.value

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
