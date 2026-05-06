import csv
import io
import os
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, File, Query, UploadFile
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.database import get_db
from app.models.customer import Customer, CustomerAttachment, CustomerContact, CustomerFollowUp, CustomerLog, CustomerTag, customer_tag_table
from app.schemas.common import fail, ok

UPLOAD_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "..", "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)


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

router = APIRouter(prefix="/customers", tags=["customers"])

SORTABLE_COLUMNS = {"id": Customer.id, "name": Customer.name, "code": Customer.code,
                    "industry": Customer.industry, "level": Customer.level, "region": Customer.region,
                    "source": Customer.source, "credit_level": Customer.credit_level,
                    "created_at": Customer.created_at, "last_contacted_at": Customer.last_contacted_at}

CSV_TEMPLATE_HEADERS = ["名称", "编码", "简称", "行业", "等级", "区域", "来源", "类型",
                        "信用等级", "信用额度", "联系人", "电话", "邮箱", "地址", "备注"]


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


def _customer_row(c: Customer) -> dict:
    return {
        "id": c.id, "code": c.code, "name": c.name,
        "short_name": c.short_name, "contact_person": c.contact_person,
        "phone": c.phone, "email": c.email, "address": c.address,
        "industry": c.industry, "level": c.level, "source": c.source,
        "notes": c.notes, "customer_type": c.customer_type, "region": c.region,
        "credit_limit": float(c.credit_limit) if c.credit_limit else None,
        "credit_level": c.credit_level,
        "last_contacted_at": str(c.last_contacted_at) if c.last_contacted_at else None,
        "created_at": str(c.created_at),
        "owner": c.owner,
        "tags": [{"id": t.id, "name": t.name, "color": t.color} for t in (c.tags or [])],
    }


# --- Customer CRUD ---

@router.get("")
async def list_customers(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=200),
    q: str | None = None,
    industry: str | None = None,
    level: str | None = None,
    customer_type: str | None = None,
    region: str | None = None,
    source: str | None = None,
    credit_level: str | None = None,
    created_from: str | None = None,
    created_to: str | None = None,
    tag_id: int | None = None,
    sort_by: str | None = None,
    sort_order: str | None = None,
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(get_current_user),
):
    base = select(Customer).where(Customer.deleted_at.is_(None))
    count_base = select(func.count(Customer.id)).where(Customer.deleted_at.is_(None))

    if q:
        like = f"%{q}%"
        filt = or_(Customer.name.ilike(like), Customer.code.ilike(like), Customer.contact_person.ilike(like))
        base = base.where(filt)
        count_base = count_base.where(filt)
    for col, val in [(Customer.industry, industry), (Customer.level, level),
                     (Customer.customer_type, customer_type), (Customer.region, region),
                     (Customer.source, source), (Customer.credit_level, credit_level)]:
        if val:
            base = base.where(col == val)
            count_base = count_base.where(col == val)
    if created_from:
        base = base.where(Customer.created_at >= datetime.fromisoformat(created_from))
        count_base = count_base.where(Customer.created_at >= datetime.fromisoformat(created_from))
    if created_to:
        base = base.where(Customer.created_at <= datetime.fromisoformat(created_to))
        count_base = count_base.where(Customer.created_at <= datetime.fromisoformat(created_to))
    if tag_id:
        base = base.join(customer_tag_table).where(customer_tag_table.c.tag_id == tag_id)
        count_base = count_base.join(customer_tag_table).where(customer_tag_table.c.tag_id == tag_id)

    total = (await db.execute(count_base)).scalar() or 0

    # Sorting
    sort_col = SORTABLE_COLUMNS.get(sort_by or "id", Customer.id)
    if sort_order == "asc":
        base = base.order_by(sort_col.asc())
    else:
        base = base.order_by(sort_col.desc())

    rows = (await db.execute(
        base.offset((page - 1) * page_size).limit(page_size)
    )).scalars().all()

    return ok({
        "list": [_customer_row(c) for c in rows],
        "total": total,
        "page": page,
        "page_size": page_size,
    })


@router.get("/import-template")
async def download_import_template(_user: dict = Depends(get_current_user)):
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(CSV_TEMPLATE_HEADERS)
    writer.writerow(["示例客户", "CUST-001", "示例", "汽车电子", "A", "华东", "展会", "终端",
                      "A", "100000", "张经理", "13800001111", "mail@example.com", "上海市...", "示例备注"])
    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=customer_template.csv"},
    )


