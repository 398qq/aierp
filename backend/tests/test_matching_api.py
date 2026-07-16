from httpx import AsyncClient


async def test_recommend_customers_uses_unambiguous_sales_order_joins(
    async_client: AsyncClient,
    auth_headers: dict,
    test_customer: dict,
    monkeypatch,
):
    from app.services.ai.client import ai_client

    async def fake_chat_structured(*args, **kwargs):
        return {
            "recommendations": [],
            "summary": "暂无候选客户",
            "outreach_strategy": "补充客户购买数据",
        }

    monkeypatch.setattr(ai_client, "chat_structured", fake_chat_structured)
    brand = await async_client.post(
        "/api/v1/brands/",
        headers=auth_headers,
        json={"name": "Matching Brand", "status": "active"},
    )
    assert brand.status_code == 200
    brand_id = brand.json()["data"]["id"]
    product = await async_client.post(
        "/api/v1/products",
        headers=auth_headers,
        json={
            "name": "推荐客户连接测试",
            "sku": "MATCH-JOIN-001",
            "brand_id": brand_id,
        },
    )
    assert product.status_code == 201
    related_product = await async_client.post(
        "/api/v1/products",
        headers=auth_headers,
        json={
            "name": "同品牌历史产品",
            "sku": "MATCH-HISTORY-001",
            "brand_id": brand_id,
        },
    )
    assert related_product.status_code == 201
    order = await async_client.post(
        "/api/v1/sales-orders",
        headers=auth_headers,
        json={
            "customer_id": test_customer["id"],
            "status": "pending",
            "items": [
                {
                    "product_id": related_product.json()["data"]["id"],
                    "product_name": "同品牌历史产品",
                    "quantity": 1,
                    "unit_price": 100,
                }
            ],
        },
    )
    assert order.status_code == 201

    response = await async_client.post(
        f"/api/v1/ai/products/{product.json()['data']['id']}/recommend-customers",
        headers=auth_headers,
    )

    assert response.status_code == 200
    assert response.json()["code"] == 0
    assert response.json()["data"]["recommendations"] == []
    assert response.json()["data"]["candidates"][0]["customer_id"] == test_customer["id"]
