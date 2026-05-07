"""Sales API tests — opportunities, quotations, sales orders, delivery notes."""
import pytest
from httpx import AsyncClient


class TestOpportunities:
    """Opportunity CRUD + funnel + batch operations."""

    async def test_list_empty(self, async_client: AsyncClient, auth_headers: dict):
        resp = await async_client.get("/api/v1/opportunities", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["code"] == 0
        assert "list" in data["data"]
        assert "total" in data["data"]

    async def test_list_filter_by_stage(self, async_client: AsyncClient, auth_headers: dict):
        resp = await async_client.get("/api/v1/opportunities?stage=lead", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["code"] == 0

    async def test_create_opportunity(self, async_client: AsyncClient, auth_headers: dict):
        resp = await async_client.post(
            "/api/v1/opportunities",
            headers=auth_headers,
            json={
                "name": "测试商机",
                "customer_id": 1,
                "amount": 50000,
                "stage": "lead",
                "probability": 10,
            },
        )
        assert resp.status_code == 201
        assert resp.json()["code"] == 0
        assert "id" in resp.json()["data"]

    async def test_get_opportunity(self, async_client: AsyncClient, auth_headers: dict):
        # create first
        create = await async_client.post(
            "/api/v1/opportunities",
            headers=auth_headers,
            json={"name": "查单条", "customer_id": 1, "amount": 10000, "stage": "lead", "probability": 10},
        )
        opp_id = create.json()["data"]["id"]
        resp = await async_client.get(f"/api/v1/opportunities/{opp_id}", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["data"]["name"] == "查单条"

    async def test_get_opportunity_not_found(self, async_client: AsyncClient, auth_headers: dict):
        resp = await async_client.get("/api/v1/opportunities/99999", headers=auth_headers)
        # fail() returns dict with code=404 in body
        assert resp.status_code == 200
        assert resp.json()["code"] == 404

    async def test_update_opportunity(self, async_client: AsyncClient, auth_headers: dict):
        create = await async_client.post(
            "/api/v1/opportunities",
            headers=auth_headers,
            json={"name": "原始名称", "customer_id": 1, "amount": 10000, "stage": "lead", "probability": 10},
        )
        opp_id = create.json()["data"]["id"]
        resp = await async_client.put(
            f"/api/v1/opportunities/{opp_id}",
            headers=auth_headers,
            json={"name": "新名称", "stage": "qualified"},
        )
        assert resp.status_code == 200
        assert resp.json()["code"] == 0

    async def test_delete_opportunity(self, async_client: AsyncClient, auth_headers: dict):
        create = await async_client.post(
            "/api/v1/opportunities",
            headers=auth_headers,
            json={"name": "待删除", "customer_id": 1, "amount": 10000, "stage": "lead", "probability": 10},
        )
        opp_id = create.json()["data"]["id"]
        resp = await async_client.delete(f"/api/v1/opportunities/{opp_id}", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["code"] == 0

    async def test_funnel(self, async_client: AsyncClient, auth_headers: dict):
        resp = await async_client.get("/api/v1/opportunities/funnel", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["code"] == 0

    async def test_batch_update(self, async_client: AsyncClient, auth_headers: dict):
        # create two
        c1 = await async_client.post(
            "/api/v1/opportunities", headers=auth_headers,
            json={"name": "批量1", "customer_id": 1, "amount": 10000, "stage": "lead", "probability": 10},
        )
        c2 = await async_client.post(
            "/api/v1/opportunities", headers=auth_headers,
            json={"name": "批量2", "customer_id": 1, "amount": 20000, "stage": "lead", "probability": 10},
        )
        ids = [c1.json()["data"]["id"], c2.json()["data"]["id"]]
        resp = await async_client.post(
            "/api/v1/opportunities/batch-update",
            headers=auth_headers,
            json={"ids": ids, "stage": "qualified"},
        )
        assert resp.status_code == 200
        assert resp.json()["data"]["updated"] == 2

    async def test_batch_delete(self, async_client: AsyncClient, auth_headers: dict):
        c1 = await async_client.post(
            "/api/v1/opportunities", headers=auth_headers,
            json={"name": "删1", "customer_id": 1, "amount": 10000, "stage": "lead", "probability": 10},
        )
        c2 = await async_client.post(
            "/api/v1/opportunities", headers=auth_headers,
            json={"name": "删2", "customer_id": 1, "amount": 10000, "stage": "lead", "probability": 10},
        )
        ids = [c1.json()["data"]["id"], c2.json()["data"]["id"]]
        resp = await async_client.post(
            "/api/v1/opportunities/batch-delete",
            headers=auth_headers,
            json={"ids": ids},
        )
        assert resp.status_code == 200
        assert resp.json()["data"]["deleted"] == 2

    async def test_unauthorized(self, async_client: AsyncClient):
        resp = await async_client.get("/api/v1/opportunities")
        assert resp.status_code == 401


class TestQuotations:
    """Quotation CRUD + items + convert-to-order."""

    async def test_list_empty(self, async_client: AsyncClient, auth_headers: dict):
        resp = await async_client.get("/api/v1/quotations", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["code"] == 0

    async def test_create_quotation(self, async_client: AsyncClient, auth_headers: dict):
        resp = await async_client.post(
            "/api/v1/quotations",
            headers=auth_headers,
            json={"customer_id": 1, "status": "draft", "total_amount": 30000},
        )
        assert resp.status_code == 201
        assert resp.json()["code"] == 0
        assert "quotation_no" in resp.json()["data"]

    async def test_get_quotation(self, async_client: AsyncClient, auth_headers: dict):
        c = await async_client.post(
            "/api/v1/quotations", headers=auth_headers,
            json={"customer_id": 1, "status": "draft", "total_amount": 30000},
        )
        quo_id = c.json()["data"]["id"]
        resp = await async_client.get(f"/api/v1/quotations/{quo_id}", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["data"]["id"] == quo_id

    async def test_update_quotation(self, async_client: AsyncClient, auth_headers: dict):
        c = await async_client.post(
            "/api/v1/quotations", headers=auth_headers,
            json={"customer_id": 1, "status": "draft", "total_amount": 30000},
        )
        quo_id = c.json()["data"]["id"]
        resp = await async_client.put(
            f"/api/v1/quotations/{quo_id}",
            headers=auth_headers,
            json={"status": "approved"},
        )
        assert resp.status_code == 200

    async def test_delete_quotation(self, async_client: AsyncClient, auth_headers: dict):
        c = await async_client.post(
            "/api/v1/quotations", headers=auth_headers,
            json={"customer_id": 1, "status": "draft", "total_amount": 30000},
        )
        quo_id = c.json()["data"]["id"]
        resp = await async_client.delete(f"/api/v1/quotations/{quo_id}", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["code"] == 0

    async def test_add_quotation_item(self, async_client: AsyncClient, auth_headers: dict):
        quo = await async_client.post(
            "/api/v1/quotations", headers=auth_headers,
            json={"customer_id": 1, "status": "draft", "total_amount": 30000},
        )
        quo_id = quo.json()["data"]["id"]
        resp = await async_client.post(
            f"/api/v1/quotations/{quo_id}/items",
            headers=auth_headers,
            json={"product_id": 1, "quantity": 100, "unit_price": 5.0, "amount": 500},
        )
        assert resp.status_code == 201
        assert resp.json()["code"] == 0

    async def test_list_quotation_items(self, async_client: AsyncClient, auth_headers: dict):
        quo = await async_client.post(
            "/api/v1/quotations", headers=auth_headers,
            json={"customer_id": 1, "status": "draft", "total_amount": 30000},
        )
        quo_id = quo.json()["data"]["id"]
        resp = await async_client.get(f"/api/v1/quotations/{quo_id}/items", headers=auth_headers)
        assert resp.status_code == 200
        assert isinstance(resp.json()["data"], list)

    async def test_convert_quotation_to_order(self, async_client: AsyncClient, auth_headers: dict):
        quo = await async_client.post(
            "/api/v1/quotations", headers=auth_headers,
            json={"customer_id": 1, "status": "draft", "total_amount": 30000},
        )
        quo_id = quo.json()["data"]["id"]
        resp = await async_client.post(
            f"/api/v1/quotations/{quo_id}/convert-to-order",
            headers=auth_headers,
        )
        assert resp.status_code == 200
        assert "document_no" in resp.json()["data"]

    async def test_batch_delete_quotations(self, async_client: AsyncClient, auth_headers: dict):
        c1 = await async_client.post(
            "/api/v1/quotations", headers=auth_headers,
            json={"customer_id": 1, "status": "draft", "total_amount": 30000},
        )
        c2 = await async_client.post(
            "/api/v1/quotations", headers=auth_headers,
            json={"customer_id": 1, "status": "draft", "total_amount": 30000},
        )
        ids = [c1.json()["data"]["id"], c2.json()["data"]["id"]]
        resp = await async_client.post(
            "/api/v1/quotations/batch-delete",
            headers=auth_headers,
            json={"ids": ids},
        )
        assert resp.status_code == 200
        assert resp.json()["data"]["deleted"] == 2


class TestSalesOrders:
    """SalesOrder CRUD + items + convert-to-delivery."""

    async def test_list_empty(self, async_client: AsyncClient, auth_headers: dict):
        resp = await async_client.get("/api/v1/sales-orders", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["code"] == 0

    async def test_create_sales_order(self, async_client: AsyncClient, auth_headers: dict):
        resp = await async_client.post(
            "/api/v1/sales-orders",
            headers=auth_headers,
            json={"customer_id": 1, "status": "pending", "total_amount": 50000},
        )
        assert resp.status_code == 201
        assert resp.json()["code"] == 0
        assert "order_no" in resp.json()["data"]

    async def test_get_sales_order(self, async_client: AsyncClient, auth_headers: dict):
        c = await async_client.post(
            "/api/v1/sales-orders", headers=auth_headers,
            json={"customer_id": 1, "status": "pending", "total_amount": 50000},
        )
        order_id = c.json()["data"]["id"]
        resp = await async_client.get(f"/api/v1/sales-orders/{order_id}", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["data"]["id"] == order_id

    async def test_update_sales_order(self, async_client: AsyncClient, auth_headers: dict):
        c = await async_client.post(
            "/api/v1/sales-orders", headers=auth_headers,
            json={"customer_id": 1, "status": "pending", "total_amount": 50000},
        )
        order_id = c.json()["data"]["id"]
        resp = await async_client.put(
            f"/api/v1/sales-orders/{order_id}",
            headers=auth_headers,
            json={"status": "confirmed"},
        )
        assert resp.status_code == 200

    async def test_delete_sales_order(self, async_client: AsyncClient, auth_headers: dict):
        c = await async_client.post(
            "/api/v1/sales-orders", headers=auth_headers,
            json={"customer_id": 1, "status": "pending", "total_amount": 50000},
        )
        order_id = c.json()["data"]["id"]
        resp = await async_client.delete(f"/api/v1/sales-orders/{order_id}", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["code"] == 0

    async def test_add_sales_order_item(self, async_client: AsyncClient, auth_headers: dict):
        order = await async_client.post(
            "/api/v1/sales-orders", headers=auth_headers,
            json={"customer_id": 1, "status": "pending", "total_amount": 50000},
        )
        order_id = order.json()["data"]["id"]
        resp = await async_client.post(
            f"/api/v1/sales-orders/{order_id}/items",
            headers=auth_headers,
            json={"product_id": 1, "quantity": 50, "unit_price": 10.0, "amount": 500},
        )
        assert resp.status_code == 201

    async def test_list_sales_order_items(self, async_client: AsyncClient, auth_headers: dict):
        order = await async_client.post(
            "/api/v1/sales-orders", headers=auth_headers,
            json={"customer_id": 1, "status": "pending", "total_amount": 50000},
        )
        order_id = order.json()["data"]["id"]
        resp = await async_client.get(f"/api/v1/sales-orders/{order_id}/items", headers=auth_headers)
        assert resp.status_code == 200
        assert isinstance(resp.json()["data"], list)

    async def test_convert_order_to_delivery(self, async_client: AsyncClient, auth_headers: dict):
        order = await async_client.post(
            "/api/v1/sales-orders", headers=auth_headers,
            json={"customer_id": 1, "status": "pending", "total_amount": 50000},
        )
        order_id = order.json()["data"]["id"]
        resp = await async_client.post(
            f"/api/v1/sales-orders/{order_id}/convert-to-delivery",
            headers=auth_headers,
        )
        assert resp.status_code == 200
        assert "document_no" in resp.json()["data"]

    async def test_convert_order_twice_fails(self, async_client: AsyncClient, auth_headers: dict):
        order = await async_client.post(
            "/api/v1/sales-orders", headers=auth_headers,
            json={"customer_id": 1, "status": "pending", "total_amount": 50000},
        )
        order_id = order.json()["data"]["id"]
        await async_client.post(
            f"/api/v1/sales-orders/{order_id}/convert-to-delivery",
            headers=auth_headers,
        )
        resp = await async_client.post(
            f"/api/v1/sales-orders/{order_id}/convert-to-delivery",
            headers=auth_headers,
        )
        # fail() returns HTTP 200 with code=409 in body
        assert resp.status_code == 200
        assert resp.json()["code"] == 409

    async def test_batch_delete_orders(self, async_client: AsyncClient, auth_headers: dict):
        c1 = await async_client.post(
            "/api/v1/sales-orders", headers=auth_headers,
            json={"customer_id": 1, "status": "pending", "total_amount": 50000},
        )
        c2 = await async_client.post(
            "/api/v1/sales-orders", headers=auth_headers,
            json={"customer_id": 1, "status": "pending", "total_amount": 50000},
        )
        ids = [c1.json()["data"]["id"], c2.json()["data"]["id"]]
        resp = await async_client.post(
            "/api/v1/sales-orders/batch-delete",
            headers=auth_headers,
            json={"ids": ids},
        )
        assert resp.status_code == 200
        assert resp.json()["data"]["deleted"] == 2


class TestDeliveryNotes:
    """DeliveryNote CRUD + items."""

    async def test_list_empty(self, async_client: AsyncClient, auth_headers: dict):
        resp = await async_client.get("/api/v1/delivery-notes", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["code"] == 0

    async def test_create_delivery_note(self, async_client: AsyncClient, auth_headers: dict):
        resp = await async_client.post(
            "/api/v1/delivery-notes",
            headers=auth_headers,
            json={"customer_id": 1, "sales_order_id": 1, "status": "pending"},
        )
        assert resp.status_code == 201
        assert resp.json()["code"] == 0
        assert "note_no" in resp.json()["data"]

    async def test_get_delivery_note(self, async_client: AsyncClient, auth_headers: dict):
        c = await async_client.post(
            "/api/v1/delivery-notes", headers=auth_headers,
            json={"customer_id": 1, "sales_order_id": 1, "status": "pending"},
        )
        note_id = c.json()["data"]["id"]
        resp = await async_client.get(f"/api/v1/delivery-notes/{note_id}", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["data"]["id"] == note_id

    async def test_update_delivery_note(self, async_client: AsyncClient, auth_headers: dict):
        c = await async_client.post(
            "/api/v1/delivery-notes", headers=auth_headers,
            json={"customer_id": 1, "sales_order_id": 1, "status": "pending"},
        )
        note_id = c.json()["data"]["id"]
        resp = await async_client.put(
            f"/api/v1/delivery-notes/{note_id}",
            headers=auth_headers,
            json={"status": "delivered"},
        )
        assert resp.status_code == 200

    async def test_delete_delivery_note(self, async_client: AsyncClient, auth_headers: dict):
        c = await async_client.post(
            "/api/v1/delivery-notes", headers=auth_headers,
            json={"customer_id": 1, "sales_order_id": 1, "status": "pending"},
        )
        note_id = c.json()["data"]["id"]
        resp = await async_client.delete(f"/api/v1/delivery-notes/{note_id}", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["code"] == 0

    async def test_add_delivery_note_item(self, async_client: AsyncClient, auth_headers: dict):
        note = await async_client.post(
            "/api/v1/delivery-notes", headers=auth_headers,
            json={"customer_id": 1, "sales_order_id": 1, "status": "pending"},
        )
        note_id = note.json()["data"]["id"]
        resp = await async_client.post(
            f"/api/v1/delivery-notes/{note_id}/items",
            headers=auth_headers,
            json={"product_id": 1, "quantity": 20},
        )
        assert resp.status_code == 201

    async def test_list_delivery_note_items(self, async_client: AsyncClient, auth_headers: dict):
        note = await async_client.post(
            "/api/v1/delivery-notes", headers=auth_headers,
            json={"customer_id": 1, "sales_order_id": 1, "status": "pending"},
        )
        note_id = note.json()["data"]["id"]
        resp = await async_client.get(f"/api/v1/delivery-notes/{note_id}/items", headers=auth_headers)
        assert resp.status_code == 200
        assert isinstance(resp.json()["data"], list)

    async def test_batch_delete_notes(self, async_client: AsyncClient, auth_headers: dict):
        c1 = await async_client.post(
            "/api/v1/delivery-notes", headers=auth_headers,
            json={"customer_id": 1, "sales_order_id": 1, "status": "pending"},
        )
        c2 = await async_client.post(
            "/api/v1/delivery-notes", headers=auth_headers,
            json={"customer_id": 1, "sales_order_id": 1, "status": "pending"},
        )
        ids = [c1.json()["data"]["id"], c2.json()["data"]["id"]]
        resp = await async_client.post(
            "/api/v1/delivery-notes/batch-delete",
            headers=auth_headers,
            json={"ids": ids},
        )
        assert resp.status_code == 200
        assert resp.json()["data"]["deleted"] == 2


class TestSalesStats:
    """Sales stats endpoints."""

    async def test_summary(self, async_client: AsyncClient, auth_headers: dict):
        resp = await async_client.get("/api/v1/sales/stats/summary", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert "total_orders" in data
        assert "total_amount" in data
        assert "active_opportunities" in data

    async def test_trend(self, async_client: AsyncClient, auth_headers: dict):
        # date_trunc is PostgreSQL-only — skip on SQLite
        pytest.skip("date_trunc not supported in SQLite")

    async def test_trend_with_params(self, async_client: AsyncClient, auth_headers: dict):
        pytest.skip("date_trunc not supported in SQLite")

    async def test_stage_distribution(self, async_client: AsyncClient, auth_headers: dict):
        resp = await async_client.get("/api/v1/sales/stats/stage-distribution", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert isinstance(data, list)

    async def test_stats_unauthorized(self, async_client: AsyncClient):
        resp = await async_client.get("/api/v1/sales/stats/summary")
        assert resp.status_code == 401
