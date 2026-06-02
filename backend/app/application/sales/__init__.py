"""Sales use cases — thin orchestration of domain + infrastructure.

Use cases:
- ConfirmSalesOrderUseCase — confirm a draft order, emit OrderConfirmed, lock stock
- CancelSalesOrderUseCase — cancel an order, emit OrderCancelled, release stock
- ConvertQuotationToOrderUseCase — convert quotation to sales order
"""

from app.application.sales.cancel_order import CancelSalesOrderUseCase
from app.application.sales.confirm_order import ConfirmSalesOrderUseCase
from app.application.sales.convert_quotation import ConvertQuotationToOrderUseCase

__all__ = [
    "CancelSalesOrderUseCase",
    "ConfirmSalesOrderUseCase",
    "ConvertQuotationToOrderUseCase",
]
