"""Stage 8 Day 2: per-user commission rate on sales_targets.

Adds commission_rate column (0.0–1.0, e.g. 0.05 = 5%) to sales_targets
so each sales user can have a custom rate per period.

Down revision: 0005
"""

from alembic import op
import sqlalchemy as sa

revision = "0006"
down_revision = "0005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "sales_targets",
        sa.Column(
            "commission_rate",
            sa.Numeric(8, 4),
            nullable=True,
            comment="Per-user commission rate (e.g. 0.05 = 5%)",
        ),
    )
    # Default for existing rows: 5% (matches commission_listener hardcoded default)
    op.execute("UPDATE sales_targets SET commission_rate = 0.05 WHERE commission_rate IS NULL")
    # Make non-nullable for new rows (existing rows already have 0.05)
    op.alter_column("sales_targets", "commission_rate", nullable=False)
    op.create_check_constraint(
        "ck_sales_targets_commission_rate_range",
        "sales_targets",
        "commission_rate >= 0 AND commission_rate <= 1",
    )


def downgrade() -> None:
    op.drop_constraint("ck_sales_targets_commission_rate_range", "sales_targets", type_="check")
    op.drop_column("sales_targets", "commission_rate")
