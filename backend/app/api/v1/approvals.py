"""Approval workflow — rules, requests, submit/approve/reject."""

import datetime

from fastapi import APIRouter, Depends, Query, Request
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.permissions import require_perm, write_audit_log
from app.database import get_db
from app.models.approval import ApprovalAction, ApprovalRequest, ApprovalRule
from app.models.sales import Quotation
from app.models.transaction import PurchaseOrder
from app.schemas.common import fail, ok, paginated_ok

router = APIRouter(prefix="/approvals", tags=["approvals"])

DOC_TYPES = {"quotation": "报价单", "purchase_order": "采购订单"}


# ---------------------------------------------------------------------------
# Approval Rules
# ---------------------------------------------------------------------------
@router.get("/rules")
async def list_rules(
    doc_type: str | None = None,
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(get_current_user),
):
    q = select(ApprovalRule).where(ApprovalRule.deleted_at.is_(None))
    if doc_type:
        q = q.where(ApprovalRule.doc_type == doc_type)
    result = await db.execute(q.order_by(ApprovalRule.id))
    rules = result.scalars().all()
    return ok([{
        "id": r.id, "doc_type": r.doc_type, "min_amount": float(r.min_amount),
        "customer_level": r.customer_level, "flow_config": r.flow_config,
        "enabled": r.enabled, "created_at": str(r.created_at),
    } for r in rules])


class RuleCreate(BaseModel):
    doc_type: str
    min_amount: float = 0
    customer_level: str | None = None
    flow_config: list[dict] = []  # [{level:1, approver_role:"", approver_id:null}]
    enabled: bool = True


@router.post("/rules", status_code=201)
async def create_rule(
    body: RuleCreate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_perm("system", "write")),
):
    if body.doc_type not in DOC_TYPES:
        return fail(f"不支持的单据类型: {body.doc_type}")
    rule = ApprovalRule(
        doc_type=body.doc_type, min_amount=body.min_amount,
        customer_level=body.customer_level, flow_config=body.flow_config,
        enabled=body.enabled,
    )
    db.add(rule)
    await db.commit()
    await write_audit_log(db, current_user["user_id"], current_user.get("username", ""),
                          "create", "approval_rule", rule.id, f"创建审批规则: {DOC_TYPES[body.doc_type]}",
                          request.client.host if request.client else "")
    await db.commit()
    return ok({"id": rule.id}, msg="规则创建成功")


@router.put("/rules/{rule_id}")
async def update_rule(rule_id: int, body: RuleCreate, request: Request,
                      db: AsyncSession = Depends(get_db),
                      current_user: dict = Depends(require_perm("system", "write"))):
    rule = (await db.execute(
        select(ApprovalRule).where(ApprovalRule.id == rule_id, ApprovalRule.deleted_at.is_(None))
    )).scalar_one_or_none()
    if not rule:
        return fail("规则不存在")
    rule.doc_type = body.doc_type
    rule.min_amount = body.min_amount
    rule.customer_level = body.customer_level
    rule.flow_config = body.flow_config
    rule.enabled = body.enabled
    await db.commit()
    return ok(msg="规则更新成功")


@router.delete("/rules/{rule_id}")
async def delete_rule(rule_id: int, request: Request,
                      db: AsyncSession = Depends(get_db),
                      current_user: dict = Depends(require_perm("system", "write"))):
    rule = (await db.execute(
        select(ApprovalRule).where(ApprovalRule.id == rule_id, ApprovalRule.deleted_at.is_(None))
    )).scalar_one_or_none()
    if not rule:
        return fail("规则不存在")
    rule.deleted_at = datetime.datetime.now(datetime.timezone.utc)
    await db.commit()
    return ok(msg="规则已删除")


