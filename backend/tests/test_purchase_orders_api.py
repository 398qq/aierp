from httpx import AsyncClient


async def _create_supplier(async_client: AsyncClient, auth_headers: dict) -> int:
    response = await async_client.post(
        "/api/v1/suppliers/",
        headers=auth_headers,
        json={"name": "采购单删除测试供应商"},
    )
    assert response.status_code == 200, response.text
    return response.json()["data"]["id"]


async def _create_po(
    async_client: AsyncClient,
    auth_headers: dict,
    supplier_id: int,
    status: str = "draft",
) -> int:
    response = await async_client.post(
        "/api/v1/purchase-orders",
        headers=auth_headers,
        json={"supplier_id": supplier_id, "status": status},
    )
    assert response.status_code == 201, response.text
    return response.json()["data"]["id"]


class TestPurchaseOrderDelete:
    async def test_batch_delete_draft_orders(
        self, async_client: AsyncClient, auth_headers: dict
    ):
        supplier_id = await _create_supplier(async_client, auth_headers)
        ids = [
            await _create_po(async_client, auth_headers, supplier_id),
            await _create_po(async_client, auth_headers, supplier_id),
        ]

        response = await async_client.post(
            "/api/v1/purchase-orders/batch-delete",
            headers=auth_headers,
            json={"ids": ids},
        )

        assert response.status_code == 200, response.text
        assert response.json()["data"]["deleted"] == 2
        for po_id in ids:
            get_response = await async_client.get(
                f"/api/v1/purchase-orders/{po_id}", headers=auth_headers
            )
            assert get_response.status_code == 404

    async def test_batch_delete_is_atomic_when_order_is_not_draft(
        self, async_client: AsyncClient, auth_headers: dict
    ):
        supplier_id = await _create_supplier(async_client, auth_headers)
        draft_id = await _create_po(async_client, auth_headers, supplier_id)
        confirmed_id = await _create_po(
            async_client, auth_headers, supplier_id, status="confirmed"
        )

        response = await async_client.post(
            "/api/v1/purchase-orders/batch-delete",
            headers=auth_headers,
            json={"ids": [draft_id, confirmed_id]},
        )

        assert response.status_code == 422
        assert "只能删除草稿状态" in response.json()["msg"]
        draft_response = await async_client.get(
            f"/api/v1/purchase-orders/{draft_id}", headers=auth_headers
        )
        assert draft_response.status_code == 200
