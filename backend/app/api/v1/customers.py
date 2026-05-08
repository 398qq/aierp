import csv
import io
import os
import uuid
from datetime import datetime, timezone, timedelta

from fastapi import APIRouter, Depends, File, Query, UploadFile
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.database import get_db
from app.models.customer import AlertEvent, AlertRule, Customer, CustomerAttachment, CustomerContact, CustomerFollowUp, CustomerLog, CustomerTag, LevelRule, customer_tag_table
from app.schemas.common import fail, ok
from app.services.customer_service import calc_health, calc_lifecycle, detect_duplicates as detect_dups

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
        "created_at": str(c.created_at) if c.created_at else None,
        "owner": c.owner,
        "parent_id": c.parent_id,
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
    owner: str | None = None,
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
                     (Customer.source, source), (Customer.credit_level, credit_level),
                     (Customer.owner, owner)]:
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
    owner: str | None = None,
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(get_current_user),
):
    base = select(Customer).where(Customer.deleted_at.is_(None))
    if q:
        like = f"%{q}%"
        base = base.where(or_(Customer.name.ilike(like), Customer.code.ilike(like), Customer.contact_person.ilike(like)))
    for col, val in [(Customer.industry, industry), (Customer.level, level),
                     (Customer.customer_type, customer_type), (Customer.region, region),
                     (Customer.source, source), (Customer.credit_level, credit_level),
                     (Customer.owner, owner)]:
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
            str(c.created_at) if c.created_at else "",
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
    async def _agg(field):
        col = getattr(Customer, field)
        r = await db.execute(
            select(col, func.count(Customer.id))
            .where(Customer.deleted_at.is_(None))
            .group_by(col)
        )
        return sorted(
            [{"name": row[0] or "未设置", "value": row[1]} for row in r.all()],
            key=lambda x: -x["value"],
        )

    async def _monthly():
        month_expr = func.date_trunc("month", Customer.created_at)
        r = await db.execute(
            select(month_expr, func.count(Customer.id))
            .where(Customer.deleted_at.is_(None), Customer.created_at.isnot(None))
            .group_by(month_expr)
            .order_by(month_expr.desc())
            .limit(12)
        )
        rows = r.all()
        rows.reverse()
        return [{"month": str(row[0])[:7], "count": row[1]} for row in rows]

    total_r = await db.execute(select(func.count(Customer.id)).where(Customer.deleted_at.is_(None)))
    by_industry = await _agg("industry")
    by_level = await _agg("level")
    by_region = await _agg("region")
    by_source = await _agg("source")
    by_type = await _agg("customer_type")
    monthly = await _monthly()

    return ok({
        "total": total_r.scalar() or 0,
        "by_industry": by_industry,
        "by_level": by_level,
        "by_region": by_region,
        "by_source": by_source,
        "by_type": by_type,
        "monthly": monthly,
    })


@router.get("/recent-activity")
async def recent_activity(limit: int = Query(20, le=100), db: AsyncSession = Depends(get_db), _user: dict = Depends(get_current_user)):
    """Recent customer activity across all customers."""
    logs = (await db.execute(
        select(CustomerLog, Customer.name).join(
            Customer, CustomerLog.customer_id == Customer.id
        ).where(
            CustomerLog.deleted_at.is_(None),
            Customer.deleted_at.is_(None),
        ).order_by(CustomerLog.created_at.desc()).limit(limit)
    )).all()

    return ok([{
        "id": row[0].id,
        "customer_id": row[0].customer_id,
        "customer_name": row[1],
        "action": row[0].action,
        "field_name": row[0].field_name,
        "old_value": row[0].old_value,
        "new_value": row[0].new_value,
        "operator": row[0].operator,
        "summary": row[0].summary,
        "created_at": str(row[0].created_at) if row[0].created_at else None,
    } for row in logs])


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
    pairs = detect_dups(rows, threshold)
    return ok({"total": len(pairs), "pairs": pairs})


# --- Alert Rules ---

class AlertRuleCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    rule_type: str
    threshold_days: int | None = None
    threshold_pct: float | None = None
    threshold_amount: float | None = None
    enabled: bool = True
    severity: str = "warning"


class AlertRuleUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=100)
    threshold_days: int | None = None
    threshold_pct: float | None = None
    threshold_amount: float | None = None
    enabled: bool | None = None
    severity: str | None = None


@router.get("/alerts/rules")
async def list_alert_rules(db: AsyncSession = Depends(get_db), _user: dict = Depends(get_current_user)):
    rows = (await db.execute(
        select(AlertRule).where(AlertRule.deleted_at.is_(None)).order_by(AlertRule.rule_type, AlertRule.name)
    )).scalars().all()
    return ok([{
        "id": r.id, "name": r.name, "rule_type": r.rule_type,
        "threshold_days": r.threshold_days, "threshold_pct": r.threshold_pct,
        "threshold_amount": r.threshold_amount, "enabled": r.enabled, "severity": r.severity,
    } for r in rows])