# ---------------------------------------------------------------------------
# Approval Requests
# ---------------------------------------------------------------------------
@router.get("/requests")
async def list_requests(
    status: str | None = None,
    doc_type: str | None = None,
    submitter_id: int | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(get_current_user),
):
    q = select(ApprovalRequest).where(ApprovalRequest.deleted_at.is_(None))
    if status:
        q = q.where(ApprovalRequest.status == status)
    if doc_type:
        q = q.where(ApprovalRequest.doc_type == doc_type)
    if submitter_id:
        q = q.where(ApprovalRequest.submitter_id == submitter_id)

    count_q = select(ApprovalRequest.id).where(ApprovalRequest.deleted_at.is_(None))
    if status:
        count_q = count_q.where(ApprovalRequest.status == status)
    if doc_type:
        count_q = count_q.where(ApprovalRequest.doc_type == doc_type)
    if submitter_id:
        count_q = count_q.where(ApprovalRequest.submitter_id == submitter_id)

    total = len((await db.execute(count_q)).scalars().all())
    result = await db.execute(
        q.order_by(ApprovalRequest.id.desc()).offset((page - 1) * page_size).limit(page_size)
    )
    requests = result.scalars().all()
    return paginated_ok([{
        "id": r.id, "doc_type": r.doc_type, "doc_id": r.doc_id,
        "submitter_id": r.submitter_id,
        "submitter_name": r.submitter.username if r.submitter else "",
        "status": r.status, "current_level": r.current_level,
        "created_at": str(r.created_at),
    } for r in requests], total, page, page_size)


@router.get("/requests/{request_id}")
async def get_request_detail(
    request_id: int,
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(get_current_user),
):
    req = (await db.execute(
        select(ApprovalRequest).where(ApprovalRequest.id == request_id, ApprovalRequest.deleted_at.is_(None))
    )).scalar_one_or_none()
    if not req:
        return fail("审批请求不存在")

    # Load doc summary
    doc_summary = {}
    if req.doc_type == "quotation":
        doc = (await db.execute(
            select(Quotation).where(Quotation.id == req.doc_id)
        )).scalar_one_or_none()
        if doc:
            doc_summary = {"title": doc.title, "total_amount": float(doc.total_amount), "status": doc.status}
    elif req.doc_type == "purchase_order":
        doc = (await db.execute(
            select(PurchaseOrder).where(PurchaseOrder.id == req.doc_id)
        )).scalar_one_or_none()
        if doc:
            doc_summary = {"order_no": doc.order_no, "total_amount": float(doc.total_amount), "status": doc.status}

    return ok({
        "id": req.id, "doc_type": req.doc_type, "doc_id": req.doc_id,
        "submitter_id": req.submitter_id,
        "submitter_name": req.submitter.username if req.submitter else "",
        "status": req.status, "current_level": req.current_level,
        "flow_snapshot": req.flow_snapshot,
        "doc_summary": doc_summary,
        "actions": [{
            "id": a.id, "approver_id": a.approver_id,
            "approver_name": a.approver.username if a.approver else "",
            "action": a.action, "comment": a.comment, "level": a.level,
            "created_at": str(a.created_at),
        } for a in (req.actions or [])],
        "created_at": str(req.created_at),
    })


# ---------------------------------------------------------------------------
# Submit for approval
# ---------------------------------------------------------------------------
class SubmitBody(BaseModel):
    doc_type: str
    doc_id: int


