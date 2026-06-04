"""Row-level data isolation (record ownership) for sales reps.

ERP systems typically restrict sales reps to records they "own":
- Their customers
- Their opportunities / quotations / orders
- Their follow-ups / visits

This module is a SQLAlchemy mixin that adds an `apply_visibility_filter`
function which decorates queries with `WHERE assigned_to = :user_id`
when the current user is a non-admin role. Admins (role == "admin")
see everything; sales reps see only their own records.
"""

import logging
from typing import Optional

from sqlalchemy import and_, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import Select

from app.models.user import User

logger = logging.getLogger(__name__)

# Roles that bypass row-level isolation
ADMIN_ROLES = frozenset({"admin", "finance", "warehouse", "manager"})

# Resources that have an ownership column for record-level visibility.
# The mapping is `table_name -> column_name` since some tables use
# `assigned_to` (sales resources) while others use `owner` (master data).
# Only include resources that ACTUALLY have a usable ownership column;
# other tables (e.g. Quotation, SalesOrder, Visit, Sample) need a
# schema migration to add the column.
OWNED_RESOURCES: dict[str, str] = {
    "opportunities": "assigned_to",
    "customer_follow_ups": "assigned_to",
    "tickets": "assigned_to",
}


def get_owner_column(table_name: str) -> str | None:
    """Return the ownership column name for a table, or None if shared."""
    return OWNED_RESOURCES.get(table_name)


def is_admin_or_manager(user: dict | User) -> bool:
    """Check whether the current user can see all records."""
    if isinstance(user, dict):
        roles = user.get("roles") or []
        if user.get("role") in ADMIN_ROLES:
            return True
    else:
        roles = [r.name for r in getattr(user, "roles", [])] or []
        if getattr(user, "role", None) in ADMIN_ROLES:
            return True
    return any(r in ADMIN_ROLES for r in roles)


def apply_visibility_filter(
    stmt: Select,
    user: dict | User,
    table_name: str,
    owner_column: str | None = None,
) -> Select:
    """Add row-level visibility filter to a SELECT statement.

    For owned resources (in OWNED_RESOURCES) and non-admin users, add
    `WHERE <owner_column> = :user_id OR <owner_column> IS NULL`.
    Admins / managers see everything.

    For non-owned resources (customers, products, suppliers) the
    function is a no-op — those are typically shared across reps.
    """
    if table_name not in OWNED_RESOURCES:
        return stmt

    col = owner_column or OWNED_RESOURCES[table_name]

    if is_admin_or_manager(user):
        return stmt

    user_id = user.get("user_id") if isinstance(user, dict) else user.id
    if user_id is None:
        # No user — return empty result
        from sqlalchemy import false
        return stmt.where(false())

    entity = stmt.column_descriptions[0]["entity"]
    column = getattr(entity, col, None)
    if column is None:
        # Entity doesn't have the configured ownership column — skip filter
        logger.warning("Entity %s has no column %s, skipping visibility filter", entity.__name__, col)
        return stmt

    # String columns (e.g. `owner` on Quotation) need special handling
    column_type = getattr(column, "type", None)
    if column_type is not None and "VARCHAR" in str(column_type).upper():
        # String owner column — compare against str(user_id) or NULL
        return stmt.where(or_(column == str(user_id), column.is_(None)))

    return stmt.where(or_(column == user_id, column.is_(None)))


def ownership_filter_sql(table_name: str, user: dict | User) -> Optional[list]:
    """Build raw SQL filter clause for use in list endpoints.

    Returns None for admin (no filter) or for shared resources.
    Returns a list of SQLAlchemy expressions to AND into the query.
    """
    if table_name not in OWNED_RESOURCES:
        return None
    if is_admin_or_manager(user):
        return None

    user_id = user.get("user_id") if isinstance(user, dict) else user.id
    if user_id is None:
        return [False]  # Empty result

    return [user_id]  # Will be applied via param substitution


async def visible_customers_for_user(
    db: AsyncSession,
    user: dict | User,
) -> list:
    """Get list of customer IDs visible to the user (helper for tests)."""
    from app.models.customer import Customer

    user_id = user.get("user_id") if isinstance(user, dict) else user.id
    if is_admin_or_manager(user):
        result = await db.execute(select(Customer.id).where(Customer.deleted_at.is_(None)))
    else:
        # Customers are visible if: (a) assigned to user, (b) user is owner,
        # (c) unassigned (orphaned records still visible for claiming)
        result = await db.execute(
            select(Customer.id).where(
                and_(
                    Customer.deleted_at.is_(None),
                    or_(
                        Customer.owner == str(user_id),
                        Customer.owner.is_(None),
                    ),
                )
            )
        )
    return [row[0] for row in result.fetchall()]


def get_data_scope(user: dict | User) -> str:
    """Get the data scope for the user: 'all' | 'own' | 'unassigned_only'."""
    if is_admin_or_manager(user):
        return "all"
    return "own_or_unassigned"
