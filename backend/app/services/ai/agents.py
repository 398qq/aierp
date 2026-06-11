"""Back-compat shim — re-exports the public surface of ``app.services.ai.agents``.

The 1089-line monolith ``agents.py`` was split into per-domain
modules under ``app.services.ai.agent_modules``. This shim keeps
the legacy import path ``from app.services.ai.agents import X``
working so existing callers don't need to change.

New code should import directly from ``app.services.ai.agent_modules``
or from the top-level ``app.services.ai`` package.
"""

from __future__ import annotations

from app.services.ai.agent_modules import (  # noqa: F401  (re-export back-compat)
    BaseAgent,
    BUSINESS_CARD_TITLES,
    CustomerAgent,
    EmbeddingService,
    InventoryAgent,
    ProductAgent,
    WatchtowerService,
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
from app.services.ai.agent_modules.embedding import (  # noqa: F401
    _euclidean_sq,
    _run_kmeans,
)

# Back-compat underscore aliases for the text-extraction helpers
# (original module exposed them with leading underscores).
_text_lines = text_lines
_extract_email = extract_email
_extract_phone = extract_phone
_extract_contact_person = extract_contact_person
_extract_company_name = extract_company_name
_normalize_customer_source_text = normalize_customer_source_text
_heuristic_customer_recognition = heuristic_customer_recognition
_merge_customer_recognition = merge_customer_recognition
_compose_customer_recognition_context = compose_customer_recognition_context


__all__ = [
    "CustomerAgent",
    "InventoryAgent",
    "ProductAgent",
    "EmbeddingService",
    "WatchtowerService",
    "BaseAgent",
    "BUSINESS_CARD_TITLES",
    # Public text extraction helpers
    "compose_customer_recognition_context",
    "extract_company_name",
    "extract_contact_person",
    "extract_email",
    "extract_phone",
    "heuristic_customer_recognition",
    "merge_customer_recognition",
    "normalize_customer_source_text",
    "text_lines",
    # Underscore back-compat
    "_text_lines",
    "_extract_email",
    "_extract_phone",
    "_extract_contact_person",
    "_extract_company_name",
    "_normalize_customer_source_text",
    "_heuristic_customer_recognition",
    "_merge_customer_recognition",
    "_compose_customer_recognition_context",
    "_run_kmeans",
    "_euclidean_sq",
]
