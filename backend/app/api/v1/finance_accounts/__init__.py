"""Finance accounts API — subpackage aggregator.

Thin HTTP adapters organized by bounded context:
- accounts  → chart of accounts CRUD
- journal   → journal entries + posting
- bank      → bank reconciliation
- reports   → P&L and AP aggregation

The legacy ``app.api.v1.finance_accounts`` module is replaced by this
subpackage which owns the same URL namespace and tags.
"""

from fastapi import APIRouter

from app.api.v1.finance_accounts.accounts import router as accounts_router
from app.api.v1.finance_accounts.bank import router as bank_router
from app.api.v1.finance_accounts.journal import router as journal_router
from app.api.v1.finance_accounts.reports import router as reports_router

router = APIRouter(prefix="/finance", tags=["finance-account"])
router.include_router(accounts_router)
router.include_router(journal_router)
router.include_router(bank_router)
router.include_router(reports_router)

__all__ = ["router"]
