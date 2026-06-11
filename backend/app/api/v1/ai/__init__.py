"""AI API sub-modules — re-export all routers."""

from fastapi import APIRouter

from app.api.v1.ai.brand_ai import router as brand_ai_router
from app.api.v1.ai.chat import router as chat_router
from app.api.v1.ai.contract_ai import router as contract_ai_router
from app.api.v1.ai.customer import router as customer_ai_router
from app.api.v1.ai.finance_ai import router as finance_ai_router
from app.api.v1.ai.inventory_ai import router as inventory_ai_router
from app.api.v1.ai.matching_ai import router as matching_ai_router
from app.api.v1.ai.nlp_ai import router as nlp_ai_router
from app.api.v1.ai.orchestration_ai import router as orchestration_ai_router
from app.api.v1.ai.po_ai import router as po_ai_router
from app.api.v1.ai.pricing_ai import router as pricing_ai_router
from app.api.v1.ai.product_ai import router as product_ai_router
from app.api.v1.ai.supplier_ai import router as supplier_ai_router
from app.api.v1.ai.supplier_product_ai import router as supplier_product_ai_router
from app.api.v1.ai.target_ai import router as target_ai_router
from app.api.v1.ai.ticket_ai import router as ticket_ai_router
from app.api.v1.ai.visit_ai import router as visit_ai_router
from app.api.v1.ai.watchtower import router as watchtower_router

# Main composed router (used by app.api.v1.router)
# NOTE: No prefix here — sub-routers already have prefix="/ai", so paths resolve to /api/v1/ai/...
router = APIRouter()
router.include_router(brand_ai_router)
router.include_router(chat_router)
router.include_router(contract_ai_router)
router.include_router(customer_ai_router)
router.include_router(finance_ai_router)
router.include_router(inventory_ai_router)
router.include_router(matching_ai_router)
router.include_router(nlp_ai_router)
router.include_router(orchestration_ai_router)
router.include_router(po_ai_router)
router.include_router(pricing_ai_router)
router.include_router(product_ai_router)
router.include_router(supplier_ai_router)
router.include_router(supplier_product_ai_router)
router.include_router(target_ai_router)
router.include_router(ticket_ai_router)
router.include_router(visit_ai_router)
router.include_router(watchtower_router)

__all__ = [
    "router",
    "brand_ai_router",
    "chat_router",
    "contract_ai_router",
    "customer_ai_router",
    "finance_ai_router",
    "inventory_ai_router",
    "matching_ai_router",
    "nlp_ai_router",
    "orchestration_ai_router",
    "po_ai_router",
    "pricing_ai_router",
    "product_ai_router",
    "supplier_ai_router",
    "supplier_product_ai_router",
    "target_ai_router",
    "ticket_ai_router",
    "visit_ai_router",
]