@router.post("/submit")
async def submit_approval(
    body: SubmitBody,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_perm("sales", "write")),
):
    # Find matching rule
    rule = (await db.execute(
        select(ApprovalRule).where(
            ApprovalRule.doc_type == body.doc_type,
            ApprovalRule.enabled.is_(True),
            ApprovalRule.deleted_at.is_(None),
        )
    )).scalars().first()
    if not rule:
        return fail(f"未找到 {body.doc_type} 的审批规则")

    # Check amount threshold
    doc_amount = 0.0
    if body.doc_type == "quotation":
        doc = (await db.execute(
            select(Quotation).where(Quotation.id == body.doc_id, Quotation.deleted_at.is_(None))
        )).scalar_one_or_none()
        if doc:
            doc_amount = float(doc.total_amount)
    elif body.doc_type == "purchase_order":
        doc = (await db.execute(
            select(PurchaseOrder).where(PurchaseOrder.id == body.doc_id, PurchaseOrder.deleted_at.is_(None))
        )).scalar_one_or_none()
        if doc:
            doc_amount = float(doc.total_amount)

    if doc_amount < float(rule.min_amount):
        return fail(f"金额未达到审批阈值 (¥{rule.min_amount:,.2f})")

    # Check existing pending request
    existing = (await db.execute(
        select(ApprovalRequest).where(
            ApprovalRequest.doc_type == body.doc_type,
            ApprovalRequest.doc_id == body.doc_id,
            ApprovalRequest.status == "pending",
            ApprovalRequest.deleted_at.is_(None),
        )
    )).scalar_one_or_none()
    if existing:
        return fail("该单据已有待审批请求")

    # Create request
    flow_config = rule.flow_config if isinstance(rule.flow_config, list) else []
    approval_req = ApprovalRequest(
        doc_type=body.doc_type, doc_id=body.doc_id,
        submitter_id=current_user["user_id"],
        status="pending", current_level=1,
        flow_snapshot=flow_config,
    )
    db.add(approval_req)
    await db.commit()

    await write_audit_log(db, current_user["user_id"], current_user.get("username", ""),
                          "submit_approval", body.doc_type, body.doc_id,
                          f"提交审批: {DOC_TYPES.get(body.doc_type, body.doc_type)} #{body.doc_id}",
                          request.client.host if request.client else "")
    await db.commit()
    return ok({"id": approval_req.id}, msg="审批已提交")


# ---------------------------------------------------------------------------
# Approve / Reject
# ---------------------------------------------------------------------------
class ActionBody(BaseModel):
    comment: str = ""


@router.post("/requests/{request_id}/approve")
async def approve_request(
    request_id: int,
    body: ActionBody,
    req_ctx: Request,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    approval_req = (await db.execute(
        select(ApprovalRequest).where(ApprovalRequest.id == request_id, ApprovalRequest.deleted_at.is_(None))
    )).scalar_one_or_none()
    if not approval_req:
        return fail("审批请求不存在")
    if approval_req.status != "pending":
        return fail(f"审批请求状态为 {approval_req.status}，无法操作")

    action = ApprovalAction(
        request_id=request_id, approver_id=current_user["user_id"],
        action="approve", comment=body.comment, level=approval_req.current_level,
    )
    db.add(action)

    # Check if more levels remain
    flow = approval_req.flow_snapshot if isinstance(approval_req.flow_snapshot, list) else []
    if approval_req.current_level >= len(flow):
        approval_req.status = "approved"
    else:
        approval_req.current_level += 1

    await db.commit()

    await write_audit_log(db, current_user["user_id"], current_user.get("username", ""),
                          "approve", approval_req.doc_type, approval_req.doc_id,
                          f"审批通过 (level {action.level}): {approval_req.doc_type} #{approval_req.doc_id}",
                          req_ctx.client.host if req_ctx.client else "")
    await db.commit()
    return ok(msg="审批通过")


@router.post("/requests/{request_id}/reject")
async def reject_request(
    request_id: int,
    body: ActionBody,
    req_ctx: Request,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    approval_req = (await db.execute(
        select(ApprovalRequest).where(ApprovalRequest.id == request_id, ApprovalRequest.deleted_at.is_(None))
    )).scalar_one_or_none()
    if not approval_req:
        return fail("审批请求不存在")
    if approval_req.status != "pending":
        return fail(f"审批请求状态为 {approval_req.status}，无法操作")

    action = ApprovalAction(
        request_id=request_id, approver_id=current_user["user_id"],
        action="reject", comment=body.comment, level=approval_req.current_level,
    )
    db.add(action)
    approval_req.status = "rejected"
    await db.commit()

    await write_audit_log(db, current_user["user_id"], current_user.get("username", ""),
                          "reject", approval_req.doc_type, approval_req.doc_id,
                          f"审批驳回: {approval_req.doc_type} #{approval_req.doc_id}",
                          req_ctx.client.host if req_ctx.client else "")
    await db.commit()
    return ok(msg="审批已驳回")
