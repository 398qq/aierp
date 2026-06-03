"""Transactions API — subpackage aggregator.

Re-exports the 5 sub-routers so that the existing module-level names
(``po_router``, ``pay_router``, ``ticket_router``, ``visit_router``,
``sample_router``) are preserved at the package level. This means
``app.api.v1.router.py`` can continue to do:

    from app.api.v1 import transactions
    api_router.include_router(transactions.po_router)
    api_router.include_router(transactions.pay_router)
    ...

without modification.
"""

from app.api.v1.transactions.payments import pay_router
from app.api.v1.transactions.purchase_orders import po_router
from app.api.v1.transactions.samples import sample_router
from app.api.v1.transactions.tickets import ticket_router
from app.api.v1.transactions.visits import visit_router

__all__ = ["po_router", "pay_router", "ticket_router", "visit_router", "sample_router"]