@router.post("/alerts/rules", status_code=201)
async def create_alert_rule(body: AlertRuleCreate, db: AsyncSession = Depends(get_db), _user: dict = Depends(get_current_user)):
    rule = AlertRule(**body.model_dump())
    db.add(rule)
    await db.flush()
    return ok({"id": rule.id, "name": rule.name})


@router.put("/alerts/rules/{rule_id}")
async def update_alert_rule(rule_id: int, body: AlertRuleUpdate, db: AsyncSession = Depends(get_db), _user: dict = Depends(get_current_user)):
    result = await db.execute(
        select(AlertRule).where(AlertRule.id == rule_id, AlertRule.deleted_at.is_(None))
    )
    rule = result.scalar_one_or_none()
    if not rule:
        return fail("Rule not found", 404)
    for k, v in body.model_dump(exclude_unset=True).items():
        setattr(rule, k, v)
    await db.flush()
    return ok({"id": rule.id})


@router.delete("/alerts/rules/{rule_id}")
async def delete_alert_rule(rule_id: int, db: AsyncSession = Depends(get_db), _user: dict = Depends(get_current_user)):
    result = await db.execute(
        select(AlertRule).where(AlertRule.id == rule_id, AlertRule.deleted_at.is_(None))
    )
    rule = result.scalar_one_or_none()
    if not rule:
        return fail("Rule not found", 404)
    rule.deleted_at = datetime.now(timezone.utc)
    await db.flush()
    return ok(msg="deleted")


# --- Alert Events ---

