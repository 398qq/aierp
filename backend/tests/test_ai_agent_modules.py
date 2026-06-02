"""Tests for AI agent modules — base class and extracted services."""

from unittest.mock import AsyncMock, patch

import pytest

from app.services.ai.agent_modules.base import BaseAgent


class TestBaseAgent:
    def test_subclass_with_name_works(self):
        class GoodAgent(BaseAgent):
            name = "good"
        agent = GoodAgent()
        assert agent.name == "good"

    def test_fallback_returns_safe_dict(self):
        result = BaseAgent._fallback(reason="timeout")
        assert result["fallback"] is True
        assert result["reason"] == "timeout"
        assert result["confidence"] == 0.0


@pytest.mark.asyncio
class TestBaseAgentAsync:
    async def test_call_structured_returns_empty_on_failure(self):
        with patch("app.services.ai.agent_modules.base.ai_client") as mock_client:
            mock_client.chat_structured = AsyncMock(side_effect=RuntimeError("boom"))
            result = await BaseAgent._call_structured(
                system_prompt="you are helpful",
                user_context={"q": "hi"},
                schema={"answer": "string"},
            )
        assert result == {}


class TestKMeansHelper:
    def test_kmeans_clusters_clear_groups(self):
        """Three well-separated groups of 2D points should each become their own cluster."""
        from app.services.ai.agent_modules.embedding import _run_kmeans

        embeddings = [
            [0.1, 0.0], [0.0, 0.1], [0.2, 0.1],       # cluster 0
            [10.1, 10.0], [10.0, 10.1], [9.9, 10.0],  # cluster 1
            [20.1, 20.0], [20.0, 20.1], [20.0, 19.9],  # cluster 2
        ]
        labels, centroids = _run_kmeans(embeddings, n_clusters=3, n_iter=50)

        assert len(labels) == 9
        assert len(centroids) == 3
        assert len(set(labels)) == 3

        first_three_same = len(set(labels[i] for i in range(3))) == 1
        middle_three_same = len(set(labels[i] for i in range(3, 6))) == 1
        last_three_same = len(set(labels[i] for i in range(6, 9))) == 1
        assert first_three_same
        assert middle_three_same
        assert last_three_same

    def test_kmeans_handles_minimum_inputs(self):
        from app.services.ai.agent_modules.embedding import _run_kmeans
        embeddings = [[0.0, 0.0], [1.0, 1.0]]
        labels, centroids = _run_kmeans(embeddings, n_clusters=2)
        assert len(labels) == 2
        assert set(labels) == {0, 1}


class TestWatchtowerSummarize:
    def test_summarize_groups_by_severity_and_domain(self):
        from app.services.ai.agent_modules.watchtower import WatchtowerService

        findings = [
            {"domain": "库存", "severity": "high", "title": "x", "detail": "x"},
            {"domain": "库存", "severity": "low", "title": "x", "detail": "x"},
            {"domain": "财务", "severity": "critical", "title": "x", "detail": "x"},
        ]
        summary = WatchtowerService.summarize(findings)

        assert summary["total"] == 3
        assert summary["by_severity"]["high"] == 1
        assert summary["by_severity"]["low"] == 1
        assert summary["by_severity"]["critical"] == 1
        assert summary["by_domain"]["库存"] == 2
        assert summary["by_domain"]["财务"] == 1

    def test_summarize_empty_findings(self):
        from app.services.ai.agent_modules.watchtower import WatchtowerService
        summary = WatchtowerService.summarize([])
        assert summary["total"] == 0
        assert all(v == 0 for v in summary["by_severity"].values())
