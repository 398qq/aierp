"""Service layer for 013 commission scheme configuration.

CRUD + tier validation + calculation engine + scheme simulation.
"""

import json
import logging
from datetime import date, datetime, timezone
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.domain.shared.errors import (
    BusinessRuleViolation,
    ConflictError,
    NotFoundError,
    ValidationError,
)
from app.models.commission_scheme import (
    CommissionScheme,
    SchemeAssignment,
    SchemeTier,
    SchemeVersion,
)

logger = logging.getLogger(__name__)

# ── Helpers ─────────────────────────────────────────────────────────────


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _today() -> date:
    return _now().date()


def _take_snapshot(
    scheme: CommissionScheme,
    tiers: list | None = None,
    assignments: list | None = None,
) -> dict:
    """Serialize the current scheme state (tiers + assignments) for audit.

    Accepts optional pre-loaded ``tiers`` and ``assignments`` lists to
    avoid lazy-loading relationship access in async sessions.
    """
    return {
        "name": scheme.name,
        "description": scheme.description,
        "version_no": scheme.version_no,
        "status": scheme.status,
        "effective_from": str(scheme.effective_from),
        "effective_to": str(scheme.effective_to) if scheme.effective_to else None,
        "is_default": scheme.is_default,
        "tiers": [
            {
                "tier_no": t.tier_no if hasattr(t, "tier_no") else t["tier_no"],
                "metric_type": t.metric_type
                if hasattr(t, "metric_type")
                else t["metric_type"],
                "low_amount": str(t.low_amount)
                if hasattr(t, "low_amount")
                else str(t["low_amount"]),
                "high_amount": str(t.high_amount)
                if hasattr(t, "high_amount") and t.high_amount
                else (
                    str(t["high_amount"])
                    if isinstance(t, dict) and t.get("high_amount")
                    else None
                ),
                "rate": str(t.rate) if hasattr(t, "rate") else str(t["rate"]),
                "cap_amount": str(t.cap_amount)
                if hasattr(t, "cap_amount")
                else str(t["cap_amount"]),
                "floor_amount": str(t.floor_amount)
                if hasattr(t, "floor_amount")
                else str(t["floor_amount"]),
                "product_category": t.product_category
                if hasattr(t, "product_category")
                else t.get("product_category"),
                "customer_level": t.customer_level
                if hasattr(t, "customer_level")
                else t.get("customer_level"),
            }
            for t in (tiers if tiers is not None else (scheme.tiers or []))
            if not (hasattr(t, "deleted_at") and t.deleted_at)
        ],
        "assignments": [
            {
                "assignee_type": a.assignee_type
                if hasattr(a, "assignee_type")
                else a["assignee_type"],
                "assignee_id": a.assignee_id
                if hasattr(a, "assignee_id")
                else a["assignee_id"],
            }
            for a in (
                assignments if assignments is not None else (scheme.assignments or [])
            )
            if not (hasattr(a, "deleted_at") and a.deleted_at)
        ],
    }


# ── CRUD ───────────────────────────────────────────────────────────────


async def list_schemes(
    db: AsyncSession,
    status: str | None = None,
    q: str | None = None,
    page: int = 1,
    page_size: int = 20,
) -> dict:
    """Paginated list of schemes."""
    base = select(CommissionScheme).where(CommissionScheme.deleted_at.is_(None))
    count_base = select(CommissionScheme.id).where(
        CommissionScheme.deleted_at.is_(None)
    )

    if status:
        base = base.where(CommissionScheme.status == status)
        count_base = count_base.where(CommissionScheme.status == status)
    if q:
        like = f"%{q}%"
        base = base.where(CommissionScheme.name.ilike(like))
        count_base = count_base.where(CommissionScheme.name.ilike(like))

    total = (await db.execute(count_base)).scalar() or 0
    rows = (
        (
            await db.execute(
                base.order_by(CommissionScheme.id.desc())
                .offset((page - 1) * page_size)
                .limit(page_size)
            )
        )
        .scalars()
        .all()
    )
    return {
        "list": [_scheme_to_dict(s) for s in rows],
        "total": total,
        "page": page,
        "page_size": page_size,
    }


