"""Customer API router — backward compatibility shim.

All endpoints have been moved to submodules under app.api.v1.customers/.
This file re-exports all sub-routers and schemas for backward compatibility.
"""

from fastapi import APIRouter

from app.api.v1.customers import (
    alerts_router,
    assignment_rules_router,
    attachments_router,
    contacts_router,
    crud_router,
    follow_ups_router,
    level_rules_router,
    owner_router,
    quotations_router,
    release_rules_router,
    stats_router,
    tags_router,
    transfer_requests_router,
)
from app.api.v1.customers.schemas import (
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

router = APIRouter(prefix="/customers", tags=["customers"])

# Mount all sub-routers
router.include_router(crud_router)
router.include_router(stats_router)
router.include_router(contacts_router)
router.include_router(follow_ups_router)
router.include_router(owner_router)
router.include_router(quotations_router)
router.include_router(alerts_router)
router.include_router(assignment_rules_router)
router.include_router(level_rules_router)
router.include_router(release_rules_router)
router.include_router(attachments_router)
router.include_router(transfer_requests_router)
router.include_router(tags_router)

__all__ = [
    "router",
    "CustomerCreate",
    "CustomerUpdate",
    "ContactCreate",
    "ContactUpdate",
    "FollowUpCreate",
    "FollowUpUpdate",
    "quotations_router",
    "TagCreate",
    "TagUpdate",
    "BatchTag",
    "BatchDelete",
    "MergeRequest",
]
