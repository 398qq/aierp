"""critical indexes — 100+ performance indexes on hot-path columns

This migration consolidates migrations/008_critical_indexes.sql into a
proper Alembic migration so it can be tracked in version control.

The same SQL is also still applied automatically at startup via
_ensure_critical_indexes() in app/database.py, ensuring self-healing
deployments. Alembic just gives a clean migration history.

Run: alembic upgrade head
"""

from alembic import op

# revision identifiers, used by Alembic.
revision = "0002_critical_indexes"
down_revision = "0001_baseline"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Apply all critical indexes from migrations/008_critical_indexes.sql.

    The SQL is split on `;` and each statement is executed separately.
    This is safe because every statement is idempotent
    (`CREATE INDEX IF NOT EXISTS`).
    """
    import pathlib
    sql_path = (
        pathlib.Path(__file__).resolve().parents[2]
        / "migrations" / "008_critical_indexes.sql"
    )
    sql = sql_path.read_text()
    for stmt in sql.split(";"):
        stmt = stmt.strip()
        if not stmt or stmt.startswith("--"):
            continue
        op.execute(stmt + ";")


def downgrade() -> None:
    """Drop all indexes created by 008_critical_indexes.sql.

    For rollback safety, drops are best-effort (one failure should not
    block the rest). In production, prefer restoring from a backup
    rather than running this downgrade.
    """
    import pathlib
    sql_path = (
        pathlib.Path(__file__).resolve().parents[2]
        / "migrations" / "008_critical_indexes.sql"
    )
    # Extract index names
    sql = sql_path.read_text()
    import re
    index_names = re.findall(
        r"CREATE\s+(?:UNIQUE\s+)?INDEX\s+IF\s+NOT\s+EXISTS\s+(\w+)",
        sql,
        re.IGNORECASE,
    )
    for name in index_names:
        try:
            op.execute(f"DROP INDEX IF EXISTS {name};")
        except Exception:
            pass
