"""Re-export all schemas from crud.py for backward compatibility."""

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

__all__ = [
    "BatchDelete",
    "BatchTag",
    "ContactCreate",
    "ContactUpdate",
    "CustomerCreate",
    "CustomerUpdate",
    "FollowUpCreate",
    "FollowUpUpdate",
    "MergeRequest",
    "TagCreate",
    "TagUpdate",
]
