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


EMBEDDING_BATCH_SIZE = 16
EMBEDDING_TEXT_LIMIT = 2000


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
        async with httpx.AsyncClient(trust_env=False, timeout=180) as client:
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
            text = data["choices"][0]["message"]["content"]

            # Strip markdown code block wrappers: ```json ... ```
            text = text.strip()
            if text.startswith("```"):
                # Find the end of the opening line (```json or ```)
                end_marker = text.find("\n")
                if end_marker >= 0:
                    text = text[end_marker+1:]
                # Remove closing ```
                if text.rstrip().endswith("```"):
                    text = text[:text.rfind("```")]
            text = text.strip()

            return text

    async def chat_stream(self, messages: list[dict], temperature: float = 0.7, max_tokens: int = 2048, model: str | None = None) -> AsyncGenerator[str, None]:
        async with httpx.AsyncClient(trust_env=False, timeout=120) as client:
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

    async def chat_structured(
        self,
        messages: list[dict],
        output_schema: dict,
        temperature: float = 0.3,
        max_tokens: int = 8192,
        model: str | None = None,
    ) -> dict:
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
        text = await self.chat(messages, temperature=temperature, max_tokens=max_tokens, model=model)
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
        # Fix extra quote after number: 23" -> 23 (but not "42" string terminator)
        text = re.sub(r'(?<!")(?<!\d)(\d+)"(\s*[,}\]\n])', r'\1\2', text)
        # Remove trailing commas before ] or }
        text = re.sub(r',\s*}', '}', text)
        text = re.sub(r',\s*]', ']', text)
        # Fix string values where closing quote is missing before next field key
        text = re.sub(r'(":\s*"[^\n"]+?)(\n\s*"[a-z_]+"\s*:)', r'\1"\2', text)
        # Fix number wrapped in extra quotes: "780," → 780,
        text = re.sub(r'"(-?\d+\.?\d*)"(\s*[,}\]])', r'\1\2', text)
        # Pre-extract first complete JSON object (handles truncated multi-object output)
        import re
        # Find first complete JSON object or array
        first_open = text.find("{")
        first_close = text.rfind("}")
        if first_open >= 0 and first_close > first_open:
            extracted = text[first_open:first_close+1]
            # Verify it has balanced braces
            if extracted.count("{") == extracted.count("}"):
                text = extracted
        # Fix number with double-quote prefix: " "85 → 85
        text = re.sub(r'"\s*"(\d+)', r'\1', text)
        # === Fix Type B: stray commas inside string values ===
        # "VALUE,\n" (comma inside string before closing quote) -> "VALUE"\n
        text = re.sub(r'"([A-Za-z0-9/_\-+.]+),(\s*\n\s*")', r'"\1"\2', text)
        # === Fix Type A: missing commas between fields ===
        # Add comma after "value" lines followed by "key": lines
        if text.strip().startswith("{"):
            _lines = text.split("\n")
            _fixed = []
            for _i, _line in enumerate(_lines):
                _fixed.append(_line)
                if _i < len(_lines) - 1:
                    _s = _lines[_i].rstrip()
                    _next = _lines[_i+1].strip()
                    if _s.endswith('"') or _s[-1].isdigit():
                        if _next.startswith('"') and ':' in _next:
                            if not _s.endswith(","):
                                _fixed[-1] = _s + ","
            text = "\n".join(_fixed)

        # Fix trailing comma inside string values: "value"," -> "value",
        text = re.sub(r'"([^"]+),"(\s*[,}"a-z_])', r'"\1"\2', text)
        # Fix missing commas between a value and the next key on one line.
        # Examples:
        #   "phone":13800001111"email":"..."
        #   "credit_limit":null"credit_level":"A"
        text = re.sub(r'(\d)\s*("([A-Za-z_][A-Za-z0-9_]*)"\s*:)', r'\1,\2', text)
        text = re.sub(r'(null|true|false)\s*("([A-Za-z_][A-Za-z0-9_]*)"\s*:)', r'\1,\2', text)
        text = re.sub(r'(")\s*("([A-Za-z_][A-Za-z0-9_]*)"\s*:)', r'\1,\2', text)

        # Line-by-line fix: insert comma after value lines followed by key lines
        if text.strip().startswith("{"):
            # Split by lines, detect value lines followed by key lines
            _lines = text.split("\n")
            _fixed = []
            for _i, _line in enumerate(_lines):
                _fixed.append(_line)
                if _i < len(_lines) - 1:
                    _s = _lines[_i].rstrip()
                    _next = _lines[_i+1].strip()
                    if (_s.endswith('"') or _s[-1].isdigit()) and _next.startswith('"') and _next.endswith(':'):
                        if not _s.endswith(","):
                            _fixed[-1] = _s + ","
            text = "\n".join(_fixed)
        # Handle AI returning a JSON array directly (comma-separated objects missing commas)
        # Pattern: starts with "{" and ends with "}" but is actually [{...},{...}] not {key:[{...}]}
        text_stripped = text.strip()
        if text_stripped.startswith("{") and text_stripped.endswith("}"):
            # Check if this is actually a JSON array wrapper (no schema key found)
            # Look for the schema key pattern "products": [
            schema_key_match = re.search(r'"(\w+)":\s*\[', text_stripped)
            
            if schema_key_match:
                # Extract the array content between [ and last ]
                key_name = schema_key_match.group(1)
                arr_start = text_stripped.find('[')
                arr_end = text_stripped.rfind(']')
                if arr_start >= 0 and arr_end > arr_start:
                    arr_content = text_stripped[arr_start+1:arr_end]
                    # Fix missing commas: } { -> }, {
                    arr_content = re.sub(r'}\s*{', '}, {', arr_content)
                    # Also handle }\n{ -> }, {
                    arr_content = re.sub(r'}\s*\n\s*{', '}, {', arr_content)
                    try:
                        objs = json.loads('[' + arr_content + ']')
                        result = {key_name: objs}
                        result = _coerce_numbers(result)
                        return result
                    except json.JSONDecodeError:
                        pass

        try:
            result = json.loads(text)
            return _coerce_numbers(result)
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
        if not texts:
            return []

        safe_texts = [text[:EMBEDDING_TEXT_LIMIT] for text in texts]
        embeddings: list[list[float]] = []

        async with httpx.AsyncClient(trust_env=False, timeout=30) as client:
            for start in range(0, len(safe_texts), EMBEDDING_BATCH_SIZE):
                batch = safe_texts[start:start + EMBEDDING_BATCH_SIZE]
                resp = await client.post(
                    f"{self.base_url}/embeddings",
                    headers=self.headers,
                    json={"model": settings.AI_EMBEDDING_MODEL, "input": batch},
                )
                resp.raise_for_status()
                data = resp.json()
                embeddings.extend(item["embedding"] for item in data["data"])

        return embeddings

    async def embed_single(self, text: str) -> list[float]:
        results = await self.embed([text])
        return results[0]


ai_client = AIClient()
