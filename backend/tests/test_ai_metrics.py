"""Tests for AI client metrics — timing and outcome tracking."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.core.observability.metrics import (
    ai_call_duration_seconds,
    reset_all,
)


@pytest.fixture(autouse=True)
def _reset_metrics():
    reset_all()
    yield
    reset_all()


class TestChatMetrics:
    async def test_successful_chat_records_duration(self):
        from app.services.ai.client import AIClient

        client = AIClient()

        # Mock the inner httpx call
        mock_resp = MagicMock()
        mock_resp.json.return_value = {
            "choices": [{"message": {"content": "hello"}}],
        }
        mock_resp.raise_for_status = MagicMock()

        mock_http_client = AsyncMock()
        mock_http_client.post = AsyncMock(return_value=mock_resp)
        mock_http_client.__aenter__ = AsyncMock(return_value=mock_http_client)
        mock_http_client.__aexit__ = AsyncMock(return_value=None)

        with patch("app.services.ai.client.httpx.AsyncClient", return_value=mock_http_client):
            result = await client.chat(
                messages=[{"role": "user", "content": "hi"}],
            )

        assert result == "hello"
        snap = ai_call_duration_seconds.snapshot()
        # The key includes (agent_name, outcome)
        assert any("success" in str(k) for k in snap.keys())

    async def test_failed_chat_records_error_outcome(self):
        from app.services.ai.client import AIClient

        client = AIClient()

        mock_http_client = AsyncMock()
        mock_http_client.post = AsyncMock(side_effect=RuntimeError("network down"))
        mock_http_client.__aenter__ = AsyncMock(return_value=mock_http_client)
        mock_http_client.__aexit__ = AsyncMock(return_value=None)

        with patch("app.services.ai.client.httpx.AsyncClient", return_value=mock_http_client):
            # tenacity retries 3 times → still raises after retries
            from tenacity import RetryError
            with pytest.raises((RuntimeError, RetryError)):
                await client.chat(messages=[{"role": "user", "content": "hi"}])

        # The metric should have been recorded at least once with error outcome
        snap = ai_call_duration_seconds.snapshot()
        assert any("error" in str(k) for k in snap.keys())


class TestEmbedMetrics:
    async def test_successful_embed_records_duration(self):
        from app.services.ai.client import AIClient

        client = AIClient()

        mock_resp = MagicMock()
        mock_resp.json.return_value = {
            "data": [{"embedding": [0.1, 0.2, 0.3]}],
        }
        mock_resp.raise_for_status = MagicMock()

        mock_http_client = AsyncMock()
        mock_http_client.post = AsyncMock(return_value=mock_resp)
        mock_http_client.__aenter__ = AsyncMock(return_value=mock_http_client)
        mock_http_client.__aexit__ = AsyncMock(return_value=None)

        with patch("app.services.ai.client.httpx.AsyncClient", return_value=mock_http_client):
            result = await client.embed(["hello"])

        assert result == [[0.1, 0.2, 0.3]]
        snap = ai_call_duration_seconds.snapshot()
        assert any("success" in str(k) for k in snap.keys())

    async def test_empty_embed_returns_empty_no_metric(self):
        from app.services.ai.client import AIClient
        client = AIClient()
        result = await client.embed([])
        assert result == []
        snap = ai_call_duration_seconds.snapshot()
        assert len(snap) == 0
