"""Customers — bulk operations (import, export, merge, dedupe, batch delete).

These endpoints all operate on multiple customer rows in a single
request — they share validation helpers and conflict-detection logic
from ``crud.py`` but never touch the read or write paths used by
single-record CRUD.
"""

from __future__ import annotations

import csv
import io
import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, File, Query, Response, UploadFile
from fastapi.responses import StreamingResponse
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from starlette import status

from app.api.v1.customers.crud import (
    BatchDelete,
    CSV_TEMPLATE_HEADERS,
    MergeRequest,
    _code_number_conflict_message,
    _dedupe_auto_short_name,
    _find_code_number_conflict,
    _generate_short_name,
    _log,
    customer_name_conflict_message,
    find_name_conflict,
)
from app.core.permissions import require_perm
from app.database import get_db
from app.models.customer import (
    Customer,
    CustomerAttachment,
    CustomerContact as CustomerContact,
    CustomerFollowUp,
)
from app.schemas.common import fail, ok
from app.services.cache_service import cache_bump_version
from app.services.customer_service import detect_duplicates as detect_dups

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/customers", tags=["customers"])

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/customers", tags=["customers"])


@router.get("/import-template")
async def import_template(
    current_user: dict = Depends(require_perm("customers", "read")),
):
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(CSV_TEMPLATE_HEADERS)
    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={
            "Content-Disposition": "attachment; filename=customer_import_template.csv"
        },
    )


@router.post("/import")
async def import_customers(
    response: Response,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_perm("customers", "write")),
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
                stmt = select(Customer).where(
                    Customer.code == code, Customer.deleted_at.is_(None)
                )
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
                        ("name", name),
                        ("short_name", next_short_name),
                        ("industry", industry),
                        ("level", level),
                        ("region", region),
                        ("source", source),
                        ("customer_type", customer_type),
                        ("credit_level", credit_level),
                        ("credit_limit", credit_limit),
                        ("contact_person", contact_person),
                        ("phone", phone),
                        ("email", email),
                        ("address", address),
                        ("notes", notes),
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
                name=name,
                code=code,
                short_name=short_name,
                industry=industry,
                level=level,
                region=region,
                source=source,
                customer_type=customer_type,
                credit_level=credit_level,
                credit_limit=credit_limit,
                contact_person=contact_person,
                phone=phone,
                email=email,
                address=address,
                notes=notes,
            )
            db.add(customer)
            imported += 1
        await db.commit()
        await cache_bump_version("customers:list")
        await cache_bump_version("dashboard:overview")
        await cache_bump_version("dashboard:kpi")
        return ok({"imported": imported, "updated": updated})
    except Exception as e:
        response.status_code = status.HTTP_400_BAD_REQUEST
        await db.rollback()
        return fail(f"Import failed: {str(e)}")


