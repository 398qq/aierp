import datetime

import pytest
from sqlalchemy import text

from app.models.uom import UomDict


@pytest.mark.integration
async def test_uom_seed_migration_is_idempotent(engine, create_tables):
    if engine.dialect.name != "postgresql":
        pytest.skip("The production seed migration is PostgreSQL-specific")

    from app.database import _ensure_uom_schema

    await _ensure_uom_schema(engine)
    await _ensure_uom_schema(engine)

    async with engine.connect() as connection:
        count = await connection.scalar(text("SELECT count(*) FROM uom_dict"))
    assert count == 34


@pytest.mark.integration
async def test_list_uoms_filters_deleted_and_type(async_client, db_session):
    db_session.add_all(
        [
            UomDict(code="PCS", name="个", uom_type="count", category="count", sort_order=2),
            UomDict(code="EA", name="件", uom_type="count", category="count", sort_order=1),
            UomDict(code="REEL", name="盘装", uom_type="package", category="reel", sort_order=3),
            UomDict(
                code="OLD",
                name="已停用",
                uom_type="count",
                category="count",
                sort_order=0,
                deleted_at=datetime.datetime.now(datetime.timezone.utc),
            ),
        ]
    )
    await db_session.flush()

    response = await async_client.get("/api/v1/uoms", params={"uom_type": "count"})

    assert response.status_code == 200
    assert [item["code"] for item in response.json()["data"]] == ["EA", "PCS"]

    invalid = await async_client.get("/api/v1/uoms", params={"uom_type": "weight"})
    assert invalid.status_code == 422


@pytest.mark.integration
async def test_get_uom_and_missing_uom(async_client, db_session):
    db_session.add(
        UomDict(code="TRAY", name="托盘装", uom_type="package", category="tray")
    )
    await db_session.flush()

    response = await async_client.get("/api/v1/uoms/TRAY")
    missing = await async_client.get("/api/v1/uoms/UNKNOWN")

    assert response.status_code == 200
    assert response.json()["data"] == {
        "code": "TRAY",
        "name": "托盘装",
        "uom_type": "package",
        "category": "tray",
        "sort_order": 0,
    }
    assert missing.status_code == 404
