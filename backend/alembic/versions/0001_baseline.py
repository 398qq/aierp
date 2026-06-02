"""initial baseline — mark current schema as the migration starting point

This empty migration records the state of the database BEFORE the
critical_indexes migration. Running `alembic stamp head` against an
existing database that has all the 008_critical_indexes.sql applied
will mark it as up-to-date.

Run: cd backend && alembic stamp head
"""

# revision identifiers, used by Alembic.
revision = "0001_baseline"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # No-op: this migration only records the baseline.
    pass


def downgrade() -> None:
    pass
