"""Customer CRUD operations — list, create, update, delete, merge, import, export."""

import csv
import hashlib
import io
import json
import logging
import os
import re
import unicodedata
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, File, Query, Response, UploadFile, status
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.database import get_db
from app.models.customer import Customer, CustomerAttachment, CustomerContact, CustomerFollowUp, CustomerLog
from app.schemas.common import fail, ok
from app.services.cache_service import cache_bump_version, cache_get_versioned, cache_set_versioned
from app.services.customer_service import (
    calc_health,
    customer_name_conflict_message,
    detect_duplicates as detect_dups,
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
            value = value[:-len(suffix)]
            break
    return (value or name.strip())[:100]


def _short_name_with_suffix(base: str, suffix: str) -> str:
    suffix_text = f"-{suffix}"
    return f"{base[:100 - len(suffix_text)]}{suffix_text}"


async def _short_name_exists(db: AsyncSession, short_name: str, exclude_id: int | None = None) -> bool:
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
    while await _short_name_exists(db, _short_name_with_suffix(short_name, f"{customer_id:06d}-{suffix}"), exclude_id=exclude_id):
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

    stmt = select(Customer).where(Customer.deleted_at.is_(None), Customer.code.isnot(None))
    if exclude_id is not None:
        stmt = stmt.where(Customer.id != exclude_id)
    rows = (await db.execute(stmt)).scalars().all()
    return next((row for row in rows if _extract_code_number(row.code) == code_number), None)


async def _generate_unique_code(db: AsyncSession, start_number: int, region: str | None, exclude_id: int | None = None) -> str:
    number = max(1, start_number)
    while True:
        code = _generate_code(number, region)
        if await _find_code_number_conflict(db, code, exclude_id=exclude_id) is None:
            return code
        number += 1


async def _log(db: AsyncSession, customer_id: int, action: str, field_name: str | None = None,
               old_value: str | None = None, new_value: str | None = None,
               operator: str | None = None, summary: str | None = None):
    entry = CustomerLog(
        customer_id=customer_id, action=action, field_name=field_name,
        old_value=old_value, new_value=new_value, operator=operator, summary=summary,
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
    address: str | None = None
    industry: str | None = None
    level: str | None = None
    source: str | None = None
    notes: str | None = None
    customer_type: str | None = None
    region: str | None = None
    credit_limit: float | None = None
    credit_level: str | None = None
    owner: str | None = None


class CustomerUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=255)
    code: str | None = None
    short_name: str | None = None
    contact_person: str | None = None
    phone: str | None = None
    email: str | None = None
    address: str | None = None
    industry: str | None = None
    level: str | None = None
    source: str | None = None
    notes: str | None = None
    customer_type: str | None = None
    region: str | None = None
    credit_limit: float | None = None
    credit_level: str | None = None
    owner: str | None = None


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
    method: str | None = None
    status: str | None = None
    content: str | None = None
    result: str | None = None
    planned_at: str | None = None
    completed_at: str | None = None
    priority: str | None = None
    assigned_to: str | None = None


class FollowUpUpdate(BaseModel):
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


def _customer_row(c: Customer, now: datetime | None = None) -> dict:
    if now is None:
        now = datetime.now(timezone.utc)
    health_score, health_label = calc_health(c, orders=[], payments=[], now=now)
    return {
        "id": c.id, "code": c.code, "name": c.name,
        "short_name": c.short_name, "contact_person": c.contact_person,
        "phone": c.phone, "email": c.email, "address": c.address,
        "industry": c.industry, "level": c.level, "source": c.source,
        "notes": c.notes, "customer_type": c.customer_type, "region": c.region,
        "credit_limit": float(c.credit_limit) if c.credit_limit else None,
        "credit_level": c.credit_level,
        "lifecycle": c.lifecycle,
        "last_contacted_at": str(c.last_contacted_at) if c.last_contacted_at else None,
        "created_at": str(c.created_at) if c.created_at else None,
        "owner": c.owner,
        "parent_id": c.parent_id,
        "health_score": health_score,
        "health_label": health_label,
        "tags": [{"id": t.id, "name": t.name, "color": t.color} for t in (c.tags or [])],
    }


def _generate_code(customer_id: int, region: str | None = None) -> str:
    region_prefix = _region_abbr(region)
    if region_prefix:
        return f"CUST-{region_prefix}-{customer_id:06d}"
    return f"CUST-{customer_id:06d}"


REGION_ABBR_MAP = {
    "华东": "HD", "华南": "HN", "华北": "HB",
    "华中": "HZ", "西南": "XN", "西北": "XB",
    "东北": "DB", "海外": "HW",
}


def _region_abbr(region: str | None) -> str:
    if not region:
        return ""
    return REGION_ABBR_MAP.get(region, region[:2].upper())


SORTABLE_COLUMNS = {"id": Customer.id, "name": Customer.name, "code": Customer.code,
                    "industry": Customer.industry, "level": Customer.level, "region": Customer.region,
                    "source": Customer.source, "credit_level": Customer.credit_level,
                    "created_at": Customer.created_at, "last_contacted_at": Customer.last_contacted_at}

CSV_TEMPLATE_HEADERS = ["名称", "编码", "简称", "行业", "等级", "区域", "来源", "类型",
                        "信用等级", "信用额度", "联系人", "电话", "邮箱", "地址", "备注"]

router = APIRouter(prefix="/customers", tags=["customers"])

CUSTOMERS_LIST_CACHE_TTL = 300
CUSTOMERS_LIST_CACHE_VERSION = "v1"
logger = logging.getLogger(__name__)


def _customers_cache_key(**parts: object) -> str:
    canonical = json.dumps(parts, sort_keys=True, default=str)
    digest = hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:16]
    return f"customers:list:{CUSTOMERS_LIST_CACHE_VERSION}:{digest}"


