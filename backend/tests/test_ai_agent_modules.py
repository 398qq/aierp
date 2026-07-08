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


class TestEuclideanSq:
    def test_same_vectors_return_zero(self):
        from app.services.ai.agent_modules.embedding import _euclidean_sq

        assert _euclidean_sq([1.0, 2.0, 3.0], [1.0, 2.0, 3.0]) == 0.0

    def test_different_vectors_return_positive(self):
        from app.services.ai.agent_modules.embedding import _euclidean_sq

        result = _euclidean_sq([1.0, 1.0], [4.0, 5.0])
        assert result == 25.0  # (4-1)^2 + (5-1)^2 = 9 + 16

    def test_one_dimensional(self):
        from app.services.ai.agent_modules.embedding import _euclidean_sq

        assert _euclidean_sq([3.0], [7.0]) == 16.0


class TestCustomerText:
    def test_all_fields_populated(self):
        from app.services.ai.agent_modules.embedding import EmbeddingService

        text = EmbeddingService._customer_text(
            {
                "name": "深圳电子",
                "industry": "电子制造",
                "region": "华南",
                "customer_type": "企业客户",
                "level": "A级",
                "credit_level": "AAA",
                "source": "展会",
                "notes": "长期合作",
            }
        )
        assert "深圳电子" in text
        assert "电子制造" in text
        assert "华南" in text
        assert "企业客户" in text
        assert "A级" in text
        assert "AAA" in text
        assert "展会" in text
        assert "长期合作" in text

    def test_missing_fields_default_to_empty(self):
        from app.services.ai.agent_modules.embedding import EmbeddingService

        text = EmbeddingService._customer_text({"name": "测试客户"})
        assert "测试客户" in text
        assert "行业：" in text
        assert "区域：" in text
        assert "类型：" in text
        assert "等级：" in text
        assert "信用等级：" in text
        assert "来源：" in text
        assert "备注：" in text

    def test_empty_dict_handles_gracefully(self):
        from app.services.ai.agent_modules.embedding import EmbeddingService

        text = EmbeddingService._customer_text({})
        assert text  # should produce something, not crash


class TestProductText:
    def test_with_part_number(self):
        from app.services.ai.agent_modules.embedding import EmbeddingService

        text = EmbeddingService._product_text(
            {
                "part_number": "LM358",
                "sku": "SKU-001",
                "description": "双运放",
                "name": "运算放大器",
                "brand_name": "TI",
            }
        )
        assert "LM358" in text
        assert "双运放" in text
        assert "TI" in text

    def test_falls_back_to_sku_when_no_part_number(self):
        from app.services.ai.agent_modules.embedding import EmbeddingService

        text = EmbeddingService._product_text(
            {"sku": "FALLBACK-SKU", "description": "", "brand_name": ""}
        )
        assert "FALLBACK-SKU" in text

    def test_falls_back_to_name_when_no_description(self):
        from app.services.ai.agent_modules.embedding import EmbeddingService

        text = EmbeddingService._product_text(
            {
                "part_number": "P1",
                "sku": "",
                "description": "",
                "name": "替代名称",
                "brand_name": "",
            }
        )
        assert "替代名称" in text

    def test_empty_all_fields(self):
        from app.services.ai.agent_modules.embedding import EmbeddingService

        text = EmbeddingService._product_text(
            {"part_number": "", "sku": "", "description": "", "brand_name": ""}
        )
        assert "型号：" in text
        assert "描述：" in text
        assert "品牌：" in text


class TestSupplierText:
    def test_all_fields_populated(self):
        from app.services.ai.agent_modules.embedding import EmbeddingService

        text = EmbeddingService._supplier_text(
            {
                "name": "元器件供应商A",
                "product_lines": "电容、电阻",
                "supplier_type": "代理商",
                "region": "华东",
                "certifications": "ISO9001",
                "payment_terms": "30天",
                "financial_rating": "A+",
                "website": "https://example.com",
                "notes": "优质供应商",
            }
        )
        assert "元器件供应商A" in text
        assert "电容、电阻" in text
        assert "代理商" in text
        assert "华东" in text
        assert "ISO9001" in text
        assert "30天" in text
        assert "A+" in text
        assert "https://example.com" in text
        assert "优质供应商" in text

    def test_missing_fields_default_to_empty(self):
        from app.services.ai.agent_modules.embedding import EmbeddingService

        text = EmbeddingService._supplier_text({"name": "新供应商"})
        assert "新供应商" in text
        assert "产品线：" in text
        assert "类型：" in text
        assert "区域：" in text
        assert "认证：" in text
        assert "付款条件：" in text
        assert "财务评级：" in text
        assert "网站：" in text
        assert "备注：" in text


