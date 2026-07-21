"""Batch operations — RED phase (tests before implementation)."""

from httpx import AsyncClient


class TestBatchConvertToInvoice:
    """POST /delivery-notes/batch-convert-to-invoice."""

    async def _create_order(self, async_client, auth_headers, customer_id):
        r = await async_client.post(
            "/api/v1/sales-orders",
            headers=auth_headers,
            json={
                "customer_id": customer_id,
                "status": "pending",
                "total_amount": 10000,
                "items": [
                    {"product_name": "Batch-Test", "quantity": 2, "unit_price": 5000}
                ],
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
                "items": [{"product_name": "Batch-Test", "quantity": 2}],
            },
        )
        note_id = r.json()["data"]["id"]
        await async_client.put(
            f"/api/v1/delivery-notes/{note_id}",
            headers=auth_headers,
            json={"status": "delivered"},
        )
        return note_id

    async def test_batch_convert_success(
        self, async_client: AsyncClient, auth_headers: dict, test_customer: dict
    ):
        """Batch convert 2 deliveries → 2 invoices."""
        cid = test_customer["id"]
        o1 = await self._create_order(async_client, auth_headers, cid)
        o2 = await self._create_order(async_client, auth_headers, cid)
        n1 = await self._create_delivery(async_client, auth_headers, cid, o1)
        n2 = await self._create_delivery(async_client, auth_headers, cid, o2)

        r = await async_client.post(
            "/api/v1/delivery-notes/batch-convert-to-invoice",
            headers=auth_headers,
            json={"ids": [n1, n2]},
        )
        assert r.status_code == 200
        data = r.json()["data"]
        assert data["succeeded"] == 2
        assert data["failed"] == 0

    async def test_batch_convert_partial_failure(
        self, async_client: AsyncClient, auth_headers: dict, test_customer: dict
    ):
        """Mix valid + invalid → partial success."""
        cid = test_customer["id"]
        o1 = await self._create_order(async_client, auth_headers, cid)
        n_valid = await self._create_delivery(async_client, auth_headers, cid, o1)

        r = await async_client.post(
            "/api/v1/delivery-notes/batch-convert-to-invoice",
            headers=auth_headers,
            json={"ids": [n_valid, 99999]},
        )
        assert r.status_code == 200
        data = r.json()["data"]
        assert data["succeeded"] == 1
        assert data["failed"] == 1

    async def test_batch_convert_empty_ids(
        self, async_client: AsyncClient, auth_headers: dict
    ):
        """Empty ID list → validation error."""
        r = await async_client.post(
            "/api/v1/delivery-notes/batch-convert-to-invoice",
            headers=auth_headers,
            json={"ids": []},
        )
        assert r.json()["code"] != 0


class TestBatchConfirmOrders:
    """POST /sales-orders/batch-confirm."""

    async def _create_order(self, async_client, auth_headers, customer_id):
        r = await async_client.post(
            "/api/v1/sales-orders",
            headers=auth_headers,
            json={
                "customer_id": customer_id,
                "status": "pending",
                "total_amount": 10000,
                "items": [
                    {"product_name": "Batch-Test", "quantity": 2, "unit_price": 5000}
                ],
            },
        )
        return r.json()["data"]["id"]

    async def test_batch_confirm_success(
        self, async_client: AsyncClient, auth_headers: dict, test_customer: dict
    ):
        """Batch confirm 2 pending orders."""
        cid = test_customer["id"]
        o1 = await self._create_order(async_client, auth_headers, cid)
        o2 = await self._create_order(async_client, auth_headers, cid)

        r = await async_client.post(
            "/api/v1/sales-orders/batch-confirm",
            headers=auth_headers,
            json={"ids": [o1, o2]},
        )
        assert r.status_code == 200
        data = r.json()["data"]
        assert data["succeeded"] == 2
        assert data["failed"] == 0

    async def test_batch_confirm_rejects_non_pending(
        self, async_client: AsyncClient, auth_headers: dict, test_customer: dict
    ):
        """Confirmed orders cannot be re-confirmed."""
        cid = test_customer["id"]
        o1 = await self._create_order(async_client, auth_headers, cid)
        await async_client.put(
            f"/api/v1/sales-orders/{o1}",
            headers=auth_headers,
            json={"status": "confirmed"},
        )
        r = await async_client.post(
            "/api/v1/sales-orders/batch-confirm",
            headers=auth_headers,
            json={"ids": [o1]},
        )
        data = r.json()["data"]
        assert data["failed"] == 1