@router.get("")
@router.get("/")
async def list_customers(
    response: JSONResponse,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
    keyword: str | None = None,
    q: str | None = None,
    level: str | None = None,
    industry: str | None = None,
    region: str | None = None,
    source: str | None = None,
    credit_level: str | None = None,
    is_deleted: str | None = None,
    tag_ids: str | None = None,
    page: int = 1,
    page_size: int = 20,
    sort_by: str = "id",
    sort_order: str = "desc",
):
    cache_key = _customers_cache_key(
        keyword=keyword, q=q, level=level, industry=industry, region=region,
        source=source, credit_level=credit_level, is_deleted=is_deleted,
        tag_ids=tag_ids, page=page, page_size=page_size,
        sort_by=sort_by, sort_order=sort_order,
    )
    cached_payload = await cache_get_versioned('customers:list', cache_key)
    if cached_payload is not None:
        response.headers["X-Cache"] = "HIT"
        response.headers["X-Cache-Key"] = cache_key
        return JSONResponse(
            content=json.loads(cached_payload),
            headers={"X-Cache": "HIT", "X-Cache-Key": cache_key},
        )

    response.headers["X-Cache"] = "MISS"
    stmt = select(Customer)
    conditions = []
    _keyword = keyword or q
    if _keyword:
        conditions.append(or_(
            Customer.name.ilike(f"%{_keyword}%"),
            Customer.code.ilike(f"%{_keyword}%"),
            Customer.contact_person.ilike(f"%{_keyword}%"),
            Customer.phone.ilike(f"%{_keyword}%"),
        ))
    if level:
        conditions.append(Customer.level == level)
    if industry:
        conditions.append(Customer.industry == industry)
    if region:
        conditions.append(Customer.region == region)
    if source:
        conditions.append(Customer.source == source)
    if credit_level:
        conditions.append(Customer.credit_level == credit_level)
    if is_deleted == "true":
        conditions.append(Customer.deleted_at.isnot(None))
    elif is_deleted == "false" or is_deleted is None:
        conditions.append(Customer.deleted_at.is_(None))
    if tag_ids:
        tag_id_list = [int(t) for t in tag_ids.split(",") if t.isdigit()]
        if tag_id_list:
            from app.models.customer import customer_tag_table
            tag_filter = select(customer_tag_table.c.customer_id).where(
                customer_tag_table.c.tag_id.in_(tag_id_list)
            )
            conditions.append(Customer.id.in_(tag_filter))
    for c in conditions:
        stmt = stmt.where(c)
    sort_col = SORTABLE_COLUMNS.get(sort_by, Customer.id)
    if sort_order == "desc":
        stmt = stmt.order_by(sort_col.desc())
    else:
        stmt = stmt.order_by(sort_col.asc())
    count_stmt = select(func.count()).select_from(stmt.subquery())
    total_result = await db.execute(count_stmt)
    total = total_result.scalar() or 0
    stmt = stmt.offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(stmt)
    customers = result.scalars().all()
    now = datetime.now(timezone.utc)
    rows = [_customer_row(c, now=now) for c in customers]
    payload = {"list": rows, "total": total, "page": page, "page_size": page_size}
    await cache_set_versioned('customers:list', cache_key, json.dumps(payload, default=str), CUSTOMERS_LIST_CACHE_TTL)
    return ok(payload)