class TestEmbeddingTypeParam:
    @pytest.mark.unit
    async def test_similar_by_text_uses_query_type(self):
        from app.services.ai.agent_modules.embedding import EmbeddingService

        with patch("app.services.ai.agent_modules.embedding.ai_client") as mock_client:
            mock_client.embed_single = AsyncMock(return_value=[0.1, 0.2])

            with patch.object(
                EmbeddingService, "similar_customers", new=AsyncMock(return_value=[])
            ):
                await EmbeddingService.similar_by_text("search text", None, top_k=5)

                mock_client.embed_single.assert_called_once_with(
                    "search text", embedding_type="query"
                )

    @pytest.mark.unit
    async def test_similar_suppliers_by_text_uses_query_type(self):
        from app.services.ai.agent_modules.embedding import EmbeddingService

        with patch("app.services.ai.agent_modules.embedding.ai_client") as mock_client:
            mock_client.embed_single = AsyncMock(return_value=[0.1, 0.2])

            with patch.object(
                EmbeddingService, "similar_suppliers", new=AsyncMock(return_value=[])
            ):
                await EmbeddingService.similar_suppliers_by_text(
                    "supplier search", None, top_k=5
                )

                mock_client.embed_single.assert_called_once_with(
                    "supplier search", embedding_type="query"
                )

    @pytest.mark.unit
    async def test_embed_customer_uses_default_db_type(self):
        from app.services.ai.agent_modules.embedding import EmbeddingService

        with patch("app.services.ai.agent_modules.embedding.ai_client") as mock_client:
            mock_client.embed_single = AsyncMock(return_value=[0.1, 0.2])

            await EmbeddingService.embed_customer({"name": "test", "industry": ""})

            # No embedding_type passed → defaults to "db"
            call_kwargs = mock_client.embed_single.call_args.kwargs
            if "embedding_type" in call_kwargs:
                assert call_kwargs["embedding_type"] == "db"

    @pytest.mark.unit
    async def test_embed_product_uses_default_db_type(self):
        from app.services.ai.agent_modules.embedding import EmbeddingService

        with patch("app.services.ai.agent_modules.embedding.ai_client") as mock_client:
            mock_client.embed_single = AsyncMock(return_value=[0.1, 0.2])

            await EmbeddingService.embed_product(
                {"part_number": "P1", "sku": "", "description": "", "brand_name": ""}
            )

            call_kwargs = mock_client.embed_single.call_args.kwargs
            if "embedding_type" in call_kwargs:
                assert call_kwargs["embedding_type"] == "db"

    @pytest.mark.unit
    async def test_embed_supplier_uses_default_db_type(self):
        from app.services.ai.agent_modules.embedding import EmbeddingService

        with patch("app.services.ai.agent_modules.embedding.ai_client") as mock_client:
            mock_client.embed_single = AsyncMock(return_value=[0.1, 0.2])

            await EmbeddingService.embed_supplier({"name": "test"})

            call_kwargs = mock_client.embed_single.call_args.kwargs
            if "embedding_type" in call_kwargs:
                assert call_kwargs["embedding_type"] == "db"


class TestKMeansHelper:
    def test_kmeans_clusters_clear_groups(self):
        """Three well-separated groups of 2D points should each become their own cluster."""
        from app.services.ai.agent_modules.embedding import _run_kmeans

        embeddings = [
            [0.1, 0.0],
            [0.0, 0.1],
            [0.2, 0.1],  # cluster 0
            [10.1, 10.0],
            [10.0, 10.1],
            [9.9, 10.0],  # cluster 1
            [20.1, 20.0],
            [20.0, 20.1],
            [20.0, 19.9],  # cluster 2
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