def _scheme_to_dict(s: CommissionScheme) -> dict:
    return {
        "id": s.id,
        "name": s.name,
        "description": s.description,
        "version_no": s.version_no,
        "status": s.status,
        "effective_from": str(s.effective_from),
        "effective_to": str(s.effective_to) if s.effective_to else None,
        "is_default": s.is_default,
        "created_by": s.created_by,
        "created_at": str(s.created_at) if s.created_at else None,
    }


async def get_scheme(db: AsyncSession, scheme_id: int) -> CommissionScheme:
    """Get scheme detail with eager-loaded tiers + assignments."""
    result = await db.execute(
        select(CommissionScheme)
        .options(
            selectinload(CommissionScheme.tiers),
            selectinload(CommissionScheme.assignments),
        )
        .where(
            CommissionScheme.id == scheme_id, CommissionScheme.deleted_at.is_(None)
        )
    )
    scheme = result.scalar_one_or_none()
    if not scheme:
        raise NotFoundError("Scheme not found")
    return scheme


async def create_scheme(db: AsyncSession, data: dict, user_id: int) -> CommissionScheme:
    """Create a new scheme with tiers and assignments."""
    tiers_data = data.pop("tiers", [])
    assignments_data = data.pop("assignments", [])

    if not data.get("effective_from"):
        data["effective_from"] = _today()
    data["version_no"] = 1
    data["created_by"] = user_id
    data["status"] = "draft"

    # Check for duplicate active scheme per user
    if assignments_data:
        for a in assignments_data:
            if a.get("assignee_type") == "user":
                await _check_active_scheme_conflict(
                    db, a["assignee_id"], data.get("effective_from", _today())
                )

    scheme = CommissionScheme(**data)
    db.add(scheme)
    await db.flush()

    for td in tiers_data:
        td["scheme_id"] = scheme.id
        db.add(SchemeTier(**td))
    for ad in assignments_data:
        ad["scheme_id"] = scheme.id
        db.add(SchemeAssignment(**ad))

    # Create initial version snapshot
    await db.flush()
    db.add(
        SchemeVersion(
            scheme_id=scheme.id,
            version_no=1,
            snapshot=json.dumps(
                _take_snapshot(scheme, tiers=tiers_data, assignments=assignments_data)
            ),
            changed_by=user_id,
            changed_at=_now(),
        )
    )
    await db.commit()
    await db.refresh(scheme)
    return scheme


async def update_scheme(
    db: AsyncSession, scheme_id: int, data: dict, user_id: int
) -> CommissionScheme:
    """Update a draft/pending scheme. Bumps version."""
    scheme = await get_scheme(db, scheme_id)

    if scheme.status not in ("draft", "pending"):
        raise BusinessRuleViolation("Only draft or pending schemes can be edited")

    tiers_data = data.pop("tiers", None)
    assignments_data = data.pop("assignments", None)

    for field, value in data.items():
        if value is not None:
            setattr(scheme, field, value)

    # Replace tiers
    if tiers_data is not None:
        # Soft-delete existing
        for t in scheme.tiers or []:
            t.deleted_at = _now()
        await db.flush()
        for td in tiers_data:
            td["scheme_id"] = scheme.id
            db.add(SchemeTier(**td))

    # Replace assignments
    if assignments_data is not None:
        for a in scheme.assignments or []:
            a.deleted_at = _now()
        await db.flush()
        for ad in assignments_data:
            ad["scheme_id"] = scheme.id
            db.add(SchemeAssignment(**ad))
        # Check for active scheme conflicts
        for ad in assignments_data or []:
            if ad.get("assignee_type") == "user":
                await _check_active_scheme_conflict(
                    db, ad["assignee_id"], scheme.effective_from, exclude_id=scheme_id
                )

    scheme.version_no += 1
    await db.flush()

    db.add(
        SchemeVersion(
            scheme_id=scheme.id,
            version_no=scheme.version_no,
            snapshot=json.dumps(
                _take_snapshot(
                    scheme,
                    tiers=tiers_data if tiers_data is not None else None,
                    assignments=assignments_data
                    if assignments_data is not None
                    else None,
                )
            ),
            changed_by=user_id,
            changed_at=_now(),
        )
    )
    await db.commit()
    await db.refresh(scheme)
    return scheme


