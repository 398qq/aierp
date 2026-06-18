"""Tests for Phase 7 API modules — documents, import/export, dashboard widgets/KPI."""

from httpx import AsyncClient


class TestDocuments:
    """Document upload, list, download, delete."""

    async def test_list_documents_empty(
        self, async_client: AsyncClient, auth_headers: dict
    ):
        resp = await async_client.get(
            "/api/v1/documents?entity_type=customer&entity_id=1", headers=auth_headers
        )
        assert resp.status_code == 200
        assert resp.json()["code"] == 0

    async def test_upload_text_file(
        self, async_client: AsyncClient, auth_headers: dict
    ):
        resp = await async_client.post(
            "/api/v1/documents/upload",
            headers=auth_headers,
            data={"entity_type": "customer", "entity_id": 1},
            files={"file": ("test.txt", b"hello world", "text/plain")},
        )
        # text/plain is not in ALLOWED_MIME — should be rejected
        assert resp.status_code == 400
        assert resp.json()["code"] == 400

    async def test_upload_csv_file(self, async_client: AsyncClient, auth_headers: dict):
        resp = await async_client.post(
            "/api/v1/documents/upload",
            headers=auth_headers,
            data={"entity_type": "customer", "entity_id": 1},
            files={"file": ("data.csv", b"col1,col2\n1,2", "text/csv")},
        )
        assert resp.status_code == 200
        assert resp.json()["code"] == 0
        assert "id" in resp.json()["data"]

    async def test_list_after_upload(
        self, async_client: AsyncClient, auth_headers: dict
    ):
        await async_client.post(
            "/api/v1/documents/upload",
            headers=auth_headers,
            data={"entity_type": "product", "entity_id": 10},
            files={"file": ("spec.csv", b"a,b\n1,2", "text/csv")},
        )
        resp = await async_client.get(
            "/api/v1/documents?entity_type=product&entity_id=10", headers=auth_headers
        )
        assert resp.status_code == 200
        assert len(resp.json()["data"]) > 0

    async def test_delete_document(self, async_client: AsyncClient, auth_headers: dict):
        c = await async_client.post(
            "/api/v1/documents/upload",
            headers=auth_headers,
            data={"entity_type": "order", "entity_id": 1},
            files={"file": ("note.csv", b"data", "text/csv")},
        )
        doc_id = c.json()["data"]["id"]
        resp = await async_client.delete(
            f"/api/v1/documents/{doc_id}", headers=auth_headers
        )
        assert resp.status_code == 200
        assert resp.json()["code"] == 0

    async def test_requires_auth(self, async_client: AsyncClient):
        resp = await async_client.get(
            "/api/v1/documents?entity_type=customer&entity_id=1"
        )
        assert resp.status_code == 401


