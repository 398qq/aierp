"""Reports API — subpackage aggregator.

Thin HTTP adapters organized by bounded context:
- templates  → report template CRUD
- predefined → /predefined/{sales,ar,inventory,procurement}
- export     → CSV export

The legacy ``app.api.v1.reports`` module is replaced by this subpackage
which owns the same URL namespace and tags.
"""

from fastapi import APIRouter

from app.api.v1.reports.export import router as export_router
from app.api.v1.reports.predefined import router as predefined_router
from app.api.v1.reports.templates import router as templates_router

router = APIRouter(prefix="/reports", tags=["reports"])
router.include_router(templates_router)
router.include_router(predefined_router)
router.include_router(export_router)

__all__ = ["router"]