async def delete_scheme(db: AsyncSession, scheme_id: int) -> None:
    """Soft-delete a scheme. Refuse if any commission references it."""
    scheme = await get_scheme(db, scheme_id)

    # Check if any commission references this scheme
    # (Wrapped in try/except for environments where commission_scheme_id
    # column has not been migrated yet — test SQLite doesn't have it.)
    try:
        from app.models.finance import Commission

        col = getattr(Commission, "commission_scheme_id", None)
        if col is not None:
            ref_count = (
                await db.execute(
                    select(Commission.id)
                    .where(
                        col == scheme_id,
                        Commission.deleted_at.is_(None),
                    )
                    .limit(1)
                )
            ).first()
            if ref_count:
                raise ConflictError(
                    "Scheme is referenced by existing commissions and cannot be deleted"
                )
    except AttributeError:
        pass

    scheme.deleted_at = _now()
    await db.commit()


async def activate_scheme(db: AsyncSession, scheme_id: int) -> CommissionScheme:
    """Change status from draft → pending/active based on effective_from."""
    scheme = await get_scheme(db, scheme_id)

    if scheme.status not in ("draft", "pending", "inactive"):
        raise BusinessRuleViolation(f"Cannot activate scheme in status {scheme.status}")

    if scheme.effective_from <= _today():
        scheme.status = "active"
    else:
        scheme.status = "pending"

    scheme.version_no += 1
    await db.commit()
    await db.refresh(scheme)
    return scheme


async def deactivate_scheme(db: AsyncSession, scheme_id: int) -> CommissionScheme:
    """Manually deactivate an active scheme."""
    scheme = await get_scheme(db, scheme_id)
    if scheme.status != "active":
        raise BusinessRuleViolation("Only active schemes can be deactivated")
    scheme.status = "inactive"
    await db.commit()
    await db.refresh(scheme)
    return scheme


# ── Assignment ─────────────────────────────────────────────────────────


async def get_my_scheme(db: AsyncSession, user_id: int) -> dict | None:
    """Find the effective scheme for a user.

    Resolution order: user-level → role-level → default.
    Returns the current active scheme or None.
    """
    # Check user-level assignment
    result = await db.execute(
        select(CommissionScheme)
        .join(SchemeAssignment, SchemeAssignment.scheme_id == CommissionScheme.id)
        .where(
            SchemeAssignment.assignee_type == "user",
            SchemeAssignment.assignee_id == user_id,
            SchemeAssignment.deleted_at.is_(None),
            CommissionScheme.status == "active",
            CommissionScheme.deleted_at.is_(None),
        )
    )
    scheme = result.scalar_one_or_none()
    if scheme:
        return _scheme_to_dict(scheme)

    # Check role-level (take first matching role)
    from app.models.rbac import user_roles_table

    user_roles = (
        (
            await db.execute(
                select(user_roles_table.c.role_id).where(
                    user_roles_table.c.user_id == user_id
                )
            )
        )
        .scalars()
        .all()
    )

    if user_roles:
        result = await db.execute(
            select(CommissionScheme)
            .join(SchemeAssignment, SchemeAssignment.scheme_id == CommissionScheme.id)
            .where(
                SchemeAssignment.assignee_type == "role",
                SchemeAssignment.assignee_id.in_(list(user_roles)),
                SchemeAssignment.deleted_at.is_(None),
                CommissionScheme.status == "active",
                CommissionScheme.deleted_at.is_(None),
            )
            .order_by(CommissionScheme.id.desc())
            .limit(1)
        )
        scheme = result.scalar_one_or_none()
        if scheme:
            return _scheme_to_dict(scheme)

    # Fallback to default
    result = await db.execute(
        select(CommissionScheme)
        .where(
            CommissionScheme.is_default.is_(True),
            CommissionScheme.status == "active",
            CommissionScheme.deleted_at.is_(None),
        )
        .limit(1)
    )
    scheme = result.scalar_one_or_none()
    if scheme:
        return _scheme_to_dict(scheme)

    return None


