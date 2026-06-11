from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.permissions import require_perm
from app.database import get_db
from app.models.customer import AlertEvent, AlertRule, Customer
from app.schemas.common import fail, ok

router = APIRouter(prefix="/customers", tags=["customers"])


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
async def list_alert_rules(
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(require_perm("customers", "read")),
):
    rows = (await db.execute(
        select(AlertRule).where(AlertRule.deleted_at.is_(None)).order_by(AlertRule.rule_type, AlertRule.name)
    )).scalars().all()
    return ok([{
        "id": r.id, "name": r.name, "rule_type": r.rule_type,
        "threshold_days": r.threshold_days, "threshold_pct": r.threshold_pct,
        "threshold_amount": r.threshold_amount, "enabled": r.enabled, "severity": r.severity,
    } for r in rows])


@router.post("/alerts/rules", status_code=201)
async def create_alert_rule(
    body: AlertRuleCreate,
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(require_perm("customers", "write")),
):
    rule = AlertRule(**body.model_dump())
    db.add(rule)
    await db.flush()
    return ok({"id": rule.id, "name": rule.name})


@router.put("/alerts/rules/{rule_id}")
async def update_alert_rule(
    rule_id: int,
    body: AlertRuleUpdate,
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(require_perm("customers", "write")),
):
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
async def delete_alert_rule(
    rule_id: int,
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(require_perm("customers", "delete")),
):
    result = await db.execute(
        select(AlertRule).where(AlertRule.id == rule_id, AlertRule.deleted_at.is_(None))
    )
    rule = result.scalar_one_or_none()
    if not rule:
        return fail("Rule not found", 404)
    rule.deleted_at = datetime.now(timezone.utc)
    await db.flush()
    return ok(msg="deleted")


@router.get("/alerts")
async def list_alert_events(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    severity: str | None = None,
    rule_type: str | None = None,
    is_read: bool | None = None,
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(require_perm("customers", "read")),
):
    base = (
        select(AlertEvent, Customer.name.label("customer_name"))
        .join(Customer, AlertEvent.customer_id == Customer.id)
        .where(AlertEvent.deleted_at.is_(None))
    )
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
    )).all()
    return ok({
        "list": [{
            "id": e.AlertEvent.id, "customer_id": e.AlertEvent.customer_id,
            "customer_name": e.customer_name,
            "rule_type": e.AlertEvent.rule_type,
            "rule_name": e.AlertEvent.rule_name, "severity": e.AlertEvent.severity,
            "message": e.AlertEvent.message,
            "is_read": e.AlertEvent.is_read,
            "read_at": str(e.AlertEvent.read_at) if e.AlertEvent.read_at else None,
            "created_at": str(e.AlertEvent.created_at) if e.AlertEvent.created_at else None,
        } for e in rows],
        "total": total, "page": page, "page_size": page_size,
    })


@router.put("/alerts/{event_id}/read")
async def mark_alert_read(
    event_id: int,
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(require_perm("customers", "write")),
):
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
async def mark_all_alerts_read(
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(require_perm("customers", "write")),
):
    rows = (await db.execute(
        select(AlertEvent).where(~AlertEvent.is_read, AlertEvent.deleted_at.is_(None))
    )).scalars().all()
    now = datetime.now(timezone.utc)
    for e in rows:
        e.is_read = True
        e.read_at = now
    await db.flush()
    return ok({"marked": len(rows)})


@router.get("/alerts/{alert_id}/events")
async def get_alert_events(
    alert_id: int,
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(require_perm("customers", "read")),
):
    """Get events for a specific alert rule."""
    rows = (await db.execute(
        select(AlertEvent, Customer.name.label("customer_name"))
        .join(Customer, AlertEvent.customer_id == Customer.id)
        .where(
            AlertEvent.deleted_at.is_(None),
            AlertEvent.rule_type == select(AlertRule.rule_type).where(AlertRule.id == alert_id).scalar_subquery(),
        )
        .order_by(AlertEvent.created_at.desc())
    )).all()
    return ok([{
        "id": e.AlertEvent.id, "customer_id": e.AlertEvent.customer_id,
        "customer_name": e.customer_name, "rule_type": e.AlertEvent.rule_type,
        "rule_name": e.AlertEvent.rule_name, "severity": e.AlertEvent.severity,
        "message": e.AlertEvent.message,
        "is_read": e.AlertEvent.is_read,
        "read_at": str(e.AlertEvent.read_at) if e.AlertEvent.read_at else None,
        "created_at": str(e.AlertEvent.created_at) if e.AlertEvent.created_at else None,
    } for e in rows])


