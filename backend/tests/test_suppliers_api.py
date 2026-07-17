from httpx import AsyncClient


class TestSuppliersAPI:
    async def test_supplier_product_crud(
        self, async_client: AsyncClient, auth_headers: dict, db_session
    ):
        from app.models.product import Brand, Product, Supplier

        supplier = Supplier(name="Factory CRUD", supplier_type="原厂")
        brand = Brand(name="Factory Brand")
        product = Product(
            name="Factory MCU",
            sku="MCU-CRUD-01",
            category="MCU",
            package_type="QFN-32",
            brand=brand,
        )
        db_session.add_all([supplier, brand, product])
        await db_session.flush()

        create_resp = await async_client.post(
            f"/api/v1/suppliers/{supplier.id}/products",
            headers=auth_headers,
            json={
                "product_id": product.id,
                "supplier_sku": "FACTORY-MCU-01",
                "cost_price": 1.25,
                "currency": "CNY",
                "lead_time_days": 14,
                "moq": 100,
                "spq": 10,
                "is_preferred": True,
            },
        )
        assert create_resp.status_code == 200
        assert create_resp.json()["code"] == 0

        update_resp = await async_client.put(
            f"/api/v1/suppliers/{supplier.id}/products/{product.id}",
            headers=auth_headers,
            json={
                "product_id": product.id,
                "supplier_sku": "FACTORY-MCU-01A",
                "cost_price": 1.15,
                "currency": "USD",
                "lead_time_days": 10,
                "moq": 50,
                "spq": 5,
                "is_preferred": False,
                "is_active": True,
            },
        )
        assert update_resp.status_code == 200
        assert update_resp.json()["code"] == 0

        list_resp = await async_client.get(
            f"/api/v1/suppliers/{supplier.id}/products", headers=auth_headers
        )
        assert list_resp.status_code == 200
        items = list_resp.json()["data"]
        assert len(items) == 1
        assert items[0] == {
            **items[0],
            "product_name": "Factory MCU",
            "product_sku": "MCU-CRUD-01",
            "sku": "MCU-CRUD-01",
            "category": "MCU",
            "package_type": "QFN-32",
            "brand_name": "Factory Brand",
            "supplier_sku": "FACTORY-MCU-01A",
            "cost_price": 1.15,
            "currency": "USD",
            "lead_time_days": 10,
            "moq": 50,
            "spq": 5,
            "is_preferred": False,
            "is_active": True,
        }

        delete_resp = await async_client.delete(
            f"/api/v1/suppliers/{supplier.id}/products/{product.id}",
            headers=auth_headers,
        )
        assert delete_resp.status_code == 200
        assert delete_resp.json()["code"] == 0

        empty_resp = await async_client.get(
            f"/api/v1/suppliers/{supplier.id}/products", headers=auth_headers
        )
        assert empty_resp.json()["data"] == []

    async def test_supplier_stats_summary(
        self, async_client: AsyncClient, auth_headers: dict, db_session
    ):
        from app.models.product import Product, Supplier, SupplierProduct

        factory = Supplier(
            name="Factory A",
            contact_person="Alice",
            phone="13800000000",
            supplier_type="原厂",
            product_lines="MCU",
            region="上海",
            payment_terms="月结30天",
            financial_rating="A",
            certifications="ISO9001",
        )
        overseas = Supplier(
            name="Overseas B",
            supplier_type="agency",
            region="香港",
        )
        product = Product(name="Sensor A", sku="SNS-A")
        db_session.add_all([factory, overseas, product])
        await db_session.flush()
        db_session.add(
            SupplierProduct(
                supplier_id=factory.id, product_id=product.id, cost_price=1.2
            )
        )
        await db_session.flush()

        resp = await async_client.get(
            "/api/v1/suppliers/stats/summary", headers=auth_headers
        )

        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["total"] == 2
        assert data["certified"] == 1
        assert data["rated"] == 1
        assert data["missing_contact"] == 1
        assert data["missing_profile"] == 1
        assert data["overseas"] == 1
        assert {"type": "原厂", "count": 1} in data["by_type"]
        assert {"type": "代理商", "count": 1} in data["by_type"]
        assert data["top_suppliers"][0]["name"] == "Factory A"
        assert data["top_suppliers"][0]["product_count"] == 1

        list_resp = await async_client.get(
            "/api/v1/suppliers/",
            params={"supplier_type": "代理商"},
            headers=auth_headers,
        )
        assert list_resp.status_code == 200
        list_data = list_resp.json()["data"]
        assert list_data["total"] == 1
        assert list_data["list"][0]["supplier_type"] == "代理商"
