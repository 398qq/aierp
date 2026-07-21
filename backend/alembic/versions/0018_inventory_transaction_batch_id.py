"""add batch_id to inventory_transactions for per-batch traceability

Stage 18 / Production Batch Management.
Historical transactions (pre-Stage 18) leave batch_id NULL — forward
traceability is opt-in by nature.

Revision ID: 0018
Revises: 0017
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "0018"
down_revision: Union[str, None] = "0017"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "inventory_transactions",
        sa.Column("batch_id", sa.Integer(), nullable=True),
    )
    op.create_foreign_key(
        "fk_inventory_transactions_batch_id",
        "inventory_transactions",
        "inventory_batches",
        ["batch_id"],
        ["id"],
    )
    op.create_index(
        "ix_inventory_transactions_batch_id",
        "inventory_transactions",
        ["batch_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_inventory_transactions_batch_id", table_name="inventory_transactions")
    op.drop_constraint(
        "fk_inventory_transactions_batch_id",
        "inventory_transactions",
        type_="foreignkey",
    )
    op.drop_column("inventory_transactions", "batch_id")