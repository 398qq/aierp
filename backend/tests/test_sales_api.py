"""Sales API tests — opportunities, quotations, sales orders, delivery notes."""

from httpx import AsyncClient


class TestOpportunities:
    """Opportunity CRUD + batch operations."""

    async def test_list_empty(self, async_client: AsyncClient, auth_headers: dict):
        resp = await async_client.get("/api/v1/opportunities", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["code"] == 0
        assert "list" in data["data"]
        assert "total" in data["data"]

    async def test_list_filter_by_stage(
        self, async_client: AsyncClient, auth_headers: dict
    ):
        resp = await async_client.get(
            "/api/v1/opportunities?stage=lead", headers=auth_headers
        )
        assert resp.status_code == 200
        assert resp.json()["code"] == 0

    async def test_list_searches_all_opportunities(
        self, async_client: AsyncClient, auth_headers: dict, test_customer: dict
    ):
        target = await async_client.post(
            "/api/v1/opportunities",
            headers=auth_headers,
            json={
                "title": "全局搜索商机-磁传感器",
                "customer_id": test_customer["id"],
                "amount": 10000,
                "stage": "lead",
                "win_probability": 10,
            },
        )
        await async_client.post(
            "/api/v1/opportunities",
            headers=auth_headers,
            json={
                "title": "普通商机",
                "customer_id": test_customer["id"],
                "amount": 10000,
                "stage": "lead",
                "win_probability": 10,
            },
        )

        resp = await async_client.get(
            "/api/v1/opportunities?q=磁传感器&page_size=1", headers=auth_headers
        )

        assert resp.status_code == 200
        payload = resp.json()["data"]
        assert payload["total"] == 1
        assert payload["list"][0]["id"] == target.json()["data"]["id"]

    async def test_create_opportunity(
        self, async_client: AsyncClient, auth_headers: dict, test_customer: dict
    ):
        resp = await async_client.post(
            "/api/v1/opportunities",
            headers=auth_headers,
            json={
                "title": "测试商机",
                "customer_id": test_customer["id"],
                "amount": 50000,
                "stage": "lead",
                "win_probability": 10,
            },
        )
        assert resp.status_code == 201
        assert resp.json()["code"] == 0
        assert "id" in resp.json()["data"]

    async def test_get_opportunity(
        self, async_client: AsyncClient, auth_headers: dict, test_customer: dict
    ):
        create = await async_client.post(
            "/api/v1/opportunities",
            headers=auth_headers,
            json={
                "title": "查单条",
                "customer_id": test_customer["id"],
                "amount": 10000,
                "stage": "lead",
                "win_probability": 10,
            },
        )
        opp_id = create.json()["data"]["id"]
        resp = await async_client.get(
            f"/api/v1/opportunities/{opp_id}", headers=auth_headers
        )
        assert resp.status_code == 200
        assert resp.json()["data"]["title"] == "查单条"

    async def test_get_opportunity_with_ai_serializes_expected_close_date(
        self,
        async_client: AsyncClient,
        auth_headers: dict,
        test_customer: dict,
        monkeypatch,
    ):
        from app.services import sales_ai_service

        async def fake_enrich_opportunity(db, opp):
            return {
                "risk_level": "low",
                "win_probability": 60,
                "next_best_action": None,
                "key_concerns": [],
            }

        monkeypatch.setattr(
            sales_ai_service, "enrich_opportunity", fake_enrich_opportunity
        )

        create = await async_client.post(
            "/api/v1/opportunities",
            headers=auth_headers,
            json={
                "title": "带预计关闭日期",
                "customer_id": test_customer["id"],
                "amount": 10000,
                "stage": "lead",
                "win_probability": 10,
                "expected_close_date": "2026-05-30T10:00:00Z",
            },
        )
        opp_id = create.json()["data"]["id"]

        resp = await async_client.get(
            f"/api/v1/opportunities/{opp_id}?include_ai=true", headers=auth_headers
        )

        assert resp.status_code == 200
        payload = resp.json()
        assert payload["code"] == 0
        assert payload["data"]["expected_close_date"].startswith("2026-05-30T10:00:00")

    async def test_get_opportunity_not_found(
        self, async_client: AsyncClient, auth_headers: dict
    ):
        resp = await async_client.get(
            "/api/v1/opportunities/99999", headers=auth_headers
        )
        assert resp.status_code == 404
        assert resp.json()["code"] == 404

    async def test_update_opportunity(
        self, async_client: AsyncClient, auth_headers: dict, test_customer: dict
    ):
        create = await async_client.post(
            "/api/v1/opportunities",
            headers=auth_headers,
            json={
                "title": "原始名称",
                "customer_id": test_customer["id"],
                "amount": 10000,
                "stage": "lead",
                "win_probability": 10,
            },
        )
        opp_id = create.json()["data"]["id"]
        resp = await async_client.put(
            f"/api/v1/opportunities/{opp_id}",
            headers=auth_headers,
            json={"title": "新名称", "stage": "qualified"},
        )
        assert resp.status_code == 200
        assert resp.json()["code"] == 0

    async def test_delete_opportunity(
        self, async_client: AsyncClient, auth_headers: dict, test_customer: dict
    ):
        create = await async_client.post(
            "/api/v1/opportunities",
            headers=auth_headers,
            json={
                "title": "待删除",
                "customer_id": test_customer["id"],
                "amount": 10000,
                "stage": "lead",
                "win_probability": 10,
            },
        )
        opp_id = create.json()["data"]["id"]
        resp = await async_client.delete(
            f"/api/v1/opportunities/{opp_id}", headers=auth_headers
        )
        assert resp.status_code == 200
        assert resp.json()["code"] == 0

    async def test_batch_update(
        self, async_client: AsyncClient, auth_headers: dict, test_customer: dict
    ):
        c1 = await async_client.post(
            "/api/v1/opportunities",
            headers=auth_headers,
            json={
                "title": "批量1",
                "customer_id": test_customer["id"],
                "amount": 10000,
                "stage": "lead",
                "win_probability": 10,
            },
        )
        c2 = await async_client.post(
            "/api/v1/opportunities",
            headers=auth_headers,
            json={
                "title": "批量2",
                "customer_id": test_customer["id"],
                "amount": 20000,
                "stage": "lead",
                "win_probability": 10,
            },
        )
        ids = [c1.json()["data"]["id"], c2.json()["data"]["id"]]
        resp = await async_client.post(
            "/api/v1/opportunities/batch-update",
            headers=auth_headers,
            json={"ids": ids, "stage": "qualified"},
        )
        assert resp.status_code == 200
        assert resp.json()["data"]["updated"] == 2

    async def test_batch_delete(
        self, async_client: AsyncClient, auth_headers: dict, test_customer: dict
    ):
        c1 = await async_client.post(
            "/api/v1/opportunities",
            headers=auth_headers,
            json={
                "title": "删1",
                "customer_id": test_customer["id"],
                "amount": 10000,
                "stage": "lead",
                "win_probability": 10,
            },
        )
        c2 = await async_client.post(
            "/api/v1/opportunities",
            headers=auth_headers,
            json={
                "title": "删2",
                "customer_id": test_customer["id"],
                "amount": 10000,
                "stage": "lead",
                "win_probability": 10,
            },
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
    """Quotation CRUD + convert-to-order."""

    async def test_list_empty(self, async_client: AsyncClient, auth_headers: dict):
        resp = await async_client.get("/api/v1/quotations", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["code"] == 0

    async def test_create_quotation(
        self, async_client: AsyncClient, auth_headers: dict, test_customer: dict
    ):
        resp = await async_client.post(
            "/api/v1/quotations",
            headers=auth_headers,
            json={
                "customer_id": test_customer["id"],
                "status": "draft",
                "total_amount": 30000,
                "items": [
                    {
                        "product_name": "Test",
                        "quantity": 10,
                        "unit_price": 5,
                        "cost_price": 3,
                    }
                ],
            },
        )
        assert resp.status_code == 201
        assert resp.json()["code"] == 0
        assert "quotation_no" in resp.json()["data"]
        assert resp.json()["data"]["total_amount"] == 50
        item = resp.json()["data"]["items"][0]
        assert item["cost_price"] == 3
        assert item["untaxed_cost"] == 30
        assert round(item["taxed_cost"], 2) == 33.90
        assert round(item["sales_profit"], 2) == 16.10

    async def test_list_searches_quotation_product_lines(
        self, async_client: AsyncClient, auth_headers: dict, test_customer: dict
    ):
        target = await async_client.post(
            "/api/v1/quotations",
            headers=auth_headers,
            json={
                "customer_id": test_customer["id"],
                "status": "draft",
                "total_amount": 1200,
                "items": [
                    {
                        "product_name": "QST-QMI8658X",
                        "quantity": 10,
                        "unit_price": 120,
                        "total_price": 1200,
                    }
                ],
            },
        )
        await async_client.post(
            "/api/v1/quotations",
            headers=auth_headers,
            json={
                "customer_id": test_customer["id"],
                "status": "draft",
                "total_amount": 100,
                "items": [
                    {
                        "product_name": "NOHIT-QUOTE",
                        "quantity": 1,
                        "unit_price": 100,
                        "total_price": 100,
                    }
                ],
            },
        )

        resp = await async_client.get(
            "/api/v1/quotations?q=QMI8658X&page_size=1", headers=auth_headers
        )

        assert resp.status_code == 200
        payload = resp.json()["data"]
        assert payload["total"] == 1
        assert payload["list"][0]["id"] == target.json()["data"]["id"]

    async def test_get_quotation(
        self, async_client: AsyncClient, auth_headers: dict, test_customer: dict
    ):
        c = await async_client.post(
            "/api/v1/quotations",
            headers=auth_headers,
            json={
                "customer_id": test_customer["id"],
                "status": "draft",
                "total_amount": 30000,
                "items": [
                    {
                        "product_name": "Test",
                        "quantity": 10,
                        "unit_price": 5,
                        "total_price": 50,
                    }
                ],
            },
        )
        quo_id = c.json()["data"]["id"]
        resp = await async_client.get(
            f"/api/v1/quotations/{quo_id}", headers=auth_headers
        )
        assert resp.status_code == 200
        assert resp.json()["data"]["id"] == quo_id

    async def test_quotation_response_includes_customer_name(
        self,
        async_client: AsyncClient,
        auth_headers: dict,
        test_customer: dict,
    ):
        """Quotation response must include denormalized customer_name to avoid N+1."""
        # Create a quotation tied to a real customer
        customer_name = test_customer["name"]
        c = await async_client.post(
            "/api/v1/quotations",
            headers=auth_headers,
            json={
                "customer_id": test_customer["id"],
                "status": "draft",
                "total_amount": 5000,
                "items": [
                    {
                        "product_name": "Chip-X",
                        "quantity": 1,
                        "unit_price": 100,
                        "total_price": 100,
                    }
                ],
            },
        )
        assert c.status_code == 201, c.text
        quo_id = c.json()["data"]["id"]

        # List endpoint
        list_resp = await async_client.get("/api/v1/quotations", headers=auth_headers)
        assert list_resp.status_code == 200
        items = list_resp.json()["data"]["list"]
        match = next((q for q in items if q["id"] == quo_id), None)
        assert match is not None, "newly created quotation not in list"
        assert match.get("customer_id") == test_customer["id"]
        assert (
            match.get("customer_name") == customer_name
        ), f"BUG: list response missing customer_name (got {match.get('customer_name')!r})"

        # Detail endpoint
        detail_resp = await async_client.get(
            f"/api/v1/quotations/{quo_id}", headers=auth_headers
        )
        assert detail_resp.status_code == 200
        detail = detail_resp.json()["data"]
        assert detail.get("customer_name") == customer_name

        # Update endpoint
        upd_resp = await async_client.put(
            f"/api/v1/quotations/{quo_id}",
            headers=auth_headers,
            json={"status": "sent"},
        )
        assert upd_resp.status_code == 200
        assert upd_resp.json()["data"].get("customer_name") == customer_name

    async def test_update_quotation(
        self, async_client: AsyncClient, auth_headers: dict, test_customer: dict
    ):
        c = await async_client.post(
            "/api/v1/quotations",
            headers=auth_headers,
            json={
                "customer_id": test_customer["id"],
                "status": "draft",
                "total_amount": 30000,
                "items": [
                    {
                        "product_name": "Test",
                        "quantity": 10,
                        "unit_price": 5,
                        "total_price": 50,
                    }
                ],
            },
        )
        quo_id = c.json()["data"]["id"]
        resp = await async_client.put(
            f"/api/v1/quotations/{quo_id}",
            headers=auth_headers,
            json={"status": "sent"},
        )
        assert resp.status_code == 200

    async def test_update_quotation_replaces_items_without_returning_deleted_rows(
        self,
        async_client: AsyncClient,
        auth_headers: dict,
        test_customer: dict,
    ):
        created = await async_client.post(
            "/api/v1/quotations",
            headers=auth_headers,
            json={
                "customer_id": test_customer["id"],
                "status": "draft",
                "items": [
                    {"product_name": "Old Item", "quantity": 1, "unit_price": 10}
                ],
            },
        )
        quote_id = created.json()["data"]["id"]

        first = await async_client.put(
            f"/api/v1/quotations/{quote_id}",
            headers=auth_headers,
            json={
                "items": [
                    {
                        "product_name": "New Item",
                        "quantity": 2,
                        "unit_price": 20,
                        "cost_price": 5,
                    }
                ],
            },
        )
        assert first.status_code == 200

        second = await async_client.put(
            f"/api/v1/quotations/{quote_id}",
            headers=auth_headers,
            json={
                "items": [
                    {
                        "product_name": "Final Item",
                        "quantity": 3,
                        "unit_price": 30,
                        "cost_price": 10,
                    }
                ],
            },
        )
        assert second.status_code == 200
        items = second.json()["data"]["items"]
        assert len(items) == 1
        assert items[0]["product_name"] == "Final Item"
        assert items[0]["total_price"] == 90

    async def test_delete_quotation(
        self, async_client: AsyncClient, auth_headers: dict, test_customer: dict
    ):
        c = await async_client.post(
            "/api/v1/quotations",
            headers=auth_headers,
            json={
                "customer_id": test_customer["id"],
                "status": "draft",
                "total_amount": 30000,
                "items": [
                    {
                        "product_name": "Test",
                        "quantity": 10,
                        "unit_price": 5,
                        "total_price": 50,
                    }
                ],
            },
        )
        quo_id = c.json()["data"]["id"]
        resp = await async_client.delete(
            f"/api/v1/quotations/{quo_id}", headers=auth_headers
        )
        assert resp.status_code == 200
        assert resp.json()["code"] == 0

    async def test_convert_quotation_to_order(
        self, async_client: AsyncClient, auth_headers: dict, test_customer: dict
    ):
        quo = await async_client.post(
            "/api/v1/quotations",
            headers=auth_headers,
            json={
                "customer_id": test_customer["id"],
                "status": "draft",
                "total_amount": 30000,
                "items": [
                    {
                        "product_name": "Test",
                        "quantity": 10,
                        "unit_price": 5,
                        "total_price": 50,
                    }
                ],
            },
        )
        quo_id = quo.json()["data"]["id"]
        resp = await async_client.post(
            f"/api/v1/quotations/{quo_id}/convert-to-order",
            headers=auth_headers,
        )
        assert resp.status_code == 200
        assert "document_no" in resp.json()["data"]

    async def test_batch_delete_quotations(
        self, async_client: AsyncClient, auth_headers: dict, test_customer: dict
    ):
        payload = {
            "customer_id": test_customer["id"],
            "status": "draft",
            "total_amount": 30000,
            "items": [
                {
                    "product_name": "Test",
                    "quantity": 10,
                    "unit_price": 5,
                    "total_price": 50,
                }
            ],
        }
        c1 = await async_client.post(
            "/api/v1/quotations", headers=auth_headers, json=payload
        )
        c2 = await async_client.post(
            "/api/v1/quotations", headers=auth_headers, json=payload
        )
        ids = [c1.json()["data"]["id"], c2.json()["data"]["id"]]
        resp = await async_client.post(
            "/api/v1/quotations/batch-delete",
            headers=auth_headers,
            json={"ids": ids},
        )
        assert resp.status_code == 200
        assert resp.json()["data"]["deleted"] == 2

    async def test_quotation_stats_duplicate_and_status(
        self, async_client: AsyncClient, auth_headers: dict, test_customer: dict
    ):
        created = await async_client.post(
            "/api/v1/quotations",
            headers=auth_headers,
            json={
                "customer_id": test_customer["id"],
                "status": "draft",
                "items": [
                    {"product_name": "Stats Test", "quantity": 2, "unit_price": 12.5}
                ],
            },
        )
        quote = created.json()["data"]

        stats = await async_client.get("/api/v1/quotations/stats", headers=auth_headers)
        assert stats.status_code == 200
        assert stats.json()["data"]["total"] >= 1
        assert "quote_to_order_rate" in stats.json()["data"]

        status = await async_client.put(
            f"/api/v1/quotations/{quote['id']}/status",
            headers=auth_headers,
            json={"status": "sent"},
        )
        assert status.status_code == 200
        assert status.json()["data"]["status"] == "sent"

        lost = await async_client.put(
            f"/api/v1/quotations/{quote['id']}/status",
            headers=auth_headers,
            json={"status": "lost"},
        )
        assert lost.status_code == 200
        assert lost.json()["data"]["status"] == "lost"

        duplicate = await async_client.post(
            f"/api/v1/quotations/{quote['id']}/duplicate",
            headers=auth_headers,
        )
        assert duplicate.status_code == 201
        assert duplicate.json()["data"]["id"] != quote["id"]
        assert duplicate.json()["data"]["status"] == "draft"
        assert duplicate.json()["data"]["total_amount"] == quote["total_amount"]


class TestSalesOrders:
    """SalesOrder CRUD + convert-to-delivery."""

    async def test_list_empty(self, async_client: AsyncClient, auth_headers: dict):
        resp = await async_client.get("/api/v1/sales-orders", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["code"] == 0

    async def test_create_sales_order(
        self, async_client: AsyncClient, auth_headers: dict, test_customer: dict
    ):
        resp = await async_client.post(
            "/api/v1/sales-orders",
            headers=auth_headers,
            json={
                "customer_id": test_customer["id"],
                "status": "pending",
                "total_amount": 50000,
                "items": [
                    {
                        "product_name": "Test",
                        "quantity": 5,
                        "unit_price": 10,
                        "total_price": 50,
                    }
                ],
            },
        )
        assert resp.status_code == 201
        assert resp.json()["code"] == 0
        assert "order_no" in resp.json()["data"]

    async def test_list_searches_sales_order_product_lines(
        self, async_client: AsyncClient, auth_headers: dict, test_customer: dict
    ):
        target = await async_client.post(
            "/api/v1/sales-orders",
            headers=auth_headers,
            json={
                "customer_id": test_customer["id"],
                "status": "pending",
                "total_amount": 600,
                "items": [
                    {
                        "product_name": "WK2212-SALES-SEARCH",
                        "quantity": 3,
                        "unit_price": 200,
                        "total_price": 600,
                    }
                ],
            },
        )
        await async_client.post(
            "/api/v1/sales-orders",
            headers=auth_headers,
            json={
                "customer_id": test_customer["id"],
                "status": "pending",
                "total_amount": 200,
                "items": [
                    {
                        "product_name": "NOHIT-ORDER",
                        "quantity": 1,
                        "unit_price": 200,
                        "total_price": 200,
                    }
                ],
            },
        )

        resp = await async_client.get(
            "/api/v1/sales-orders?q=WK2212-SALES&page_size=1", headers=auth_headers
        )

        assert resp.status_code == 200
        payload = resp.json()["data"]
        assert payload["total"] == 1
        assert payload["list"][0]["id"] == target.json()["data"]["id"]

    async def test_get_sales_order(
        self, async_client: AsyncClient, auth_headers: dict, test_customer: dict
    ):
        c = await async_client.post(
            "/api/v1/sales-orders",
            headers=auth_headers,
            json={
                "customer_id": test_customer["id"],
                "status": "pending",
                "total_amount": 50000,
                "items": [
                    {
                        "product_name": "Test",
                        "quantity": 5,
                        "unit_price": 10,
                        "total_price": 50,
                    }
                ],
            },
        )
        order_id = c.json()["data"]["id"]
        resp = await async_client.get(
            f"/api/v1/sales-orders/{order_id}", headers=auth_headers
        )
        assert resp.status_code == 200
        assert resp.json()["data"]["id"] == order_id

    async def test_sales_order_response_includes_customer_name(
        self,
        async_client: AsyncClient,
        auth_headers: dict,
        test_customer: dict,
    ):
        """Sales order response must include denormalized customer_name."""
        customer_name = test_customer["name"]
        create_resp = await async_client.post(
            "/api/v1/sales-orders",
            headers=auth_headers,
            json={
                "customer_id": test_customer["id"],
                "status": "pending",
                "items": [
                    {
                        "product_name": "X",
                        "quantity": 1,
                        "unit_price": 100,
                        "total_price": 100,
                    }
                ],
            },
        )
        assert create_resp.status_code == 201, create_resp.text
        order_id = create_resp.json()["data"]["id"]

        # List
        list_resp = await async_client.get("/api/v1/sales-orders", headers=auth_headers)
        assert list_resp.status_code == 200
        items = list_resp.json()["data"]["list"]
        match = next((o for o in items if o["id"] == order_id), None)
        assert match is not None, "newly created order not in list"
        assert match.get("customer_id") == test_customer["id"]
        assert (
            match.get("customer_name") == customer_name
        ), f"BUG: order list missing customer_name (got {match.get('customer_name')!r})"

        # Detail
        detail_resp = await async_client.get(
            f"/api/v1/sales-orders/{order_id}", headers=auth_headers
        )
        assert detail_resp.status_code == 200
        assert detail_resp.json()["data"].get("customer_name") == customer_name

    async def test_update_sales_order(
        self, async_client: AsyncClient, auth_headers: dict, test_customer: dict
    ):
        c = await async_client.post(
            "/api/v1/sales-orders",
            headers=auth_headers,
            json={
                "customer_id": test_customer["id"],
                "status": "pending",
                "total_amount": 50000,
                "items": [
                    {
                        "product_name": "Test",
                        "quantity": 5,
                        "unit_price": 10,
                        "total_price": 50,
                    }
                ],
            },
        )
        order_id = c.json()["data"]["id"]
        resp = await async_client.put(
            f"/api/v1/sales-orders/{order_id}",
            headers=auth_headers,
            json={"status": "confirmed"},
        )
        assert resp.status_code == 200

    async def test_update_sales_order_replaces_items(
        self,
        async_client: AsyncClient,
        auth_headers: dict,
        test_customer: dict,
    ):
        created = await async_client.post(
            "/api/v1/sales-orders",
            headers=auth_headers,
            json={
                "customer_id": test_customer["id"],
                "status": "pending",
                "items": [
                    {"product_name": "Old Order Item", "quantity": 1, "unit_price": 10}
                ],
            },
        )
        order_id = created.json()["data"]["id"]

        resp = await async_client.put(
            f"/api/v1/sales-orders/{order_id}",
            headers=auth_headers,
            json={
                "items": [
                    {"product_name": "New Order Item", "quantity": 4, "unit_price": 25}
                ],
            },
        )

        assert resp.status_code == 200
        items = resp.json()["data"]["items"]
        assert len(items) == 1
        assert items[0]["product_name"] == "New Order Item"
        assert items[0]["total_price"] == 100
        assert resp.json()["data"]["total_amount"] == 100

    async def test_delete_sales_order(
        self, async_client: AsyncClient, auth_headers: dict, test_customer: dict
    ):
        c = await async_client.post(
            "/api/v1/sales-orders",
            headers=auth_headers,
            json={
                "customer_id": test_customer["id"],
                "status": "pending",
                "total_amount": 50000,
                "items": [
                    {
                        "product_name": "Test",
                        "quantity": 5,
                        "unit_price": 10,
                        "total_price": 50,
                    }
                ],
            },
        )
        order_id = c.json()["data"]["id"]
        resp = await async_client.delete(
            f"/api/v1/sales-orders/{order_id}", headers=auth_headers
        )
        assert resp.status_code == 200
        assert resp.json()["code"] == 0

    async def test_convert_order_to_delivery(
        self, async_client: AsyncClient, auth_headers: dict, test_customer: dict
    ):
        order = await async_client.post(
            "/api/v1/sales-orders",
            headers=auth_headers,
            json={
                "customer_id": test_customer["id"],
                "status": "pending",
                "total_amount": 50000,
                "items": [
                    {
                        "product_name": "Test",
                        "quantity": 5,
                        "unit_price": 10,
                        "total_price": 50,
                    }
                ],
            },
        )
        order_id = order.json()["data"]["id"]
        resp = await async_client.post(
            f"/api/v1/sales-orders/{order_id}/convert-to-delivery",
            headers=auth_headers,
        )
        assert resp.status_code == 200
        assert "document_no" in resp.json()["data"]

    async def test_download_sales_order_pdf(
        self, async_client: AsyncClient, auth_headers: dict, test_customer: dict
    ):
        order = await async_client.post(
            "/api/v1/sales-orders",
            headers=auth_headers,
            json={
                "customer_id": test_customer["id"],
                "status": "confirmed",
                "items": [
                    {"product_name": "PDF Order Item", "quantity": 2, "unit_price": 50}
                ],
            },
        )
        order_id = order.json()["data"]["id"]

        resp = await async_client.get(
            f"/api/v1/sales-orders/{order_id}/pdf", headers=auth_headers
        )

        assert resp.status_code == 200
        assert resp.headers["content-type"] == "application/pdf"
        assert resp.content.startswith(b"%PDF")

    async def test_import_sales_order_pdf(
        self,
        async_client: AsyncClient,
        auth_headers: dict,
        test_customer: dict,
        monkeypatch,
    ):
        from app.services import sales_order_pdf_import

        monkeypatch.setattr(
            sales_order_pdf_import,
            "extract_pdf_text",
            lambda _content: (
                "Order No: PO-20260529\n"
                f"Customer: {test_customer['name']}\n"
                "Order Date: 2026-05-20\n"
                "Delivery Date: 2026-05-30\n"
                "ABC-100 2 15 30\n"
                "XYZ-200 3 20 60\n"
                "Total Amount: 90\n"
            ),
        )

        resp = await async_client.post(
            "/api/v1/sales-orders/import-pdf",
            headers=auth_headers,
            files={"file": ("customer_order.pdf", b"%PDF-1.4", "application/pdf")},
        )

        assert resp.status_code == 201
        payload = resp.json()["data"]
        assert payload["order_no"] == "PO-20260529"
        assert payload["customer_id"] == test_customer["id"]
        assert payload["parsed"]["item_count"] == 2
        assert payload["parsed"]["total_amount"] == 90

        order = await async_client.get(
            f"/api/v1/sales-orders/{payload['id']}", headers=auth_headers
        )
        assert order.status_code == 200
        assert len(order.json()["data"]["items"]) == 2

    async def test_convert_order_twice_fails(
        self, async_client: AsyncClient, auth_headers: dict, test_customer: dict
    ):
        order = await async_client.post(
            "/api/v1/sales-orders",
            headers=auth_headers,
            json={
                "customer_id": test_customer["id"],
                "status": "pending",
                "total_amount": 50000,
                "items": [
                    {
                        "product_name": "Test",
                        "quantity": 5,
                        "unit_price": 10,
                        "total_price": 50,
                    }
                ],
            },
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
        assert resp.status_code == 409

    async def test_batch_delete_orders(
        self, async_client: AsyncClient, auth_headers: dict, test_customer: dict
    ):
        payload = {
            "customer_id": test_customer["id"],
            "status": "pending",
            "total_amount": 50000,
            "items": [
                {
                    "product_name": "Test",
                    "quantity": 5,
                    "unit_price": 10,
                    "total_price": 50,
                }
            ],
        }
        c1 = await async_client.post(
            "/api/v1/sales-orders", headers=auth_headers, json=payload
        )
        c2 = await async_client.post(
            "/api/v1/sales-orders", headers=auth_headers, json=payload
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
    """DeliveryNote CRUD."""

    async def _create_order(self, async_client, auth_headers, customer_id, product_name="Test"):
        resp = await async_client.post(
            "/api/v1/sales-orders",
            headers=auth_headers,
            json={
                "customer_id": customer_id,
                "status": "pending",
                "total_amount": 200,
                "items": [
                    {
                        "product_name": product_name,
                        "quantity": 20,
                        "unit_price": 10,
                        "total_price": 200,
                    }
                ],
            },
        )
        assert resp.status_code == 201
        return resp.json()["data"]["id"]

    async def test_list_empty(self, async_client: AsyncClient, auth_headers: dict):
        resp = await async_client.get("/api/v1/delivery-notes", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["code"] == 0

    async def test_create_delivery_note(
        self, async_client: AsyncClient, auth_headers: dict, test_customer: dict
    ):
        order_id = await self._create_order(
            async_client, auth_headers, test_customer["id"]
        )
        resp = await async_client.post(
            "/api/v1/delivery-notes",
            headers=auth_headers,
            json={
                "customer_id": test_customer["id"],
                "sales_order_id": order_id,
                "status": "pending",
                "items": [{"product_name": "Test", "quantity": 20}],
            },
        )
        assert resp.status_code == 201
        assert resp.json()["code"] == 0
        assert "delivery_no" in resp.json()["data"]

    async def test_list_searches_delivery_product_lines(
        self, async_client: AsyncClient, auth_headers: dict, test_customer: dict
    ):
        target_order_id = await self._create_order(
            async_client, auth_headers, test_customer["id"], "SCT-DELIVERY-SEARCH"
        )
        other_order_id = await self._create_order(
            async_client, auth_headers, test_customer["id"], "NOHIT-DELIVERY"
        )
        target = await async_client.post(
            "/api/v1/delivery-notes",
            headers=auth_headers,
            json={
                "customer_id": test_customer["id"],
                "sales_order_id": target_order_id,
                "status": "pending",
                "items": [{"product_name": "SCT-DELIVERY-SEARCH", "quantity": 20}],
            },
        )
        await async_client.post(
            "/api/v1/delivery-notes",
            headers=auth_headers,
            json={
                "customer_id": test_customer["id"],
                "sales_order_id": other_order_id,
                "status": "pending",
                "items": [{"product_name": "NOHIT-DELIVERY", "quantity": 20}],
            },
        )

        resp = await async_client.get(
            "/api/v1/delivery-notes?q=SCT-DELIVERY&page_size=1", headers=auth_headers
        )

        assert resp.status_code == 200
        payload = resp.json()["data"]
        assert payload["total"] == 1
        assert payload["list"][0]["id"] == target.json()["data"]["id"]

    async def test_create_delivery_note_uses_sales_order_customer(
        self,
        async_client: AsyncClient,
        auth_headers: dict,
        test_customer: dict,
        db_session,
    ):
        from app.models.customer import Customer

        other_customer = Customer(name="不应关联客户", industry="电子", level="B")
        db_session.add(other_customer)
        await db_session.flush()

        order = await async_client.post(
            "/api/v1/sales-orders",
            headers=auth_headers,
            json={
                "customer_id": test_customer["id"],
                "status": "pending",
                "total_amount": 50000,
                "items": [
                    {
                        "product_name": "SO Item",
                        "quantity": 3,
                        "unit_price": 10,
                        "total_price": 30,
                    }
                ],
            },
        )
        order_id = order.json()["data"]["id"]

        resp = await async_client.post(
            "/api/v1/delivery-notes",
            headers=auth_headers,
            json={
                "customer_id": other_customer.id,
                "sales_order_id": order_id,
                "status": "pending",
            },
        )

        assert resp.status_code == 201
        payload = resp.json()["data"]
        assert payload["customer_id"] == test_customer["id"]
        assert payload["items"][0]["product_name"] == "SO Item"
        assert payload["items"][0]["quantity"] == 3

    async def test_get_delivery_note(
        self, async_client: AsyncClient, auth_headers: dict, test_customer: dict
    ):
        order_id = await self._create_order(
            async_client, auth_headers, test_customer["id"]
        )
        c = await async_client.post(
            "/api/v1/delivery-notes",
            headers=auth_headers,
            json={
                "customer_id": test_customer["id"],
                "sales_order_id": order_id,
                "status": "pending",
                "items": [{"product_name": "Test", "quantity": 20}],
            },
        )
        note_id = c.json()["data"]["id"]
        resp = await async_client.get(
            f"/api/v1/delivery-notes/{note_id}", headers=auth_headers
        )
        assert resp.status_code == 200
        assert resp.json()["data"]["id"] == note_id

    async def test_update_delivery_note(
        self, async_client: AsyncClient, auth_headers: dict, test_customer: dict
    ):
        order_id = await self._create_order(
            async_client, auth_headers, test_customer["id"]
        )
        c = await async_client.post(
            "/api/v1/delivery-notes",
            headers=auth_headers,
            json={
                "customer_id": test_customer["id"],
                "sales_order_id": order_id,
                "status": "pending",
                "items": [{"product_name": "Test", "quantity": 20}],
            },
        )
        note_id = c.json()["data"]["id"]
        resp = await async_client.put(
            f"/api/v1/delivery-notes/{note_id}",
            headers=auth_headers,
            json={"status": "delivered"},
        )
        assert resp.status_code == 200

    async def test_delete_delivery_note(
        self, async_client: AsyncClient, auth_headers: dict, test_customer: dict
    ):
        order_id = await self._create_order(
            async_client, auth_headers, test_customer["id"]
        )
        c = await async_client.post(
            "/api/v1/delivery-notes",
            headers=auth_headers,
            json={
                "customer_id": test_customer["id"],
                "sales_order_id": order_id,
                "status": "pending",
                "items": [{"product_name": "Test", "quantity": 20}],
            },
        )
        note_id = c.json()["data"]["id"]
        resp = await async_client.delete(
            f"/api/v1/delivery-notes/{note_id}", headers=auth_headers
        )
        assert resp.status_code == 200
        assert resp.json()["code"] == 0

    async def test_batch_delete_notes(
        self, async_client: AsyncClient, auth_headers: dict, test_customer: dict
    ):
        order_id = await self._create_order(
            async_client, auth_headers, test_customer["id"]
        )
        payload = {
            "customer_id": test_customer["id"],
            "sales_order_id": order_id,
            "status": "pending",
            "items": [{"product_name": "Test", "quantity": 20}],
        }
        c1 = await async_client.post(
            "/api/v1/delivery-notes", headers=auth_headers, json=payload
        )
        c2 = await async_client.post(
            "/api/v1/delivery-notes", headers=auth_headers, json=payload
        )
        ids = [c1.json()["data"]["id"], c2.json()["data"]["id"]]
        resp = await async_client.post(
            "/api/v1/delivery-notes/batch-delete",
            headers=auth_headers,
            json={"ids": ids},
        )
        assert resp.status_code == 200
        assert resp.json()["data"]["deleted"] == 2


class TestConversions:
    """Integration tests for cross-entity conversion endpoints."""

    async def _create_order(self, async_client, auth_headers, customer_id, **kw):
        r = await async_client.post(
            "/api/v1/sales-orders",
            headers=auth_headers,
            json={
                "customer_id": customer_id,
                "status": "pending",
                "total_amount": 50000,
                "items": [
                    {"product_name": "ConvTest", "quantity": 5, "unit_price": 10000}
                ],
                **kw,
            },
        )
        return r.json()["data"]["id"]

    async def _create_delivery(self, async_client, auth_headers, customer_id, order_id):
        r = await async_client.post(
            "/api/v1/delivery-notes",
            headers=auth_headers,
            json={
                "customer_id": customer_id,
                "sales_order_id": order_id,
                "status": "pending",
                "items": [{"product_name": "ConvTest", "quantity": 3}],
            },
        )
        return r.json()["data"]["id"]

    # ── v1 convert-to-delivery ───────────────────────────────────────

    async def test_convert_to_delivery_auto_transitions_order(
        self, async_client: AsyncClient, auth_headers: dict, test_customer: dict
    ):
        """convert-to-delivery should auto-transition order pending→confirmed."""
        order_id = await self._create_order(
            async_client, auth_headers, test_customer["id"]
        )
        r = await async_client.post(
            f"/api/v1/sales-orders/{order_id}/convert-to-delivery", headers=auth_headers
        )
        assert r.status_code == 200
        # Verify order was auto-transitioned
        order_r = await async_client.get(
            f"/api/v1/sales-orders/{order_id}", headers=auth_headers
        )
        assert order_r.json()["data"]["status"] == "confirmed"

    async def test_convert_to_delivery_twice_returns_existing_note(
        self, async_client: AsyncClient, auth_headers: dict, test_customer: dict
    ):
        """Repeated conversion is idempotent and returns the original note."""
        order_id = await self._create_order(
            async_client, auth_headers, test_customer["id"]
        )
        first = await async_client.post(
            f"/api/v1/sales-orders/{order_id}/convert-to-delivery", headers=auth_headers
        )
        second = await async_client.post(
            f"/api/v1/sales-orders/{order_id}/convert-to-delivery", headers=auth_headers
        )
        assert first.status_code == 200
        assert second.status_code == 200
        assert second.json()["data"]["id"] == first.json()["data"]["id"]

    # ── v1 convert-to-invoice ────────────────────────────────────────

    async def test_convert_delivery_to_invoice_success(
        self, async_client: AsyncClient, auth_headers: dict, test_customer: dict
    ):
        """delivered note → invoice should succeed."""
        order_id = await self._create_order(
            async_client, auth_headers, test_customer["id"]
        )
        note_id = await self._create_delivery(
            async_client, auth_headers, test_customer["id"], order_id
        )
        # Transition delivery to delivered first
        await async_client.put(
            f"/api/v1/delivery-notes/{note_id}",
            headers=auth_headers,
            json={"status": "delivered"},
        )
        r = await async_client.post(
            f"/api/v1/delivery-notes/{note_id}/convert-to-invoice", headers=auth_headers
        )
        assert r.status_code == 200
        assert r.json()["code"] == 0
        assert r.json()["data"]["document_no"].startswith("INV")

    async def test_convert_delivery_to_invoice_rejects_pending(
        self, async_client: AsyncClient, auth_headers: dict, test_customer: dict
    ):
        """pending note must NOT convert to invoice."""
        order_id = await self._create_order(
            async_client, auth_headers, test_customer["id"]
        )
        note_id = await self._create_delivery(
            async_client, auth_headers, test_customer["id"], order_id
        )
        r = await async_client.post(
            f"/api/v1/delivery-notes/{note_id}/convert-to-invoice", headers=auth_headers
        )
        assert r.json()["code"] == 409

    async def test_convert_delivery_to_invoice_duplicate_fails(
        self, async_client: AsyncClient, auth_headers: dict, test_customer: dict
    ):
        """Second invoice conversion for same order must fail."""
        order_id = await self._create_order(
            async_client, auth_headers, test_customer["id"]
        )
        note_id = await self._create_delivery(
            async_client, auth_headers, test_customer["id"], order_id
        )
        await async_client.put(
            f"/api/v1/delivery-notes/{note_id}",
            headers=auth_headers,
            json={"status": "delivered"},
        )
        r1 = await async_client.post(
            f"/api/v1/delivery-notes/{note_id}/convert-to-invoice", headers=auth_headers
        )
        assert r1.json()["code"] == 0
        r2 = await async_client.post(
            f"/api/v1/delivery-notes/{note_id}/convert-to-invoice", headers=auth_headers
        )
        assert r2.json()["code"] == 409

    # ── v2 endpoints ─────────────────────────────────────────────────

    async def test_v2_convert_order_to_delivery(
        self, async_client: AsyncClient, auth_headers: dict, test_customer: dict
    ):
        """v2 convert-to-delivery should create DN and transition order."""
        order_id = await self._create_order(
            async_client, auth_headers, test_customer["id"]
        )
        r = await async_client.post(
            f"/api/v1/sales-v2/orders/{order_id}/convert-to-delivery",
            headers=auth_headers,
        )
        assert r.status_code == 200
        assert r.json()["code"] == 0
        data = r.json()["data"]
        assert "delivery_no" in data

    async def test_v2_convert_delivery_to_invoice(
        self, async_client: AsyncClient, auth_headers: dict, test_customer: dict
    ):
        """v2 delivery→invoice should succeed for delivered note."""
        order_id = await self._create_order(
            async_client, auth_headers, test_customer["id"]
        )
        note_id = await self._create_delivery(
            async_client, auth_headers, test_customer["id"], order_id
        )
        await async_client.put(
            f"/api/v1/delivery-notes/{note_id}",
            headers=auth_headers,
            json={"status": "delivered"},
        )
        r = await async_client.post(
            f"/api/v1/sales-v2/delivery-notes/{note_id}/convert-to-invoice",
            headers=auth_headers,
        )
        assert r.status_code == 200
        assert r.json()["code"] == 0
        assert "invoice_no" in r.json()["data"]

    # ── Return note conversion ──────────────────────────────────────

    async def test_convert_delivery_to_return_success(
        self, async_client: AsyncClient, auth_headers: dict, test_customer: dict
    ):
        """delivered note → return note should succeed."""
        order_id = await self._create_order(
            async_client, auth_headers, test_customer["id"]
        )
        note_id = await self._create_delivery(
            async_client, auth_headers, test_customer["id"], order_id
        )
        await async_client.put(
            f"/api/v1/delivery-notes/{note_id}",
            headers=auth_headers,
            json={"status": "delivered"},
        )
        r = await async_client.post(
            f"/api/v1/delivery-notes/{note_id}/convert-to-return?reason=质量问题",
            headers=auth_headers,
        )
        assert r.status_code == 200
        assert r.json()["code"] == 0
        assert "RTN" in r.json()["data"]["document_no"]

    async def test_convert_delivery_to_return_rejects_pending(
        self, async_client: AsyncClient, auth_headers: dict, test_customer: dict
    ):
        """pending note must NOT convert to return."""
        order_id = await self._create_order(
            async_client, auth_headers, test_customer["id"]
        )
        note_id = await self._create_delivery(
            async_client, auth_headers, test_customer["id"], order_id
        )
        r = await async_client.post(
            f"/api/v1/delivery-notes/{note_id}/convert-to-return", headers=auth_headers
        )
        assert r.json()["code"] == 409

    async def test_convert_delivery_to_return_duplicate_fails(
        self, async_client: AsyncClient, auth_headers: dict, test_customer: dict
    ):
        """Second return for same delivery must fail."""
        order_id = await self._create_order(
            async_client, auth_headers, test_customer["id"]
        )
        note_id = await self._create_delivery(
            async_client, auth_headers, test_customer["id"], order_id
        )
        await async_client.put(
            f"/api/v1/delivery-notes/{note_id}",
            headers=auth_headers,
            json={"status": "delivered"},
        )
        r1 = await async_client.post(
            f"/api/v1/delivery-notes/{note_id}/convert-to-return", headers=auth_headers
        )
        assert r1.json()["code"] == 0
        r2 = await async_client.post(
            f"/api/v1/delivery-notes/{note_id}/convert-to-return", headers=auth_headers
        )
        assert r2.json()["code"] == 409


class TestSalesDashboard:
    """Sales dashboard endpoints."""

    async def test_overview(self, async_client: AsyncClient, auth_headers: dict):
        resp = await async_client.get(
            "/api/v1/sales/dashboard/overview", headers=auth_headers
        )
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert "funnel" in data
        assert "total_pipeline" in data

    async def test_trends(self, async_client: AsyncClient, auth_headers: dict):
        resp = await async_client.get(
            "/api/v1/sales/dashboard/trends", headers=auth_headers
        )
        assert resp.status_code == 200
        assert "trends" in resp.json()["data"]

    async def test_alerts(self, async_client: AsyncClient, auth_headers: dict):
        resp = await async_client.get(
            "/api/v1/sales/dashboard/alerts", headers=auth_headers
        )
        assert resp.status_code == 200
        assert "alerts" in resp.json()["data"]

    async def test_dashboard_unauthorized(self, async_client: AsyncClient):
        resp = await async_client.get("/api/v1/sales/dashboard/overview")
        assert resp.status_code == 401
