"""AI agent modules — split for maintainability.

Each module owns a single class. The original monolithic
``app.services.ai.agents`` re-exports everything for back-compat.

Per-domain:
- ``base``        — ``BaseAgent`` shared scaffolding
- ``embedding``   — ``EmbeddingService`` + clustering helpers
- ``watchtower``  — ``WatchtowerService`` cross-domain anomaly detection
- ``customer``    — ``CustomerAgent`` (RFM, churn, recognition, follow-up)
- ``inventory``   — ``InventoryAgent``
- ``product``     — ``ProductAgent`` (parse, BOM, substitute matching)
- ``_text_extraction`` — OCR / business-card text parsing helpers
"""

from __future__ import annotations

from app.services.ai.agent_modules._text_extraction import (
    compose_customer_recognition_context,
    extract_company_name,
    extract_contact_person,
    extract_email,
    extract_phone,
    heuristic_customer_recognition,
    merge_customer_recognition,
    normalize_customer_source_text,
    text_lines,
)
from app.services.ai.agent_modules.base import BaseAgent
from app.services.ai.agent_modules.customer import BUSINESS_CARD_TITLES, CustomerAgent
from app.services.ai.agent_modules.embedding import EmbeddingService
from app.services.ai.agent_modules.inventory import InventoryAgent
from app.services.ai.agent_modules.product import ProductAgent
from app.services.ai.agent_modules.watchtower import WatchtowerService

__all__ = [
    "BaseAgent",
    "CustomerAgent",
    "InventoryAgent",
    "ProductAgent",
    "EmbeddingService",
    "WatchtowerService",
    "BUSINESS_CARD_TITLES",
    # Text extraction helpers (public names)
    "compose_customer_recognition_context",
    "extract_company_name",
    "extract_contact_person",
    "extract_email",
    "extract_phone",
    "heuristic_customer_recognition",
    "merge_customer_recognition",
    "normalize_customer_source_text",
    "text_lines",
]