@router.post("/import")
async def import_customers(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(get_current_user),
):
    if not file.filename or not file.filename.endswith(".csv"):
        return fail("请上传 CSV 文件", 400)

    content = await file.read()
    try:
        text = content.decode("utf-8-sig")
    except UnicodeDecodeError:
        text = content.decode("gbk", errors="replace")

    reader = csv.DictReader(io.StringIO(text))
    columns = reader.fieldnames or []
    created, skipped = 0, 0

    col_map = {
        "名称": "name", "编码": "code", "简称": "short_name", "行业": "industry",
        "等级": "level", "区域": "region", "来源": "source", "类型": "customer_type",
        "信用等级": "credit_level", "联系人": "contact_person", "电话": "phone",
        "邮箱": "email", "地址": "address", "备注": "notes",
    }

    for row in reader:
        name = (row.get("名称") or "").strip()
        if not name:
            skipped += 1
            continue

        data: dict = {}
        for cn_key, en_key in col_map.items():
            val = (row.get(cn_key) or "").strip()
            if val:
                if en_key == "credit_level":
                    data[en_key] = val  # keep as string for model field
                elif en_key == "credit_limit":
                    try:
                        data["credit_limit"] = float(val)
                    except ValueError:
                        data["credit_limit"] = 0.0
                else:
                    data[en_key] = val

        data["name"] = name
        customer = Customer(**data)
        db.add(customer)
        created += 1

    await db.flush()
    return ok({"created": created, "skipped": skipped})


@router.get("/export")
async def export_customers(
    q: str | None = None,
    industry: str | None = None,
    level: str | None = None,
    customer_type: str | None = None,
    region: str | None = None,
    source: str | None = None,
    credit_level: str | None = None,
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(get_current_user),
):
    base = select(Customer).where(Customer.deleted_at.is_(None))
    if q:
        like = f"%{q}%"
        base = base.where(or_(Customer.name.ilike(like), Customer.code.ilike(like), Customer.contact_person.ilike(like)))
    for col, val in [(Customer.industry, industry), (Customer.level, level),
                     (Customer.customer_type, customer_type), (Customer.region, region),
                     (Customer.source, source), (Customer.credit_level, credit_level)]:
        if val:
            base = base.where(col == val)
    rows = (await db.execute(base.order_by(Customer.id.desc()))).scalars().all()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["ID", "编码", "名称", "简称", "行业", "等级", "区域", "来源", "类型", "信用等级", "信用额度",
                      "联系人", "电话", "邮箱", "地址", "备注", "最近联系", "创建时间"])
    for c in rows:
        writer.writerow([
            c.id, c.code, c.name, c.short_name, c.industry, c.level, c.region, c.source,
            c.customer_type, c.credit_level, c.credit_limit, c.contact_person, c.phone,
            c.email, c.address, c.notes, str(c.last_contacted_at) if c.last_contacted_at else "",
            str(c.created_at),
        ])
    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=customers.csv"},
    )


# --- Dashboard Stats ---

@router.get("/stats")
async def customer_dashboard_stats(db: AsyncSession = Depends(get_db), _user: dict = Depends(get_current_user)):
    rows = (await db.execute(
        select(Customer).where(Customer.deleted_at.is_(None))
    )).scalars().all()

    total = len(rows)
    if total == 0:
        return ok({"total": 0, "by_industry": [], "by_level": [], "by_region": [], "by_source": [], "by_type": [], "monthly": []})

    def _count(field: str):
        counts: dict[str, int] = {}
        for r in rows:
            v = getattr(r, field, None) or "未设置"
            counts[v] = counts.get(v, 0) + 1
        return sorted([{"name": k, "value": c} for k, c in counts.items()], key=lambda x: -x["value"])

    monthly: dict[str, int] = {}
    now = datetime.now(timezone.utc)
    for r in rows:
        month_key = r.created_at.strftime("%Y-%m")
        monthly[month_key] = monthly.get(month_key, 0) + 1
    monthly_list = sorted([{"month": k, "count": v} for k, v in monthly.items()])[-12:]

    return ok({
        "total": total,
        "by_industry": _count("industry"),
        "by_level": _count("level"),
        "by_region": _count("region"),
        "by_source": _count("source"),
        "by_type": _count("customer_type"),
        "monthly": monthly_list,
    })


# --- Overdue Follow-ups (reminders) ---

@router.get("/overdue-followups")
async def overdue_followups(db: AsyncSession = Depends(get_db), _user: dict = Depends(get_current_user)):
    now = datetime.now(timezone.utc)
    rows = (await db.execute(
        select(CustomerFollowUp, Customer).join(Customer, CustomerFollowUp.customer_id == Customer.id).where(
            CustomerFollowUp.deleted_at.is_(None),
            Customer.deleted_at.is_(None),
            CustomerFollowUp.planned_at < now,
            CustomerFollowUp.status != "completed",
        ).order_by(CustomerFollowUp.planned_at.asc()).limit(50)
    )).all()

    result = []
    for fu, cust in rows:
        overdue_days = (now - fu.planned_at.replace(tzinfo=timezone.utc)).days
        result.append({
            "id": fu.id,
            "customer_id": cust.id,
            "customer_name": cust.name,
            "owner": cust.owner,
            "method": fu.method,
            "priority": fu.priority,
            "planned_at": str(fu.planned_at),
            "status": fu.status,
            "content": fu.content,
            "overdue_days": overdue_days,
        })

    result.sort(key=lambda x: -x["overdue_days"])
    return ok({"total": len(result), "items": result})


