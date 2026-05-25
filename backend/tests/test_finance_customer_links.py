"""Finance document customer-link tests."""

from httpx import AsyncClient


async def _create_order(async_client: AsyncClient, auth_headers: dict, customer_id: int) -> int:
    resp = await async_client.post(
        "/api/v1/sales-orders",
        headers=auth_headers,
        json={
            "customer_id": customer_id,
            "status": "pending",
            "total_amount": 8000,
            "items": [{"product_name": "Finance Item", "quantity": 2, "unit_price": 10, "total_price": 20}],
        },
    )
    return resp.json()["data"]["id"]


class TestFinanceCustomerLinks:
    async def test_invoice_uses_sales_order_customer(
        self,
        async_client: AsyncClient,
        auth_headers: dict,
        test_customer: dict,
        db_session,
    ):
        from app.models.customer import Customer

        other_customer = Customer(name="发票错误客户", industry="电子", level="B")
        db_session.add(other_customer)
        await db_session.flush()
        order_id = await _create_order(async_client, auth_headers, test_customer["id"])

        resp = await async_client.post(
            "/api/v1/invoices",
            headers=auth_headers,
            json={
                "sales_order_id": order_id,
                "customer_id": other_customer.id,
                "amount": 8000,
                "tax_amount": 0,
            },
        )

        assert resp.status_code == 200
        assert resp.json()["data"]["customer_id"] == test_customer["id"]

    async def test_payment_uses_sales_order_customer(
        self,
        async_client: AsyncClient,
        auth_headers: dict,
        test_customer: dict,
        db_session,
    ):
        from app.models.customer import Customer

        other_customer = Customer(name="回款错误客户", industry="电子", level="B")
        db_session.add(other_customer)
        await db_session.flush()
        order_id = await _create_order(async_client, auth_headers, test_customer["id"])

        resp = await async_client.post(
            "/api/v1/payments",
            headers=auth_headers,
            json={
                "sales_order_id": order_id,
                "customer_id": other_customer.id,
                "amount": 8000,
            },
        )

        assert resp.status_code == 200
        payment_id = resp.json()["data"]["id"]
        detail = await async_client.get(f"/api/v1/payments/{payment_id}", headers=auth_headers)
        assert detail.json()["data"]["customer_id"] == test_customer["id"]

    async def test_contract_uses_sales_order_customer_when_order_linked(
        self,
        async_client: AsyncClient,
        auth_headers: dict,
        test_customer: dict,
        db_session,
    ):
        from app.models.customer import Customer

        other_customer = Customer(name="合同错误客户", industry="电子", level="B")
        db_session.add(other_customer)
        await db_session.flush()
        order_id = await _create_order(async_client, auth_headers, test_customer["id"])

        resp = await async_client.post(
            "/api/v1/contracts",
            headers=auth_headers,
            json={
                "sales_order_id": order_id,
                "customer_id": other_customer.id,
                "title": "订单合同",
                "amount": 8000,
            },
        )

        assert resp.status_code == 200
        assert resp.json()["data"]["customer_id"] == test_customer["id"]
