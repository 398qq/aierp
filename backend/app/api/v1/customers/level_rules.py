from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.permissions import require_perm
from app.database import get_db
from app.models.customer import Customer, LevelRule
from app.schemas.common import fail, ok

from .crud import _log

router = APIRouter(prefix="/customers", tags=["customers"])


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


@router.get("/level-rules")
async def list_level_rules(
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(require_perm("customers", "read")),
):
    rows = (await db.execute(
        select(LevelRule).where(LevelRule.deleted_at.is_(None)).order_by(LevelRule.priority)
    )).scalars().all()
    return ok([{
        "id": r.id, "name": r.name, "target_level": r.target_level,
        "condition_type": r.condition_type, "operator": r.operator,
        "threshold_value": r.threshold_value, "period_days": r.period_days,
        "enabled": r.enabled, "priority": r.priority,
    } for r in rows])


@router.post("/level-rules", status_code=201)
async def create_level_rule(
    body: LevelRuleCreate,
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(require_perm("customers", "write")),
):
    rule = LevelRule(**body.model_dump())
    db.add(rule)
    await db.flush()
    return ok({"id": rule.id, "name": rule.name})


@router.put("/level-rules/{rule_id}")
async def update_level_rule(
    rule_id: int,
    body: LevelRuleUpdate,
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(require_perm("customers", "write")),
):
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


@router.delete("/level-rules/{rule_id}")
async def delete_level_rule(
    rule_id: int,
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(require_perm("customers", "delete")),
):
    result = await db.execute(
        select(LevelRule).where(LevelRule.id == rule_id, LevelRule.deleted_at.is_(None))
    )
    rule = result.scalar_one_or_none()
    if not rule:
        return fail("Rule not found", 404)
    rule.deleted_at = datetime.now(timezone.utc)
    await db.flush()
    return ok(msg="deleted")


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


@router.post("/auto-level")
async def auto_level_customers(
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(require_perm("customers", "write")),
):
    """Run auto-leveling rules on all customers."""
    from app.models.sales import SalesOrder
    from app.services.customer_service import calc_lifecycle

    rules = (await db.execute(
        select(LevelRule).where(LevelRule.enabled, LevelRule.deleted_at.is_(None)).order_by(LevelRule.priority)
    )).scalars().all()
    if not rules:
        return ok({"updated": 0, "lifecycle_updated": 0, "rules_checked": 0, "customers_checked": 0})

    customers_list = (await db.execute(
        select(Customer).where(Customer.deleted_at.is_(None))
    )).scalars().all()
    customers = {c.id: c for c in customers_list}

    orders_map = {}
    for o in (await db.execute(
        select(SalesOrder).where(SalesOrder.deleted_at.is_(None))
    )).scalars().all():
        orders_map.setdefault(o.customer_id, []).append(o)

    now = datetime.now(timezone.utc)
    updated = 0
    lifecycle_updated = 0

    for c in customers.values():
        c_orders = orders_map.get(c.id, [])

        latest_order = max((o.created_at.replace(tzinfo=timezone.utc) for o in c_orders if o.created_at), default=None)
        new_lifecycle = calc_lifecycle(c, len(c_orders), latest_order, now)
        if c.lifecycle != new_lifecycle:
            c.lifecycle = new_lifecycle
            lifecycle_updated += 1

        for rule in rules:
            if c.level == rule.target_level:
                continue

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
                break

    await db.flush()
    return ok({"updated": updated, "lifecycle_updated": lifecycle_updated, "rules_checked": len(rules), "customers_checked": len(customers_list)})