@router.get("/import-template")
async def import_template(
    current_user: dict = Depends(get_current_user),
):
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(CSV_TEMPLATE_HEADERS)
    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=customer_import_template.csv"},
    )


@router.post("/import")
async def import_customers(
    response: Response,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    if not file.filename or not file.filename.endswith(".csv"):
        response.status_code = status.HTTP_400_BAD_REQUEST
        return fail("Only CSV files are supported")
    try:
        content = await file.read()
        if len(content) == 0:
            response.status_code = status.HTTP_400_BAD_REQUEST
            return fail("Empty file uploaded")
        text = content.decode("utf-8-sig")
        reader = csv.DictReader(io.StringIO(text))
        imported = 0
        updated = 0
        for row in reader:
            name = row.get("名称", "").strip()
            if not name:
                continue
            code = row.get("编码", "").strip() or None
            raw_short_name = row.get("简称", "").strip()
            short_name = raw_short_name or _generate_short_name(name)
            industry = row.get("行业", "").strip() or None
            level = row.get("等级", "").strip() or None
            region = row.get("区域", "").strip() or None
            source = row.get("来源", "").strip() or None
            customer_type = row.get("类型", "").strip() or None
            credit_level = row.get("信用等级", "").strip() or None
            credit_limit_str = row.get("信用额度", "").strip()
            credit_limit = float(credit_limit_str) if credit_limit_str else None
            contact_person = row.get("联系人", "").strip() or None
            phone = row.get("电话", "").strip() or None
            email = row.get("邮箱", "").strip() or None
            address = row.get("地址", "").strip() or None
            notes = row.get("备注", "").strip() or None
            if code:
                stmt = select(Customer).where(Customer.code == code, Customer.deleted_at.is_(None))
                existing = await db.execute(stmt)
                cust = existing.scalar_one_or_none()
                if cust:
                    conflict = await find_name_conflict(db, name, exclude_id=cust.id)
                    if conflict:
                        conflict_name = conflict.name
                        response.status_code = status.HTTP_400_BAD_REQUEST
                        await db.rollback()
                        return fail(customer_name_conflict_message(name, conflict_name))
                    if raw_short_name:
                        next_short_name = raw_short_name
                    elif cust.short_name:
                        next_short_name = None
                    else:
                        next_short_name = await _dedupe_auto_short_name(
                            db,
                            short_name,
                            cust.id,
                            exclude_id=cust.id,
                        )
                    for attr, val in [
                        ("name", name), ("short_name", next_short_name), ("industry", industry),
                        ("level", level), ("region", region), ("source", source),
                        ("customer_type", customer_type), ("credit_level", credit_level),
                        ("credit_limit", credit_limit), ("contact_person", contact_person),
                        ("phone", phone), ("email", email), ("address", address), ("notes", notes),
                    ]:
                        if val is not None:
                            setattr(cust, attr, val)
                    updated += 1
                    continue
                conflict = await _find_code_number_conflict(db, code)
                if conflict:
                    conflict_code = conflict.code
                    response.status_code = status.HTTP_400_BAD_REQUEST
                    await db.rollback()
                    return fail(_code_number_conflict_message(code, conflict_code))
            conflict = await find_name_conflict(db, name)
            if conflict:
                conflict_name = conflict.name
                response.status_code = status.HTTP_400_BAD_REQUEST
                await db.rollback()
                return fail(customer_name_conflict_message(name, conflict_name))
            customer = Customer(
                name=name, code=code, short_name=short_name, industry=industry,
                level=level, region=region, source=source, customer_type=customer_type,
                credit_level=credit_level, credit_limit=credit_limit,
                contact_person=contact_person, phone=phone, email=email,
                address=address, notes=notes,
            )
            db.add(customer)
            imported += 1
        await db.commit()
        await cache_bump_version("customers:list")
        return ok({"imported": imported, "updated": updated})
    except Exception as e:
        response.status_code = status.HTTP_400_BAD_REQUEST
        await db.rollback()
        return fail(f"Import failed: {str(e)}")


@router.get("/export")
async def export_customers(
    current_user: dict = Depends(get_current_user),
    keyword: str | None = None,
    q: str | None = None,
    level: str | None = None,
    industry: str | None = None,
    region: str | None = None,
    source: str | None = None,
    credit_level: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    stmt = select(Customer).where(Customer.deleted_at.is_(None))
    conditions = []
    _keyword = keyword or q
    if _keyword:
        conditions.append(or_(
            Customer.name.ilike(f"%{_keyword}%"),
            Customer.code.ilike(f"%{_keyword}%"),
            Customer.contact_person.ilike(f"%{_keyword}%"),
        ))
    if level:
        conditions.append(Customer.level == level)
    if industry:
        conditions.append(Customer.industry == industry)
    if region:
        conditions.append(Customer.region == region)
    if source:
        conditions.append(Customer.source == source)
    if credit_level:
        conditions.append(Customer.credit_level == credit_level)
    for c in conditions:
        stmt = stmt.where(c)
    result = await db.execute(stmt)
    customers = result.scalars().all()
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(CSV_TEMPLATE_HEADERS)
    for c in customers:
        writer.writerow([
            c.name, c.code or "", c.short_name or "", c.industry or "", c.level or "",
            c.region or "", c.source or "", c.customer_type or "", c.credit_level or "",
            str(c.credit_limit) if c.credit_limit else "", c.contact_person or "",
            c.phone or "", c.email or "", c.address or "", c.notes or "",
        ])
    output.seek(0)
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    filename = f"customers_export_{timestamp}.csv"
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


@router.post("/merge")
async def merge_customers(body: MergeRequest, db: AsyncSession = Depends(get_db), _user: dict = Depends(get_current_user)):
    if body.source_id == body.target_id:
        return fail("不能合并到自身", 400)

    source = (await db.execute(
        select(Customer).where(Customer.id == body.source_id, Customer.deleted_at.is_(None))
    )).scalar_one_or_none()
    target = (await db.execute(
        select(Customer).where(Customer.id == body.target_id, Customer.deleted_at.is_(None))
    )).scalar_one_or_none()

    if not source or not target:
        return fail("客户不存在", 404)

    username = _user.get("username", "system")
    transferred: dict[str, int] = {}

    contacts = (await db.execute(
        select(CustomerContact).where(CustomerContact.customer_id == body.source_id, CustomerContact.deleted_at.is_(None))
    )).scalars().all()
    for c in contacts:
        c.customer_id = body.target_id
    transferred["contacts"] = len(contacts)

    fus = (await db.execute(
        select(CustomerFollowUp).where(CustomerFollowUp.customer_id == body.source_id, CustomerFollowUp.deleted_at.is_(None))
    )).scalars().all()
    for f in fus:
        f.customer_id = body.target_id
    transferred["follow_ups"] = len(fus)

    for t in source.tags:
        if t not in target.tags:
            target.tags.append(t)
    transferred["tags"] = len(source.tags)

    atts = (await db.execute(
        select(CustomerAttachment).where(CustomerAttachment.customer_id == body.source_id, CustomerAttachment.deleted_at.is_(None))
    )).scalars().all()
    for a in atts:
        a.customer_id = body.target_id
    transferred["attachments"] = len(atts)

    from app.models.sales import SalesOrder
    orders = (await db.execute(
        select(SalesOrder).where(SalesOrder.customer_id == body.source_id, SalesOrder.deleted_at.is_(None))
    )).scalars().all()
    for o in orders:
        o.customer_id = body.target_id
    transferred["orders"] = len(orders)

    source.deleted_at = datetime.now(timezone.utc)
    await _log(db, body.source_id, "merge", summary=f"合并到 #{body.target_id} {target.name}", operator=username)
    await _log(db, body.target_id, "merge", summary=f"从 #{body.source_id} {source.name} 合并入", operator=username)

    await db.flush()
    await cache_bump_version("customers:list")
    return ok({"merged": True, "transferred": transferred})


@router.get("/duplicates")
async def detect_duplicates(
    threshold: float = Query(0.9, ge=0.5, le=1.0),
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(get_current_user),
):
    rows = (await db.execute(
        select(Customer).where(Customer.deleted_at.is_(None)).order_by(Customer.name)
    )).scalars().all()
    pairs = detect_dups(rows, threshold)
    return ok({"total": len(pairs), "pairs": pairs})


@router.post("/batch-delete")
async def batch_delete(
    body: BatchDelete,
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(get_current_user),
):
    if not body.ids:
        return fail("ids required", 400)
    result = await db.execute(
        select(Customer).where(Customer.id.in_(body.ids), Customer.deleted_at.is_(None))
    )
    customers = result.scalars().all()
    now = datetime.now(timezone.utc)
    for c in customers:
        c.deleted_at = now
    await db.flush()
    await cache_bump_version("customers:list")
    return ok({"deleted": len(customers)})


@router.get("/{customer_id:int}")
async def get_customer(
    customer_id: int,
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(get_current_user),
):
    result = await db.execute(
        select(Customer).where(Customer.id == customer_id, Customer.deleted_at.is_(None))
    )
    customer = result.scalar_one_or_none()
    if customer is None:
        return fail("Customer not found", 404)
    now = datetime.now(timezone.utc)
    data = _customer_row(customer, now=now)
    data["contacts"] = [{
        "id": ct.id, "name": ct.name, "title": ct.title, "role": ct.role,
        "phone": ct.phone, "email": ct.email, "wechat": ct.wechat,
        "is_primary": ct.is_primary, "notes": ct.notes,
    } for ct in (customer.contacts or [])]
    data["follow_ups"] = [{
        "id": f.id, "method": f.method, "status": f.status,
        "content": f.content, "result": f.result,
        "planned_at": str(f.planned_at) if f.planned_at else None,
        "completed_at": str(f.completed_at) if f.completed_at else None,
        "priority": f.priority, "assigned_to": f.assigned_to,
        "created_at": str(f.created_at) if f.created_at else None,
    } for f in (customer.follow_ups or [])]
    return ok(data)


@router.post("", status_code=201)
async def create_customer(
    body: CustomerCreate,
    response: Response,
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(get_current_user),
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
        customer.code = await _generate_unique_code(db, customer.id, customer.region, exclude_id=customer.id)
        await db.flush()
    if auto_short_name:
        customer.short_name = await _dedupe_auto_short_name(
            db,
            customer.short_name,
            customer.id,
            exclude_id=customer.id,
        )
        await db.flush()
    await _log(db, customer.id, "create", summary=f"创建客户: {customer.name}", operator=_user.get("username"))
    await db.flush()
    from app.services.embedding_pipeline import after_customer_save
    after_customer_save(customer.id)
    await cache_bump_version("customers:list")
    return ok({
        "id": customer.id,
        "name": customer.name,
        "code": customer.code,
        "created_at": str(customer.created_at) if customer.created_at else None,
    })


@router.put("/{customer_id:int}")
async def update_customer(
    customer_id: int,
    body: CustomerUpdate,
    response: Response,
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(get_current_user),
):
    result = await db.execute(
        select(Customer).where(Customer.id == customer_id, Customer.deleted_at.is_(None))
    )
    customer = result.scalar_one_or_none()
    if customer is None:
        return fail("Customer not found", 404)
    data = body.model_dump(exclude_unset=True)
    if data.get("name"):
        name_conflict = await find_name_conflict(db, data["name"], exclude_id=customer_id)
        if name_conflict:
            response.status_code = status.HTTP_400_BAD_REQUEST
            return fail(customer_name_conflict_message(data["name"], name_conflict.name))
    if data.get("code"):
        conflict = await _find_code_number_conflict(db, data["code"], exclude_id=customer_id)
        if conflict:
            response.status_code = status.HTTP_400_BAD_REQUEST
            return fail(_code_number_conflict_message(data["code"], conflict.code))
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
    await db.flush()
    from app.services.embedding_pipeline import after_customer_save
    after_customer_save(customer.id)
    await cache_bump_version("customers:list")
    return ok({"id": customer.id})


@router.delete("/{customer_id:int}")
async def delete_customer(
    customer_id: int,
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(get_current_user),
):
    result = await db.execute(
        select(Customer).where(Customer.id == customer_id, Customer.deleted_at.is_(None))
    )
    customer = result.scalar_one_or_none()
    if customer is None:
        return fail("Customer not found", 404)
    customer.deleted_at = datetime.now(timezone.utc)
    await _log(db, customer_id, "delete", summary=f"删除客户: {customer.name}", operator=_user.get("username"))
    await db.flush()
    await cache_bump_version("customers:list")
    return ok(msg="deleted")