@router.get("/export")
async def export_customers(
    current_user: dict = Depends(require_perm("customers", "export")),
    ids: str | None = None,
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
    if ids:
        selected_ids = [int(value) for value in ids.split(",") if value.strip().isdigit()]
        if selected_ids:
            conditions.append(Customer.id.in_(selected_ids))
        else:
            conditions.append(Customer.id.in_([]))
    _keyword = keyword or q
    if _keyword:
        conditions.append(
            or_(
                Customer.name.ilike(f"%{_keyword}%"),
                Customer.code.ilike(f"%{_keyword}%"),
                Customer.contact_person.ilike(f"%{_keyword}%"),
            )
        )
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
    for cust in customers:
        writer.writerow(
            [
                cust.name,
                cust.code or "",
                cust.short_name or "",
                cust.industry or "",
                cust.level or "",
                cust.region or "",
                cust.source or "",
                cust.customer_type or "",
                cust.credit_level or "",
                str(cust.credit_limit) if cust.credit_limit else "",
                cust.contact_person or "",
                cust.phone or "",
                cust.email or "",
                cust.website or "",
                cust.address or "",
                cust.tax_id or "",
                cust.registration_number or "",
                cust.invoice_title or "",
                cust.invoice_address or "",
                cust.bank_name or "",
                cust.bank_account or "",
                cust.price_tier or "",
                str(cust.annual_revenue) if cust.annual_revenue else "",
                str(cust.employee_count) if cust.employee_count else "",
                cust.payment_terms or "",
                cust.payment_method or "",
                cust.currency or "CNY",
                cust.delivery_address or "",
                cust.default_incoterm or "",
                cust.notes or "",
            ]
        )
    output.seek(0)
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    filename = f"customers_export_{timestamp}.csv"
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


@router.post("/merge")
async def merge_customers(
    body: MergeRequest,
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(require_perm("customers", "write")),
):
    if body.source_id == body.target_id:
        return fail("不能合并到自身", 400)

    source = (
        await db.execute(
            select(Customer).where(
                Customer.id == body.source_id, Customer.deleted_at.is_(None)
            )
        )
    ).scalar_one_or_none()
    target = (
        await db.execute(
            select(Customer).where(
                Customer.id == body.target_id, Customer.deleted_at.is_(None)
            )
        )
    ).scalar_one_or_none()

    if not source or not target:
        return fail("客户不存在", 404)

    username = _user.get("username", "system")
    transferred: dict[str, int] = {}

    contacts = (
        (
            await db.execute(
                select(CustomerContact).where(
                    CustomerContact.customer_id == body.source_id,
                    CustomerContact.deleted_at.is_(None),
                )
            )
        )
        .scalars()
        .all()
    )
    for c in contacts:
        c.customer_id = body.target_id
    transferred["contacts"] = len(contacts)

    fus = (
        (
            await db.execute(
                select(CustomerFollowUp).where(
                    CustomerFollowUp.customer_id == body.source_id,
                    CustomerFollowUp.deleted_at.is_(None),
                )
            )
        )
        .scalars()
        .all()
    )
    for f in fus:
        f.customer_id = body.target_id
    transferred["follow_ups"] = len(fus)

    for t in source.tags:
        if t not in target.tags:
            target.tags.append(t)
    transferred["tags"] = len(source.tags)

    atts = (
        (
            await db.execute(
                select(CustomerAttachment).where(
                    CustomerAttachment.customer_id == body.source_id,
                    CustomerAttachment.deleted_at.is_(None),
                )
            )
        )
        .scalars()
        .all()
    )
    for a in atts:
        a.customer_id = body.target_id
    transferred["attachments"] = len(atts)

    from app.models.sales import SalesOrder

    orders = (
        (
            await db.execute(
                select(SalesOrder).where(
                    SalesOrder.customer_id == body.source_id,
                    SalesOrder.deleted_at.is_(None),
                )
            )
        )
        .scalars()
        .all()
    )
    for o in orders:
        o.customer_id = body.target_id
    transferred["orders"] = len(orders)

    source.deleted_at = datetime.now(timezone.utc)
    await _log(
        db,
        body.source_id,
        "merge",
        summary=f"合并到 #{body.target_id} {target.name}",
        operator=username,
    )
    await _log(
        db,
        body.target_id,
        "merge",
        summary=f"从 #{body.source_id} {source.name} 合并入",
        operator=username,
    )

    await db.flush()
    await cache_bump_version("customers:list")
    await cache_bump_version("dashboard:overview")
    await cache_bump_version("dashboard:kpi")
    return ok({"merged": True, "transferred": transferred})


@router.get("/duplicates")
async def detect_duplicates(
    threshold: float = Query(0.9, ge=0.5, le=1.0),
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(require_perm("customers", "read")),
):
    rows = (
        (
            await db.execute(
                select(Customer)
                .where(Customer.deleted_at.is_(None))
                .order_by(Customer.name)
            )
        )
        .scalars()
        .all()
    )
    pairs = detect_dups(list(rows), threshold)
    return ok({"total": len(pairs), "pairs": pairs})


@router.post("/batch-delete")
async def batch_delete(
    body: BatchDelete,
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(require_perm("customers", "delete")),
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
    await cache_bump_version("dashboard:overview")
    await cache_bump_version("dashboard:kpi")
    return ok({"deleted": len(customers)})


__all__ = ["router"]
