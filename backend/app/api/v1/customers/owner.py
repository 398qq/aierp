"""Customer owner assignment endpoints — assign, claim, release, history."""

import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Response, status
from pydantic import BaseModel, Field
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.permissions import require_perm
from app.database import get_db
from app.models.customer import Customer, CustomerOwnerLog
from app.models.user import User
from app.schemas.common import fail, ok
from app.services.cache_service import cache_bump_version

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/customers", tags=["customers"])

# ── Schemas ──


class AssignRequest(BaseModel):
    ids: list[int] = Field(min_length=1)
    owner: str = Field(min_length=1, max_length=100)


class BatchOwnerRequest(BaseModel):
    ids: list[int] = Field(min_length=1)
    action: str = Field(pattern=r"^(claim|release|assign)$")
    owner: str | None = Field(None, max_length=100)


class ClaimStatsResponse(BaseModel):
    claimed: int
    max_limit: int
    remaining: int


# ── Helpers ──


def _config_max_claim() -> int:
    """Return the per-user max claim limit.
    Configurable via env var or config; default 100, 0 = unlimited.
    """
    import os

    raw = os.getenv("AIERP_OWNER_MAX_CLAIM", "100")
    try:
        return max(0, int(raw))
    except (ValueError, TypeError):
        return 100


async def _write_owner_log(
    db: AsyncSession,
    customer_id: int,
    from_owner: str | None,
    to_owner: str | None,
    action_type: str,
    operator: str | None = None,
    reason: str | None = None,
) -> None:
    log = CustomerOwnerLog(
        customer_id=customer_id,
        from_owner=from_owner,
        to_owner=to_owner,
        action_type=action_type,
        operator=operator,
        reason=reason,
    )
    db.add(log)


async def _count_claimed(db: AsyncSession, username: str) -> int:
    result = await db.execute(
        select(func.count(Customer.id)).where(
            Customer.owner == username,
            Customer.deleted_at.is_(None),
        )
    )
    return result.scalar() or 0


async def _check_claim_limit(
    db: AsyncSession, username: str, additional: int = 1
) -> tuple[bool, int, int]:
    """Check if user can claim N more customers. Returns (ok, current, max)."""
    max_limit = _config_max_claim()
    if max_limit <= 0:
        return True, 0, 0
    current = await _count_claimed(db, username)
    if current + additional > max_limit:
        return False, current, max_limit
    return True, current, max_limit


async def _validate_owner_exists(db: AsyncSession, username: str) -> bool:
    result = await db.execute(
        select(User).where(User.username == username, User.deleted_at.is_(None))
    )
    return result.scalar_one_or_none() is not None


# ── Endpoints ──


@router.post("/batch-owner")
async def batch_set_owner(
    body: BatchOwnerRequest,
    response: Response,
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(require_perm("customers", "write")),
):
    """批量认领/释放/分配客户。

    - claim: 认领给自己
    - release: 释放到公海
    - assign: 分配给指定负责人
    """
    ids = body.ids
    action = body.action
    username = _user.get("username", "")

    if action in ("claim", "assign"):
        target_owner = username if action == "claim" else body.owner
        if action == "assign":
            if not target_owner:
                response.status_code = status.HTTP_400_BAD_REQUEST
                return fail("分配操作必须指定负责人 owner")
            if not await _validate_owner_exists(db, target_owner):
                response.status_code = status.HTTP_400_BAD_REQUEST
                return fail(f"负责人 {target_owner} 不存在或已停用")
        # check claim limit
        ok_flag, current, max_limit = await _check_claim_limit(
            db, target_owner or "", len(ids)
        )
        if not ok_flag:
            response.status_code = status.HTTP_400_BAD_REQUEST
            return fail(
                f"负责人 {target_owner} 已认领 {current} 个客户，"
                f"再认领 {len(ids)} 个将超过上限 {max_limit}"
            )
    else:
        target_owner = None

    now = datetime.now(timezone.utc)

    # Fetch current owners before update
    rows = (
        await db.execute(
            select(Customer.id, Customer.owner).where(
                Customer.id.in_(ids), Customer.deleted_at.is_(None)
            )
        )
    ).all()
    current_owner_map = {row.id: row.owner for row in rows}
    found_ids = list(current_owner_map.keys())

    if not found_ids:
        return fail("未找到有效客户", 404)

    # Perform update
    await db.execute(
        update(Customer)
        .where(Customer.id.in_(found_ids), Customer.deleted_at.is_(None))
        .values(owner=target_owner, updated_at=now)
    )

    # Write owner change logs
    for cid in found_ids:
        await _write_owner_log(
            db,
            cid,
            from_owner=current_owner_map[cid],
            to_owner=target_owner,
            action_type=action,
            operator=username,
            reason=body.owner if action == "assign" else None,
        )

    await db.flush()
    await cache_bump_version("customers:list")
    await cache_bump_version("dashboard:overview")
    await cache_bump_version("dashboard:kpi")
    await cache_bump_version("watchtower:scan")

    return ok(
        {
            "updated": len(found_ids),
            "action": action,
            "owner": target_owner,
        }
    )


