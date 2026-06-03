"""Sales API — subpackage aggregator.

Thin HTTP adapters organized by bounded context:
- opportunities  → lead / opportunity lifecycle
- quotations     → quotation lifecycle + PDF + from-inquiry
- orders         → sales order lifecycle + PDF + PDF import
- delivery_notes → delivery note lifecycle + mark-paid
- conversions    → cross-aggregate flow (quotation→order, order→delivery)
- inquiry        → AI-powered inquiry auto-reply

Mirrors the use-case route direction in
``docs/architecture/001-design-audit-2026-06-03.md`` §1.3:
HTTP adapters stay thin, business logic lives in
``app.services.sales_service`` and (long-term)
``app.application.sales.use_cases``.

Replace the legacy ``app.api.v1.sales`` module — this subpackage owns
the same URL namespace and tags.
"""

from fastapi import APIRouter

from app.api.v1.sales.conversions import router as conversions_router
from app.api.v1.sales.delivery_notes import router as delivery_notes_router
from app.api.v1.sales.inquiry import router as inquiry_router
from app.api.v1.sales.opportunities import router as opportunities_router
from app.api.v1.sales.orders import router as orders_router
from app.api.v1.sales.quotations import router as quotations_router

router = APIRouter(tags=["sales"])
router.include_router(opportunities_router)
router.include_router(quotations_router)
router.include_router(orders_router)
router.include_router(delivery_notes_router)
router.include_router(conversions_router)
router.include_router(inquiry_router)

__all__ = ["router"]
