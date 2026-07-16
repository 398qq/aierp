"""link invoices to delivery notes for partial invoicing

Revision ID: 0011
Revises: 0010
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0011"
down_revision: Union[str, None] = "0010"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("invoices", sa.Column("delivery_note_id", sa.Integer(), nullable=True))
    op.create_foreign_key(
        "fk_invoices_delivery_note_id",
        "invoices",
        "delivery_notes",
        ["delivery_note_id"],
        ["id"],
    )
    op.create_index("ix_invoices_delivery_note_id", "invoices", ["delivery_note_id"])


def downgrade() -> None:
    op.drop_index("ix_invoices_delivery_note_id", table_name="invoices")
    op.drop_constraint("fk_invoices_delivery_note_id", "invoices", type_="foreignkey")
    op.drop_column("invoices", "delivery_note_id")
