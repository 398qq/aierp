"""add payment allocation ledger

Revision ID: 0012
Revises: 0011
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0012"
down_revision: Union[str, None] = "0011"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column("payment_records", "sales_order_id", existing_type=sa.Integer(), nullable=True)
    # Some development installations run Base.metadata.create_all() during
    # hot reload. Preserve a table created by that path instead of failing the
    # versioned migration; production databases normally take the create path.
    if not sa.inspect(op.get_bind()).has_table("payment_allocations"):
        op.create_table(
            "payment_allocations",
            sa.Column("payment_id", sa.Integer(), nullable=False),
            sa.Column("invoice_id", sa.Integer(), nullable=False),
            sa.Column("sales_order_id", sa.Integer(), nullable=False),
            sa.Column("amount", sa.DECIMAL(20, 6), nullable=False),
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
            sa.ForeignKeyConstraint(["payment_id"], ["payment_records.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["invoice_id"], ["invoices.id"]),
            sa.ForeignKeyConstraint(["sales_order_id"], ["sales_orders.id"]),
            sa.CheckConstraint("amount > 0", name="ck_payment_allocations_amount_positive"),
            sa.UniqueConstraint("payment_id", "invoice_id", name="uq_payment_allocation_payment_invoice"),
        )
        op.create_index("ix_payment_allocations_payment_id", "payment_allocations", ["payment_id"])
        op.create_index("ix_payment_allocations_invoice_id", "payment_allocations", ["invoice_id"])


def downgrade() -> None:
    op.drop_table("payment_allocations")
    op.alter_column("payment_records", "sales_order_id", existing_type=sa.Integer(), nullable=False)
