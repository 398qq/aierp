"""Owner transfer request & approval workflow API."""

import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Query, Response, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.permissions import require_perm
from app.database import get_db
from app.models.customer import Customer, CustomerOwnerLog, OwnerTransferRequest
from app.schemas.common import fail, ok

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/customers/transfer-requests", tags=["customers"])

REQUEST_STATUS_TRANSITIONS = {
    "pending": ["approved", "rejected", "cancelled"],
    "approved": [],
    "rejected": [],
    "cancelled": [],
}


class TransferRequestCreate(BaseModel):
    customer_id: int = Field(gt=0)
    to_owner: str = Field(min_length=1, max_length=100)
    reason: str | None = Field(None, max_length=500)


class TransferRequestReview(BaseModel):
    comment: str | None = Field(None, max_length=500)


def _row(r: OwnerTransferRequest) -> dict:
    return {
        "id": r.id,
        "customer_id": r.customer_id,
        "from_owner": r.from_owner,
        "to_owner": r.to_owner,
        "requested_by": r.requested_by,
        "status": r.status,
        "reason": r.reason,
        "reviewed_by": r.reviewed_by,
        "review_comment": r.review_comment,
        "reviewed_at": str(r.reviewed_at) if r.reviewed_at else None,
        "created_at": str(r.created_at) if r.created_at else None,
        "updated_at": str(r.updated_at) if r.updated_at else None,
    }


@router.post("", status_code=201)
async def create_transfer_request(
    body: TransferRequestCreate,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(require_perm("customers", "write")),
):
    """提交负责人转移申请。转移必须经过审批才能生效。"""
    current_user = user.get("username", user.get("sub", "unknown"))

    customer = (
        await db.execute(
            select(Customer).where(
                Customer.id == body.customer_id, Customer.deleted_at.is_(None)
            )
        )
    ).scalar_one_or_none()

    if not customer:
        return fail("客户不存在", status.HTTP_404_NOT_FOUND)

    # Check for existing pending request for this customer
    existing = (
        await db.execute(
            select(OwnerTransferRequest).where(
                OwnerTransferRequest.customer_id == body.customer_id,
                OwnerTransferRequest.status == "pending",
                OwnerTransferRequest.deleted_at.is_(None),
            )
        )
    ).scalar_one_or_none()

    if existing:
        return fail("该客户已有一个待审批的转移申请", status.HTTP_409_CONFLICT)

    req = OwnerTransferRequest(
        customer_id=body.customer_id,
        from_owner=customer.owner,
        to_owner=body.to_owner,
        requested_by=current_user,
        reason=body.reason,
    )
    db.add(req)
    await db.flush()
    return ok(_row(req))


@router.get("")
async def list_transfer_requests(
    status_filter: str | None = Query(None, alias="status"),
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(require_perm("customers", "read")),
):
    q = select(OwnerTransferRequest).where(OwnerTransferRequest.deleted_at.is_(None))
    if status_filter:
        q = q.where(OwnerTransferRequest.status == status_filter)
    q = q.order_by(OwnerTransferRequest.created_at.desc())
    result = await db.execute(q)
    rows = result.scalars().all()
    return ok([_row(r) for r in rows])


@router.get("/{request_id}")
async def get_transfer_request(
    request_id: int,
    response: Response,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(require_perm("customers", "read")),
):
    row = (
        await db.execute(
            select(OwnerTransferRequest).where(
                OwnerTransferRequest.id == request_id,
                OwnerTransferRequest.deleted_at.is_(None),
            )
        )
    ).scalar_one_or_none()

    if not row:
        response.status_code = status.HTTP_404_NOT_FOUND
        return fail("转移申请不存在")
    return ok(_row(row))


@router.post("/{request_id}/approve")
async def approve_transfer_request(
    request_id: int,
    body: TransferRequestReview,
    response: Response,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(require_perm("customers", "write")),
):
    """审批通过转移申请，实际执行负责人变更。"""
    current_user = user.get("username", user.get("sub", "unknown"))

    row = (
        await db.execute(
            select(OwnerTransferRequest).where(
                OwnerTransferRequest.id == request_id,
                OwnerTransferRequest.deleted_at.is_(None),
            )
        )
    ).scalar_one_or_none()

    if not row:
        response.status_code = status.HTTP_404_NOT_FOUND
        return fail("转移申请不存在")

    if row.status != "pending":
        return fail(f"申请已{row.status}，无法再次审批", status.HTTP_409_CONFLICT)

    customer = (
        await db.execute(
            select(Customer).where(
                Customer.id == row.customer_id,
                Customer.deleted_at.is_(None),
            )
        )
    ).scalar_one_or_none()

    if not customer:
        return fail("客户已被删除", status.HTTP_404_NOT_FOUND)

    row.status = "approved"
    row.reviewed_by = current_user
    row.review_comment = body.comment
    row.reviewed_at = datetime.now(timezone.utc)

    old_owner = customer.owner
    customer.owner = row.to_owner

    log = CustomerOwnerLog(
        customer_id=row.customer_id,
        from_owner=old_owner,
        to_owner=row.to_owner,
        action_type="transfer_in",
        operator=current_user,
        reason=f"转移审批通过: {row.reason or ''}",
    )
    db.add(log)

    await db.flush()
    # ``updated_at`` uses a server-side ``onupdate`` — flush expires it, so
    # refresh before serialising to avoid implicit IO under async (MissingGreenlet).
    await db.refresh(row)
    return ok(_row(row))


@router.post("/{request_id}/reject")
async def reject_transfer_request(
    request_id: int,
    body: TransferRequestReview,
    response: Response,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(require_perm("customers", "write")),
):
    """驳回转移申请。"""
    current_user = user.get("username", user.get("sub", "unknown"))

    row = (
        await db.execute(
            select(OwnerTransferRequest).where(
                OwnerTransferRequest.id == request_id,
                OwnerTransferRequest.deleted_at.is_(None),
            )
        )
    ).scalar_one_or_none()

    if not row:
        response.status_code = status.HTTP_404_NOT_FOUND
        return fail("转移申请不存在")

    if row.status != "pending":
        return fail(f"申请已{row.status}，无法驳回", status.HTTP_409_CONFLICT)

    row.status = "rejected"
    row.reviewed_by = current_user
    row.review_comment = body.comment
    row.reviewed_at = datetime.now(timezone.utc)
    await db.flush()
    await db.refresh(row)
    return ok(_row(row))


@router.post("/{request_id}/cancel")
async def cancel_transfer_request(
    request_id: int,
    response: Response,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(require_perm("customers", "write")),
):
    """撤销转移申请（仅限申请人自己）。"""
    current_user = user.get("username", user.get("sub", "unknown"))

    row = (
        await db.execute(
            select(OwnerTransferRequest).where(
                OwnerTransferRequest.id == request_id,
                OwnerTransferRequest.deleted_at.is_(None),
            )
        )
    ).scalar_one_or_none()

    if not row:
        response.status_code = status.HTTP_404_NOT_FOUND
        return fail("转移申请不存在")

    if row.requested_by != current_user:
        return fail("只能撤销自己的申请", status.HTTP_403_FORBIDDEN)

    if row.status != "pending":
        return fail(f"申请已{row.status}，无法撤销", status.HTTP_409_CONFLICT)

    row.status = "cancelled"
    await db.flush()
    await db.refresh(row)
    return ok(_row(row))
