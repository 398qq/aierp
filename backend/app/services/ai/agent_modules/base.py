"""Base class for all AI agents.

Centralizes structured-output calls, fallback handling, and common
prompt-context assembly. New agents should subclass `BaseAgent` and use
`_call_structured()` for any JSON-mode LLM call.
"""

from abc import ABC
import json
import logging

from app.services.ai.client import ai_client

logger = logging.getLogger(__name__)


class BaseAgent(ABC):
    """Abstract base for AI domain agents.

    Subclasses define:
    - `name` (str): short identifier for logs
    - `description` (str): human-readable purpose
    - async methods that perform domain analysis
    """

    name: str = ""
    description: str = ""

    @staticmethod
    async def _call_structured(
        system_prompt: str,
        user_context: dict,
        schema: dict,
        temperature: float = 0.0,
        model: str | None = None,
    ) -> dict:
        """Invoke the LLM with JSON-mode output and a defined schema.

        Returns a parsed dict. If the call fails, logs and returns an empty
        dict — callers should check and apply rule-based fallbacks.
        """
        try:
            return await ai_client.chat_structured(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {
                        "role": "user",
                        "content": json.dumps(user_context, ensure_ascii=False),
                    },
                ],
                output_schema=schema,
                temperature=temperature,
                model=model,
            )
        except Exception as e:
            logger.exception("%s structured call failed: %s", BaseAgent.__name__, e)
            return {}

    @staticmethod
    def _fallback(reason: str = "ai_unavailable") -> dict:
        """Return a safe fallback dict for any AI failure."""
        return {"fallback": True, "reason": reason, "confidence": 0.0}
