"""Tests for /audit/field-changes/export.csv (Stage 12 Day 3)."""

import csv
import io

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import Base


@pytest_asyncio.fixture
async def sample_data(db_session: AsyncSession):
    """Insert sample field change logs."""
    from app.models.audit import FieldChangeLog

    items = []
    for i in range(3):
        c = FieldChangeLog(
            table_name="customer",
            record_id=42,
            field_name="email",
            old_value=f"old{i}@x.com",
            new_value=f"new{i}@x.com",
            actor="alice",
            reason="user request",
        )
        db_session.add(c)
        items.append(c)
    await db_session.commit()
    return items


@pytest.mark.asyncio
async def test_csv_export_returns_csv_response(db_session: AsyncSession, sample_data):
    """Endpoint returns text/csv with content-disposition header."""
    from app.main import app
    from app.api.deps import get_current_user
    from app.database import get_db

    # Override auth to skip JWT
    async def mock_user():
        return {"id": 1, "username": "tester"}

    app.dependency_overrides[get_current_user] = mock_user
    app.dependency_overrides[get_db] = lambda: (yield db_session)

    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            resp = await client.get(
                "/api/v1/audit/field-changes/export.csv",
                params={"table_name": "customer", "days_back": 30},
            )
        assert resp.status_code == 200
        assert "text/csv" in resp.headers["content-type"]
        assert "attachment" in resp.headers["content-disposition"]
        assert ".csv" in resp.headers["content-disposition"]
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_csv_export_includes_all_columns(db_session: AsyncSession, sample_data):
    """CSV body has header + 3 data rows with all expected columns."""
    from app.main import app
    from app.api.deps import get_current_user
    from app.database import get_db

    async def mock_user():
        return {"id": 1, "username": "tester"}

    app.dependency_overrides[get_current_user] = mock_user
    app.dependency_overrides[get_db] = lambda: (yield db_session)

    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            resp = await client.get(
                "/api/v1/audit/field-changes/export.csv",
                params={"table_name": "customer", "days_back": 30},
            )
        reader = csv.reader(io.StringIO(resp.text))
        rows = list(reader)
        assert len(rows) == 4  # 1 header + 3 data
        assert rows[0] == [
            "id", "changed_at", "table_name", "record_id",
            "field_name", "old_value", "new_value", "actor", "reason",
        ]
        # Data rows: new values are like "new0@x.com", "new1@x.com", "new2@x.com"
        new_values = [r[6] for r in rows[1:]]
        assert "new0@x.com" in new_values
        assert "new1@x.com" in new_values
        assert "new2@x.com" in new_values
        # actor column
        assert all(r[7] == "alice" for r in rows[1:])
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_csv_export_filters(db_session: AsyncSession, sample_data):
    """Filter by actor works."""
    from app.main import app
    from app.api.deps import get_current_user
    from app.database import get_db
    from app.models.audit import FieldChangeLog

    # Add a different-actor row
    db_session.add(FieldChangeLog(
        table_name="customer", record_id=99, field_name="phone",
        old_value="111", new_value="222", actor="bob",
    ))
    await db_session.commit()

    async def mock_user():
        return {"id": 1, "username": "tester"}

    app.dependency_overrides[get_current_user] = mock_user
    app.dependency_overrides[get_db] = lambda: (yield db_session)

    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            resp = await client.get(
                "/api/v1/audit/field-changes/export.csv",
                params={"actor": "bob", "days_back": 30},
            )
        reader = csv.reader(io.StringIO(resp.text))
        rows = list(reader)
        # 1 header + 1 bob row
        assert len(rows) == 2
        assert rows[1][7] == "bob"  # actor
        assert rows[1][3] == "99"   # record_id (CSV stores as str)
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_csv_export_empty_returns_header_only(db_session: AsyncSession):
    """No matching rows → CSV with header only (no 404)."""
    from app.main import app
    from app.api.deps import get_current_user
    from app.database import get_db

    async def mock_user():
        return {"id": 1, "username": "tester"}

    app.dependency_overrides[get_current_user] = mock_user
    app.dependency_overrides[get_db] = lambda: (yield db_session)

    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            resp = await client.get(
                "/api/v1/audit/field-changes/export.csv",
                params={"table_name": "nonexistent_table", "days_back": 30},
            )
        assert resp.status_code == 200
        reader = csv.reader(io.StringIO(resp.text))
        rows = list(reader)
        assert len(rows) == 1  # header only
        assert rows[0][0] == "id"  # header row
    finally:
        app.dependency_overrides.clear()
