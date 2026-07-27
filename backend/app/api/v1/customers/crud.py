"""Customer CRUD operations — list, create, update, delete, merge, import, export."""

import hashlib
import json
import logging
import os
import re
import unicodedata
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Response, status
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.permissions import require_perm
from app.core.pii_policy import apply_pii_mask
from app.database import get_db
from app.models.customer import Customer, CustomerLog
from app.schemas.common import fail, ok
from app.services.cache_service import cache_bump_version
from app.services.customer_service import (
    calc_health,
    customer_name_conflict_message,
    find_name_conflict,
)

UPLOAD_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "..", "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)

_FORBIDDEN_FILENAME_CHARS = re.compile(r"[/\\\x00\r\n]")
_CODE_NUMBER_RE = re.compile(r"\d+")
COMPANY_SUFFIXES = (
    "有限责任公司",
    "股份有限公司",
    "集团有限公司",
    "控股有限公司",
    "有限公司",
    "责任公司",
    "股份公司",
    "控股集团",
    "集团",
    "公司",
)


def _safe_filename(name: str) -> str:
    if not name:
        return "unnamed"
    name = _FORBIDDEN_FILENAME_CHARS.sub("", name)
    return name or "unnamed"


def _generate_short_name(name: str | None) -> str | None:
    if not name:
        return None
    value = unicodedata.normalize("NFKC", name.strip())
    value = re.sub(r"\s+", "", value)
    value = re.sub(r"\([^()]*\)", "", value)
    for suffix in COMPANY_SUFFIXES:
        if value.endswith(suffix) and len(value) > len(suffix):
            value = value[: -len(suffix)]
            break
    return (value or name.strip())[:100]


def _short_name_with_suffix(base: str, suffix: str) -> str:
    suffix_text = f"-{suffix}"
    return f"{base[: 100 - len(suffix_text)]}{suffix_text}"


async def _short_name_exists(
    db: AsyncSession, short_name: str, exclude_id: int | None = None
) -> bool:
    stmt = select(func.count(Customer.id)).where(
        Customer.deleted_at.is_(None),
        Customer.short_name == short_name,
    )
    if exclude_id is not None:
        stmt = stmt.where(Customer.id != exclude_id)
    return bool((await db.execute(stmt)).scalar() or 0)


async def _dedupe_auto_short_name(
    db: AsyncSession,
    short_name: str | None,
    customer_id: int,
    exclude_id: int | None = None,
) -> str | None:
    if not short_name:
        return short_name
    if not await _short_name_exists(db, short_name, exclude_id=exclude_id):
        return short_name

    numbered = _short_name_with_suffix(short_name, f"{customer_id:06d}")
    if not await _short_name_exists(db, numbered, exclude_id=exclude_id):
        return numbered

    suffix = 2
    while await _short_name_exists(
        db,
        _short_name_with_suffix(short_name, f"{customer_id:06d}-{suffix}"),
        exclude_id=exclude_id,
    ):
        suffix += 1
    return _short_name_with_suffix(short_name, f"{customer_id:06d}-{suffix}")


def _extract_code_number(code: str | None) -> str | None:
    if not code:
        return None
    matches = _CODE_NUMBER_RE.findall(unicodedata.normalize("NFKC", code))
    if not matches:
        return None
    value = matches[-1].lstrip("0")
    return value or "0"


def _code_number_conflict_message(code: str, conflict_code: str | None) -> str:
    return f"客户编码数字部分已存在：{code} 与 {conflict_code or '-'} 数字部分相同，请变更后再添加"


async def _find_code_number_conflict(
    db: AsyncSession,
    code: str | None,
    exclude_id: int | None = None,
) -> Customer | None:
    code_number = _extract_code_number(code)
    if code_number is None:
        return None

    stmt = select(Customer).where(
        Customer.deleted_at.is_(None), Customer.code.isnot(None)
    )
    if exclude_id is not None:
        stmt = stmt.where(Customer.id != exclude_id)
    rows = (await db.execute(stmt)).scalars().all()
    return next(
        (row for row in rows if _extract_code_number(row.code) == code_number), None
    )


