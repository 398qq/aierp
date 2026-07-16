"""add professional contract business terms

Revision ID: 0014
Revises: 0013
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0014"
down_revision: Union[str, None] = "0013"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    for name, column in (
        ("delivery_address", sa.Text()),
        ("delivery_terms", sa.Text()),
        ("payment_terms", sa.Text()),
        ("acceptance_terms", sa.Text()),
        ("warranty_terms", sa.Text()),
        ("dispute_terms", sa.Text()),
        ("invoice_type", sa.String(length=30)),
    ):
        op.add_column("contracts", sa.Column(name, column, nullable=True))


def downgrade() -> None:
    for name in (
        "invoice_type",
        "dispute_terms",
        "warranty_terms",
        "acceptance_terms",
        "payment_terms",
        "delivery_terms",
        "delivery_address",
    ):
        op.drop_column("contracts", name)