# --- Customer Merge ---

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

    # Transfer contacts
    contacts = (await db.execute(
        select(CustomerContact).where(CustomerContact.customer_id == body.source_id, CustomerContact.deleted_at.is_(None))
    )).scalars().all()
    for c in contacts:
        c.customer_id = body.target_id
    transferred["contacts"] = len(contacts)

    # Transfer follow-ups
    fus = (await db.execute(
        select(CustomerFollowUp).where(CustomerFollowUp.customer_id == body.source_id, CustomerFollowUp.deleted_at.is_(None))
    )).scalars().all()
    for f in fus:
        f.customer_id = body.target_id
    transferred["follow_ups"] = len(fus)

    # Transfer tags
    for t in source.tags:
        if t not in target.tags:
            target.tags.append(t)
    transferred["tags"] = len(source.tags)

    # Transfer attachments
    atts = (await db.execute(
        select(CustomerAttachment).where(CustomerAttachment.customer_id == body.source_id, CustomerAttachment.deleted_at.is_(None))
    )).scalars().all()
    for a in atts:
        a.customer_id = body.target_id
    transferred["attachments"] = len(atts)

    # Transfer orders
    from app.models.sales import SalesOrder
    orders = (await db.execute(
        select(SalesOrder).where(SalesOrder.customer_id == body.source_id, SalesOrder.deleted_at.is_(None))
    )).scalars().all()
    for o in orders:
        o.customer_id = body.target_id
    transferred["orders"] = len(orders)

    # Soft delete source
    source.deleted_at = datetime.now(timezone.utc)
    await _log(db, body.source_id, "merge", summary=f"合并到 #{body.target_id} {target.name}", operator=username)
    await _log(db, body.target_id, "merge", summary=f"从 #{body.source_id} {source.name} 合并入", operator=username)

    await db.flush()
    return ok({"merged": True, "transferred": transferred})


# --- Duplicate Detection ---

@router.get("/duplicates")
async def detect_duplicates(
    threshold: float = Query(0.7, ge=0.5, le=1.0),
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(get_current_user),
):
    """Find potential duplicate customers by name similarity using trigram matching."""
    rows = (await db.execute(
        select(Customer).where(Customer.deleted_at.is_(None)).order_by(Customer.name)
    )).scalars().all()

    # Simple name-based fuzzy matching (normalize + trigram overlap)
    import re

    def normalize(s: str) -> str:
        return re.sub(r'[（）\(\)\s\-_\.\,，、。有限公司有限责任控股集团分公司]', '', s or '').lower()

    pairs = []
    norm_map = {c.id: normalize(c.name) for c in rows}

    for i, a in enumerate(rows):
        na = norm_map[a.id]
        if len(na) < 2:
            continue
        for j in range(i + 1, len(rows)):
            nb = norm_map[rows[j].id]
            if len(nb) < 2:
                continue
            # Simple similarity: shared character ratio
            common = len(set(na) & set(nb))
            longer = max(len(na), len(nb))
            if longer == 0:
                continue
            sim = common / longer
            if sim >= threshold:
                pairs.append({
                    "similarity": round(sim, 3),
                    "customer_a": {"id": a.id, "name": a.name, "phone": a.phone, "owner": a.owner},
                    "customer_b": {"id": rows[j].id, "name": rows[j].name, "phone": rows[j].phone, "owner": rows[j].owner},
                })

    pairs.sort(key=lambda x: -x["similarity"])
    return ok({"total": len(pairs), "pairs": pairs[:30]})


@router.get("/{customer_id}")
async def get_customer(customer_id: int, db: AsyncSession = Depends(get_db), _user: dict = Depends(get_current_user)):
    result = await db.execute(
        select(Customer).where(Customer.id == customer_id, Customer.deleted_at.is_(None))
    )
    customer = result.scalar_one_or_none()
    if customer is None:
        return fail("Customer not found", 404)
    data = _customer_row(customer)
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
        "created_at": str(f.created_at),
    } for f in (customer.follow_ups or [])]
    return ok(data)


