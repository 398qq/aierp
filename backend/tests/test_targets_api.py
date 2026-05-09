"""Sales targets API tests."""
from httpx import AsyncClient


class TestTargets:
    """Sales target CRUD."""

    async def test_list_empty(self, async_client: AsyncClient, auth_headers: dict):
        resp = await async_client.get("/api/v1/sales/targets", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["code"] == 0

    async def test_create_target(self, async_client: AsyncClient, auth_headers: dict):
        resp = await async_client.post(
            "/api/v1/sales/targets",
            headers=auth_headers,
            json={"user_id": 1, "period": "2025-Q1", "target_amount": 100000, "target_orders": 20},
        )
        assert resp.status_code == 201
        assert resp.json()["code"] == 0
        assert "id" in resp.json()["data"]

    async def test_get_target(self, async_client: AsyncClient, auth_headers: dict):
        c = await async_client.post(
            "/api/v1/sales/targets",
            headers=auth_headers,
            json={"user_id": 1, "period": "2025-Q2", "target_amount": 50000, "target_orders": 10},
        )
        tid = c.json()["data"]["id"]
        resp = await async_client.get(f"/api/v1/sales/targets/{tid}", headers=auth_headers)
        assert resp.status_code == 200

    async def test_update_target(self, async_client: AsyncClient, auth_headers: dict):
        c = await async_client.post(
            "/api/v1/sales/targets",
            headers=auth_headers,
            json={"user_id": 1, "period": "2025-Q3", "target_amount": 100000, "target_orders": 20},
        )
        tid = c.json()["data"]["id"]
        resp = await async_client.put(
            f"/api/v1/sales/targets/{tid}",
            headers=auth_headers,
            json={"target_amount": 150000},
        )
        assert resp.status_code == 200
        assert resp.json()["code"] == 0

    async def test_delete_target(self, async_client: AsyncClient, auth_headers: dict):
        c = await async_client.post(
            "/api/v1/sales/targets",
            headers=auth_headers,
            json={"user_id": 1, "period": "2025-Q4", "target_amount": 80000, "target_orders": 15},
        )
        tid = c.json()["data"]["id"]
        resp = await async_client.delete(f"/api/v1/sales/targets/{tid}", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["code"] == 0
    async def test_summary(self, async_client: AsyncClient, auth_headers: dict):
        resp = await async_client.get("/api/v1/sales/targets/summary", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["code"] == 0

    async def test_unauthorized(self, async_client: AsyncClient):
        resp = await async_client.get("/api/v1/sales/targets")
        assert resp.status_code == 401
