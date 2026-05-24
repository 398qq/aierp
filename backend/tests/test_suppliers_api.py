from httpx import AsyncClient


class TestSuppliersAPI:
    async def test_supplier_stats_summary(self, async_client: AsyncClient, auth_headers: dict, db_session):
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
        db_session.add(SupplierProduct(supplier_id=factory.id, product_id=product.id, cost_price=1.2))
        await db_session.flush()

        resp = await async_client.get("/api/v1/suppliers/stats/summary", headers=auth_headers)

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