async def assign_scheme(
    db: AsyncSession, scheme_id: int, assignments: list[dict]
) -> CommissionScheme:
    """Add assignments to a scheme."""
    scheme = await get_scheme(db, scheme_id)
    for a in assignments:
        if a.get("assignee_type") == "user":
            await _check_active_scheme_conflict(
                db, a["assignee_id"], scheme.effective_from, exclude_id=scheme_id
            )
        existing = await db.execute(
            select(SchemeAssignment).where(
                SchemeAssignment.scheme_id == scheme_id,
                SchemeAssignment.assignee_type == a["assignee_type"],
                SchemeAssignment.assignee_id == a["assignee_id"],
                SchemeAssignment.deleted_at.is_(None),
            )
        )
        if not existing.scalar_one_or_none():
            db.add(SchemeAssignment(scheme_id=scheme_id, **a))
    await db.commit()
    await db.refresh(scheme)
    return scheme


async def unassign_scheme(
    db: AsyncSession, scheme_id: int, assignment_id: int
) -> CommissionScheme:
    """Remove an assignment."""
    result = await db.execute(
        select(SchemeAssignment).where(
            SchemeAssignment.id == assignment_id,
            SchemeAssignment.scheme_id == scheme_id,
            SchemeAssignment.deleted_at.is_(None),
        )
    )
    assignment = result.scalar_one_or_none()
    if not assignment:
        raise NotFoundError("Assignment not found")
    assignment.deleted_at = _now()
    await db.commit()
    scheme = await get_scheme(db, scheme_id)
    return scheme


# ── Tier Validation ────────────────────────────────────────────────────


def validate_tiers(tiers: list[dict]) -> list[dict]:
    """Validate tier definitions server-side. Returns normalized tiers."""
    if not tiers:
        raise ValidationError("At least one tier is required")
    if len(tiers) > 10:
        raise ValidationError("Maximum 10 tiers allowed")

    sorted_tiers = sorted(tiers, key=lambda t: t["low_amount"])
    for i in range(len(sorted_tiers) - 1):
        curr = sorted_tiers[i]
        nxt = sorted_tiers[i + 1]
        if curr["high_amount"] is None:
            raise ValidationError(
                f"Tier {curr['tier_no']}: only the last tier can have unlimited high"
            )
        if curr["high_amount"] != nxt["low_amount"]:
            raise ValidationError(
                f"Gap between tier {curr['tier_no']} (high={curr['high_amount']}) "
                f"and tier {nxt['tier_no']} (low={nxt['low_amount']})"
            )
    return sorted_tiers


# ── Calculation Engine ─────────────────────────────────────────────────


class CommissionResult:
    """Result of a commission calculation using a scheme."""

    def __init__(
        self,
        amount: Decimal,
        rate: Decimal,
        tier_matched: str,
        scheme_id: int,
        scheme_snapshot: dict,
        amount_before_cap: Decimal | None = None,
    ):
        self.amount = amount
        self.rate = rate
        self.tier_matched = tier_matched
        self.scheme_id = scheme_id
        self.scheme_snapshot = scheme_snapshot
        self.amount_before_cap = amount_before_cap


async def compute_commission(
    db: AsyncSession,
    user_id: int,
    base_amount: Decimal,
    product_category: str | None,
    customer_level: str | None,
    period: str,
    ref_date: date | None = None,
) -> CommissionResult:
    """Compute commission for a user using their assigned scheme.

    Resolution order: user-level → role-level → default → 3% hardcoded.
    """
    if ref_date is None:
        ref_date = _today()

    # Find scheme
    scheme = await _resolve_scheme(db, user_id, ref_date)

    if scheme is None:
        # Hardcoded fallback
        rate = Decimal("0.03")
        amount = (Decimal(str(base_amount)) * rate).quantize(Decimal("0.000001"))
        return CommissionResult(
            amount=amount,
            rate=rate,
            tier_matched="default_3pct",
            scheme_id=0,
            scheme_snapshot={},
            amount_before_cap=amount,
        )

    snapshot = _take_snapshot(scheme)
    tiers = scheme.tiers or []
    active_tiers = [t for t in tiers if not t.deleted_at]

    # Find matching tier
    matched_tier = _match_tier(
        active_tiers, base_amount, product_category, customer_level
    )

    if matched_tier is None:
        # If no tier matched, use the default rate from the scheme (last tier's rate, or 0)
        rate = Decimal("0.00")
        amount = Decimal("0")
        amount_before_cap = amount
        tier_desc = "no_match"
    else:
        rate = matched_tier.rate
        amount = (Decimal(str(base_amount)) * rate).quantize(Decimal("0.000001"))

        # Floor (min guarantee)
        if matched_tier.floor_amount and amount < matched_tier.floor_amount:
            amount = matched_tier.floor_amount
            tier_desc = f"floor_applied_{matched_tier.tier_no}"
        else:
            tier_desc = f"tier_{matched_tier.tier_no}"

        # Cap (max limit)
        amount_before_cap = amount
        if matched_tier.cap_amount and amount > matched_tier.cap_amount:
            amount = matched_tier.cap_amount
            tier_desc += "_capped"

    return CommissionResult(
        amount=amount,
        rate=rate,
        tier_matched=tier_desc,
        scheme_id=scheme.id,
        scheme_snapshot=snapshot,
        amount_before_cap=amount_before_cap,
    )


