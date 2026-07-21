"""add composite index on inventory_transactions for Stage 18 query patterns

Stage 18 P0–P5 hot queries all filter by (product_id, warehouse_id) and order
by created_at DESC (e.g. expiry scan, traceability upstream/downstream,
transfer src/dst, recall consumption, merge/split audit transactions).

Before this migration only ``batch_id`` was indexed, forcing sequential
scans on (product_id, warehouse_id) filters across the whole table.

Revision ID: 0019
Revises: 0018
"""

from typing import Sequence, Union

from alembic import op


revision: str = "0019"
down_revision: Union[str, None] = "0018"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_index(
        "ix_inventory_transactions_prod_wh_created",
        "inventory_transactions",
        ["product_id", "warehouse_id", "created_at"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_inventory_transactions_prod_wh_created",
        table_name="inventory_transactions",
    )