@router.post("", status_code=201)
async def create_customer(body: CustomerCreate, db: AsyncSession = Depends(get_db), _user: dict = Depends(get_current_user)):
    customer = Customer(**body.model_dump())
    db.add(customer)
    await db.flush()
    await _log(db, customer.id, "create", summary=f"创建客户: {customer.name}", operator=_user.get("username"))
    await db.flush()
    return ok({"id": customer.id, "name": customer.name})


@router.put("/{customer_id}")
async def update_customer(customer_id: int, body: CustomerUpdate, db: AsyncSession = Depends(get_db), _user: dict = Depends(get_current_user)):
    result = await db.execute(select(Customer).where(Customer.id == customer_id, Customer.deleted_at.is_(None)))
    customer = result.scalar_one_or_none()
    if customer is None:
        return fail("Customer not found", 404)
    for key, val in body.model_dump(exclude_unset=True).items():
        old = getattr(customer, key, None)
        setattr(customer, key, val)
        if str(old) != str(val) and key != "notes":
            await _log(db, customer_id, "update", field_name=key, old_value=str(old), new_value=str(val), operator=_user.get("username"))
    await db.flush()
    return ok({"id": customer.id})


@router.delete("/{customer_id}")
async def delete_customer(customer_id: int, db: AsyncSession = Depends(get_db), _user: dict = Depends(get_current_user)):
    result = await db.execute(select(Customer).where(Customer.id == customer_id, Customer.deleted_at.is_(None)))
    customer = result.scalar_one_or_none()
    if customer is None:
        return fail("Customer not found", 404)
    customer.deleted_at = datetime.now(timezone.utc)
    await _log(db, customer_id, "delete", summary=f"删除客户: {customer.name}", operator=_user.get("username"))
    await db.flush()
    return ok(msg="deleted")


# --- Batch operations ---

@router.post("/batch-delete")
async def batch_delete(body: BatchDelete, db: AsyncSession = Depends(get_db), _user: dict = Depends(get_current_user)):
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
    return ok({"deleted": len(customers)})


@router.post("/batch-tag")
async def batch_tag(body: BatchTag, db: AsyncSession = Depends(get_db), _user: dict = Depends(get_current_user)):
    if not body.ids or not body.tag_ids:
        return fail("ids and tag_ids required", 400)
    customers_result = await db.execute(
        select(Customer).where(Customer.id.in_(body.ids), Customer.deleted_at.is_(None))
    )
    customers = customers_result.scalars().all()
    tags_result = await db.execute(
        select(CustomerTag).where(CustomerTag.id.in_(body.tag_ids), CustomerTag.deleted_at.is_(None))
    )
    tags = tags_result.scalars().all()
    for c in customers:
        for t in tags:
            if t not in c.tags:
                c.tags.append(t)
    await db.flush()
    return ok({"updated": len(customers), "tags_added": len(tags)})


# --- Contacts ---

@router.get("/{customer_id}/contacts")
async def list_contacts(customer_id: int, db: AsyncSession = Depends(get_db), _user: dict = Depends(get_current_user)):
    rows = (await db.execute(
        select(CustomerContact).where(CustomerContact.customer_id == customer_id, CustomerContact.deleted_at.is_(None))
    )).scalars().all()
    return ok([{
        "id": c.id, "name": c.name, "title": c.title, "role": c.role,
        "phone": c.phone, "email": c.email, "wechat": c.wechat,
        "is_primary": c.is_primary, "notes": c.notes,
    } for c in rows])


@router.post("/{customer_id}/contacts", status_code=201)
async def create_contact(customer_id: int, body: ContactCreate, db: AsyncSession = Depends(get_db), _user: dict = Depends(get_current_user)):
    contact = CustomerContact(customer_id=customer_id, **body.model_dump())
    db.add(contact)
    await db.flush()
    return ok({"id": contact.id, "name": contact.name})


@router.put("/{customer_id}/contacts/{contact_id}")
async def update_contact(customer_id: int, contact_id: int, body: ContactUpdate, db: AsyncSession = Depends(get_db), _user: dict = Depends(get_current_user)):
    result = await db.execute(
        select(CustomerContact).where(
            CustomerContact.id == contact_id,
            CustomerContact.customer_id == customer_id,
            CustomerContact.deleted_at.is_(None),
        )
    )
    contact = result.scalar_one_or_none()
    if contact is None:
        return fail("Contact not found", 404)
    for key, val in body.model_dump(exclude_unset=True).items():
        setattr(contact, key, val)
    await db.flush()
    return ok({"id": contact.id})


@router.delete("/{customer_id}/contacts/{contact_id}")
async def delete_contact(customer_id: int, contact_id: int, db: AsyncSession = Depends(get_db), _user: dict = Depends(get_current_user)):
    result = await db.execute(
        select(CustomerContact).where(
            CustomerContact.id == contact_id,
            CustomerContact.customer_id == customer_id,
            CustomerContact.deleted_at.is_(None),
        )
    )
    contact = result.scalar_one_or_none()
    if contact is None:
        return fail("Contact not found", 404)
    contact.deleted_at = datetime.now(timezone.utc)
    await db.flush()
    return ok(msg="deleted")


