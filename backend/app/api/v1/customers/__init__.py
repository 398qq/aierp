"""Customer API sub-modules — re-export all routers and schemas."""

from fastapi import APIRouter

from app.api.v1.customers.alerts import router as alerts_router
from app.api.v1.customers.attachments import router as attachments_router
from app.api.v1.customers.bulk import router as bulk_router
from app.api.v1.customers.contacts import router as contacts_router
from app.api.v1.customers.crud import router as crud_router
from app.api.v1.customers.follow_ups import router as follow_ups_router
from app.api.v1.customers.level_rules import router as level_rules_router
from app.api.v1.customers.list import router as list_router
from app.api.v1.customers.assignment_rules import router as assignment_rules_router
from app.api.v1.customers.owner import router as owner_router
from app.api.v1.customers.quotations import router as quotations_router
from app.api.v1.customers.release_rules import router as release_rules_router
from app.api.v1.customers.stats import router as stats_router
from app.api.v1.customers.transfer_requests import router as transfer_requests_router
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
router.include_router(list_router)
router.include_router(crud_router)
router.include_router(bulk_router)
router.include_router(stats_router)
router.include_router(contacts_router)
router.include_router(follow_ups_router)
router.include_router(quotations_router)
router.include_router(alerts_router)
router.include_router(assignment_rules_router)
router.include_router(level_rules_router)
router.include_router(release_rules_router)
router.include_router(attachments_router)
router.include_router(owner_router)
router.include_router(transfer_requests_router)
router.include_router(customer_tags_router)
router.include_router(tags_router)

__all__ = [
    "router",
    "tags_router",
    "crud_router",
    "stats_router",
    "contacts_router",
    "follow_ups_router",
    "quotations_router",
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