@router.get("/alerts")
async def list_alert_events(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    severity: str | None = None,
    rule_type: str | None = None,
    is_read: bool | None = None,
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(get_current_user),
):
    base = select(AlertEvent).where(AlertEvent.deleted_at.is_(None))
    count_base = select(func.count(AlertEvent.id)).where(AlertEvent.deleted_at.is_(None))
    if severity:
        base = base.where(AlertEvent.severity == severity)
        count_base = count_base.where(AlertEvent.severity == severity)
    if rule_type:
        base = base.where(AlertEvent.rule_type == rule_type)
        count_base = count_base.where(AlertEvent.rule_type == rule_type)
    if is_read is not None:
        base = base.where(AlertEvent.is_read == is_read)
        count_base = count_base.where(AlertEvent.is_read == is_read)
    total = (await db.execute(count_base)).scalar() or 0
    rows = (await db.execute(
        base.order_by(AlertEvent.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
    )).scalars().all()
    return ok({
        "list": [{
            "id": e.id, "customer_id": e.customer_id, "rule_type": e.rule_type,
            "rule_name": e.rule_name, "severity": e.severity, "message": e.message,
            "is_read": e.is_read, "read_at": str(e.read_at) if e.read_at else None,
            "created_at": str(e.created_at) if e.created_at else None,
        } for e in rows],
        "total": total, "page": page, "page_size": page_size,
    })


@router.put("/alerts/{event_id}/read")
async def mark_alert_read(event_id: int, db: AsyncSession = Depends(get_db), _user: dict = Depends(get_current_user)):
    result = await db.execute(
        select(AlertEvent).where(AlertEvent.id == event_id, AlertEvent.deleted_at.is_(None))
    )
    event = result.scalar_one_or_none()
    if not event:
        return fail("Alert event not found", 404)
    event.is_read = True
    event.read_at = datetime.now(timezone.utc)
    await db.flush()
    return ok({"id": event.id})


@router.post("/alerts/read-all")
async def mark_all_alerts_read(db: AsyncSession = Depends(get_db), _user: dict = Depends(get_current_user)):
    rows = (await db.execute(
        select(AlertEvent).where(~AlertEvent.is_read, AlertEvent.deleted_at.is_(None))
    )).scalars().all()
    now = datetime.now(timezone.utc)
    for e in rows:
        e.is_read = True
        e.read_at = now
    await db.flush()
    return ok({"marked": len(rows)})


@router.post("/alerts/check")
async def check_alerts(db: AsyncSession = Depends(get_db), _user: dict = Depends(get_current_user)):
    from app.models.sales import SalesOrder
    from app.models.transaction import Payment

    rules = (await db.execute(
        select(AlertRule).where(AlertRule.enabled, AlertRule.deleted_at.is_(None))
    )).scalars().all()

    customers = (await db.execute(
        select(Customer).where(Customer.deleted_at.is_(None))
    )).scalars().all()

    now = datetime.now(timezone.utc)
    generated = 0

    for c in customers:
        c_orders = (await db.execute(
            select(SalesOrder).where(SalesOrder.customer_id == c.id, SalesOrder.deleted_at.is_(None))
        )).scalars().all()

        for rule in rules:
            message = None
            if rule.rule_type == "no_order" and rule.threshold_days:
                latest_order = max((o.created_at for o in c_orders), default=None)
                if latest_order:
                    days_since = (now - latest_order.replace(tzinfo=timezone.utc)).days
                    if days_since < rule.threshold_days:
                        continue
                    message = f"{c.name} 已 {days_since} 天未下单，触发规则「{rule.name}」"
                elif c.created_at and (now - (c.created_at or now).replace(tzinfo=timezone.utc)).days > rule.threshold_days:
                    message = f"{c.name} 创建 {(now - (c.created_at or now).replace(tzinfo=timezone.utc)).days} 天尚无订单，触发规则「{rule.name}」"

            elif rule.rule_type == "credit_over":
                cl = float(c.credit_limit or 0)
                if cl > 0:
                    pay_rows = (await db.execute(
                        select(Payment).where(Payment.customer_id == c.id, Payment.deleted_at.is_(None), Payment.paid_at.is_(None))
                    )).scalars().all()
                    outstanding = sum(float(p.amount or 0) for p in pay_rows)
                    usage = outstanding / cl * 100
                    if usage >= 80:
                        message = f"{c.name} 信用额度使用率达 {usage:.0f}%（¥{outstanding:.0f}/¥{cl:.0f}），触发规则「{rule.name}」"

            elif rule.rule_type == "ar_overdue":
                pay_rows = (await db.execute(
                    select(Payment).where(Payment.customer_id == c.id, Payment.deleted_at.is_(None), Payment.paid_at.is_(None))
                )).scalars().all()
                for p in pay_rows:
                    overdue_days = (now - p.created_at.replace(tzinfo=timezone.utc)).days
                    if rule.threshold_days and overdue_days > rule.threshold_days:
                        message = f"{c.name} 存在逾期 {overdue_days} 天应收款 ¥{float(p.amount or 0):.0f}，触发规则「{rule.name}」"
                        break

            elif rule.rule_type == "order_drop":
                if len(c_orders) >= 2:
                    recent = sum(float(o.total_amount or 0) for o in c_orders if (now - o.created_at.replace(tzinfo=timezone.utc)).days <= 90)
                    prior = sum(float(o.total_amount or 0) for o in c_orders if 90 < (now - o.created_at.replace(tzinfo=timezone.utc)).days <= 180)
                    if prior > 0 and recent < prior * 0.5:
                        message = f"{c.name} 近90天订单金额 ¥{recent:.0f} 较前值 ¥{prior:.0f} 骤降超50%，触发规则「{rule.name}」"

            if message:
                existing = (await db.execute(
                    select(AlertEvent).where(
                        AlertEvent.customer_id == c.id,
                        AlertEvent.rule_type == rule.rule_type,
                        AlertEvent.deleted_at.is_(None),
                        AlertEvent.created_at > func.now() - func.make_interval(days=1),
                    )
                )).scalar_one_or_none()
                if not existing:
                    event = AlertEvent(
                        customer_id=c.id, rule_type=rule.rule_type, rule_name=rule.name,
                        severity=rule.severity, message=message,
                    )
                    db.add(event)
                    generated += 1

    await db.flush()
    return ok({"generated": generated, "rules_checked": len(rules), "customers_checked": len(customers)})

@router.post("/auto-level")
async def auto_level_customers(db: AsyncSession = Depends(get_db), _user: dict = Depends(get_current_user)):
    """Run auto-leveling rules on all customers."""
    from app.models.sales import SalesOrder

    rules = (await db.execute(
        select(LevelRule).where(LevelRule.enabled, LevelRule.deleted_at.is_(None)).order_by(LevelRule.priority)
    )).scalars().all()

    customers = (await db.execute(
        select(Customer).where(Customer.deleted_at.is_(None))
    )).scalars().all()

    now = datetime.now(timezone.utc)
    updated = 0
    lifecycle_updated = 0

    for c in customers:
        c_orders = (await db.execute(
            select(SalesOrder).where(SalesOrder.customer_id == c.id, SalesOrder.deleted_at.is_(None))
        )).scalars().all()

        # Auto-track lifecycle stage
        latest_order = max((o.created_at.replace(tzinfo=timezone.utc) for o in c_orders if o.created_at), default=None)
        new_lifecycle = calc_lifecycle(c, len(c_orders), latest_order, now)
        if c.lifecycle != new_lifecycle:
            c.lifecycle = new_lifecycle
            lifecycle_updated += 1

        for rule in rules:
            if c.level == rule.target_level:
                continue  # already at this level

            match = False
            if rule.condition_type == "revenue":
                if rule.period_days:
                    total = sum(float(o.total_amount or 0) for o in c_orders
                               if (now - o.created_at.replace(tzinfo=timezone.utc)).days <= rule.period_days)
                else:
                    total = sum(float(o.total_amount or 0) for o in c_orders)
                match = _compare(total, rule.operator, rule.threshold_value)

            elif rule.condition_type == "order_count":
                if rule.period_days:
                    count = len([o for o in c_orders
                                if (now - o.created_at.replace(tzinfo=timezone.utc)).days <= rule.period_days])
                else:
                    count = len(c_orders)
                match = _compare(count, rule.operator, rule.threshold_value)

            elif rule.condition_type == "no_order_days":
                latest = max((o.created_at for o in c_orders), default=None)
                days = (now - (latest or c.created_at or now).replace(tzinfo=timezone.utc)).days
                match = _compare(days, rule.operator, rule.threshold_value)

            if match:
                old_level = c.level
                c.level = rule.target_level
                await _log(db, c.id, "update", field_name="level",
                           old_value=old_level, new_value=rule.target_level,
                           summary=f"自动升级: {rule.name}", operator="system")
                updated += 1
                break  # first matching rule wins

    await db.flush()
    return ok({"updated": updated, "lifecycle_updated": lifecycle_updated, "rules_checked": len(rules), "customers_checked": len(customers)})


def _compare(value: float, op: str, threshold: float) -> bool:
    if op == ">":
        return value > threshold
    elif op == "<":
        return value < threshold
    elif op == ">=":
        return value >= threshold
    elif op == "<=":
        return value <= threshold
    return False


# --- Customer Insight ---
@router.get("/level-rules")
async def list_level_rules(db: AsyncSession = Depends(get_db), _user: dict = Depends(get_current_user)):
    rows = (await db.execute(
        select(LevelRule).where(LevelRule.deleted_at.is_(None)).order_by(LevelRule.priority)
    )).scalars().all()
    return ok([{
        "id": r.id, "name": r.name, "target_level": r.target_level,
        "condition_type": r.condition_type, "operator": r.operator,
        "threshold_value": r.threshold_value, "period_days": r.period_days,
        "enabled": r.enabled, "priority": r.priority,
    } for r in rows])

@router.delete("/level-rules/{rule_id}")
async def delete_level_rule(rule_id: int, db: AsyncSession = Depends(get_db), _user: dict = Depends(get_current_user)):
    result = await db.execute(
        select(LevelRule).where(LevelRule.id == rule_id, LevelRule.deleted_at.is_(None))
    )
    rule = result.scalar_one_or_none()
    if not rule:
        return fail("Rule not found", 404)
    rule.deleted_at = datetime.now(timezone.utc)
    await db.flush()
    return ok(msg="deleted")



class LevelRuleCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    target_level: str
    condition_type: str
    operator: str
    threshold_value: float
    period_days: int | None = None
    enabled: bool = True
    priority: int = 0


class LevelRuleUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=100)
    target_level: str | None = None
    condition_type: str | None = None
    operator: str | None = None
    threshold_value: float | None = None
    period_days: int | None = None
    enabled: bool | None = None
    priority: int | None = None



