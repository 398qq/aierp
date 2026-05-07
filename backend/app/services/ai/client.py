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
        async with httpx.AsyncClient(timeout=180) as client:
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

    async def chat_structured(self, messages: list[dict], output_schema: dict, temperature: float = 0.3, max_tokens: int = 8192) -> dict:
        """Get structured JSON output matching the given schema."""
        system_msg = messages[0]["content"] if messages and messages[0]["role"] == "system" else ""
        schema_str = json.dumps(output_schema, indent=2, ensure_ascii=False)
        messages[0] = {
            "role": "system",
            "content": (
                f"{system_msg}\n\n"
                "【重要指令】你必须返回严格符合以下 JSON Schema 的有效 JSON 对象。\n"
                "1. 只输出纯JSON对象，不要任何解释、注释或markdown标记\n"
                "2. 所有字段名必须与schema完全一致，不要发明新字段\n"
                "3. 数值字段只能是数字，绝对不能包含文字说明\n"
                "4. 字符串字段使用双引号，不要使用单引号\n"
                "5. 数组和对象使用 [] 和 {{}}，括号必须成对闭合\n"
                f"```json\n{schema_str}\n```"
            ),
        }
        text = await self.chat(messages, temperature=temperature, max_tokens=max_tokens)
        text = text.strip()
        # Sanitize control characters and invalid Unicode that break JSON
        import unicodedata
        # Detect hallucination loops (excessive repetition)
        if len(text) > 800:
            # Check for any single character dominating the text
            from collections import Counter
            char_counts = Counter(text)
            if char_counts:
                top_char, top_count = char_counts.most_common(1)[0]
                top_ratio = top_count / len(text)
                # If any single char >50%, it's hallucination
                if top_ratio > 0.5:
                    raise ValueError(f"AI hallucination detected: excessive '{top_char}' repetition ({top_ratio:.0%})")
            # Low character diversity: text is long but very few unique chars
            unique_ratio = len(char_counts) / len(text)
            if len(text) > 1500 and unique_ratio < 0.03:
                raise ValueError(f"AI hallucination detected: low character diversity ({unique_ratio:.2%})")
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
        # Replace fullwidth punctuation that breaks JSON
        text = text.replace('，', ',')
        text = text.replace('：', ':')
        text = text.replace('“', '"').replace('”', '"')
        # Fix missing commas between adjacent objects: }{\s*{
        text = re.sub(r'}\s*{', r'}, {', text)
        # Fix missing commas in arrays: }\s*\n\s*{
        text = re.sub(r'}(\s*\n\s*){', r'},\n{', text)
        # Fix double colon: "key":: -> "key":
        text = re.sub(r'"\s*::\s*', '": ', text)
        # Fix double colon with space: "key": :value -> "key": value
        text = re.sub(r'":\s+:', '": ', text)
        # Fix bare comma between fields: ],\n,\n  "next" -> ],\n  "next"
        text = re.sub(r',\s*\n\s*,', ',', text)
        # Fix extra quote after number: 23" -> 23
        text = re.sub(r'(\d+)"(\s*[,}\]\n])', r'\1\2', text)
        # Remove trailing commas before ] or }
        text = re.sub(r',\s*}', '}', text)
        text = re.sub(r',\s*]', ']', text)
        # Fix string values where closing quote is missing before next field key
        text = re.sub(r'(":\s*"[^\n"]+?)(\n\s*"[a-z_]+"\s*:)', r'\1"\2', text)
        # Fix number wrapped in extra quotes: "780," → 780,
        text = re.sub(r'"(-?\d+\.?\d*)"(\s*[,}\]])', r'\1\2', text)
        # Fix number with double-quote prefix: " "85 → 85
        text = re.sub(r'"\s*"(\d+)', r'\1', text)
        try:
            result = json.loads(text)
            result = _coerce_numbers(result)
            return result
        except (json.JSONDecodeError, ValueError):
            pass
        # Third attempt: salvage truncated JSON by closing brackets and strings
        try:
            t = text.rstrip()
            # If text ends without closing a string value, add closing quote
            if t and t[-1] != '"' and t[-1] not in ']}0123456789':
                # Check if we're inside a string value (last key: has " before value)
                last_colon = t.rfind('": "')
                last_close = max(t.rfind('}'), t.rfind(']'))
                if last_colon > last_close:
                    t = t + '"'
            open_braces = t.count("{") - t.count("}")
            open_brackets = t.count("[") - t.count("]")
            if open_braces > 0 or open_brackets > 0:
                suffix = "]" * max(0, open_brackets) + "}" * max(0, open_braces)
                result = json.loads(t + suffix)
                result = _coerce_numbers(result)
                return result
        except (json.JSONDecodeError, ValueError):
            pass
        # All attempts failed
        import logging
        logging.getLogger(__name__).error(f"JSON parse failed, raw text: {text[:2000]}")
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
