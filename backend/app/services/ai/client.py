import json
from collections.abc import AsyncGenerator

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

from app.config import settings


def _coerce_numbers(obj):
    """Recursively convert numeric strings to int/float in dicts/lists."""
    if isinstance(obj, dict):
        return {k: _coerce_numbers(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_coerce_numbers(v) for v in obj]
    if isinstance(obj, str):
        s = obj.strip()
        if s.isdigit() or (s.startswith("-") and s[1:].isdigit()):
            return int(s)
        try:
            f = float(s)
            if not (f == float("inf") or f == float("-inf") or f == float("nan")):
                return f
        except (ValueError, OverflowError):
            pass
    return obj


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
        # Sanitize control characters and invalid Unicode that break JSON
        import unicodedata
        text = ''.join(
            ch if unicodedata.category(ch)[0] != 'C' or ch in ('\n', '\r', '\t') else ' '
            for ch in text
        )
        # Fix garbled Unicode replacement characters
        text = text.replace('�', ' ')
        # Extract JSON from markdown code blocks
        if "```" in text:
            start = text.find("```") + 3
            end = text.find("```", start)
            if end > start:
                text = text[start:end].strip()
                if text.startswith("json\n"):
                    text = text[5:]
        # Try to find JSON object boundaries
        text = text.strip()
        if not text.startswith("{"):
            start = text.find("{")
            end = text.rfind("}")
            if start >= 0 and end > start:
                text = text[start:end + 1]
        # Fix common model JSON errors
        import re
        text = re.sub(r'"\s+"', '", "', text)
        text = re.sub(r'"\s+null"', '", null', text)
        # Fix missing commas between adjacent objects: }{\s*{
        text = re.sub(r'}\s*{', r'}, {', text)
        # Fix missing commas in arrays: }\s*\n\s*{
        text = re.sub(r'}(\s*\n\s*){', r'},\n{', text)
        # Fix malformed number followed by quote: 97" -> 9,"
        text = re.sub(r'(\d+)"(\s*\n\s*"dimension")', r'\1,\2', text)
        # Fix double colon: "key":: -> "key":
        text = re.sub(r'"\s*::\s*', '": ', text)
        # Fix extra quote after number: 23" -> 23
        text = re.sub(r'(\d+)"(\s*[,}\]\n])', r'\1\2', text)
        # Fix number with trailing comma inside string: "6, -> "6,
        text = re.sub(r'"\s*(\d+),(\s*[,}\]\n"\s])', r'"\1"\2', text)
        text = re.sub(r'"\s*(\d+),(\s*[,}\]\n"])', r'"\1"\2', text)
        # Fix misspelled win_probability field name (common AI hallucination)
        text = re.sub(r'"wi_probability"', '"win_probability"', text)
        # Fix missing colon: "key" value -> "key": value
        text = re.sub(r'"\s*}\s*"', '": "', text)
        # Remove trailing commas before ] or }
        text = re.sub(r',\s*}', '}', text)
        text = re.sub(r',\s*]', ']', text)
        # Fix unclosed strings by removing trailing lone quotes before comma/closing
        text = re.sub(r'"\s*"\s*([,}\]])', r'"\1', text)
        try:
            result = json.loads(text)
            result = _coerce_numbers(result)
            return result
        except (json.JSONDecodeError, ValueError):
            pass
        # Third attempt: specific fixes for known AI hallucination patterns
        text2 = text
        text2 = re.sub(r'"wi_probability"', '"win_probability"', text2)
        text2 = re.sub(r'"win_probability"[:\s]*"(\d+),"', r'"win_probability": \1,', text2)
        try:
            result = json.loads(text2)
            result = _coerce_numbers(result)
            return result
        except (json.JSONDecodeError, ValueError):
            pass
        # Fourth attempt: try to salvage by counting braces and appending missing closers
        try:
            open_braces = text.count("{") - text.count("}")
            open_brackets = text.count("[") - text.count("]")
            suffix = "]" * max(0, open_brackets) + "}" * max(0, open_braces)
            result = json.loads(text + suffix)
            result = _coerce_numbers(result)
            return result
        except (json.JSONDecodeError, ValueError):
            import logging
            logging.getLogger(__name__).error(f"JSON parse failed, raw text: {text[:800]}")
            raise ValueError(f"AI returned invalid JSON: {text[:300]}")


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