@router.put("/level-rules/{rule_id}")
async def update_level_rule(rule_id: int, body: LevelRuleUpdate, db: AsyncSession = Depends(get_db), _user: dict = Depends(get_current_user)):
    result = await db.execute(
        select(LevelRule).where(LevelRule.id == rule_id, LevelRule.deleted_at.is_(None))
    )
    rule = result.scalar_one_or_none()
    if not rule:
        return fail("Rule not found", 404)
    for k, v in body.model_dump(exclude_unset=True).items():
        setattr(rule, k, v)
    await db.flush()
    return ok({"id": rule.id})


@router.post("/level-rules", status_code=201)
async def create_level_rule(body: LevelRuleCreate, db: AsyncSession = Depends(get_db), _user: dict = Depends(get_current_user)):
    rule = LevelRule(**body.model_dump())
    db.add(rule)
    await db.flush()
    return ok({"id": rule.id, "name": rule.name})


@router.get("/visits/upcoming")
async def upcoming_visits(
    days: int = Query(14, ge=1, le=90),
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(get_current_user),
):
    from app.models.transaction import Visit
    now = datetime.now(timezone.utc)
    cutoff = now + timedelta(days=days)
    rows = (await db.execute(
        select(Visit, Customer.name).join(Customer, Visit.customer_id == Customer.id).where(
            Visit.deleted_at.is_(None),
            Visit.visit_date >= now,
            Visit.visit_date <= cutoff,
            Customer.deleted_at.is_(None),
        ).order_by(Visit.visit_date.asc())
    )).all()
    return ok([{
        "id": v.id, "visit_no": v.visit_no, "title": v.title,
        "customer_id": v.customer_id, "customer_name": cn,
        "visit_date": str(v.visit_date) if v.visit_date else None,
        "type": v.type, "status": v.status, "purpose": v.purpose,
        "stage": v.stage,
    } for v, cn in rows])



