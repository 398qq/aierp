import csv
import io
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.database import get_db
from app.models.customer import Customer, CustomerContact, CustomerFollowUp, CustomerTag, customer_tag_table
from app.schemas.common import fail, ok

router = APIRouter(prefix="/customers", tags=["customers"])


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
        "tags": [{"id": t.id, "name": t.name, "color": t.color} for t in (c.tags or [])],
    }


# --- Customer CRUD ---

@router.get("")
async def list_customers(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
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
    rows = (await db.execute(
        base.order_by(Customer.id.desc()).offset((page - 1) * page_size).limit(page_size)
    )).scalars().all()

    return ok({
        "list": [_customer_row(c) for c in rows],
        "total": total,
        "page": page,
        "page_size": page_size,
    })


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
    return ok({"id": customer.id, "name": customer.name})


@router.put("/{customer_id}")
async def update_customer(customer_id: int, body: CustomerUpdate, db: AsyncSession = Depends(get_db), _user: dict = Depends(get_current_user)):
    result = await db.execute(select(Customer).where(Customer.id == customer_id, Customer.deleted_at.is_(None)))
    customer = result.scalar_one_or_none()
    if customer is None:
        return fail("Customer not found", 404)
    for key, val in body.model_dump(exclude_unset=True).items():
        setattr(customer, key, val)
    await db.flush()
    return ok({"id": customer.id})


@router.delete("/{customer_id}")
async def delete_customer(customer_id: int, db: AsyncSession = Depends(get_db), _user: dict = Depends(get_current_user)):
    result = await db.execute(select(Customer).where(Customer.id == customer_id, Customer.deleted_at.is_(None)))
    customer = result.scalar_one_or_none()
    if customer is None:
        return fail("Customer not found", 404)
    customer.deleted_at = datetime.now(timezone.utc)
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