@router.post("/assign")
async def assign_customers(
    body: AssignRequest,
    response: Response,
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(require_perm("customers", "write")),
):
    """批量分配客户给指定负责人（简写端点）"""
    username = _user.get("username", "")

    if not await _validate_owner_exists(db, body.owner):
        response.status_code = status.HTTP_400_BAD_REQUEST
        return fail(f"负责人 {body.owner} 不存在或已停用")

    ok_flag, current, max_limit = await _check_claim_limit(
        db, body.owner, len(body.ids)
    )
    if not ok_flag:
        response.status_code = status.HTTP_400_BAD_REQUEST
        return fail(
            f"负责人 {body.owner} 已认领 {current} 个客户，"
            f"再分配 {len(body.ids)} 个将超过上限 {max_limit}"
        )

    now = datetime.now(timezone.utc)

    rows = (
        await db.execute(
            select(Customer.id, Customer.owner).where(
                Customer.id.in_(body.ids), Customer.deleted_at.is_(None)
            )
        )
    ).all()
    found_ids = [row.id for row in rows]
    current_owner_map = {row.id: row.owner for row in rows}

    if not found_ids:
        return fail("未找到有效客户", 404)

    await db.execute(
        update(Customer)
        .where(Customer.id.in_(found_ids), Customer.deleted_at.is_(None))
        .values(owner=body.owner, updated_at=now)
    )

    for cid in found_ids:
        await _write_owner_log(
            db,
            cid,
            from_owner=current_owner_map[cid],
            to_owner=body.owner,
            action_type="assign",
            operator=username,
        )

    await db.flush()
    await cache_bump_version("customers:list")
    await cache_bump_version("dashboard:overview")
    await cache_bump_version("dashboard:kpi")
    await cache_bump_version("watchtower:scan")

    return ok(
        {
            "updated": len(found_ids),
            "owner": body.owner,
        }
    )


@router.get("/{customer_id}/owner-history")
async def get_owner_history(
    customer_id: int,
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(require_perm("customers", "read")),
):
    """获取客户负责人变更历史"""
    rows = (
        (
            await db.execute(
                select(CustomerOwnerLog)
                .where(CustomerOwnerLog.customer_id == customer_id)
                .order_by(CustomerOwnerLog.created_at.desc())
                .limit(50)
            )
        )
        .scalars()
        .all()
    )

    return ok(
        {
            "list": [
                {
                    "id": r.id,
                    "from_owner": r.from_owner,
                    "to_owner": r.to_owner,
                    "action_type": r.action_type,
                    "operator": r.operator,
                    "reason": r.reason,
                    "created_at": str(r.created_at) if r.created_at else None,
                }
                for r in rows
            ]
        }
    )


@router.get("/claim-stats")
async def get_claim_stats(
    username: str | None = None,
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(require_perm("customers", "read")),
):
    """查询负责人认领统计"""
    target = username or _user.get("username", "")
    claimed = await _count_claimed(db, target)
    max_limit = _config_max_claim()
    return ok(
        {
            "username": target,
            "claimed": claimed,
            "max_limit": max_limit,
            "remaining": max(0, max_limit - claimed) if max_limit > 0 else -1,
        }
    )
