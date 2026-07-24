"""Assignment rules API — auto-assign public-sea customers to owners."""

import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Response, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.permissions import require_perm
from app.database import get_db
from app.models.customer import AssignmentRule, AssignmentRuleCondition
from app.schemas.common import fail, ok

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/customers/assignment-rules", tags=["customers"])


class ConditionSchema(BaseModel):
    field: str = Field(pattern=r"^(industry|region|source|level|customer_type)$")
    operator: str = Field(pattern=r"^(equals|in|contains|not_empty)$")
    value: str = Field(max_length=255)


class AssignmentRuleCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    priority: int = 0
    condition_logic: str = Field(default="all", pattern=r"^(all|any)$")
    assigned_to: str = Field(min_length=1, max_length=100)
    max_customers: int | None = None
    is_enabled: bool = True
    conditions: list[ConditionSchema] = []


class AssignmentRuleUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=100)
    priority: int | None = None
    condition_logic: str | None = Field(None, pattern=r"^(all|any)$")
    assigned_to: str | None = Field(None, min_length=1, max_length=100)
    max_customers: int | None = None
    is_enabled: bool | None = None
    conditions: list[ConditionSchema] | None = None


def _rule_row(
    r: AssignmentRule,
    conditions: list[AssignmentRuleCondition] | None = None,
) -> dict:
    conds = conditions if conditions is not None else (r.conditions or [])
    return {
        "id": r.id,
        "name": r.name,
        "priority": r.priority,
        "condition_logic": r.condition_logic,
        "assigned_to": r.assigned_to,
        "max_customers": r.max_customers,
        "is_enabled": r.is_enabled,
        "created_at": str(r.created_at) if r.created_at else None,
        "conditions": [
            {"id": c.id, "field": c.field, "operator": c.operator, "value": c.value}
            for c in conds
        ],
    }


@router.get("")
async def list_assignment_rules(
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(require_perm("customers", "read")),
):
    rows = (
        (
            await db.execute(
                select(AssignmentRule)
                .where(AssignmentRule.deleted_at.is_(None))
                .options(selectinload(AssignmentRule.conditions))
                .order_by(
                    AssignmentRule.priority.asc(), AssignmentRule.created_at.desc()
                )
            )
        )
        .scalars()
        .all()
    )
    return ok([_rule_row(r) for r in rows])


@router.post("", status_code=201)
async def create_assignment_rule(
    body: AssignmentRuleCreate,
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(require_perm("customers", "write")),
):
    conditions_data = body.conditions
    rule_data = body.model_dump(exclude={"conditions"})
    rule = AssignmentRule(**rule_data)
    db.add(rule)
    await db.flush()

    new_conds: list[AssignmentRuleCondition] = []
    for c in conditions_data:
        cond = AssignmentRuleCondition(rule_id=rule.id, **c.model_dump())
        db.add(cond)
        new_conds.append(cond)
    await db.flush()

    return ok(_rule_row(rule, conditions=new_conds))


@router.put("/{rule_id}")
async def update_assignment_rule(
    rule_id: int,
    body: AssignmentRuleUpdate,
    response: Response,
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(require_perm("customers", "write")),
):
    row = (
        await db.execute(
            select(AssignmentRule)
            .where(AssignmentRule.id == rule_id, AssignmentRule.deleted_at.is_(None))
            .options(selectinload(AssignmentRule.conditions))
        )
    ).scalar_one_or_none()

    if not row:
        response.status_code = status.HTTP_404_NOT_FOUND
        return fail("分配规则不存在")

    for key, val in body.model_dump(exclude={"conditions"}, exclude_unset=True).items():
        setattr(row, key, val)

    if body.conditions is not None:
        # Delete old conditions, add new ones
        for old_cond in row.conditions:
            await db.delete(old_cond)
        for c in body.conditions:
            cond = AssignmentRuleCondition(rule_id=row.id, **c.model_dump())
            db.add(cond)

    await db.flush()
    # Re-read conditions from the DB so the response reflects the replacement
    # set rather than the stale ``row.conditions`` relationship loaded earlier.
    fresh_conds = (
        (
            await db.execute(
                select(AssignmentRuleCondition).where(
                    AssignmentRuleCondition.rule_id == row.id
                )
            )
        )
        .scalars()
        .all()
    )
    return ok(_rule_row(row, conditions=list(fresh_conds)))


@router.delete("/{rule_id}")
async def delete_assignment_rule(
    rule_id: int,
    response: Response,
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(require_perm("customers", "delete")),
):
    row = (
        await db.execute(
            select(AssignmentRule).where(
                AssignmentRule.id == rule_id, AssignmentRule.deleted_at.is_(None)
            )
        )
    ).scalar_one_or_none()

    if not row:
        response.status_code = status.HTTP_404_NOT_FOUND
        return fail("分配规则不存在")

    row.deleted_at = datetime.now(timezone.utc)
    await db.flush()
    return ok(msg="deleted")


@router.post("/reorder")
async def reorder_rules(
    body: dict,
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(require_perm("customers", "write")),
):
    """拖拽排序：传入 id 列表按顺序设置 priority。"""
    ids: list[int] = body.get("ids", [])
    if not ids:
        return fail("ids 不能为空", 400)
    for idx, rid in enumerate(ids):
        await db.execute(
            select(AssignmentRule).where(
                AssignmentRule.id == rid, AssignmentRule.deleted_at.is_(None)
            )
        )
        # Use direct UPDATE to avoid loading all rows
        from sqlalchemy import update

        await db.execute(
            update(AssignmentRule).where(AssignmentRule.id == rid).values(priority=idx)
        )
    await db.flush()
    return ok(msg="reordered")


@router.post("/run")
async def run_auto_assign(
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(require_perm("customers", "write")),
):
    """手动触发自动分配：扫描公海客户，匹配规则后分配。"""
    from app.jobs.scheduler import _run_auto_assign_job

    try:
        result = await _run_auto_assign_job()
        return ok(result)
    except Exception as e:
        logger.error(f"Manual auto-assign failed: {e}")
        return fail(f"自动分配失败: {e}", 500)
