"""allow unscheduled customer follow-ups

Revision ID: 0010
Revises: 0009

The application model, schemas, and follow-up ledger all support an
unscheduled state, but older PostgreSQL schemas retained a NOT NULL
constraint on ``customer_follow_ups.planned_at``.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "0010"
down_revision: Union[str, None] = "0009"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column(
        "customer_follow_ups",
        "planned_at",
        existing_type=sa.DateTime(timezone=True),
        nullable=True,
    )


def downgrade() -> None:
    # Preserve rows created as unscheduled before restoring the legacy
    # constraint. ``created_at`` is the least surprising fallback date.
    op.execute(
        "UPDATE customer_follow_ups "
        "SET planned_at = created_at "
        "WHERE planned_at IS NULL"
    )
    op.alter_column(
        "customer_follow_ups",
        "planned_at",
        existing_type=sa.DateTime(timezone=True),
        nullable=False,
    )
