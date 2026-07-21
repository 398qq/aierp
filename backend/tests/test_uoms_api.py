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
    data = response.json()["data"]
    assert data["code"] == "TRAY"
    assert data["name"] == "托盘装"
    assert data["uom_type"] == "package"
    assert data["category"] == "tray"
    assert data["sort_order"] == 0
    assert missing.status_code == 404


@pytest.mark.integration
async def test_create_uom(async_client, db_session, auth_headers):
    response = await async_client.post(
        "/api/v1/uoms",
        json={"code": "BTL", "name": "瓶", "uom_type": "package", "category": "container", "sort_order": 10},
        headers=auth_headers,
    )
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["code"] == "BTL"
    assert data["name"] == "瓶"
    assert data["uom_type"] == "package"

    # Verify it persisted
    get_resp = await async_client.get("/api/v1/uoms/BTL")
    assert get_resp.status_code == 200


@pytest.mark.integration
async def test_create_uom_duplicate(async_client, db_session, auth_headers):
    db_session.add(UomDict(code="BOX", name="箱", uom_type="package", category="box"))
    await db_session.flush()

    response = await async_client.post(
        "/api/v1/uoms",
        json={"code": "BOX", "name": "箱", "uom_type": "package"},
        headers=auth_headers,
    )
    assert response.status_code == 409


@pytest.mark.integration
async def test_create_uom_requires_auth(async_client, db_session):
    response = await async_client.post(
        "/api/v1/uoms",
        json={"code": "BTL", "name": "瓶", "uom_type": "package"},
    )
    assert response.status_code == 401


@pytest.mark.integration
async def test_update_uom(async_client, db_session, auth_headers):
    db_session.add(
        UomDict(code="MODULE", name="模块", uom_type="count", category="unit", sort_order=5)
    )
    await db_session.flush()

    response = await async_client.put(
        "/api/v1/uoms/MODULE",
        json={"name": "模组", "sort_order": 6},
        headers=auth_headers,
    )
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["name"] == "模组"
    assert data["sort_order"] == 6


@pytest.mark.integration
async def test_update_uom_not_found(async_client, db_session, auth_headers):
    response = await async_client.put(
        "/api/v1/uoms/NONEXIST",
        json={"name": "不存在"},
        headers=auth_headers,
    )
    assert response.status_code == 404


@pytest.mark.integration
async def test_soft_delete_uom(async_client, db_session, auth_headers):
    db_session.add(
        UomDict(code="DRUM", name="桶", uom_type="package", category="container")
    )
    await db_session.flush()

    response = await async_client.delete(
        "/api/v1/uoms/DRUM",
        headers=auth_headers,
    )
    assert response.status_code == 200

    # Verify soft-deleted — no longer in list
    list_resp = await async_client.get("/api/v1/uoms")
    assert all(item["code"] != "DRUM" for item in list_resp.json()["data"])


@pytest.mark.integration
async def test_delete_uom_not_found(async_client, db_session, auth_headers):
    response = await async_client.delete(
        "/api/v1/uoms/NONEXIST",
        headers=auth_headers,
    )
    assert response.status_code == 404
