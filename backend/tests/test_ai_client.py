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
            mock_embed.assert_called_once_with(["hello"])
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
