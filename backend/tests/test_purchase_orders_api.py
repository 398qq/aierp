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
        self, async_client: AsyncClient, auth_headers: dict, db_session
    ):
        supplier_id = await _create_supplier(async_client, auth_headers)
        draft_id = await _create_po(async_client, auth_headers, supplier_id)
        confirmed_id = await _create_po(async_client, auth_headers, supplier_id)
        from app.models.transaction import PurchaseOrder

        confirmed = await db_session.get(PurchaseOrder, confirmed_id)
        confirmed.status = "approved"
        await db_session.commit()

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


class TestPurchaseOrderV34:
    async def test_large_order_confirmation_and_supplier_acknowledgement(
        self, async_client: AsyncClient, auth_headers: dict, db_session
    ):
        from app.models.product import Product, Supplier

        supplier = Supplier(
            name="V3.4 原厂",
            supplier_type="原厂",
            contact_person="谢工",
            payment_terms="月结30天",
        )
        product = Product(
            name="SPI 转 UART",
            sku="WK2132-ISSG",
            mpn="WK2132-ISSG",
            package_type="SSOP-20",
        )
        db_session.add_all([supplier, product])
        await db_session.flush()

        response = await async_client.post(
            "/api/v1/purchase-orders",
            headers=auth_headers,
            json={
                "supplier_id": supplier.id,
                "supplier_contact": "谢工",
                "payment_terms": "月结30天",
                "expected_date": "2026-07-24",
                "delivery_address": "深圳市福田区",
                "tax_rate": 13,
                "contract_terms_version": "v3.4",
                "items": [
                    {
                        "product_id": product.id,
                        "supplier_mpn": "WK2132-ISSG",
                        "product_sku": "WK2132-ISSG",
                        "product_name": "SPI 转 UART",
                        "brand_name": "WK",
                        "package_type": "SSOP-20",
                        "quantity": 2000,
                        "min_pack_qty": 2500,
                        "min_pack_unit": "盘",
                        "date_code_requirement": "2年内",
                        "unit_price": 8.3,
                        "amount": 1,
                    }
                ],
            },
        )
        assert response.status_code == 201, response.text
        po_id = response.json()["data"]["id"]

        detail = await async_client.get(
            f"/api/v1/purchase-orders/{po_id}", headers=auth_headers
        )
        payload = detail.json()["data"]
        assert payload["total_amount"] == 16600
        assert payload["contract_terms_version"] == "v3.4"
        assert payload["items"][0]["date_code_requirement"] == "2年内"
        assert payload["items"][0]["min_pack_qty"] == 2500

        blocked = await async_client.post(
            f"/api/v1/purchase-orders/{po_id}/transition",
            headers=auth_headers,
            json={"target_status": "approved"},
        )
        assert blocked.status_code == 422
        assert "二次确认" in blocked.json()["msg"]

        confirmed = await async_client.post(
            f"/api/v1/purchase-orders/{po_id}/confirm-large-order",
            headers=auth_headers,
        )
        assert confirmed.status_code == 200
        approved = await async_client.post(
            f"/api/v1/purchase-orders/{po_id}/transition",
            headers=auth_headers,
            json={"target_status": "approved"},
        )
        assert approved.json()["data"]["status"] == "approved"
        ordered = await async_client.post(
            f"/api/v1/purchase-orders/{po_id}/transition",
            headers=auth_headers,
            json={"target_status": "ordered"},
        )
        assert ordered.json()["data"]["status"] == "ordered"

        receive_blocked = await async_client.post(
            f"/api/v1/purchase-orders/{po_id}/receive",
            headers=auth_headers,
            json={"warehouse_id": 1},
        )
        assert receive_blocked.status_code == 422
        assert "书面确认" in receive_blocked.json()["msg"]

        acknowledgement = await async_client.post(
            f"/api/v1/purchase-orders/{po_id}/supplier-confirmation",
            headers=auth_headers,
            json={
                "method": "wechat",
                "confirmed_delivery_date": "2026-07-24",
                "allow_partial_delivery": False,
            },
        )
        assert acknowledgement.status_code == 200
        assert acknowledgement.json()["data"]["supplier_confirmation_status"] == "confirmed"
