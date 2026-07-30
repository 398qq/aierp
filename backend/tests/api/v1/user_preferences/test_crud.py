"""Tests for /user-preferences CRUD.

Spec: docs/frontend/products-page-design.md §4.1, §5.1
"""
import json

import pytest
from httpx import AsyncClient


async def _put_pref(
    client: AsyncClient, headers: dict, scope: str, key: str, value
):
    return await client.put(
        f"/api/v1/user-preferences/{scope}/{key}",
        headers=headers,
        json={"scope": scope, "key": key, "value": json.dumps(value)},
    )


class TestUserPreferencesScope:
    """List and upsert are scoped to the authenticated user only."""

    async def test_list_empty_when_no_prefs(
        self, async_client: AsyncClient, auth_headers: dict
    ):
        resp = await async_client.get(
            "/api/v1/user-preferences/products", headers=auth_headers,
        )
        assert resp.status_code == 200
        assert resp.json()["data"] == {"items": []}

    async def test_upsert_then_list(
        self, async_client: AsyncClient, auth_headers: dict
    ):
        await _put_pref(async_client, auth_headers, "products",
                          "column_visibility", {"amount": False})
        await _put_pref(async_client, auth_headers, "products",
                          "saved_views", [{"name": "default"}])
        await _put_pref(async_client, auth_headers, "other", "x", "y")

        resp = await async_client.get(
            "/api/v1/user-preferences/products", headers=auth_headers,
        )
        body = resp.json()
        assert resp.status_code == 200
        items = {it["key"]: it["value"] for it in body["data"]["items"]}
        assert set(items) == {"column_visibility", "saved_views"}
        assert json.loads(items["column_visibility"]) == {"amount": False}
        assert json.loads(items["saved_views"]) == [{"name": "default"}]

        # "other" scope is NOT included — scope filter works
        resp_other = await async_client.get(
            "/api/v1/user-preferences/other", headers=auth_headers,
        )
        other = resp_other.json()["data"]["items"]
        assert [it["key"] for it in other] == ["x"]

    async def test_upsert_idempotent(
        self, async_client: AsyncClient, auth_headers: dict
    ):
        v1 = {"a": 1}
        v2 = {"a": 2}
        r1 = await _put_pref(async_client, auth_headers, "s", "k", v1)
        r2 = await _put_pref(async_client, auth_headers, "s", "k", v2)
        assert r1.status_code == 200
        assert r2.status_code == 200

        # list returns one row (not two) with the latest value
        listed = await async_client.get(
            "/api/v1/user-preferences/s", headers=auth_headers,
        )
        items = listed.json()["data"]["items"]
        assert len(items) == 1
        assert json.loads(items[0]["value"]) == v2

    async def test_upsert_path_body_mismatch_returns_400(
        self, async_client: AsyncClient, auth_headers: dict
    ):
        resp = await async_client.put(
            "/api/v1/user-preferences/scope1/key1",
            headers=auth_headers,
            json={"scope": "scope2", "key": "key1", "value": "x"},
        )
        assert resp.status_code == 400

        resp2 = await async_client.put(
            "/api/v1/user-preferences/scope1/key1",
            headers=auth_headers,
            json={"scope": "scope1", "key": "key2", "value": "x"},
        )
        assert resp2.status_code == 400


class TestUserPreferencesDelete:
    async def test_delete_soft_deletes(
        self, async_client: AsyncClient, auth_headers: dict
    ):
        await _put_pref(async_client, auth_headers, "s", "k", "v")

        deleted = await async_client.delete(
            "/api/v1/user-preferences/s/k", headers=auth_headers,
        )
        assert deleted.status_code == 200

        # After delete, list returns empty
        listed = await async_client.get(
            "/api/v1/user-preferences/s", headers=auth_headers,
        )
        assert listed.json()["data"]["items"] == []

    async def test_delete_missing_returns_404(
        self, async_client: AsyncClient, auth_headers: dict
    ):
        resp = await async_client.delete(
            "/api/v1/user-preferences/s/k", headers=auth_headers,
        )
        assert resp.status_code == 404

    async def test_soft_deleted_excluded_from_list(
        self, async_client: AsyncClient, auth_headers: dict
    ):
        await _put_pref(async_client, auth_headers, "s", "k1", "v1")
        await _put_pref(async_client, auth_headers, "s", "k2", "v2")
        await async_client.delete(
            "/api/v1/user-preferences/s/k1", headers=auth_headers,
        )

        listed = await async_client.get(
            "/api/v1/user-preferences/s", headers=auth_headers,
        )
        keys = [it["key"] for it in listed.json()["data"]["items"]]
        assert keys == ["k2"]


class TestUserPreferencesAuth:
    async def test_list_requires_auth(
        self, async_client: AsyncClient
    ):
        resp = await async_client.get("/api/v1/user-preferences/products")
        assert resp.status_code in (401, 403)

    async def test_upsert_requires_auth(
        self, async_client: AsyncClient
    ):
        resp = await async_client.put(
            "/api/v1/user-preferences/s/k",
            json={"scope": "s", "key": "k", "value": "v"},
        )
        assert resp.status_code in (401, 403)
