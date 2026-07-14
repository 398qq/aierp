"""add product datecode and quotation delivery fields

Revision ID: 0009
Revises: 0008
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "0009"
down_revision: Union[str, None] = "0008"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "products",
        sa.Column("datecode", sa.String(length=100), nullable=True),
    )
    op.add_column(
        "quotation_items",
        sa.Column("datecode", sa.String(length=100), nullable=True),
    )
    op.add_column(
        "quotation_items",
        sa.Column("lead_time", sa.String(length=100), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("quotation_items", "lead_time")
    op.drop_column("quotation_items", "datecode")
    op.drop_column("products", "datecode")
