"""Release rules API — configure auto-release conditions for customer owners."""

import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Response, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.permissions import require_perm
from app.database import get_db
from app.models.customer import ReleaseRule
from app.schemas.common import fail, ok

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/customers/release-rules", tags=["customers"])


class ReleaseRuleCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    rule_type: str = Field(pattern=r"^(no_followup|no_order)$")
    condition_days: int = Field(default=90, ge=1, le=9999)
    target_status: str | None = None
    is_enabled: bool = True
    priority: int = 0
    notify_owner: bool = True


class ReleaseRuleUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=100)
    rule_type: str | None = Field(None, pattern=r"^(no_followup|no_order)$")
    condition_days: int | None = Field(None, ge=1, le=9999)
    target_status: str | None = None
    is_enabled: bool | None = None
    priority: int | None = None
    notify_owner: bool | None = None


def _rule_row(r: ReleaseRule) -> dict:
    return {
        "id": r.id,
        "name": r.name,
        "rule_type": r.rule_type,
        "condition_days": r.condition_days,
        "target_status": r.target_status,
        "is_enabled": r.is_enabled,
        "priority": r.priority,
        "notify_owner": r.notify_owner,
        "created_at": str(r.created_at) if r.created_at else None,
    }


@router.get("")
async def list_release_rules(
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(require_perm("customers", "read")),
):
    rows = (
        (
            await db.execute(
                select(ReleaseRule)
                .where(ReleaseRule.deleted_at.is_(None))
                .order_by(ReleaseRule.priority.asc(), ReleaseRule.created_at.desc())
            )
        )
        .scalars()
        .all()
    )
    return ok([_rule_row(r) for r in rows])


@router.post("", status_code=201)
async def create_release_rule(
    body: ReleaseRuleCreate,
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(require_perm("customers", "write")),
):
    rule = ReleaseRule(**body.model_dump())
    db.add(rule)
    await db.flush()
    return ok(_rule_row(rule))


@router.put("/{rule_id}")
async def update_release_rule(
    rule_id: int,
    body: ReleaseRuleUpdate,
    response: Response,
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(require_perm("customers", "write")),
):
    row = (
        await db.execute(
            select(ReleaseRule).where(
                ReleaseRule.id == rule_id, ReleaseRule.deleted_at.is_(None)
            )
        )
    ).scalar_one_or_none()

    if not row:
        response.status_code = status.HTTP_404_NOT_FOUND
        return fail("释放规则不存在")

    for key, val in body.model_dump(exclude_unset=True).items():
        setattr(row, key, val)
    await db.flush()
    return ok(_rule_row(row))


@router.delete("/{rule_id}")
async def delete_release_rule(
    rule_id: int,
    response: Response,
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(require_perm("customers", "delete")),
):
    row = (
        await db.execute(
            select(ReleaseRule).where(
                ReleaseRule.id == rule_id, ReleaseRule.deleted_at.is_(None)
            )
        )
    ).scalar_one_or_none()

    if not row:
        response.status_code = status.HTTP_404_NOT_FOUND
        return fail("释放规则不存在")

    row.deleted_at = datetime.now(timezone.utc)
    await db.flush()
    return ok(msg="deleted")


@router.post("/run-check")
async def run_release_check(
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(require_perm("customers", "write")),
):
    """手动触发客户负责人释放检查。"""
    from app.jobs.scheduler import _run_owner_release_check_job

    try:
        await _run_owner_release_check_job()
        return ok(msg="释放检查已完成")
    except Exception as e:
        logger.error(f"Manual release check failed: {e}")
        return fail(f"释放检查失败: {e}", 500)
