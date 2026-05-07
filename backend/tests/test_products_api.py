import pytest
from httpx import AsyncClient


class TestProductsAPI:
    async def test_list_products_empty(self, async_client: AsyncClient, auth_headers: dict):
        resp = await async_client.get("/api/v1/products", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["code"] == 0
        assert data["data"]["list"] == []
        assert data["data"]["total"] == 0
        assert data["data"]["page"] == 1
        assert data["data"]["page_size"] == 20

    async def test_create_product(self, async_client: AsyncClient, auth_headers: dict):
        resp = await async_client.post("/api/v1/products", headers=auth_headers, json={
            "name": "Test Resistor 10K",
            "sku": "RES-10K-001",
            "category": "Resistors",
            "package_type": "0805",
            "unit": "pcs",
        })
        assert resp.status_code == 201
        data = resp.json()
        assert data["code"] == 0
        assert data["data"]["name"] == "Test Resistor 10K"
        assert data["data"]["id"] > 0

    async def test_get_product(self, async_client: AsyncClient, auth_headers: dict):
        # Create first
        create_resp = await async_client.post("/api/v1/products", headers=auth_headers, json={
            "name": "Capacitor 100uF",
            "sku": "CAP-100UF",
        })
        product_id = create_resp.json()["data"]["id"]

        # Read back
        resp = await async_client.get(f"/api/v1/products/{product_id}", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["code"] == 0
        assert data["data"]["name"] == "Capacitor 100uF"
        assert data["data"]["sku"] == "CAP-100UF"

    async def test_get_product_not_found(self, async_client: AsyncClient, auth_headers: dict):
        resp = await async_client.get("/api/v1/products/99999", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["code"] == 404

    async def test_update_product(self, async_client: AsyncClient, auth_headers: dict):
        create_resp = await async_client.post("/api/v1/products", headers=auth_headers, json={
            "name": "LED Red",
            "sku": "LED-RED",
        })
        product_id = create_resp.json()["data"]["id"]

        resp = await async_client.put(f"/api/v1/products/{product_id}", headers=auth_headers, json={
            "name": "LED Red 5mm",
            "category": "Optoelectronics",
        })
        assert resp.status_code == 200
        assert resp.json()["code"] == 0

        # Verify update
        get_resp = await async_client.get(f"/api/v1/products/{product_id}", headers=auth_headers)
        data = get_resp.json()["data"]
        assert data["name"] == "LED Red 5mm"
        assert data["category"] == "Optoelectronics"

    async def test_delete_product(self, async_client: AsyncClient, auth_headers: dict):
        create_resp = await async_client.post("/api/v1/products", headers=auth_headers, json={
            "name": "ToDelete",
        })
        product_id = create_resp.json()["data"]["id"]

        resp = await async_client.delete(f"/api/v1/products/{product_id}", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["msg"] == "deleted"

        # Verify it's gone (soft-deleted)
        get_resp = await async_client.get(f"/api/v1/products/{product_id}", headers=auth_headers)
        assert get_resp.json()["code"] == 404

    async def test_list_products_pagination(self, async_client: AsyncClient, auth_headers: dict):
        # Create 5 products
        for i in range(5):
            await async_client.post("/api/v1/products", headers=auth_headers, json={
                "name": f"Product {i}",
                "sku": f"SKU-{i}",
            })

        resp = await async_client.get("/api/v1/products?page=1&page_size=3", headers=auth_headers)
        data = resp.json()["data"]
        assert len(data["list"]) <= 3
        assert data["page"] == 1
        assert data["page_size"] == 3

    async def test_list_products_search(self, async_client: AsyncClient, auth_headers: dict):
        await async_client.post("/api/v1/products", headers=auth_headers, json={
            "name": "FPGA Chip",
            "sku": "FPGA-XC7",
        })
        await async_client.post("/api/v1/products", headers=auth_headers, json={
            "name": "MCU Chip",
            "sku": "MCU-STM32",
        })

        resp = await async_client.get("/api/v1/products?q=FPGA", headers=auth_headers)
        data = resp.json()["data"]
        assert data["total"] >= 1
        assert any("FPGA" in p["name"] for p in data["list"])

    async def test_create_product_requires_auth(self, async_client: AsyncClient):
        resp = await async_client.post("/api/v1/products", json={"name": "NoAuth"})
        assert resp.status_code == 401

    async def test_create_product_minimal(self, async_client: AsyncClient, auth_headers: dict):
        """Name-only product creation should work."""
        resp = await async_client.post("/api/v1/products", headers=auth_headers, json={
            "name": "Bare Minimum",
        })
        assert resp.status_code == 201
        data = resp.json()
        assert data["data"]["name"] == "Bare Minimum"
        assert data["data"]["id"] > 0
