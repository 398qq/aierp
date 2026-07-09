"""Regression tests for app.database.date_format.

The function must generate SQL that PostgreSQL accepts. Earlier versions
used `sqlalchemy.type_coerce` which produced SQL like
``substr(timestamp_col, 1, 7)`` — invalid on PostgreSQL because the
3-argument ``substr`` overload does not exist for timestamp / date.
The fix uses ``func.cast(col, String)`` so PostgreSQL generates
``CAST(col AS VARCHAR)`` and SQLite generates ``CAST(col AS VARCHAR)``
— both accepted.
"""

import pytest
from sqlalchemy import Column, Date, DateTime, Integer, MetaData, Table, select
from sqlalchemy.dialects import postgresql, sqlite

from app.database import date_format


metadata = MetaData()

_T = Table(
    "_test_date_format",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("d", Date),
    Column("ts", DateTime),
)


@pytest.mark.parametrize(
    "dialect_name, dialect",
    [("postgresql", postgresql.dialect()), ("sqlite", sqlite.dialect())],
)
@pytest.mark.parametrize("fmt", ["YYYY-MM", "YYYYMM", "YYYY"])
def test_date_format_generates_cast_for_postgres(dialect_name, dialect, fmt):
    """Both Date and DateTime columns must be wrapped with CAST(... AS VARCHAR)."""
    expr = date_format(_T.c.d, fmt)
    sql = str(select(expr).compile(dialect=dialect))
    assert "CAST(" in sql.upper() or "::" in sql, (
        f"[{dialect_name}] date_format({fmt}) must generate a CAST; got: {sql}"
    )
    assert "SUBSTR(" in sql.upper(), (
        f"[{dialect_name}] date_format must wrap substr; got: {sql}"
    )


@pytest.mark.parametrize("col", [_T.c.d, _T.c.ts])
def test_date_format_works_with_both_date_and_timestamp(col):
    """Both Date and DateTime must work (PG used to fail on DateTime)."""
    sql_pg = str(
        select(date_format(col, "YYYY-MM")).compile(dialect=postgresql.dialect())
    )
    sql_sqlite = str(
        select(date_format(col, "YYYY-MM")).compile(dialect=sqlite.dialect())
    )
    assert "CAST(" in sql_pg.upper() or "::" in sql_pg
    assert "CAST(" in sql_sqlite.upper() or "::" in sql_sqlite


def test_date_format_yyyymm_concatenates():
    """YYYYMM must concatenate chars 1-4 and 6-2 of the cast text."""
    sql = str(
        select(date_format(_T.c.d, "YYYYMM")).compile(dialect=postgresql.dialect())
    )
    # Expect two substr calls concatenated
    assert sql.upper().count("SUBSTR(") == 2
    assert "||" in sql


def test_date_format_yyyy_uses_chars_1_to_4():
    """YYYY format must call substr with length 4 (year = 4 chars)."""
    stmt = select(date_format(_T.c.d, "YYYY"))
    compiled = stmt.compile(dialect=postgresql.dialect())
    # bind params are placeholders; inspect construct params instead
    params = compiled.params
    # 1 and 4 must appear as positional bind values for substr
    assert 1 in params.values(), f"expected offset 1 in params, got: {params}"
    assert 4 in params.values(), f"expected length 4 in params, got: {params}"
    assert "SUBSTR(" in str(compiled).upper()


def test_date_format_unknown_fmt_returns_cast_unchanged():
    """Unknown format returns the cast expression unmodified (graceful fallback)."""
    sql = str(
        select(date_format(_T.c.d, "UNKNOWN")).compile(dialect=postgresql.dialect())
    )
    assert "CAST(" in sql.upper()