async def _resolve_scheme(
    db: AsyncSession, user_id: int, ref_date: date
) -> CommissionScheme | None:
    """Resolve active scheme for user at ref_date."""
    # User-level
    result = await db.execute(
        select(CommissionScheme)
        .join(SchemeAssignment, SchemeAssignment.scheme_id == CommissionScheme.id)
        .where(
            SchemeAssignment.assignee_type == "user",
            SchemeAssignment.assignee_id == user_id,
            SchemeAssignment.deleted_at.is_(None),
            CommissionScheme.status == "active",
            CommissionScheme.deleted_at.is_(None),
            CommissionScheme.effective_from <= ref_date,
        )
    )
    scheme = result.scalar_one_or_none()
    if scheme:
        return scheme

    # Role-level
    from app.models.rbac import user_roles_table

    user_roles = (
        (
            await db.execute(
                select(user_roles_table.c.role_id).where(
                    user_roles_table.c.user_id == user_id
                )
            )
        )
        .scalars()
        .all()
    )

    if user_roles:
        result = await db.execute(
            select(CommissionScheme)
            .join(SchemeAssignment, SchemeAssignment.scheme_id == CommissionScheme.id)
            .where(
                SchemeAssignment.assignee_type == "role",
                SchemeAssignment.assignee_id.in_(list(user_roles)),
                SchemeAssignment.deleted_at.is_(None),
                CommissionScheme.status == "active",
                CommissionScheme.deleted_at.is_(None),
                CommissionScheme.effective_from <= ref_date,
            )
            .order_by(CommissionScheme.id.desc())
            .limit(1)
        )
        scheme = result.scalar_one_or_none()
        if scheme:
            return scheme

    # Default
    result = await db.execute(
        select(CommissionScheme)
        .where(
            CommissionScheme.is_default.is_(True),
            CommissionScheme.status == "active",
            CommissionScheme.deleted_at.is_(None),
            CommissionScheme.effective_from <= ref_date,
        )
        .limit(1)
    )
    return result.scalar_one_or_none()


def _match_tier(
    tiers: list[SchemeTier],
    base_amount: Decimal,
    product_category: str | None,
    customer_level: str | None,
) -> SchemeTier | None:
    """Find the first tier matching the conditions.

    Priority: product-specific > customer-level-specific > default.
    """
    # Try product + customer match first
    if product_category and customer_level:
        for t in tiers:
            if (
                t.product_category == product_category
                and t.customer_level == customer_level
            ):
                if t.low_amount <= base_amount and (
                    t.high_amount is None or base_amount < t.high_amount
                ):
                    return t

    # Try product match
    if product_category:
        for t in tiers:
            if t.product_category == product_category and not t.customer_level:
                if t.low_amount <= base_amount and (
                    t.high_amount is None or base_amount < t.high_amount
                ):
                    return t

    # Try customer level match
    if customer_level:
        for t in tiers:
            if t.customer_level == customer_level and not t.product_category:
                if t.low_amount <= base_amount and (
                    t.high_amount is None or base_amount < t.high_amount
                ):
                    return t

    # Default — no product/customer filter
    for t in tiers:
        if not t.product_category and not t.customer_level:
            if t.low_amount <= base_amount and (
                t.high_amount is None or base_amount < t.high_amount
            ):
                return t

    return None


