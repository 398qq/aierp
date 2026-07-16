"""add product master data controls

Revision ID: 0015
Revises: 0014
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0015"
down_revision: Union[str, None] = "0014"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "products",
        sa.Column("status", sa.String(20), nullable=False, server_default="active"),
    )
    op.add_column(
        "products",
        sa.Column(
            "product_type",
            sa.String(30),
            nullable=False,
            server_default="finished_good",
        ),
    )
    op.add_column("products", sa.Column("owner", sa.String(100), nullable=True))
    op.add_column(
        "products", sa.Column("default_warehouse_id", sa.Integer(), nullable=True)
    )
    op.create_foreign_key(
        "fk_products_default_warehouse",
        "products",
        "warehouses",
        ["default_warehouse_id"],
        ["id"],
    )
    op.add_column(
        "products",
        sa.Column(
            "batch_control", sa.Boolean(), nullable=False, server_default=sa.false()
        ),
    )
    op.add_column(
        "products",
        sa.Column(
            "serial_control", sa.Boolean(), nullable=False, server_default=sa.false()
        ),
    )
    op.add_column(
        "products",
        sa.Column(
            "shelf_life_control",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
    )


def downgrade() -> None:
    op.drop_constraint("fk_products_default_warehouse", "products", type_="foreignkey")
    for name in (
        "shelf_life_control",
        "serial_control",
        "batch_control",
        "default_warehouse_id",
        "owner",
        "product_type",
        "status",
    ):
        op.drop_column("products", name)