# --- Level Rules & Auto-Leveling ---

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
        "created_at": str(f.created_at) if f.created_at else None,
    } for f in (customer.follow_ups or [])]
    return ok(data)


@router.post("", status_code=201)
async def create_customer(body: CustomerCreate, db: AsyncSession = Depends(get_db), _user: dict = Depends(get_current_user)):
    data = body.model_dump()
    auto_code = not data.get("code")
    customer = Customer(**data)
    db.add(customer)
    await db.flush()
    if auto_code:
        customer.code = _generate_code(customer.id, customer.region)
        await db.flush()
    await _log(db, customer.id, "create", summary=f"创建客户: {customer.name}", operator=_user.get("username"))
    await db.flush()
    from app.services.embedding_pipeline import after_customer_save
    after_customer_save(customer.id)
    return ok({"id": customer.id, "name": customer.name, "code": customer.code})


def _generate_code(customer_id: int, region: str | None = None) -> str:
    """Generate customer code: CUST-{REGION_PREFIX}-{id:06d} or CUST-{id:06d}."""
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
    from app.services.embedding_pipeline import after_customer_save
    after_customer_save(customer.id)
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


# --- Group Relationships ---

class LinkParentRequest(BaseModel):
    parent_id: int


@router.post("/{customer_id}/link-parent")
async def link_parent(customer_id: int, body: LinkParentRequest, db: AsyncSession = Depends(get_db), _user: dict = Depends(get_current_user)):
    if customer_id == body.parent_id:
        return fail("不能关联自身", 400)
    result = await db.execute(
        select(Customer).where(Customer.id == customer_id, Customer.deleted_at.is_(None))
    )
    customer = result.scalar_one_or_none()
    if not customer:
        return fail("Customer not found", 404)
    parent_result = await db.execute(
        select(Customer).where(Customer.id == body.parent_id, Customer.deleted_at.is_(None))
    )
    parent = parent_result.scalar_one_or_none()
    if not parent:
        return fail("Parent customer not found", 404)
    # Prevent circular reference
    ancestor_id = body.parent_id
    while ancestor_id:
        a = (await db.execute(select(Customer.parent_id).where(Customer.id == ancestor_id))).scalar()
        if a == customer_id:
            return fail("不能建立循环关联", 400)
        ancestor_id = a
    customer.parent_id = body.parent_id
    await _log(db, customer_id, "update", field_name="parent_id", new_value=str(body.parent_id), operator=_user.get("username"))
    await db.flush()
    return ok({"id": customer.id, "parent_id": body.parent_id})


@router.delete("/{customer_id}/link-parent")
async def unlink_parent(customer_id: int, db: AsyncSession = Depends(get_db), _user: dict = Depends(get_current_user)):
    result = await db.execute(
        select(Customer).where(Customer.id == customer_id, Customer.deleted_at.is_(None))
    )
    customer = result.scalar_one_or_none()
    if not customer:
        return fail("Customer not found", 404)
    if not customer.parent_id:
        return fail("Customer has no parent", 400)
    old_parent = customer.parent_id
    customer.parent_id = None
    await _log(db, customer_id, "update", field_name="parent_id", old_value=str(old_parent), new_value=None, operator=_user.get("username"))
    await db.flush()
    return ok(msg="unlinked")


@router.get("/{customer_id}/children")
async def get_children(customer_id: int, db: AsyncSession = Depends(get_db), _user: dict = Depends(get_current_user)):
    result = await db.execute(
        select(Customer).where(Customer.id == customer_id, Customer.deleted_at.is_(None))
    )
    customer = result.scalar_one_or_none()
    if not customer:
        return fail("Customer not found", 404)
    children_result = await db.execute(
        select(Customer).where(Customer.parent_id == customer_id, Customer.deleted_at.is_(None))
    )
    children = children_result.scalars().all()
    return ok([_customer_row(c) for c in children])


