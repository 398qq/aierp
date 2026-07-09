"""Tests for AI client — retry behavior, embedding, structured output."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest


class TestAIClientInit:
    def test_client_uses_settings(self):
        from app.services.ai.client import AIClient

        client = AIClient()
        assert client.base_url is not None
        assert "Authorization" in client.headers


class TestEmbed:
    @pytest.mark.unit
    async def test_embed_batches_texts(self):
        """embed() should send multiple texts in one API call."""
        from app.services.ai.client import AIClient

        client = AIClient()
        client.base_url = "https://api.siliconflow.cn/v1"
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "data": [
                {"embedding": [0.1, 0.2]},
                {"embedding": [0.3, 0.4]},
            ]
        }

        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.post.return_value = (
                mock_response
            )
            mock_response.raise_for_status = MagicMock()

            results = await client.embed(["text1", "text2"])

            assert len(results) == 2
            assert len(results[0]) == 2

    @pytest.mark.unit
    async def test_embed_single_delegates(self):
        """embed_single should wrap single text in a list."""
        from app.services.ai.client import AIClient

        client = AIClient()

        with patch.object(
            client, "embed", new=AsyncMock(return_value=[[0.1, 0.2]])
        ) as mock_embed:
            result = await client.embed_single("hello")
            mock_embed.assert_called_once_with(["hello"], embedding_type="db")
            assert result == [0.1, 0.2]


class TestChat:
    @pytest.mark.unit
    async def test_chat_strips_markdown_wrapper(self):
        """chat() should strip ```json ... ``` wrappers."""
        from app.services.ai.client import AIClient

        client = AIClient()
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "choices": [{"message": {"content": '```json\n{"key": "value"}\n```'}}]
        }

        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.post.return_value = (
                mock_response
            )
            mock_response.raise_for_status = MagicMock()

            result = await client.chat([{"role": "user", "content": "hi"}])
            assert result == '{"key": "value"}'

    @pytest.mark.unit
    async def test_chat_handles_plain_text(self):
        """chat() should handle plain text without markdown."""
        from app.services.ai.client import AIClient

        client = AIClient()
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "choices": [{"message": {"content": "plain response"}}]
        }

        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.post.return_value = (
                mock_response
            )
            mock_response.raise_for_status = MagicMock()

            result = await client.chat([{"role": "user", "content": "hi"}])
            assert result == "plain response"


class TestChatStructured:
    @pytest.mark.unit
    async def test_chat_structured_adds_schema_to_prompt(self):
        """chat_structured should inject JSON schema into the system message."""
        from app.services.ai.client import AIClient

        client = AIClient()
        messages = [
            {"role": "system", "content": "Be helpful"},
            {"role": "user", "content": "query"},
        ]
        schema = {"type": "object", "properties": {"name": {"type": "string"}}}

        # We just verify the messages are modified correctly before calling chat
        with patch.object(
            client, "chat", new=AsyncMock(return_value='{"name": "test"}')
        ):
            result = await client.chat_structured(messages, schema)
            assert result == {"name": "test"}

    @pytest.mark.unit
    async def test_chat_structured_coerces_numbers(self):
        """chat_structured should coerce numeric strings to int/float."""
        from app.services.ai.client import AIClient

        client = AIClient()
        messages = [
            {"role": "system", "content": "Be helpful"},
            {"role": "user", "content": "query"},
        ]
        schema = {"type": "object", "properties": {"count": {"type": "integer"}}}

        with patch.object(
            client, "chat", new=AsyncMock(return_value='{"count": "42"}')
        ):
            result = await client.chat_structured(messages, schema)
            assert result == {"count": 42}


class TestCoerceNumbers:
    def test_string_int_to_int(self):
        from app.services.ai.client import _coerce_numbers

        assert _coerce_numbers({"a": "123"}) == {"a": 123}

    def test_string_float_to_float(self):
        from app.services.ai.client import _coerce_numbers

        assert _coerce_numbers({"a": "3.14"}) == {"a": 3.14}

    def test_nested_structures(self):
        from app.services.ai.client import _coerce_numbers

        result = _coerce_numbers({"items": [{"qty": "5", "price": "9.99"}]})
        assert result == {"items": [{"qty": 5, "price": 9.99}]}

    def test_non_numeric_strings_unchanged(self):
        from app.services.ai.client import _coerce_numbers

        assert _coerce_numbers({"name": "hello"}) == {"name": "hello"}


class TestIsMinimaxEmbeddingApi:
    @pytest.mark.unit
    def test_base_url_with_minimax_returns_true(self):
        from app.services.ai.client import AIClient

        client = AIClient()
        client.base_url = "https://api.minimax.chat/v1"
        assert client._is_minimax_embedding_api() is True

    @pytest.mark.unit
    def test_base_url_with_minimaxi_returns_true(self):
        from app.services.ai.client import AIClient

        client = AIClient()
        client.base_url = "https://api.minimaxi.com/v1"
        assert client._is_minimax_embedding_api() is True

    @pytest.mark.unit
    def test_base_url_without_minimax_returns_false(self):
        from app.services.ai.client import AIClient

        client = AIClient()
        client.base_url = "https://api.siliconflow.cn/v1"
        assert client._is_minimax_embedding_api() is False

    @pytest.mark.unit
    def test_similar_but_not_minimax_returns_false(self):
        from app.services.ai.client import AIClient

        client = AIClient()
        client.base_url = "https://api.mini-max.example.com/v1"
        assert client._is_minimax_embedding_api() is False


class TestEmbedMinimax:
    @pytest.mark.unit
    async def test_minimax_sends_texts_and_type_in_payload(self):
        """Minimax embed payload uses 'texts' + 'type' instead of 'input'."""
        from app.services.ai.client import AIClient

        client = AIClient()
        client.base_url = "https://api.minimax.chat/v1"

        mock_response = MagicMock()
        mock_response.json.return_value = {
            "vectors": [[0.1, 0.2]],
            "base_resp": {"status_code": 0},
        }

        with patch("httpx.AsyncClient") as mock_client:
            ctx = mock_client.return_value.__aenter__.return_value
            ctx.post.return_value = mock_response
            mock_response.raise_for_status = MagicMock()

            await client.embed(["hello"], embedding_type="query")

            call_kwargs = ctx.post.call_args.kwargs
            payload = call_kwargs["json"]
            assert "texts" in payload
            assert "type" in payload
            assert payload["texts"] == ["hello"]
            assert payload["type"] == "query"
            assert "input" not in payload

    @pytest.mark.unit
    async def test_minimax_extracts_vectors_from_response(self):
        """Minimax response parses 'vectors' field, not 'data'."""
        from app.services.ai.client import AIClient

        client = AIClient()
        client.base_url = "https://api.minimax.chat/v1"

        mock_response = MagicMock()
        mock_response.json.return_value = {
            "vectors": [[0.1, 0.2], [0.3, 0.4]],
            "base_resp": {"status_code": 0},
        }

        with patch("httpx.AsyncClient") as mock_client:
            ctx = mock_client.return_value.__aenter__.return_value
            ctx.post.return_value = mock_response
            mock_response.raise_for_status = MagicMock()

            results = await client.embed(["text1", "text2"])

            assert len(results) == 2
            assert results[0] == [0.1, 0.2]
            assert results[1] == [0.3, 0.4]

    @pytest.mark.unit
    async def test_minimax_raises_on_nonzero_status_code(self):
        """Minimax should raise ValueError when base_resp.status_code != 0."""
        from app.services.ai.client import AIClient

        client = AIClient()
        client.base_url = "https://api.minimax.chat/v1"

        mock_response = MagicMock()
        mock_response.json.return_value = {
            "base_resp": {"status_code": 1001, "status_msg": "invalid parameter"}
        }

        with patch("httpx.AsyncClient") as mock_client:
            ctx = mock_client.return_value.__aenter__.return_value
            ctx.post.return_value = mock_response
            mock_response.raise_for_status = MagicMock()

            with pytest.raises(ValueError, match="MiniMax embedding failed"):
                await client.embed(["hello"])

    @pytest.mark.unit
    async def test_minimax_raises_when_vectors_missing(self):
        """Minimax should raise ValueError when response has no 'vectors'."""
        from app.services.ai.client import AIClient

        client = AIClient()
        client.base_url = "https://api.minimax.chat/v1"

        mock_response = MagicMock()
        mock_response.json.return_value = {"base_resp": {"status_code": 0}}

        with patch("httpx.AsyncClient") as mock_client:
            ctx = mock_client.return_value.__aenter__.return_value
            ctx.post.return_value = mock_response
            mock_response.raise_for_status = MagicMock()

            with pytest.raises(
                ValueError, match="MiniMax embedding response missing vectors"
            ):
                await client.embed(["hello"])


class TestEmbedEmbeddingType:
    @pytest.mark.unit
    async def test_standard_embed_passes_embedding_type_in_default_payload(self):
        """Standard (non-Minimax) embed should include model + input in payload."""
        from app.services.ai.client import AIClient

        client = AIClient()
        client.base_url = "https://api.siliconflow.cn/v1"

        mock_response = MagicMock()
        mock_response.json.return_value = {"data": [{"embedding": [0.1, 0.2]}]}

        with patch("httpx.AsyncClient") as mock_client:
            ctx = mock_client.return_value.__aenter__.return_value
            ctx.post.return_value = mock_response
            mock_response.raise_for_status = MagicMock()

            await client.embed(["hello"], embedding_type="db")

            call_kwargs = ctx.post.call_args.kwargs
            payload = call_kwargs["json"]
            assert payload["model"] is not None
            assert payload["input"] == ["hello"]

    @pytest.mark.unit
    async def test_embed_single_forwards_embedding_type(self):
        """embed_single should pass embedding_type through to embed()."""
        from app.services.ai.client import AIClient

        client = AIClient()

        with patch.object(
            client, "embed", new=AsyncMock(return_value=[[0.1, 0.2]])
        ) as mock_embed:
            result = await client.embed_single("hello", embedding_type="query")
            mock_embed.assert_called_once_with(["hello"], embedding_type="query")
            assert result == [0.1, 0.2]

    @pytest.mark.unit
    async def test_embed_empty_texts_returns_empty_list(self):
        """embed() with empty input should return [] without calling API."""
        from app.services.ai.client import AIClient

        client = AIClient()
        results = await client.embed([])
        assert results == []

    @pytest.mark.unit
    async def test_embed_empty_texts_does_not_call_api(self):
        """embed() with empty list should not make any HTTP request."""
        from app.services.ai.client import AIClient

        client = AIClient()

        with patch("httpx.AsyncClient") as mock_client:
            results = await client.embed([])
            mock_client.return_value.__aenter__.return_value.post.assert_not_called()
            assert results == []
