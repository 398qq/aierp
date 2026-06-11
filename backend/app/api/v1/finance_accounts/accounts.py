"""Finance accounts API — chart of accounts bounded context.

Routes for the chart-of-accounts lifecycle:
- list (with optional type filter)
- create / update / delete (soft)
"""

import json
import logging

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.permissions import require_perm, write_audit_log
from app.database import get_db
from app.models.account import Account
from app.schemas.common import fail, ok
from app.api.v1.finance_accounts._shared import (
    ACCOUNTS_LIST_CACHE_TTL,
    _accounts_cache_key,
)
from app.services.cache_service import (
    cache_bump_version,
    cache_get_versioned,
    cache_set_versioned,
)
from starlette.requests import Request

logger = logging.getLogger(__name__)

router = APIRouter(tags=["finance-account:account"])


@router.get("/accounts")
async def list_accounts(
    response: JSONResponse,
    type: str | None = None,
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(require_perm("finance", "read")),
):
    cache_key = _accounts_cache_key(type=type)
    cached_payload = await cache_get_versioned("accounts:list", cache_key)
    if cached_payload is not None:
        response.headers["X-Cache"] = "HIT"
        response.headers["X-Cache-Key"] = cache_key
        return ok(json.loads(cached_payload))
    response.headers["X-Cache"] = "MISS"
    q = select(Account).where(Account.deleted_at.is_(None))
    if type:
        q = q.where(Account.type == type)
    result = await db.execute(q.order_by(Account.code))
    accounts = result.scalars().all()
    payload = [
        {
            "id": a.id,
            "code": a.code,
            "name": a.name,
            "type": a.type,
            "parent_id": a.parent_id,
            "description": a.description,
            "is_active": a.is_active,
        }
        for a in accounts
    ]
    await cache_set_versioned(
        "accounts:list",
        cache_key,
        json.dumps(payload, default=str),
        ACCOUNTS_LIST_CACHE_TTL,
    )
    return ok(payload)


class AccountCreate(BaseModel):
    code: str
    name: str
    type: str
    parent_id: int | None = None
    description: str = ""


@router.post("/accounts", status_code=201)
async def create_account(
    body: AccountCreate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_perm("finance", "write")),
):
    if body.type not in ("asset", "liability", "equity", "income", "expense"):
        return fail("科目类型无效")
    a = Account(**body.model_dump())
    db.add(a)
    await db.commit()
    await write_audit_log(
        db,
        current_user["user_id"],
        current_user.get("username", ""),
        "create",
        "account",
        a.id,
        f"创建科目: {a.code} {a.name}",
        request.client.host if request.client else "",
    )
    await db.commit()
    await cache_bump_version("accounts:list")
    return ok({"id": a.id}, msg="科目创建成功")


@router.put("/accounts/{account_id}")
async def update_account(
    account_id: int,
    body: AccountCreate,
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(require_perm("finance", "write")),
):
    a = (
        await db.execute(
            select(Account).where(
                Account.id == account_id, Account.deleted_at.is_(None)
            )
        )
    ).scalar_one_or_none()
    if not a:
        return fail("科目不存在")
    for k, v in body.model_dump().items():
        setattr(a, k, v)
    await db.commit()
    await cache_bump_version("accounts:list")
    return ok(msg="科目更新成功")


@router.delete("/accounts/{account_id}")
async def delete_account(
    account_id: int,
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(require_perm("finance", "write")),
):
    import datetime

    a = (
        await db.execute(
            select(Account).where(
                Account.id == account_id, Account.deleted_at.is_(None)
            )
        )
    ).scalar_one_or_none()
    if not a:
        return fail("科目不存在")
    a.deleted_at = datetime.datetime.now(datetime.timezone.utc)
    await db.commit()
    await cache_bump_version("accounts:list")
    return ok(msg="科目已删除")
