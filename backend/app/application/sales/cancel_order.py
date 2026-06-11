"""CancelSalesOrderUseCase — orchestrates order cancellation.

Steps:
1. Load the SalesOrder ORM
2. Convert to domain aggregate
3. Call order.cancel(reason) — applies state machine + emits OrderCancelled
4. Persist back to ORM
5. Track events on the UoW for after-commit dispatch

Inventory release is handled by the OrderCancelled subscriber (see
`application.event_handlers` if added). For now the use case returns
the order and the caller is responsible for any direct orchestration.
"""

import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.domain.sales.entities import SalesOrder
from app.domain.shared.errors import NotFoundError
from app.models.sales import SalesOrder as SalesOrderModel
from app.application.sales.confirm_order import to_domain_order

logger = logging.getLogger(__name__)


class CancelSalesOrderUseCase:
    """Cancel a sales order with a reason.

    Returns the updated domain aggregate. Emits OrderCancelled; the event
    triggers the inventory release handler.
    """

    def __init__(self, session: AsyncSession, user_id: int) -> None:
        self._session = session
        self._user_id = user_id

    async def execute(self, order_id: int, reason: str) -> SalesOrder:
        if not reason or not reason.strip():
            raise ValueError("cancellation reason is required")

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

        domain_order = to_domain_order(orm)
        previous_status = domain_order.status
        domain_order.cancel(reason=reason)  # Raises InvalidStateTransition

        orm.status = domain_order.status.value

        logger.info(
            "Order cancelled SO#%s by user#%s: %s → %s, reason=%r",
            order_id,
            self._user_id,
            previous_status.value,
            domain_order.status.value,
            reason,
        )

        await self._session.flush()
        return domain_order