# --- Follow-ups ---

@router.get("/{customer_id}/follow-ups")
async def list_followups(customer_id: int, db: AsyncSession = Depends(get_db), _user: dict = Depends(get_current_user)):
    rows = (await db.execute(
        select(CustomerFollowUp).where(CustomerFollowUp.customer_id == customer_id, CustomerFollowUp.deleted_at.is_(None))
    )).scalars().all()
    return ok([{
        "id": f.id, "method": f.method, "status": f.status,
        "content": f.content, "result": f.result,
        "planned_at": str(f.planned_at) if f.planned_at else None,
        "completed_at": str(f.completed_at) if f.completed_at else None,
        "priority": f.priority, "assigned_to": f.assigned_to,
        "created_at": str(f.created_at),
    } for f in rows])


@router.post("/{customer_id}/follow-ups", status_code=201)
async def create_followup(customer_id: int, body: FollowUpCreate, db: AsyncSession = Depends(get_db), _user: dict = Depends(get_current_user)):
    data = body.model_dump()
    for date_field in ("planned_at", "completed_at"):
        if data.get(date_field):
            data[date_field] = datetime.fromisoformat(data[date_field])
    followup = CustomerFollowUp(customer_id=customer_id, **data)
    db.add(followup)
    result = await db.execute(select(Customer).where(Customer.id == customer_id))
    cust = result.scalar_one_or_none()
    if cust:
        cust.last_contacted_at = datetime.now(timezone.utc)
    await db.flush()
    return ok({"id": followup.id})


@router.put("/{customer_id}/follow-ups/{followup_id}")
async def update_followup(customer_id: int, followup_id: int, body: FollowUpUpdate, db: AsyncSession = Depends(get_db), _user: dict = Depends(get_current_user)):
    result = await db.execute(
        select(CustomerFollowUp).where(
            CustomerFollowUp.id == followup_id,
            CustomerFollowUp.customer_id == customer_id,
            CustomerFollowUp.deleted_at.is_(None),
        )
    )
    followup = result.scalar_one_or_none()
    if followup is None:
        return fail("Follow-up not found", 404)
    data = body.model_dump(exclude_unset=True)
    for date_field in ("planned_at", "completed_at"):
        if data.get(date_field):
            data[date_field] = datetime.fromisoformat(data[date_field])
    for key, val in data.items():
        setattr(followup, key, val)
    await db.flush()
    return ok({"id": followup.id})


@router.delete("/{customer_id}/follow-ups/{followup_id}")
async def delete_followup(customer_id: int, followup_id: int, db: AsyncSession = Depends(get_db), _user: dict = Depends(get_current_user)):
    result = await db.execute(
        select(CustomerFollowUp).where(
            CustomerFollowUp.id == followup_id,
            CustomerFollowUp.customer_id == customer_id,
            CustomerFollowUp.deleted_at.is_(None),
        )
    )
    followup = result.scalar_one_or_none()
    if followup is None:
        return fail("Follow-up not found", 404)
    followup.deleted_at = datetime.now(timezone.utc)
    await db.flush()
    return ok(msg="deleted")


# --- Activity Timeline ---

@router.get("/{customer_id}/timeline")
async def get_timeline(customer_id: int, db: AsyncSession = Depends(get_db), _user: dict = Depends(get_current_user)):
    from app.models.sales import SalesOrder

    contacts = (await db.execute(
        select(CustomerContact).where(
            CustomerContact.customer_id == customer_id, CustomerContact.deleted_at.is_(None)
        ).order_by(CustomerContact.created_at.desc())
    )).scalars().all()

    followups = (await db.execute(
        select(CustomerFollowUp).where(
            CustomerFollowUp.customer_id == customer_id, CustomerFollowUp.deleted_at.is_(None)
        ).order_by(CustomerFollowUp.created_at.desc())
    )).scalars().all()

    orders = (await db.execute(
        select(SalesOrder).where(
            SalesOrder.customer_id == customer_id, SalesOrder.deleted_at.is_(None)
        ).order_by(SalesOrder.created_at.desc())
    )).scalars().all()

    events = []
    for c in contacts:
        events.append({
            "type": "contact",
            "title": f"新建联系人: {c.name}",
            "detail": c.title or "",
            "time": str(c.created_at),
            "id": c.id,
        })
    for f in followups:
        events.append({
            "type": "followup",
            "title": f"跟进: {f.method or '未指定'} - {f.status or '进行中'}",
            "detail": f.content or "",
            "time": str(f.created_at),
            "id": f.id,
        })
    for o in orders:
        events.append({
            "type": "order",
            "title": f"销售订单: {o.order_no or 'NO-{}'.format(o.id)}",
            "detail": f"金额: {o.total_amount or 0:.2f}, 状态: {o.status}",
            "time": str(o.created_at),
            "id": o.id,
        })

    events.sort(key=lambda e: e["time"], reverse=True)
    return ok(events)


