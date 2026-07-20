"""ConfirmSalesOrderUseCase — orchestrates order confirmation.

Steps:
1. Load the SalesOrder ORM
2. Convert to domain aggregate (SalesOrder + OrderLine[])
3. Call order.confirm() — applies state machine + emits OrderConfirmed
4. Persist back to ORM
5. Track events on the UoW for after-commit dispatch

Side effects (inventory reservation, notifications) are handled by the
event bus subscribers. Keeping side effects out of the use case lets us
test the orchestration without database fixtures for downstream services.
"""

import logging
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.domain.sales.entities import (
    OrderLine,
    OrderStatus,
    SalesOrder,
)
from app.domain.shared.errors import NotFoundError
from app.models.sales import SalesOrder as SalesOrderModel
from app.domain.states import assert_can_transition_sales_order
from app.services.state_transition_service import transition_status

logger = logging.getLogger(__name__)


class ConfirmSalesOrderUseCase:
    """Confirm a draft sales order.

    Idempotent: re-confirming an already-confirmed order raises
    InvalidStateTransition, which the caller can map to a 422 response.
    """

    def __init__(
        self,
        session: AsyncSession,
        user_id: int,
        warehouse_id: int = 1,
    ) -> None:
        self._session = session
        self._user_id = user_id
        self._warehouse_id = warehouse_id

    async def execute(self, order_id: int) -> SalesOrder:
        # 1. Load with eager-loaded items to avoid N+1
        stmt = (
            select(SalesOrderModel)
            .where(
                SalesOrderModel.id == order_id,
                SalesOrderModel.deleted_at.is_(None),
            )
            .options(selectinload(SalesOrderModel.items))
        )
        result = await self._session.execute(stmt)
        orm = result.scalar_one_or_none()
        if orm is None:
            raise NotFoundError(
                f"销售订单 {order_id} 不存在",
                order_id=order_id,
            )

        # 2. Build domain aggregate from ORM
        domain_order = SalesOrder(
            id=orm.id,
            order_no=orm.order_no,
            customer_id=orm.customer_id,
            quotation_id=orm.quotation_id,
            status=OrderStatus(orm.status) if orm.status else OrderStatus.DRAFT,
            notes=orm.notes,
            lines=[
                OrderLine(
                    product_id=item.product_id or 0,
                    product_name=item.product_name or "",
                    quantity=item.quantity,
                    unit_price=Decimal(str(item.unit_price or 0)),
                )
                for item in orm.items
                if item.product_id is not None
            ],
        )

        # 3. Apply state machine
        previous_status = domain_order.status
        domain_order.confirm()  # Raises InvalidStateTransition if not DRAFT

        # 4. Persist status change
        await transition_status(
            self._session,
            orm,
            domain_order.status.value,
            guard=assert_can_transition_sales_order,
            aggregate_type="SalesOrder",
            actor=self._user_id,
            action="confirm",
        )

        logger.info(
            "Order confirmed SO#%s by user#%s: %s → %s, %d lines",
            order_id,
            self._user_id,
            previous_status.value,
            domain_order.status.value,
            len(domain_order.lines),
        )

        # 5. Flush but don't commit — caller (UoW) will commit
        await self._session.flush()
        return domain_order


def to_domain_order(orm: SalesOrderModel) -> SalesOrder:
    """Helper to convert ORM → domain (also used by other use cases)."""
    return SalesOrder(
        id=orm.id,
        order_no=orm.order_no,
        customer_id=orm.customer_id,
        status=OrderStatus(orm.status) if orm.status else OrderStatus.DRAFT,
        lines=[
            OrderLine(
                product_id=item.product_id or 0,
                product_name=item.product_name or "",
                quantity=item.quantity,
                unit_price=Decimal(str(item.unit_price or 0)),
            )
            for item in orm.items
            if item.product_id is not None
        ],
    )