async def _check_active_scheme_conflict(
    db: AsyncSession,
    user_id: int,
    effective_from: date,
    exclude_id: int | None = None,
) -> None:
    """Raise if the user already has an active scheme overlapping the dates."""
    query = (
        select(CommissionScheme)
        .join(SchemeAssignment, SchemeAssignment.scheme_id == CommissionScheme.id)
        .where(
            SchemeAssignment.assignee_type == "user",
            SchemeAssignment.assignee_id == user_id,
            SchemeAssignment.deleted_at.is_(None),
            CommissionScheme.status == "active",
            CommissionScheme.deleted_at.is_(None),
            CommissionScheme.effective_from <= effective_from,
        )
    )
    if exclude_id:
        query = query.where(CommissionScheme.id != exclude_id)

    existing = (await db.execute(query)).scalar_one_or_none()
    if existing:
        raise ConflictError(
            f"User {user_id} already has active scheme '{existing.name}' (id={existing.id})"
        )


# ── Scheme Simulation ──────────────────────────────────────────────────


async def simulate_scheme(
    db: AsyncSession,
    scheme_id: int,
    period_from: date,
    period_to: date,
    user_ids: list[int] | None = None,
) -> dict:
    """Run a what-if simulation comparing actual commissions vs scheme."""
    await get_scheme(db, scheme_id)

    from app.models.finance import Commission

    query = select(Commission).where(
        Commission.deleted_at.is_(None),
        Commission.created_at >= period_from,
        Commission.created_at <= period_to,
    )
    if user_ids:
        query = query.where(Commission.sales_user_id.in_(user_ids))

    rows = (await db.execute(query)).scalars().all()

    by_user_map: dict[int, dict] = {}
    for c in rows:
        uid = c.sales_user_id or 0
        if uid not in by_user_map:
            by_user_map[uid] = {
                "user_id": uid,
                "old_amount": Decimal("0"),
                "new_amount": Decimal("0"),
            }
        by_user_map[uid]["old_amount"] += c.commission_amount or Decimal("0")

        # Recompute with new scheme
        result = await compute_commission(
            db,
            uid,
            Decimal(str(c.base_amount or "0")),
            None,  # product_category - simplified
            None,  # customer_level - simplified
            c.period or "",
            period_from,
        )
        by_user_map[uid]["new_amount"] += result.amount

    by_user = sorted(by_user_map.values(), key=lambda x: x["old_amount"], reverse=True)
    total_old = sum(u["old_amount"] for u in by_user)
    total_new = sum(u["new_amount"] for u in by_user)

    summary = {
        "total_old": float(total_old),
        "total_new": float(total_new),
        "diff_amount": float(total_new - total_old),
        "diff_pct": float(
            round((total_new - total_old) / total_old * 100, 1) if total_old else 0
        ),
        "affected_users": len(by_user),
    }

    user_rows = []
    for u in by_user:
        diff_pct = (
            round((u["new_amount"] - u["old_amount"]) / u["old_amount"] * 100, 1)
            if u["old_amount"]
            else Decimal("0")
        )
        flag = "red" if abs(diff_pct) > 20 else "normal"
        user_rows.append(
            {
                "user_id": u["user_id"],
                "name": f"user_{u['user_id']}",  # Simplified; can join users table
                "old_amount": float(u["old_amount"]),
                "new_amount": float(u["new_amount"]),
                "diff_pct": float(diff_pct),
                "flag": flag,
            }
        )

    return {"summary": summary, "by_user": user_rows}


async def auto_expire_schemes(db: AsyncSession) -> int:
    """Cron task: mark schemes as expired when effective_to is past.

    Returns count of expired schemes.
    """
    today = _today()
    result = await db.execute(
        select(CommissionScheme).where(
            CommissionScheme.status == "active",
            CommissionScheme.effective_to.isnot(None),
            CommissionScheme.effective_to < today,
            CommissionScheme.deleted_at.is_(None),
        )
    )
    schemes = result.scalars().all()
    for s in schemes:
        s.status = "expired"
        logger.info("Scheme %s (id=%s) auto-expired", s.name, s.id)
    await db.commit()
    return len(schemes)


async def list_versions(db: AsyncSession, scheme_id: int) -> list[SchemeVersion]:
    """Get version history for a scheme."""
    result = await db.execute(
        select(SchemeVersion)
        .where(SchemeVersion.scheme_id == scheme_id)
        .order_by(SchemeVersion.version_no.desc())
    )
    return list(result.scalars().all())