# --- Customer Stats (profile: lifecycle, credit, aging, health) ---

@router.get("/{customer_id}/stats")
async def customer_stats(customer_id: int, db: AsyncSession = Depends(get_db), _user: dict = Depends(get_current_user)):
    from app.models.sales import SalesOrder
    from app.models.transaction import Payment

    result = await db.execute(
        select(Customer).where(Customer.id == customer_id, Customer.deleted_at.is_(None))
    )
    customer = result.scalar_one_or_none()
    if customer is None:
        return fail("Customer not found", 404)

    now = datetime.now(timezone.utc)

    # Order summary
    order_rows = (await db.execute(
        select(SalesOrder).where(
            SalesOrder.customer_id == customer_id, SalesOrder.deleted_at.is_(None)
        ).order_by(SalesOrder.created_at.desc())
    )).scalars().all()
    order_count = len(order_rows)
    total_revenue = sum(float(o.total_amount or 0) for o in order_rows)
    last_order_date = max((o.created_at for o in order_rows), default=None)

    # Lifecycle stage
    created_days = (now - customer.created_at.replace(tzinfo=timezone.utc)).days
    if order_count == 0:
        lifecycle = "新客户" if created_days <= 30 else "沉默客户"
    elif last_order_date:
        days_since_last = (now - last_order_date.replace(tzinfo=timezone.utc)).days
        if days_since_last <= 90:
            lifecycle = "活跃"
        elif days_since_last <= 365:
            lifecycle = "衰退"
        else:
            lifecycle = "流失"
    else:
        lifecycle = "新客户"

    # Credit usage
    credit_limit = float(customer.credit_limit or 0)
    pay_rows = (await db.execute(
        select(Payment).where(
            Payment.customer_id == customer_id,
            Payment.deleted_at.is_(None),
        )
    )).scalars().all()
    outstanding = sum(float(p.amount or 0) for p in pay_rows if p.paid_at is None)
    paid_total = sum(float(p.amount or 0) for p in pay_rows if p.paid_at is not None)
    credit_usage_pct = round((outstanding / credit_limit * 100), 1) if credit_limit > 0 else 0

    # AR aging buckets
    aging = {"0-30": 0.0, "30-60": 0.0, "60-90": 0.0, "90+": 0.0}
    for p in pay_rows:
        if p.paid_at is not None:
            continue
        amt = float(p.amount or 0)
        overdue_days = (now - p.created_at.replace(tzinfo=timezone.utc)).days
        if overdue_days <= 30:
            aging["0-30"] += amt
        elif overdue_days <= 60:
            aging["30-60"] += amt
        elif overdue_days <= 90:
            aging["60-90"] += amt
        else:
            aging["90+"] += amt

    # Health score (0-100): composite of recency, frequency, credit, activity
    health_score = _calc_health(customer, order_rows, pay_rows, created_days, now)
    health_label = "优秀" if health_score >= 80 else "良好" if health_score >= 60 else "一般" if health_score >= 40 else "差"

    return ok({
        "lifecycle": lifecycle,
        "created_days": created_days,
        "order_count": order_count,
        "total_revenue": round(total_revenue, 2),
        "last_order_date": str(last_order_date) if last_order_date else None,
        "credit_limit": credit_limit,
        "outstanding": round(outstanding, 2),
        "paid_total": round(paid_total, 2),
        "credit_usage_pct": credit_usage_pct,
        "aging": aging,
        "health_score": health_score,
        "health_label": health_label,
    })


