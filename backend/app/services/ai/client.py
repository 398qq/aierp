import json
from collections.abc import AsyncGenerator

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

from app.config import settings


class AIClient:
    """Unified AI client — text generation + embeddings."""

    def __init__(self):
        self.base_url = settings.AI_BASE_URL
        self.headers = {
            "Authorization": f"Bearer {settings.AI_API_KEY}",
            "Content-Type": "application/json",
        }

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=10))
    async def chat(self, messages: list[dict], temperature: float = 0.7, max_tokens: int = 2048, model: str | None = None) -> str:
        async with httpx.AsyncClient(timeout=60) as client:
            resp = await client.post(
                f"{self.base_url}/chat/completions",
                headers=self.headers,
                json={
                    "model": model or settings.AI_MODEL,
                    "messages": messages,
                    "temperature": temperature,
                    "max_tokens": max_tokens,
                },
            )
            resp.raise_for_status()
            data = resp.json()
            return data["choices"][0]["message"]["content"]

    async def chat_stream(self, messages: list[dict], temperature: float = 0.7, max_tokens: int = 2048, model: str | None = None) -> AsyncGenerator[str, None]:
        async with httpx.AsyncClient(timeout=120) as client:
            async with client.stream(
                "POST",
                f"{self.base_url}/chat/completions",
                headers=self.headers,
                json={
                    "model": model or settings.AI_MODEL,
                    "messages": messages,
                    "temperature": temperature,
                    "max_tokens": max_tokens,
                    "stream": True,
                },
            ) as resp:
                resp.raise_for_status()
                async for line in resp.aiter_lines():
                    if line.startswith("data: "):
                        chunk = line[6:]
                        if chunk == "[DONE]":
                            break
                        try:
                            delta = json.loads(chunk)["choices"][0].get("delta", {})
                            if content := delta.get("content"):
                                yield content
                        except (json.JSONDecodeError, KeyError, IndexError):
                            continue

    async def chat_structured(self, messages: list[dict], output_schema: dict, temperature: float = 0.3) -> dict:
        """Get structured JSON output matching the given schema."""
        system_msg = messages[0]["content"] if messages and messages[0]["role"] == "system" else ""
        schema_str = json.dumps(output_schema, indent=2, ensure_ascii=False)
        messages[0] = {
            "role": "system",
            "content": f"{system_msg}\n\n你必须返回符合以下 JSON Schema 的有效 JSON，不要输出任何解释：\n```json\n{schema_str}\n```",
        }
        text = await self.chat(messages, temperature=temperature, max_tokens=4096)
        text = text.strip()
        if text.startswith("```"):
            text = text.split("\n", 1)[1]
            if text.endswith("```"):
                text = text[:-3]
        return json.loads(text)

    async def embed(self, texts: list[str]) -> list[list[float]]:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                f"{self.base_url}/embeddings",
                headers=self.headers,
                json={"model": settings.AI_EMBEDDING_MODEL, "input": texts},
            )
            resp.raise_for_status()
            data = resp.json()
            return [item["embedding"] for item in data["data"]]

    async def embed_single(self, text: str) -> list[float]:
        results = await self.embed([text])
        return results[0]


ai_client = AIClient()
