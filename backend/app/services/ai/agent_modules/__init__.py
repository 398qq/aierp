"""AI agent modules — split for maintainability.

Each module is a single class that depends on the shared `ai_client` and
`prompts` resources. The original `agents.py` re-exports these for
backward compatibility.
"""

from app.services.ai.agent_modules.base import BaseAgent
from app.services.ai.agent_modules.embedding import EmbeddingService, _run_kmeans, _euclidean_sq
from app.services.ai.agent_modules.watchtower import WatchtowerService

__all__ = [
    "BaseAgent",
    "EmbeddingService",
    "WatchtowerService",
    "_run_kmeans",
    "_euclidean_sq",
]