def _calc_health(customer, order_rows: list, pay_rows: list, created_days: int, now: datetime) -> int:
    """Composite health score 0-100."""
    score = 50  # baseline

    # Recency: more recent order = better (max +20)
    if order_rows:
        days_since_last = (now - order_rows[0].created_at.replace(tzinfo=timezone.utc)).days
        if days_since_last <= 30:
            score += 20
        elif days_since_last <= 90:
            score += 15
        elif days_since_last <= 180:
            score += 8
        elif days_since_last <= 365:
            score += 3
        else:
            score -= 5
    elif created_days > 90:
        score -= 10  # old customer with no orders

    # Frequency: more orders relative to age = better (max +15)
    if created_days > 0 and order_rows:
        annual_rate = len(order_rows) / (created_days / 365)
        if annual_rate >= 12:
            score += 15
        elif annual_rate >= 6:
            score += 10
        elif annual_rate >= 2:
            score += 5
        elif annual_rate >= 1:
            score += 2

    # Credit: low usage = better (max +15)
    credit_limit = float(customer.credit_limit or 0)
    if credit_limit > 0:
        outstanding = sum(float(p.amount or 0) for p in pay_rows if p.paid_at is None)
        ratio = outstanding / credit_limit
        if ratio < 0.2:
            score += 15
        elif ratio < 0.5:
            score += 10
        elif ratio < 0.8:
            score += 5
        elif ratio > 0.95:
            score -= 15
        else:
            score -= 5

    # Activity: recent contacts/followups (max +10)
    last_contact = customer.last_contacted_at
    if last_contact:
        days_since_contact = (now - last_contact.replace(tzinfo=timezone.utc)).days
        if days_since_contact <= 30:
            score += 10
        elif days_since_contact <= 90:
            score += 5
        elif days_since_contact > 365:
            score -= 5

    # Customer level bonus
    if customer.level == "A":
        score += 5
    elif customer.level in ("C", "D"):
        score -= 5

    return max(0, min(100, score))


# --- Change Logs ---

@router.get("/{customer_id}/logs")
async def get_customer_logs(customer_id: int, db: AsyncSession = Depends(get_db), _user: dict = Depends(get_current_user)):
    result = await db.execute(
        select(Customer).where(Customer.id == customer_id, Customer.deleted_at.is_(None))
    )
    customer = result.scalar_one_or_none()
    if customer is None:
        return fail("Customer not found", 404)

    rows = (await db.execute(
        select(CustomerLog).where(
            CustomerLog.customer_id == customer_id, CustomerLog.deleted_at.is_(None)
        ).order_by(CustomerLog.created_at.desc()).limit(100)
    )).scalars().all()

    return ok([{
        "id": r.id,
        "action": r.action,
        "field_name": r.field_name,
        "old_value": r.old_value,
        "new_value": r.new_value,
        "operator": r.operator,
        "summary": r.summary,
        "created_at": str(r.created_at),
    } for r in rows])


# --- Customer-Tag linking ---

@router.get("/{customer_id}/tags")
async def get_customer_tags(customer_id: int, db: AsyncSession = Depends(get_db), _user: dict = Depends(get_current_user)):
    result = await db.execute(
        select(Customer).where(Customer.id == customer_id, Customer.deleted_at.is_(None))
    )
    customer = result.scalar_one_or_none()
    if customer is None:
        return fail("Customer not found", 404)
    return ok([{"id": t.id, "name": t.name, "color": t.color} for t in (customer.tags or [])])


@router.post("/{customer_id}/tags/{tag_id}")
async def link_tag(customer_id: int, tag_id: int, db: AsyncSession = Depends(get_db), _user: dict = Depends(get_current_user)):
    result = await db.execute(
        select(Customer).where(Customer.id == customer_id, Customer.deleted_at.is_(None))
    )
    customer = result.scalar_one_or_none()
    if customer is None:
        return fail("Customer not found", 404)
    tag_result = await db.execute(
        select(CustomerTag).where(CustomerTag.id == tag_id, CustomerTag.deleted_at.is_(None))
    )
    tag = tag_result.scalar_one_or_none()
    if tag is None:
        return fail("Tag not found", 404)
    if tag not in customer.tags:
        customer.tags.append(tag)
        await db.flush()
    return ok({"tag_id": tag_id})


@router.delete("/{customer_id}/tags/{tag_id}")
async def unlink_tag(customer_id: int, tag_id: int, db: AsyncSession = Depends(get_db), _user: dict = Depends(get_current_user)):
    result = await db.execute(
        select(Customer).where(Customer.id == customer_id, Customer.deleted_at.is_(None))
    )
    customer = result.scalar_one_or_none()
    if customer is None:
        return fail("Customer not found", 404)
    tag_result = await db.execute(
        select(CustomerTag).where(CustomerTag.id == tag_id, CustomerTag.deleted_at.is_(None))
    )
    tag = tag_result.scalar_one_or_none()
    if tag is None:
        return fail("Tag not found", 404)
    if tag in customer.tags:
        customer.tags.remove(tag)
        await db.flush()
    return ok(msg="unlinked")


# --- Global Tags CRUD ---

tags_router = APIRouter(prefix="/tags", tags=["tags"])


@tags_router.get("")
async def list_tags(db: AsyncSession = Depends(get_db), _user: dict = Depends(get_current_user)):
    rows = (await db.execute(
        select(CustomerTag).where(CustomerTag.deleted_at.is_(None)).order_by(CustomerTag.name)
    )).scalars().all()
    return ok([{"id": t.id, "name": t.name, "color": t.color} for t in rows])


