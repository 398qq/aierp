from httpx import AsyncClient


async def _create_product(client: AsyncClient, headers: dict, sku: str) -> int:
    response = await client.post(
        "/api/v1/products",
        headers=headers,
        json={"name": "工业控制模块", "sku": sku},
    )
    assert response.status_code == 201
    return response.json()["data"]["id"]


async def test_customer_product_code_crud_and_uniqueness(
    async_client: AsyncClient, auth_headers: dict, test_customer: dict
):
    product_id = await _create_product(async_client, auth_headers, "INT-CPC-001")
    second_product_id = await _create_product(
        async_client, auth_headers, "INT-CPC-002"
    )

    created = await async_client.post(
        f"/api/v1/products/{product_id}/customer-codes",
        headers=auth_headers,
        json={
            "customer_id": test_customer["id"],
            "customer_part_no": "CUST-PN-1001",
            "customer_product_name": "客户控制器 A",
        },
    )
    assert created.status_code == 200
    link = created.json()["data"]
    assert link["customer_name"] == test_customer["name"]
    assert link["customer_part_no"] == "CUST-PN-1001"

    duplicate_product = await async_client.post(
        f"/api/v1/products/{product_id}/customer-codes",
        headers=auth_headers,
        json={
            "customer_id": test_customer["id"],
            "customer_part_no": "CUST-PN-OTHER",
        },
    )
    assert duplicate_product.status_code == 409

    duplicate_part_no = await async_client.post(
        f"/api/v1/products/{second_product_id}/customer-codes",
        headers=auth_headers,
        json={
            "customer_id": test_customer["id"],
            "customer_part_no": "cust-pn-1001",
        },
    )
    assert duplicate_part_no.status_code == 409

    updated = await async_client.put(
        f"/api/v1/products/{product_id}/customer-codes/{link['id']}",
        headers=auth_headers,
        json={"customer_part_no": "CUST-PN-1001-R2", "is_active": False},
    )
    assert updated.status_code == 200
    assert updated.json()["data"]["customer_part_no"] == "CUST-PN-1001-R2"
    assert updated.json()["data"]["is_active"] is False

    deleted = await async_client.delete(
        f"/api/v1/products/{product_id}/customer-codes/{link['id']}",
        headers=auth_headers,
    )
    assert deleted.status_code == 200
    listed = await async_client.get(
        f"/api/v1/products/{product_id}/customer-codes", headers=auth_headers
    )
    assert listed.json()["data"] == []

    recreated = await async_client.post(
        f"/api/v1/products/{product_id}/customer-codes",
        headers=auth_headers,
        json={
            "customer_id": test_customer["id"],
            "customer_part_no": "CUST-PN-1001-R2",
        },
    )
    assert recreated.status_code == 200


async def test_customer_product_code_is_snapshotted_through_sales_flow(
    async_client: AsyncClient, auth_headers: dict, test_customer: dict
):
    product_id = await _create_product(async_client, auth_headers, "INT-FLOW-001")
    link_response = await async_client.post(
        f"/api/v1/products/{product_id}/customer-codes",
        headers=auth_headers,
        json={
            "customer_id": test_customer["id"],
            "customer_part_no": "BUYER-OLD-01",
            "customer_product_name": "买方专用模块",
        },
    )
    link_id = link_response.json()["data"]["id"]

    quotation = await async_client.post(
        "/api/v1/quotations",
        headers=auth_headers,
        json={
            "customer_id": test_customer["id"],
            "status": "draft",
            "items": [
                {
                    "product_id": product_id,
                    "product_name": "工业控制模块",
                    "quantity": 2,
                    "unit_price": 100,
                }
            ],
        },
    )
    assert quotation.status_code == 201
    quote = quotation.json()["data"]
    assert quote["items"][0]["customer_part_no"] == "BUYER-OLD-01"
    assert quote["items"][0]["customer_product_name"] == "买方专用模块"
    searched = await async_client.get(
        "/api/v1/quotations?q=BUYER-OLD-01", headers=auth_headers
    )
    assert any(item["id"] == quote["id"] for item in searched.json()["data"]["list"])

    changed = await async_client.put(
        f"/api/v1/products/{product_id}/customer-codes/{link_id}",
        headers=auth_headers,
        json={"customer_part_no": "BUYER-NEW-02"},
    )
    assert changed.status_code == 200

    quote_again = await async_client.get(
        f"/api/v1/quotations/{quote['id']}", headers=auth_headers
    )
    assert quote_again.json()["data"]["items"][0]["customer_part_no"] == "BUYER-OLD-01"

    sent = await async_client.put(
        f"/api/v1/quotations/{quote['id']}/send", headers=auth_headers
    )
    assert sent.status_code == 200

    converted_order = await async_client.post(
        f"/api/v1/quotations/{quote['id']}/convert-to-order", headers=auth_headers
    )
    assert converted_order.status_code == 200
    order_id = converted_order.json()["data"]["id"]
    order = await async_client.get(
        f"/api/v1/sales-orders/{order_id}", headers=auth_headers
    )
    assert order.json()["data"]["items"][0]["customer_part_no"] == "BUYER-OLD-01"

    converted_delivery = await async_client.post(
        f"/api/v1/sales-orders/{order_id}/convert-to-delivery",
        headers=auth_headers,
    )
    assert converted_delivery.status_code == 200
    delivery_id = converted_delivery.json()["data"]["id"]
    delivery = await async_client.get(
        f"/api/v1/delivery-notes/{delivery_id}", headers=auth_headers
    )
    assert delivery.json()["data"]["items"][0]["customer_part_no"] == "BUYER-OLD-01"