async def _generate_unique_code(
    db: AsyncSession,
    start_number: int,
    region: str | None,
    exclude_id: int | None = None,
) -> str:
    number = max(1, start_number)
    while True:
        code = _generate_code(number, region)
        if await _find_code_number_conflict(db, code, exclude_id=exclude_id) is None:
            return code
        number += 1


async def _log(
    db: AsyncSession,
    customer_id: int,
    action: str,
    field_name: str | None = None,
    old_value: str | None = None,
    new_value: str | None = None,
    operator: str | None = None,
    summary: str | None = None,
):
    entry = CustomerLog(
        customer_id=customer_id,
        action=action,
        field_name=field_name,
        old_value=old_value,
        new_value=new_value,
        operator=operator,
        summary=summary,
    )
    db.add(entry)


class MergeRequest(BaseModel):
    source_id: int
    target_id: int


# --- Schemas ---


class CustomerCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    code: str | None = None
    short_name: str | None = None
    contact_person: str | None = None
    phone: str | None = None
    email: str | None = None
    website: str | None = None
    address: str | None = None
    unified_social_credit_code: str | None = None
    tax_id: str | None = None
    registration_number: str | None = None
    invoice_title: str | None = None
    invoice_address: str | None = None
    bank_name: str | None = None
    bank_account: str | None = None
    industry: str | None = None
    level: str | None = None
    source: str | None = None
    customer_type: str | None = None
    region: str | None = None
    price_tier: str | None = None
    annual_revenue: float | None = None
    employee_count: int | None = None
    credit_limit: float | None = None
    contract_required: bool = False
    credit_control_enabled: bool = False
    credit_level: str | None = None
    payment_terms: str | None = None
    payment_method: str | None = None
    currency: str = "CNY"
    delivery_address: str | None = None
    default_incoterm: str | None = None
    status: str | None = None
    owner: str | None = None
    notes: str | None = None


class CustomerUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=255)
    code: str | None = None
    short_name: str | None = None
    contact_person: str | None = None
    phone: str | None = None
    email: str | None = None
    website: str | None = None
    address: str | None = None
    unified_social_credit_code: str | None = None
    tax_id: str | None = None
    registration_number: str | None = None
    invoice_title: str | None = None
    invoice_address: str | None = None
    bank_name: str | None = None
    bank_account: str | None = None
    industry: str | None = None
    level: str | None = None
    source: str | None = None
    customer_type: str | None = None
    region: str | None = None
    price_tier: str | None = None
    annual_revenue: float | None = None
    employee_count: int | None = None
    credit_limit: float | None = None
    contract_required: bool | None = None
    credit_control_enabled: bool | None = None
    credit_level: str | None = None
    payment_terms: str | None = None
    payment_method: str | None = None
    currency: str | None = None
    delivery_address: str | None = None
    default_incoterm: str | None = None
    status: str | None = None
    owner: str | None = None
    notes: str | None = None


class ContactCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    title: str | None = None
    role: str | None = None
    phone: str | None = None
    email: str | None = None
    wechat: str | None = None
    is_primary: bool = False
    notes: str | None = None


class ContactUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=100)
    title: str | None = None
    role: str | None = None
    phone: str | None = None
    email: str | None = None
    wechat: str | None = None
    is_primary: bool | None = None
    notes: str | None = None


class FollowUpCreate(BaseModel):
    opportunity_id: int | None = None
    method: str | None = None
    status: str | None = None
    content: str | None = None
    result: str | None = None
    planned_at: str | None = None
    completed_at: str | None = None
    priority: str | None = None
    assigned_to: str | None = None


class FollowUpUpdate(BaseModel):
    opportunity_id: int | None = None
    method: str | None = None
    status: str | None = None
    content: str | None = None
    result: str | None = None
    planned_at: str | None = None
    completed_at: str | None = None
    priority: str | None = None
    assigned_to: str | None = None


class TagCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    color: str | None = Field(None, max_length=20)


class TagUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=100)
    color: str | None = Field(None, max_length=20)


class BatchTag(BaseModel):
    ids: list[int]
    tag_ids: list[int]


class BatchDelete(BaseModel):
    ids: list[int]


def _customer_row(
    c: Customer,
    now: datetime | None = None,
    total_amount: float | None = None,
) -> dict:
    if now is None:
        now = datetime.now(timezone.utc)
    health_score, health_label = calc_health(c, orders=[], payments=[], now=now)
    return {
        "id": c.id,
        "code": c.code,
        "name": c.name,
        "short_name": c.short_name,
        "contact_person": c.contact_person,
        "phone": c.phone,
        "email": c.email,
        "website": c.website,
        "address": c.address,
        "tax_id": c.tax_id,
        "registration_number": c.registration_number,
        "unified_social_credit_code": c.unified_social_credit_code,
        "invoice_title": c.invoice_title,
        "invoice_phone": c.invoice_phone,
        "tax_rate": float(c.tax_rate) if c.tax_rate else None,
        "invoice_address": c.invoice_address,
        "bank_name": c.bank_name,
        "bank_account": c.bank_account,
        "industry": c.industry,
        "level": c.level,
        "source": c.source,
        "customer_type": c.customer_type,
        "region": c.region,
        "price_tier": c.price_tier,
        "annual_revenue": float(c.annual_revenue) if c.annual_revenue else None,
        "employee_count": c.employee_count,
        "credit_limit": float(c.credit_limit) if c.credit_limit else None,
        "contract_required": c.contract_required,
        "credit_control_enabled": c.credit_control_enabled,
        "credit_level": c.credit_level,
        "payment_terms": c.payment_terms,
        "payment_method": c.payment_method,
        "currency": c.currency,
        "delivery_address": c.delivery_address,
        "default_incoterm": c.default_incoterm,
        "status": c.status.value if hasattr(c.status, "value") else c.status,
        "total_amount": float(total_amount) if total_amount is not None else None,
        "lifecycle": c.lifecycle,
        "last_contacted_at": str(c.last_contacted_at) if c.last_contacted_at else None,
        "created_at": str(c.created_at) if c.created_at else None,
        "owner": c.owner,
        "notes": c.notes,
        "parent_id": c.parent_id,
        "health_score": health_score,
        "health_label": health_label,
        "tags": [
            {"id": t.id, "name": t.name, "color": t.color} for t in (c.tags or [])
        ],
    }


def _generate_code(customer_id: int, region: str | None = None) -> str:
    region_prefix = _region_abbr(region)
    if region_prefix:
        return f"CUST-{region_prefix}-{customer_id:06d}"
    return f"CUST-{customer_id:06d}"


REGION_ABBR_MAP = {
    "华东": "HD",
    "华南": "HN",
    "华北": "HB",
    "华中": "HZ",
    "西南": "XN",
    "西北": "XB",
    "东北": "DB",
    "海外": "HW",
}


def _region_abbr(region: str | None) -> str:
    if not region:
        return ""
    return REGION_ABBR_MAP.get(region, region[:2].upper())


SORTABLE_COLUMNS = {
    "id": Customer.id,
    "name": Customer.name,
    "code": Customer.code,
    "industry": Customer.industry,
    "level": Customer.level,
    "region": Customer.region,
    "source": Customer.source,
    "credit_level": Customer.credit_level,
    "created_at": Customer.created_at,
    "updated_at": Customer.updated_at,
    "last_contacted_at": Customer.last_contacted_at,
}

