"""link customer follow-ups to opportunities

Revision ID: 0017
Revises: 0016
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "0017"
down_revision: Union[str, None] = "0016"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "customer_follow_ups",
        sa.Column("opportunity_id", sa.Integer(), nullable=True),
    )
    op.create_foreign_key(
        "fk_customer_follow_ups_opportunity_id",
        "customer_follow_ups",
        "opportunities",
        ["opportunity_id"],
        ["id"],
    )
    op.create_index(
        "ix_customer_follow_ups_opportunity_id",
        "customer_follow_ups",
        ["opportunity_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_customer_follow_ups_opportunity_id", table_name="customer_follow_ups")
    op.drop_constraint(
        "fk_customer_follow_ups_opportunity_id",
        "customer_follow_ups",
        type_="foreignkey",
    )
    op.drop_column("customer_follow_ups", "opportunity_id")