class TestImportExport:
    """Export and import endpoints."""

    async def test_export_customers_csv(
        self, async_client: AsyncClient, auth_headers: dict
    ):
        resp = await async_client.get(
            "/api/v1/export/customers?format=csv", headers=auth_headers
        )
        assert resp.status_code == 200

    async def test_export_products_csv(
        self, async_client: AsyncClient, auth_headers: dict
    ):
        resp = await async_client.get(
            "/api/v1/export/products?format=csv", headers=auth_headers
        )
        assert resp.status_code == 200

    async def test_export_invalid_entity(
        self, async_client: AsyncClient, auth_headers: dict
    ):
        resp = await async_client.get(
            "/api/v1/export/invalid_entity?format=csv", headers=auth_headers
        )
        assert resp.status_code == 400
        assert resp.json()["code"] == 400

    async def test_import_customers_csv(
        self, async_client: AsyncClient, auth_headers: dict
    ):
        csv_data = (
            "name,phone,email,industry,level\n测试导入,13800138000,test@test.com,电子,A"
        )
        resp = await async_client.post(
            "/api/v1/import/customers",
            headers=auth_headers,
            files={"file": ("customers.csv", csv_data.encode("utf-8-sig"), "text/csv")},
        )
        assert resp.status_code == 200
        assert resp.json()["code"] == 0

    async def test_generic_import_customers_rejects_duplicate_normalized_name(
        self, async_client: AsyncClient, auth_headers: dict
    ):
        await async_client.post(
            "/api/v1/customers",
            headers=auth_headers,
            json={"name": "上海市星河电子有限公司"},
        )
        csv_data = "name,phone,email,industry,level\n上海星河电子,13800138000,test@test.com,电子,A"

        resp = await async_client.post(
            "/api/v1/import/customers",
            headers=auth_headers,
            files={"file": ("customers.csv", csv_data.encode("utf-8-sig"), "text/csv")},
        )

        assert resp.status_code == 400
        assert "客户名称已存在" in resp.json()["msg"]

        listed = await async_client.get(
            "/api/v1/customers?q=星河电子", headers=auth_headers
        )
        assert listed.json()["data"]["total"] == 1

    async def test_import_products_csv(
        self, async_client: AsyncClient, auth_headers: dict
    ):
        csv_data = "name,sku,category,cost_price,selling_price,unit\n测试产品,SKU001,电子,10,20,pcs"
        resp = await async_client.post(
            "/api/v1/import/products",
            headers=auth_headers,
            files={"file": ("products.csv", csv_data.encode("utf-8-sig"), "text/csv")},
        )
        assert resp.status_code == 200
        assert resp.json()["code"] == 0

    async def test_import_suppliers_csv(
        self, async_client: AsyncClient, auth_headers: dict
    ):
        csv_data = "name,contact,phone,email,address,level\n测试供应商,张三,13900001111,zhang@test.com,深圳,B"
        resp = await async_client.post(
            "/api/v1/import/suppliers",
            headers=auth_headers,
            files={"file": ("suppliers.csv", csv_data.encode("utf-8-sig"), "text/csv")},
        )
        assert resp.status_code == 200
        assert resp.json()["code"] == 0

    async def test_import_contracts_csv(
        self, async_client: AsyncClient, auth_headers: dict
    ):
        csv_data = "title,customer_id,amount,status,signed_date,notes\n采购合同,1,50000,draft,2025-01-01,测试合同"
        resp = await async_client.post(
            "/api/v1/import/contracts",
            headers=auth_headers,
            files={"file": ("contracts.csv", csv_data.encode("utf-8-sig"), "text/csv")},
        )
        assert resp.status_code == 200
        assert resp.json()["code"] == 0

    async def test_export_contracts_csv(
        self, async_client: AsyncClient, auth_headers: dict
    ):
        resp = await async_client.get(
            "/api/v1/export/contracts?format=csv", headers=auth_headers
        )
        assert resp.status_code == 200

    async def test_import_requires_auth(self, async_client: AsyncClient):
        resp = await async_client.post(
            "/api/v1/import/customers",
            files={"file": ("test.csv", b"name\nTest", "text/csv")},
        )
        assert resp.status_code == 401

    async def test_export_requires_auth(self, async_client: AsyncClient):
        resp = await async_client.get("/api/v1/export/customers")
        assert resp.status_code == 401


class TestDashboard:
    """Dashboard widgets and KPI."""

    async def test_list_widgets_empty(
        self, async_client: AsyncClient, auth_headers: dict
    ):
        resp = await async_client.get("/api/v1/dashboard/widgets", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["code"] == 0

    async def test_save_widgets(self, async_client: AsyncClient, auth_headers: dict):
        resp = await async_client.put(
            "/api/v1/dashboard/widgets",
            headers=auth_headers,
            json={
                "widgets": [
                    {
                        "widget_type": "kpi_card",
                        "title": "本月收入",
                        "position_x": 0,
                        "position_y": 0,
                        "width": 3,
                        "height": 1,
                    },
                    {
                        "widget_type": "chart",
                        "title": "销售趋势",
                        "position_x": 3,
                        "position_y": 0,
                        "width": 6,
                        "height": 2,
                    },
                ]
            },
        )
        assert resp.status_code == 200
        assert resp.json()["code"] == 0

    async def test_list_widgets_after_save(
        self, async_client: AsyncClient, auth_headers: dict
    ):
        await async_client.put(
            "/api/v1/dashboard/widgets",
            headers=auth_headers,
            json={
                "widgets": [
                    {
                        "widget_type": "alert_list",
                        "title": "预警",
                        "position_x": 0,
                        "position_y": 1,
                        "width": 3,
                        "height": 1,
                    },
                ]
            },
        )
        resp = await async_client.get("/api/v1/dashboard/widgets", headers=auth_headers)
        assert resp.status_code == 200
        assert len(resp.json()["data"]) > 0

    async def test_kpi(self, async_client: AsyncClient, auth_headers: dict):
        resp = await async_client.get("/api/v1/dashboard/kpi", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["code"] == 0
        data = resp.json()["data"]
        assert "month_revenue" in data
        assert "total_customers" in data
        assert "total_products" in data

    async def test_widgets_require_auth(self, async_client: AsyncClient):
        resp = await async_client.get("/api/v1/dashboard/widgets")
        assert resp.status_code == 401