@tags_router.post("", status_code=201)
async def create_tag(body: TagCreate, db: AsyncSession = Depends(get_db), _user: dict = Depends(get_current_user)):
    tag = CustomerTag(**body.model_dump())
    db.add(tag)
    await db.flush()
    return ok({"id": tag.id, "name": tag.name, "color": tag.color})


@tags_router.put("/{tag_id}")
async def update_tag(tag_id: int, body: TagUpdate, db: AsyncSession = Depends(get_db), _user: dict = Depends(get_current_user)):
    result = await db.execute(
        select(CustomerTag).where(CustomerTag.id == tag_id, CustomerTag.deleted_at.is_(None))
    )
    tag = result.scalar_one_or_none()
    if tag is None:
        return fail("Tag not found", 404)
    for key, val in body.model_dump(exclude_unset=True).items():
        setattr(tag, key, val)
    await db.flush()
    return ok({"id": tag.id, "name": tag.name, "color": tag.color})


@tags_router.delete("/{tag_id}")
async def delete_tag(tag_id: int, db: AsyncSession = Depends(get_db), _user: dict = Depends(get_current_user)):
    result = await db.execute(
        select(CustomerTag).where(CustomerTag.id == tag_id, CustomerTag.deleted_at.is_(None))
    )
    tag = result.scalar_one_or_none()
    if tag is None:
        return fail("Tag not found", 404)
    tag.deleted_at = datetime.now(timezone.utc)
    await db.flush()
    return ok(msg="deleted")


# --- Attachments ---

@router.get("/{customer_id}/attachments")
async def list_attachments(customer_id: int, db: AsyncSession = Depends(get_db), _user: dict = Depends(get_current_user)):
    rows = (await db.execute(
        select(CustomerAttachment).where(
            CustomerAttachment.customer_id == customer_id,
            CustomerAttachment.deleted_at.is_(None),
        ).order_by(CustomerAttachment.created_at.desc())
    )).scalars().all()
    return ok([{
        "id": a.id, "original_name": a.original_name, "file_size": a.file_size,
        "content_type": a.content_type, "category": a.category,
        "created_at": str(a.created_at),
    } for a in rows])


@router.post("/{customer_id}/attachments", status_code=201)
async def upload_attachment(
    customer_id: int,
    file: UploadFile = File(...),
    category: str = Query("contract"),
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(get_current_user),
):
    if not file.filename:
        return fail("No file selected", 400)

    ext = os.path.splitext(file.filename)[1]
    stored_name = f"{uuid.uuid4().hex}{ext}"
    file_path = os.path.join(UPLOAD_DIR, stored_name)

    content = await file.read()
    with open(file_path, "wb") as f:
        f.write(content)

    attachment = CustomerAttachment(
        customer_id=customer_id,
        filename=stored_name,
        original_name=file.filename,
        file_size=len(content),
        content_type=file.content_type,
        category=category,
    )
    db.add(attachment)
    await db.flush()

    return ok({
        "id": attachment.id,
        "original_name": attachment.original_name,
        "file_size": attachment.file_size,
    })


@router.get("/{customer_id}/attachments/{attachment_id}/download")
async def download_attachment(
    customer_id: int,
    attachment_id: int,
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(get_current_user),
):
    result = await db.execute(
        select(CustomerAttachment).where(
            CustomerAttachment.id == attachment_id,
            CustomerAttachment.customer_id == customer_id,
            CustomerAttachment.deleted_at.is_(None),
        )
    )
    attachment = result.scalar_one_or_none()
    if attachment is None:
        return fail("Attachment not found", 404)

    file_path = os.path.join(UPLOAD_DIR, attachment.filename)
    if not os.path.exists(file_path):
        return fail("File not found on disk", 404)

    return FileResponse(
        file_path,
        filename=attachment.original_name,
        media_type=attachment.content_type or "application/octet-stream",
    )


@router.delete("/{customer_id}/attachments/{attachment_id}")
async def delete_attachment(
    customer_id: int,
    attachment_id: int,
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(get_current_user),
):
    result = await db.execute(
        select(CustomerAttachment).where(
            CustomerAttachment.id == attachment_id,
            CustomerAttachment.customer_id == customer_id,
            CustomerAttachment.deleted_at.is_(None),
        )
    )
    attachment = result.scalar_one_or_none()
    if attachment is None:
        return fail("Attachment not found", 404)

    file_path = os.path.join(UPLOAD_DIR, attachment.filename)
    if os.path.exists(file_path):
        os.remove(file_path)

    attachment.deleted_at = datetime.now(timezone.utc)
    await db.flush()
    return ok(msg="deleted")