CSV_TEMPLATE_HEADERS = [
    "名称",
    "编码",
    "简称",
    "行业",
    "等级",
    "区域",
    "来源",
    "类型",
    "信用等级",
    "信用额度",
    "联系人",
    "电话",
    "邮箱",
    "网站",
    "地址",
    "纳税人识别号",
    "统一社会信用代码",
    "发票抬头",
    "发票地址",
    "开户行",
    "银行账号",
    "价格等级",
    "年营业额",
    "员工数",
    "付款条件",
    "付款方式",
    "币种",
    "收货地址",
    "贸易条款",
    "备注",
]

router = APIRouter(prefix="/customers", tags=["customers"])

CUSTOMERS_LIST_CACHE_TTL = 300
CUSTOMERS_LIST_CACHE_VERSION = "v2"
logger = logging.getLogger(__name__)


def _customers_cache_key(**parts: object) -> str:
    canonical = json.dumps(parts, sort_keys=True, default=str)
    digest = hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:16]
    return f"customers:list:{CUSTOMERS_LIST_CACHE_VERSION}:{digest}"


@router.get("/{customer_id:int}")
async def get_customer(
    customer_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_perm("customers", "read")),
):
    result = await db.execute(
        select(Customer).where(
            Customer.id == customer_id, Customer.deleted_at.is_(None)
        )
    )
    customer = result.scalar_one_or_none()
    if customer is None:
        return fail("Customer not found", 404)
    now = datetime.now(timezone.utc)
    from app.models.sales import SalesOrder

    total_amount = await db.scalar(
        select(func.coalesce(func.sum(SalesOrder.total_amount), 0)).where(
            SalesOrder.customer_id == customer_id,
            SalesOrder.deleted_at.is_(None),
        )
    )
    data = _customer_row(customer, now=now, total_amount=total_amount)
    data["contacts"] = [
        {
            "id": ct.id,
            "name": ct.name,
            "title": ct.title,
            "role": ct.role,
            "phone": ct.phone,
            "email": ct.email,
            "wechat": ct.wechat,
            "is_primary": ct.is_primary,
            "notes": ct.notes,
        }
        for ct in (customer.contacts or [])
    ]
    data["follow_ups"] = [
        {
            "id": f.id,
            "method": f.method,
            "status": f.status,
            "content": f.content,
            "result": f.result,
            "planned_at": str(f.planned_at) if f.planned_at else None,
            "completed_at": str(f.completed_at) if f.completed_at else None,
            "priority": f.priority,
            "assigned_to": f.assigned_to,
            "created_at": str(f.created_at) if f.created_at else None,
        }
        for f in (customer.follow_ups or [])
    ]
    # Stage 19 P2 #3: per-record PII masking on detail response.
    data = apply_pii_mask(data, current_user)
    data["contacts"] = [apply_pii_mask(ct, current_user) for ct in data["contacts"]]
    return ok(data)


@router.post("", status_code=201)
async def create_customer(
    body: CustomerCreate,
    response: Response,
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(require_perm("customers", "write")),
):
    data = body.model_dump()
    name_conflict = await find_name_conflict(db, data.get("name"))
    if name_conflict:
        response.status_code = status.HTTP_400_BAD_REQUEST
        return fail(customer_name_conflict_message(data["name"], name_conflict.name))
    if data.get("code"):
        conflict = await _find_code_number_conflict(db, data["code"])
        if conflict:
            response.status_code = status.HTTP_400_BAD_REQUEST
            return fail(_code_number_conflict_message(data["code"], conflict.code))
    auto_short_name = not data.get("short_name")
    if not data.get("short_name"):
        data["short_name"] = _generate_short_name(data.get("name"))
    auto_code = not data.get("code")
    customer = Customer(**data)
    db.add(customer)
    await db.flush()
    if auto_code:
        customer.code = await _generate_unique_code(
            db, customer.id, customer.region, exclude_id=customer.id
        )
        await db.flush()
    if auto_short_name:
        customer.short_name = await _dedupe_auto_short_name(
            db,
            customer.short_name,
            customer.id,
            exclude_id=customer.id,
        )
        await db.flush()
    await _log(
        db,
        customer.id,
        "create",
        summary=f"创建客户: {customer.name}",
        operator=_user.get("username"),
    )
    await db.flush()
    from app.services.embedding_pipeline import after_customer_save

    after_customer_save(customer.id)
    await cache_bump_version("customers:list")
    await cache_bump_version("dashboard:overview")
    await cache_bump_version("dashboard:kpi")
    return ok(
        {
            "id": customer.id,
            "name": customer.name,
            "code": customer.code,
            "status": customer.status.value
            if hasattr(customer.status, "value")
            else customer.status,
            "created_at": str(customer.created_at) if customer.created_at else None,
        }
    )