@router.get("/{customer_id}/group-stats")
async def get_group_stats(customer_id: int, db: AsyncSession = Depends(get_db), _user: dict = Depends(get_current_user)):
    from app.models.sales import SalesOrder
    result = await db.execute(
        select(Customer).where(Customer.id == customer_id, Customer.deleted_at.is_(None))
    )
    customer = result.scalar_one_or_none()
    if not customer:
        return fail("Customer not found", 404)
    # Collect all group members (this customer + all descendants)
    all_ids = {customer.id}
    queue = [customer.id]
    while queue:
        pid = queue.pop()
        children = (await db.execute(
            select(Customer.id).where(Customer.parent_id == pid, Customer.deleted_at.is_(None))
        )).scalars().all()
        for cid in children:
            if cid not in all_ids:
                all_ids.add(cid)
                queue.append(cid)
    members = len(all_ids)
    # Aggregate orders
    order_rows = (await db.execute(
        select(SalesOrder).where(
            SalesOrder.customer_id.in_(list(all_ids)),
            SalesOrder.deleted_at.is_(None),
        )
    )).scalars().all()
    agg_revenue = sum(float(o.total_amount or 0) for o in order_rows)
    agg_orders = len(order_rows)
    # Aggregate credit
    credit_rows = (await db.execute(
        select(Customer.credit_limit).where(
            Customer.id.in_(list(all_ids)),
            Customer.deleted_at.is_(None),
        )
    )).all()
    agg_credit = sum(float(r[0] or 0) for r in credit_rows)
    return ok({
        "members": members,
        "all_ids": list(all_ids),
        "agg_revenue": round(agg_revenue, 2),
        "agg_orders": agg_orders,
        "agg_credit": round(agg_credit, 2),
    })


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
        "created_at": str(f.created_at) if f.created_at else None,
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
            "time": str(c.created_at) if c.created_at else None,
            "id": c.id,
        })
    for f in followups:
        events.append({
            "type": "followup",
            "title": f"跟进: {f.method or '未指定'} - {f.status or '进行中'}",
            "detail": f.content or "",
            "time": str(f.created_at) if f.created_at else None,
            "id": f.id,
        })
    for o in orders:
        events.append({
            "type": "order",
            "title": f"销售订单: {o.order_no or 'NO-{}'.format(o.id)}",
            "detail": f"金额: {o.total_amount or 0:.2f}, 状态: {o.status}",
            "time": str(o.created_at) if o.created_at else None,
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

    # Credit usage & AR aging
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

    # Lifecycle & health from service layer
    created_at = customer.created_at
    created_days = (now - created_at.replace(tzinfo=timezone.utc)).days if created_at else 0
    lifecycle = calc_lifecycle(customer, order_count, last_order_date, now)
    health_score, health_label = calc_health(customer, order_rows, pay_rows, now)

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
        "created_at": str(r.created_at) if r.created_at else None,
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
        "created_at": str(a.created_at) if a.created_at else None,
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


# --- Quotation History per Customer ---

@router.get("/{customer_id}/quotation-history")
async def get_quotation_history(
    customer_id: int,
    status: str | None = None,
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(get_current_user),
):
    """Get all quotations for a customer with optional status filter and conversion stats."""
    from app.models.sales import Quotation as QModel
    base = select(QModel).where(
        QModel.customer_id == customer_id, QModel.deleted_at.is_(None)
    ).order_by(QModel.created_at.desc())
    if status:
        base = base.where(QModel.status == status)
    rows = (await db.execute(base)).scalars().all()

    quotations = []
    for q in rows:
        items = []
        if hasattr(q, 'items') and q.items:
            items = [{"id": i.id, "product_id": i.product_id, "quantity": i.quantity,
                       "unit_price": float(i.unit_price or 0), "total_price": float(i.total_price or 0)} for i in q.items]
        quotations.append({
            "id": q.id, "quotation_no": q.quotation_no, "status": q.status,
            "total_amount": float(q.total_amount), "valid_until": str(q.valid_until) if q.valid_until else None,
            "notes": q.notes, "created_at": str(q.created_at) if q.created_at else None, "items": items,
        })

    # Conversion stats
    total = len(rows)
    won = len([q for q in rows if q.status == "won"])
    lost = len([q for q in rows if q.status == "lost"])
    pending = len([q for q in rows if q.status not in ("won", "lost")])
    conversion_rate = round(won / total * 100, 1) if total > 0 else 0
    total_won_amount = sum(float(q.total_amount or 0) for q in rows if q.status == "won")

    return ok({
        "quotations": quotations,
        "total": total,
        "stats": {
            "won": won, "lost": lost, "pending": pending,
            "conversion_rate": conversion_rate,
            "total_won_amount": round(total_won_amount, 2),
        },
    })


# --- Visits ---

class VisitCreate(BaseModel):
    title: str | None = None
    visit_date: str | None = None
    type: str | None = None
    status: str | None = "planned"
    content: str | None = None
    result: str | None = None
    next_plan: str | None = None
    stage: str | None = None
    purpose: str | None = None
    main_product: str | None = None
    key_points: str | None = None
    contact_id: int | None = None
    followup_date: str | None = None


class VisitUpdate(BaseModel):
    title: str | None = None
    visit_date: str | None = None
    type: str | None = None
    status: str | None = None
    content: str | None = None
    result: str | None = None
    next_plan: str | None = None
    stage: str | None = None
    purpose: str | None = None
    main_product: str | None = None
    key_points: str | None = None
    contact_id: int | None = None
    followup_date: str | None = None


@router.get("/{customer_id}/visits")
async def list_visits(customer_id: int, db: AsyncSession = Depends(get_db), _user: dict = Depends(get_current_user)):
    from app.models.transaction import Visit
    rows = (await db.execute(
        select(Visit).where(
            Visit.customer_id == customer_id, Visit.deleted_at.is_(None)
        ).order_by(Visit.visit_date.desc().nullslast())
    )).scalars().all()
    return ok([{
        "id": v.id, "visit_no": v.visit_no, "title": v.title,
        "visit_date": str(v.visit_date) if v.visit_date else None,
        "type": v.type, "status": v.status, "content": v.content, "result": v.result,
        "next_plan": v.next_plan, "stage": v.stage, "purpose": v.purpose,
        "main_product": v.main_product, "key_points": v.key_points,
        "contact_id": v.contact_id,
        "followup_date": str(v.followup_date) if v.followup_date else None,
        "created_at": str(v.created_at) if v.created_at else None,
    } for v in rows])


@router.post("/{customer_id}/visits", status_code=201)
async def create_visit(customer_id: int, body: VisitCreate, db: AsyncSession = Depends(get_db), _user: dict = Depends(get_current_user)):
    from app.models.transaction import Visit
    data = body.model_dump()
    if data.get("visit_date"):
        data["visit_date"] = datetime.fromisoformat(data["visit_date"])
    if data.get("followup_date"):
        data["followup_date"] = datetime.fromisoformat(data["followup_date"])
    data["customer_id"] = customer_id
    visit = Visit(**data)
    db.add(visit)
    await db.flush()
    # Update customer last_contacted_at
    result = await db.execute(select(Customer).where(Customer.id == customer_id))
    cust = result.scalar_one_or_none()
    if cust:
        cust.last_contacted_at = datetime.now(timezone.utc)
    await _log(db, customer_id, "update", field_name="visit", summary=f"新建拜访: {body.title or '未指定'}", operator=_user.get("username"))
    await db.flush()
    return ok({"id": visit.id})


@router.put("/{customer_id}/visits/{visit_id}")
async def update_visit(customer_id: int, visit_id: int, body: VisitUpdate, db: AsyncSession = Depends(get_db), _user: dict = Depends(get_current_user)):
    from app.models.transaction import Visit
    result = await db.execute(
        select(Visit).where(Visit.id == visit_id, Visit.customer_id == customer_id, Visit.deleted_at.is_(None))
    )
    visit = result.scalar_one_or_none()
    if not visit:
        return fail("Visit not found", 404)
    data = body.model_dump(exclude_unset=True)
    for date_field in ("visit_date", "followup_date"):
        if data.get(date_field):
            data[date_field] = datetime.fromisoformat(data[date_field])
    for k, v in data.items():
        setattr(visit, k, v)
    await db.flush()
    return ok({"id": visit.id})


@router.delete("/{customer_id}/visits/{visit_id}")
async def delete_visit(customer_id: int, visit_id: int, db: AsyncSession = Depends(get_db), _user: dict = Depends(get_current_user)):
    from app.models.transaction import Visit
    result = await db.execute(
        select(Visit).where(Visit.id == visit_id, Visit.customer_id == customer_id, Visit.deleted_at.is_(None))
    )
    visit = result.scalar_one_or_none()
    if not visit:
        return fail("Visit not found", 404)
    visit.deleted_at = datetime.now(timezone.utc)
    await db.flush()
    return ok(msg="deleted")







@router.get("/{customer_id}/insight")
async def get_customer_insight(customer_id: int, db: AsyncSession = Depends(get_db), _user: dict = Depends(get_current_user)):
    from app.models.sales import SalesOrder, SalesOrderItem, Opportunity
    from app.models.product import Product as ProductModel

    result = await db.execute(
        select(Customer).where(Customer.id == customer_id, Customer.deleted_at.is_(None))
    )
    customer = result.scalar_one_or_none()
    if customer is None:
        return fail("Customer not found", 404)

    # Order summary — SQL aggregation
    order_stats = (await db.execute(
        select(
            func.count(SalesOrder.id),
            func.coalesce(func.sum(SalesOrder.total_amount), 0),
            func.max(SalesOrder.created_at),
        ).where(SalesOrder.customer_id == customer_id, SalesOrder.deleted_at.is_(None))
    )).first()
    total_orders = order_stats[0] or 0
    total_amount = float(order_stats[1])
    avg_order_amount = round(total_amount / total_orders, 2) if total_orders > 0 else 0
    last_order_date = str(order_stats[2]) if order_stats[2] else None

    # Product distribution — JOIN to avoid N+1
    product_distribution = []
    item_rows = (await db.execute(
        select(
            SalesOrderItem.product_id,
            ProductModel.name,
            func.sum(SalesOrderItem.quantity),
            func.sum(SalesOrderItem.amount),
        ).select_from(SalesOrderItem).join(
            SalesOrder, SalesOrderItem.order_id == SalesOrder.id
        ).join(
            ProductModel, SalesOrderItem.product_id == ProductModel.id
        ).where(
            SalesOrder.customer_id == customer_id,
            SalesOrder.deleted_at.is_(None),
            SalesOrderItem.deleted_at.is_(None),
        ).group_by(SalesOrderItem.product_id, ProductModel.name)
        .order_by(func.sum(SalesOrderItem.amount).desc())
    )).all()
    for row in item_rows:
        product_distribution.append({
            "product_id": row[0], "product_name": row[1] or f"Product#{row[0]}",
            "quantity": row[2], "amount": float(row[3]),
        })

    # Follow-up summary — SQL filters
    now = datetime.now(timezone.utc)
    total_followups = (await db.execute(
        select(func.count(CustomerFollowUp.id)).where(
            CustomerFollowUp.customer_id == customer_id, CustomerFollowUp.deleted_at.is_(None)
        )
    )).scalar() or 0
    last_followup = (await db.execute(
        select(func.max(CustomerFollowUp.created_at)).where(
            CustomerFollowUp.customer_id == customer_id, CustomerFollowUp.deleted_at.is_(None)
        )
    )).scalar()
    pending_count = (await db.execute(
        select(func.count(CustomerFollowUp.id)).where(
            CustomerFollowUp.customer_id == customer_id,
            CustomerFollowUp.deleted_at.is_(None),
            CustomerFollowUp.status == "pending",
        )
    )).scalar() or 0
    overdue_count = (await db.execute(
        select(func.count(CustomerFollowUp.id)).where(
            CustomerFollowUp.customer_id == customer_id,
            CustomerFollowUp.deleted_at.is_(None),
            CustomerFollowUp.status == "pending",
            CustomerFollowUp.planned_at.isnot(None),
            CustomerFollowUp.planned_at < now,
        )
    )).scalar() or 0

    # Opportunity summary — SQL filters
    total_opps = (await db.execute(
        select(func.count(Opportunity.id)).where(
            Opportunity.customer_id == customer_id, Opportunity.deleted_at.is_(None)
        )
    )).scalar() or 0
    active_opps = (await db.execute(
        select(func.count(Opportunity.id)).where(
            Opportunity.customer_id == customer_id,
            Opportunity.deleted_at.is_(None),
            Opportunity.stage.notin_(["won", "lost"]),
        )
    )).scalar() or 0
    won_opps = (await db.execute(
        select(func.count(Opportunity.id)).where(
            Opportunity.customer_id == customer_id,
            Opportunity.deleted_at.is_(None),
            Opportunity.stage == "won",
        )
    )).scalar() or 0
    win_prob = round(won_opps / total_opps * 100, 1) if total_opps else 0

    # Suggestions
    suggestions = []
    if not last_order_date:
        suggestions.append("客户暂无订单记录，建议首次合作推进")
    elif (now - datetime.fromisoformat(str(last_order_date)).replace(tzinfo=timezone.utc)).days > 90:
        suggestions.append("客户超过90天未下单，建议主动联系了解需求")
    if overdue_count:
        suggestions.append(f"有{overdue_count}个跟进任务已逾期，请及时处理")
    if product_distribution:
        suggestions.append(f"客户偏好产品: {product_distribution[0]['product_name']}，可推荐相关配件或升级产品")
    if total_amount > 0 and avg_order_amount > 0:
        suggestions.append(f"平均订单金额: {avg_order_amount}元，可推荐高价值产品以提升客单价")

    return ok({
        "customer": {
            "id": customer.id, "name": customer.name, "code": customer.code,
            "industry": customer.industry, "level": customer.level,
            "contact_person": customer.contact_person, "phone": customer.phone,
            "email": customer.email, "region": customer.region,
        },
        "order_summary": {
            "total_orders": total_orders,
            "total_amount": round(total_amount, 2),
            "avg_order_amount": avg_order_amount,
            "last_order_date": last_order_date,
        },
        "product_distribution": product_distribution,
        "followup_summary": {
            "total_followups": total_followups,
            "last_followup": str(last_followup) if last_followup else None,
            "pending_count": pending_count,
            "overdue_count": overdue_count,
        },
        "opportunity_summary": {
            "total": total_opps,
            "active": active_opps,
            "won": won_opps,
            "win_probability": win_prob,
        },
        "suggestions": suggestions,
    })

