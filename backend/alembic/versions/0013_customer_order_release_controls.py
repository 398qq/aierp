"""add customer order release controls

Revision ID: 0013
Revises: 0012
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0013"
down_revision: Union[str, None] = "0012"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "customers",
        sa.Column("contract_required", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.add_column(
        "customers",
        sa.Column("credit_control_enabled", sa.Boolean(), nullable=False, server_default=sa.false()),
    )


def downgrade() -> None:
    op.drop_column("customers", "credit_control_enabled")
    op.drop_column("customers", "contract_required")
