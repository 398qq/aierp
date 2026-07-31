import pytest
from unittest.mock import patch, AsyncMock

pytestmark = pytest.mark.asyncio


async def test_scan_all_cached_hit(async_client, auth_headers, test_user):
    """Second call within TTL should not re-run scans."""
    from app.services.ai.client import ai_client

    mock_ai_result = {
        "severity": "正常",
        "summary": "无明显异常",
        "top_actions": [],
        "risk_areas": [],
    }

    with patch.object(
        ai_client, "chat_structured", new_callable=AsyncMock
    ) as mock_chat:
        mock_chat.return_value = mock_ai_result

        r1 = await async_client.get(
            "/api/v1/ai/watchtower/scan?days_back=90", headers=auth_headers
        )
        assert r1.status_code == 200
        body1 = r1.json()
        assert body1["code"] == 0
        assert "anomalies" in body1["data"]

        from app.services import watchtower_service

        with patch.object(
            watchtower_service, "scan_churn_risk", new_callable=AsyncMock
        ) as mock_churn:
            mock_churn.return_value = []
            r2 = await async_client.get(
                "/api/v1/ai/watchtower/scan?days_back=90", headers=auth_headers
            )
            assert r2.status_code == 200
            mock_churn.assert_not_called()


async def test_scan_endpoint_shape(async_client, auth_headers, test_user):
    """Response keys must match spec exactly — no additions, no removals."""
    from app.services.ai.client import ai_client

    mock_ai_result = {
        "severity": "正常",
        "summary": "无明显异常",
        "top_actions": [],
        "risk_areas": [],
    }

    with patch.object(
        ai_client, "chat_structured", new_callable=AsyncMock
    ) as mock_chat:
        mock_chat.return_value = mock_ai_result
        r = await async_client.get(
            "/api/v1/ai/watchtower/scan?days_back=90", headers=auth_headers
        )
        assert r.status_code == 200
        data = r.json()["data"]
        expected_keys = {
            "scanned_at",
            "total_alerts",
            "severity",
            "summary",
            "top_actions",
            "risk_areas",
            "alerts_persisted",
            "anomalies",
        }
        assert set(data.keys()) == expected_keys, f"Got {set(data.keys())}"
        assert set(data["anomalies"].keys()) == {
            "churn_risk",
            "order_drop",
            "low_stock",
            "out_of_stock",
        }


async def test_scan_endpoint_unauth(async_client):
    """No token -> 401."""
    r = await async_client.get("/api/v1/ai/watchtower/scan?days_back=90")
    assert r.status_code in (401, 403)


async def test_daily_report_cached(async_client, auth_headers, test_user):
    """Second call within TTL should not re-run queries."""
    from app.api.v1.ai import watchtower as watchtower_route

    with patch.object(
        watchtower_route, "_compute_daily_report", new_callable=AsyncMock
    ) as mock_compute:
        mock_compute.return_value = {
            "report_date": "2026-07-31",
            "generated_at": "2026-07-31T10:00:00+00:00",
            "metrics": {},
        }
        r1 = await async_client.get("/api/v1/ai/daily-report", headers=auth_headers)
        assert r1.status_code == 200
        assert mock_compute.call_count == 1
        r2 = await async_client.get("/api/v1/ai/daily-report", headers=auth_headers)
        assert r2.status_code == 200
        # Cached: not called again
        assert mock_compute.call_count == 1
