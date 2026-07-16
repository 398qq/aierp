"""add product price and cost controls

Revision ID: 0016
Revises: 0015
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0016"
down_revision: Union[str, None] = "0015"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "products", sa.Column("minimum_sale_price", sa.DECIMAL(20, 6), nullable=True)
    )
    op.add_column(
        "products",
        sa.Column("price_valid_from", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "products",
        sa.Column("price_valid_to", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "products", sa.Column("latest_purchase_cost", sa.DECIMAL(20, 6), nullable=True)
    )
    op.add_column(
        "products", sa.Column("weighted_avg_cost", sa.DECIMAL(20, 6), nullable=True)
    )
    op.add_column(
        "products",
        sa.Column("cost_updated_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    for name in (
        "cost_updated_at",
        "weighted_avg_cost",
        "latest_purchase_cost",
        "price_valid_to",
        "price_valid_from",
        "minimum_sale_price",
    ):
        op.drop_column("products", name)
