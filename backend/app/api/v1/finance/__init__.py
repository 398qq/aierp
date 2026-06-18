"""Finance API — subpackage aggregator.

Thin HTTP adapters organized by bounded context:
- invoices   → invoice CRUD
- payments   → payment record CRUD + stats
- contracts  → contract CRUD + PDF import
- targets    → sales target CRUD + stats

The legacy ``app.api.v1.finance`` module is replaced by this subpackage
which owns the same URL namespace and tags.
"""

from fastapi import APIRouter

from app.api.v1.finance.commission_schemes import router as commission_schemes_router
from app.api.v1.finance.contracts import router as contracts_router
from app.api.v1.finance.invoices import router as invoices_router
from app.api.v1.finance.payments import router as payments_router
from app.api.v1.finance.targets import router as targets_router

router = APIRouter(tags=["finance"])
router.include_router(invoices_router)
router.include_router(payments_router)
router.include_router(contracts_router)
router.include_router(targets_router)
router.include_router(commission_schemes_router)

__all__ = ["router"]
