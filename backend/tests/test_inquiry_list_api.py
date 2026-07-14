from httpx import AsyncClient

from app.models.sales import Inquiry


async def test_list_inquiries_returns_persisted_records(
    async_client: AsyncClient,
    auth_headers: dict,
    db_session,
    test_customer: dict,
):
    db_session.add(
        Inquiry(
            customer_id=test_customer["id"],
            channel="email",
            contact_name="张经理",
            contact_info="zhang@example.com",
            inquiry_text="询价 STM32F407 100 件",
            reply_text="已收到询价",
            status="replied",
            ai_confidence=0.85,
        )
    )
    await db_session.commit()

    response = await async_client.get(
        "/api/v1/inquiries?limit=10&sort_by=created_at&order=desc",
        headers=auth_headers,
    )

    assert response.status_code == 200
    payload = response.json()["data"]
    assert payload["total"] == 1
    assert payload["list"][0]["inquiry_text"] == "询价 STM32F407 100 件"
    assert payload["list"][0]["customer_name"]
    assert payload["list"][0]["confidence"] == 0.85


async def test_list_inquiries_rejects_unbounded_limit(
    async_client: AsyncClient, auth_headers: dict
):
    response = await async_client.get(
        "/api/v1/inquiries?limit=1000", headers=auth_headers
    )

    assert response.status_code == 422
