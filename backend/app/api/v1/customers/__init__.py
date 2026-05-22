"""Customer API sub-modules — re-export all routers and schemas."""

from fastapi import APIRouter

from app.api.v1.customers.alerts import router as alerts_router
from app.api.v1.customers.attachments import router as attachments_router
from app.api.v1.customers.contacts import router as contacts_router
from app.api.v1.customers.crud import router as crud_router
from app.api.v1.customers.follow_ups import router as follow_ups_router
from app.api.v1.customers.level_rules import router as level_rules_router
from app.api.v1.customers.stats import router as stats_router
from app.api.v1.customers.tags import router as customer_tags_router, tags_router
from app.api.v1.customers.crud import (
    BatchDelete,
    BatchTag,
    ContactCreate,
    ContactUpdate,
    CustomerCreate,
    CustomerUpdate,
    FollowUpCreate,
    FollowUpUpdate,
    MergeRequest,
    TagCreate,
    TagUpdate,
)

# Main router — NOTE: no prefix here; sub-routers already have prefix="/customers"
# so paths resolve correctly: /customers/... → /api/v1/customers/...
router = APIRouter()
router.include_router(crud_router)
router.include_router(stats_router)
router.include_router(contacts_router)
router.include_router(follow_ups_router)
router.include_router(alerts_router)
router.include_router(level_rules_router)
router.include_router(attachments_router)
router.include_router(customer_tags_router)
router.include_router(tags_router)

__all__ = [
    "router",
    "tags_router",
    "crud_router",
    "stats_router",
    "contacts_router",
    "follow_ups_router",
    "alerts_router",
    "level_rules_router",
    "attachments_router",
    "customer_tags_router",
    # Schemas
    "CustomerCreate",
    "CustomerUpdate",
    "ContactCreate",
    "ContactUpdate",
    "FollowUpCreate",
    "FollowUpUpdate",
    "TagCreate",
    "TagUpdate",
    "BatchTag",
    "BatchDelete",
    "MergeRequest",
]