@router.get("/alerts/stats")
async def alert_stats(
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(require_perm("customers", "read")),
):
    """Get alert statistics."""
    total_rules = (await db.execute(
        select(func.count(AlertRule.id)).where(AlertRule.deleted_at.is_(None))
    )).scalar() or 0
    enabled_rules = (await db.execute(
        select(func.count(AlertRule.id)).where(
            AlertRule.deleted_at.is_(None),
            AlertRule.enabled.is_(True),
        )
    )).scalar() or 0
    total_events = (await db.execute(
        select(func.count(AlertEvent.id)).where(AlertEvent.deleted_at.is_(None))
    )).scalar() or 0
    unread_events = (await db.execute(
        select(func.count(AlertEvent.id)).where(
            AlertEvent.deleted_at.is_(None),
            AlertEvent.is_read.is_(False),
        )
    )).scalar() or 0
    return ok({
        "total_rules": total_rules,
        "enabled_rules": enabled_rules,
        "total_events": total_events,
        "unread_events": unread_events,
    })


@router.post("/alerts/check")
async def check_alerts(
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(require_perm("customers", "write")),
):
    """Batch alert checker — loads all data in bulk and evaluates rules in-memory."""
    from app.models.sales import SalesOrder
    from app.models.transaction import Payment

    rules = (await db.execute(
        select(AlertRule).where(AlertRule.enabled, AlertRule.deleted_at.is_(None))
    )).scalars().all()
    if not rules:
        return ok({"generated": 0, "rules_checked": 0, "customers_checked": 0})

    customers = {c.id: c for c in (await db.execute(
        select(Customer).where(Customer.deleted_at.is_(None))
    )).scalars().all()}

    orders = {}
    for o in (await db.execute(
        select(SalesOrder).where(SalesOrder.deleted_at.is_(None))
    )).scalars().all():
        orders.setdefault(o.customer_id, []).append(o)

    payments = {}
    for p in (await db.execute(
        select(Payment).where(Payment.deleted_at.is_(None), Payment.paid_at.is_(None))
    )).scalars().all():
        payments.setdefault(p.customer_id, []).append(p)

    now = datetime.now(timezone.utc)
    generated = 0
    recent_cutoff = now - timedelta(days=1)
    existing_events = (await db.execute(
        select(AlertEvent).where(
            AlertEvent.deleted_at.is_(None),
            AlertEvent.created_at >= recent_cutoff,
        )
    )).scalars().all()
    recent_alerts = {(e.customer_id, e.rule_type) for e in existing_events}

    for c in customers.values():
        c_orders = orders.get(c.id, [])
        c_payments = payments.get(c.id, [])
        c_unpaid = sum(float(p.amount or 0) for p in c_payments)

        for rule in rules:
            message = None
            if rule.rule_type == "no_order" and rule.threshold_days:
                latest_order = max((o.created_at for o in c_orders), default=None)
                if latest_order:
                    days_since = (now - latest_order.replace(tzinfo=timezone.utc)).days
                    if days_since >= rule.threshold_days:
                        message = f"{c.name} 已 {days_since} 天未下单，触发规则「{rule.name}」"
                elif c.created_at and (now - (c.created_at or now).replace(tzinfo=timezone.utc)).days >= rule.threshold_days:
                    message = f"{c.name} 创建 {(now - (c.created_at or now).replace(tzinfo=timezone.utc)).days} 天尚无订单，触发规则「{rule.name}」"

            elif rule.rule_type == "credit_over":
                cl = float(c.credit_limit or 0)
                if cl > 0:
                    usage = c_unpaid / cl * 100
                    if usage >= 80:
                        message = f"{c.name} 信用额度使用率达 {usage:.0f}%（{c_unpaid:.0f}/{cl:.0f}），触发规则「{rule.name}」"

            elif rule.rule_type == "ar_overdue":
                for p in c_payments:
                    overdue_days = (now - p.created_at.replace(tzinfo=timezone.utc)).days
                    if rule.threshold_days and overdue_days > rule.threshold_days:
                        message = f"{c.name} 存在逾期 {overdue_days} 天应收款 {float(p.amount or 0):.0f}，触发规则「{rule.name}」"
                        break

            elif rule.rule_type == "order_drop" and len(c_orders) >= 2:
                recent = sum(float(o.total_amount or 0) for o in c_orders
                            if (now - o.created_at.replace(tzinfo=timezone.utc)).days <= 90)
                prior = sum(float(o.total_amount or 0) for o in c_orders
                            if 90 < (now - o.created_at.replace(tzinfo=timezone.utc)).days <= 180)
                if prior > 0 and recent < prior * 0.5:
                    message = f"{c.name} 近90天订单金额 {recent:.0f} 较前值 {prior:.0f} 骤降超50%，触发规则「{rule.name}」"

            if message and (c.id, rule.rule_type) not in recent_alerts:
                event = AlertEvent(
                    customer_id=c.id, rule_type=rule.rule_type, rule_name=rule.name,
                    severity=rule.severity, message=message,
                )
                db.add(event)
                recent_alerts.add((c.id, rule.rule_type))
                generated += 1

    await db.flush()
    return ok({"generated": generated, "rules_checked": len(rules), "customers_checked": len(customers)})
