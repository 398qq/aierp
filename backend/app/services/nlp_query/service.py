"""Natural-language ERP query — orchestration layer.

Public entry point: ``natural_language_query(db, query)``.

Layering (per audit §5.2 stage 2 step 5):
- Trigger  : the API caller invokes this function with a user query.
- This module : orchestration — detect domains, decide which contexts
                to build (full vs summary) given query length and
                domain hit count, call the LLM with the assembled
                context.
- Execution : the actual SQL is in :mod:`.context`; the LLM call is
                delegated to :class:`app.services.ai.client.ai_client`.

Failure mode: AI errors never raise to the caller. They degrade to
a structured error response so the API can return 200 with an
explanation, not a 500.
"""

from __future__ import annotations

import logging
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.services.ai.client import ai_client
from app.services.ai.prompts import nlp_query_prompt

from .context import build_full_context, build_summary_context
from .detection import all_domains, detect_domains

logger = logging.getLogger(__name__)


async def natural_language_query(db: AsyncSession, query: str) -> dict[str, Any]:
    """Process a natural-language query against the ERP system.

    Smart context selection:
    - Fewer than 3 characters → no context (probable test/greeting).
    - Single-domain queries: include that domain's full context +
      summary counts from all other domains.
    - Multi-domain or ambiguous queries: include full context from
      all matched domains + summary from the rest.
    - Complex queries (long, multi-domain): include everything.

    Returns a dict with ``answer``, ``related_entities``,
    ``suggested_followups``, ``actions``, and ``confidence``.
    """

    domains = detect_domains(query)
    all_d = all_domains()
    context: dict[str, str] = {}

    if len(query.strip()) < 3:
        # Trivial query — skip heavy DB work
        pass
    elif len(domains) <= 1:
        # Single-domain: full context for that domain (or general if
        # none detected) plus lightweight summary for the rest.
        primary = domains[0] if domains else "general"
        for d in all_d:
            if d == primary or (primary == "general" and len(query) > 10):
                context[f"{d}_context"] = await build_full_context(d, db)
            else:
                context[f"{d}_context"] = await build_summary_context(d, db)
    else:
        # Multi-domain: full context for each detected domain,
        # summary for the rest.
        for d in all_d:
            if d in domains or len(domains) >= 3:
                context[f"{d}_context"] = await build_full_context(d, db)
            else:
                context[f"{d}_context"] = await build_summary_context(d, db)

    output_schema: dict[str, Any] = {
        "answer": "string: 中文自然语言回答，清晰直接",
        "data_summary": "string: 支撑答案的数据摘要，1-2句话",
        "related_entities": (
            "list of dicts: {type: string (customer/product/order/opportunity/"
            "supplier/invoice), id: integer, name: string, relevance: string}"
        ),
        "suggested_followups": "list of strings: 建议追问的问题，2-3条",
        "actions": (
            "list of dicts: {action: string, type: string, entity: string, "
            "urgency: string (高/中/低)} — 如果答案暗示了可执行的操作"
        ),
        "confidence": "integer 0-100: 回答置信度",
    }

    try:
        system_prompt = (
            "你是一个电子元器件分销ERP系统的智能助手。"
            "基于提供的ERP数据上下文，用中文自然语言回答用户问题。"
            "回答应数据驱动、准确、可执行。"
            "如果数据不足以回答，诚实说明并建议如何获取数据。"
        )
        return await ai_client.chat_structured(
            [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": nlp_query_prompt(query, context)},
            ],
            output_schema,
            temperature=0.3,
        )
    except Exception as exc:
        logger.exception("NLP query failed")
        return {
            "answer": f"抱歉，查询处理失败：{exc}",
            "data_summary": "",
            "related_entities": [],
            "suggested_followups": [],
            "actions": [],
            "confidence": 0,
        }