@router.put("/{customer_id:int}")
async def update_customer(
    customer_id: int,
    body: CustomerUpdate,
    response: Response,
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(require_perm("customers", "write")),
):
    result = await db.execute(
        select(Customer).where(
            Customer.id == customer_id, Customer.deleted_at.is_(None)
        )
    )
    customer = result.scalar_one_or_none()
    if customer is None:
        return fail("Customer not found", 404)
    data = body.model_dump(exclude_unset=True)
    if data.get("name"):
        name_conflict = await find_name_conflict(
            db, data["name"], exclude_id=customer_id
        )
        if name_conflict:
            response.status_code = status.HTTP_400_BAD_REQUEST
            return fail(
                customer_name_conflict_message(data["name"], name_conflict.name)
            )
    if data.get("code"):
        conflict = await _find_code_number_conflict(
            db, data["code"], exclude_id=customer_id
        )
        if conflict:
            response.status_code = status.HTTP_400_BAD_REQUEST
            return fail(_code_number_conflict_message(data["code"], conflict.code))

    if "status" in data and data["status"] != customer.status:
        from app.domain.states import assert_can_transition_customer

        assert_can_transition_customer(customer.status, data["status"])

    next_name = data.get("name", customer.name)
    auto_short_name = False
    if "short_name" in data:
        if not data.get("short_name"):
            data["short_name"] = _generate_short_name(next_name)
            auto_short_name = True
    elif data.get("name") and not customer.short_name:
        data["short_name"] = _generate_short_name(next_name)
        auto_short_name = True
    if auto_short_name:
        data["short_name"] = await _dedupe_auto_short_name(
            db,
            data.get("short_name"),
            customer.id,
            exclude_id=customer.id,
        )
    for key, val in data.items():
        old = getattr(customer, key, None)
        setattr(customer, key, val)
        if str(old) != str(val) and key != "notes":
            await _log(
                db,
                customer_id,
                "update",
                field_name=key,
                old_value=str(old),
                new_value=str(val),
                operator=_user.get("username"),
            )
    if data:
        # SQLAlchemy's server-side ``CURRENT_TIMESTAMP`` has only second
        # precision on SQLite. Use an application timestamp so rapid updates
        # still sort ahead of records created in the same second.
        customer.updated_at = datetime.now(timezone.utc)
    await db.flush()
    from app.services.embedding_pipeline import after_customer_save

    after_customer_save(customer.id)
    await cache_bump_version("customers:list")
    await cache_bump_version("dashboard:overview")
    await cache_bump_version("dashboard:kpi")
    return ok({"id": customer.id})


@router.delete("/{customer_id:int}")
async def delete_customer(
    customer_id: int,
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(require_perm("customers", "delete")),
):
    result = await db.execute(
        select(Customer).where(
            Customer.id == customer_id, Customer.deleted_at.is_(None)
        )
    )
    customer = result.scalar_one_or_none()
    if customer is None:
        return fail("Customer not found", 404)
    customer.deleted_at = datetime.now(timezone.utc)
    await _log(
        db,
        customer_id,
        "delete",
        summary=f"删除客户: {customer.name}",
        operator=_user.get("username"),
    )
    await db.flush()
    await cache_bump_version("customers:list")
    await cache_bump_version("dashboard:overview")
    await cache_bump_version("dashboard:kpi")
    return ok(msg="deleted")


