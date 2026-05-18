from unittest.mock import patch

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

    async def test_brand_stats_summary_and_product_count(
        self,
        async_client: AsyncClient,
        auth_headers: dict,
        db_session,
    ):
        """Brand stats summary route should not be swallowed by /brands/{brand_id}."""
        from app.models.product import Product

        brand_resp = await async_client.post(
            "/api/v1/brands/",
            headers=auth_headers,
            json={
                "name": "Risky Brand",
                "status": "active",
                "level": "A",
                "brand_type": "agency",
                "lifecycle_stage": "eol",
                "risk_level": "high",
                "risk_score": 88,
                "authorization_status": "authorized",
                "is_automotive": True,
            },
        )
        assert brand_resp.status_code == 200
        brand_id = brand_resp.json()["data"]["id"]

        db_session.add(Product(name="Brand Product", sku="BRAND-PROD", brand_id=brand_id))
        await db_session.flush()

        list_resp = await async_client.get("/api/v1/brands/", headers=auth_headers)
        assert list_resp.status_code == 200
        brands = list_resp.json()["data"]["list"]
        assert brands[0]["product_count"] == 1

        stats_resp = await async_client.get("/api/v1/brands/stats/summary", headers=auth_headers)
        assert stats_resp.status_code == 200
        stats = stats_resp.json()["data"]
        assert stats["total"] == 1
        assert stats["eol_nrnd_count"] == 1
        assert stats["automotive_count"] == 1
        assert stats["high_risk_count"] == 1
        assert stats["by_status"] == [{"status": "active", "count": 1}]
        assert stats["top_risk_brands"][0]["id"] == brand_id

    async def test_brand_batch_update_and_delete_contract(
        self,
        async_client: AsyncClient,
        auth_headers: dict,
    ):
        brand_resp = await async_client.post(
            "/api/v1/brands/",
            headers=auth_headers,
            json={"name": "Batch Brand", "status": "active", "level": "C"},
        )
        brand_id = brand_resp.json()["data"]["id"]

        update_resp = await async_client.patch(
            "/api/v1/brands/batch",
            headers=auth_headers,
            json={"ids": [brand_id], "updates": {"status": "inactive", "level": "B"}},
        )
        assert update_resp.status_code == 200
        update_data = update_resp.json()["data"]
        assert update_data["updated"] == 1
        assert update_data["fields"] == ["level", "status"]

        get_resp = await async_client.get(f"/api/v1/brands/{brand_id}", headers=auth_headers)
        assert get_resp.json()["data"]["status"] == "inactive"
        assert get_resp.json()["data"]["level"] == "B"

        delete_resp = await async_client.post(
            "/api/v1/brands/batch-delete",
            headers=auth_headers,
            json={"ids": [brand_id]},
        )
        assert delete_resp.status_code == 200
        assert delete_resp.json()["data"]["deleted"] == 1

        missing_resp = await async_client.get(f"/api/v1/brands/{brand_id}", headers=auth_headers)
        assert missing_resp.json()["code"] == 404

    @patch("app.services.embedding_pipeline.after_product_save")
    async def test_list_products_filter_in_stock(self, mock_embed, async_client: AsyncClient, auth_headers: dict, db_session):
        """Filter by in_stock returns only products with positive available inventory."""
        # Create warehouse first
        from app.models.product import Warehouse, Inventory
        wh = Warehouse(name="主仓")
        db_session.add(wh)
        await db_session.flush()

        # Create product with inventory (quantity > 0, no lock)
        p1_resp = await async_client.post("/api/v1/products", headers=auth_headers, json={
            "name": "有库存商品", "sku": "STOCK-001",
        })
        p1_id = p1_resp.json()["data"]["id"]
        inv1 = Inventory(product_id=p1_id, warehouse_id=wh.id, quantity=100, safety_stock=10, locked_quantity=0)
        db_session.add(inv1)

        # Create product with zero inventory
        p2_resp = await async_client.post("/api/v1/products", headers=auth_headers, json={
            "name": "无库存商品", "sku": "STOCK-002",
        })
        p2_id = p2_resp.json()["data"]["id"]
        inv2 = Inventory(product_id=p2_id, warehouse_id=wh.id, quantity=0, safety_stock=10, locked_quantity=0)
        db_session.add(inv2)
        await db_session.flush()

        resp = await async_client.get("/api/v1/products?stock_status=in_stock", headers=auth_headers)
        data = resp.json()["data"]
        assert data["total"] >= 1
        names = [p["name"] for p in data["list"]]
        assert "有库存商品" in names
        assert "无库存商品" not in names

    @patch("app.services.embedding_pipeline.after_product_save")
    async def test_list_products_filter_out_of_stock(self, mock_embed, async_client: AsyncClient, auth_headers: dict, db_session):
        """Filter by out_of_stock returns products with zero available inventory."""
        from app.models.product import Warehouse, Inventory
        wh = Warehouse(name="主仓")
        db_session.add(wh)
        await db_session.flush()

        # Product with stock
        p1_resp = await async_client.post("/api/v1/products", headers=auth_headers, json={
            "name": "热销产品", "sku": "OOS-001",
        })
        p1_id = p1_resp.json()["data"]["id"]
        db_session.add(Inventory(product_id=p1_id, warehouse_id=wh.id, quantity=50, safety_stock=5, locked_quantity=0))

        # Product without stock
        p2_resp = await async_client.post("/api/v1/products", headers=auth_headers, json={
            "name": "缺货产品", "sku": "OOS-002",
        })
        p2_id = p2_resp.json()["data"]["id"]
        db_session.add(Inventory(product_id=p2_id, warehouse_id=wh.id, quantity=0, safety_stock=5, locked_quantity=0))
        await db_session.flush()

        resp = await async_client.get("/api/v1/products?stock_status=out_of_stock", headers=auth_headers)
        data = resp.json()["data"]
        names = [p["name"] for p in data["list"]]
        assert "缺货产品" in names
        assert "热销产品" not in names

    @patch("app.services.embedding_pipeline.after_product_save")
    async def test_list_products_filter_low_stock(self, mock_embed, async_client: AsyncClient, auth_headers: dict, db_session):
        """Filter by low_stock returns products where quantity <= safety_stock."""
        from app.models.product import Warehouse, Inventory
        wh = Warehouse(name="主仓")
        db_session.add(wh)
        await db_session.flush()

        # Low stock: qty=5 <= safety_stock=10
        p1_resp = await async_client.post("/api/v1/products", headers=auth_headers, json={
            "name": "低库存商品", "sku": "LOW-001",
        })
        p1_id = p1_resp.json()["data"]["id"]
        db_session.add(Inventory(product_id=p1_id, warehouse_id=wh.id, quantity=5, safety_stock=10, locked_quantity=0))

        # Normal stock: qty=100 > safety_stock=10
        p2_resp = await async_client.post("/api/v1/products", headers=auth_headers, json={
            "name": "正常库存", "sku": "LOW-002",
        })
        p2_id = p2_resp.json()["data"]["id"]
        db_session.add(Inventory(product_id=p2_id, warehouse_id=wh.id, quantity=100, safety_stock=10, locked_quantity=0))
        await db_session.flush()

        resp = await async_client.get("/api/v1/products?stock_status=low_stock", headers=auth_headers)
        data = resp.json()["data"]
        names = [p["name"] for p in data["list"]]
        assert "低库存商品" in names
        assert "正常库存" not in names

    async def test_list_products_sort_by_name_asc(self, async_client: AsyncClient, auth_headers: dict):
        """Sort by name ascending."""
        for name in ["Zebra", "Apple", "Mango"]:
            await async_client.post("/api/v1/products", headers=auth_headers, json={
                "name": name, "sku": f"SORT-{name}",
            })

        resp = await async_client.get("/api/v1/products?sort=name_asc", headers=auth_headers)
        data = resp.json()["data"]
        names = [p["name"] for p in data["list"] if p["name"] in ("Apple", "Mango", "Zebra")]
        assert names == ["Apple", "Mango", "Zebra"], f"Expected sorted asc, got {names}"

    async def test_list_products_sort_by_created_at_desc(self, async_client: AsyncClient, auth_headers: dict):
        """Sort by created_at descending (newest first, default)."""
        for i, name in enumerate(["First", "Second", "Third"]):
            await async_client.post("/api/v1/products", headers=auth_headers, json={
                "name": name, "sku": f"SORT-DATE-{i}",
            })

        resp = await async_client.get("/api/v1/products?sort=created_at_desc", headers=auth_headers)
        data = resp.json()["data"]
        names = [p["name"] for p in data["list"] if p["name"] in ("First", "Second", "Third")]
        assert names == ["Third", "Second", "First"], f"Expected newest first, got {names}"
