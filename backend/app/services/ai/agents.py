"""AI Agents — each business domain has a specialized agent with structured output."""

import json
import logging
from collections.abc import AsyncGenerator

from app.config import settings
from app.services.ai.client import ai_client
from app.services.ai.prompts import (
    CUSTOMER_AGENT_SYSTEM,
    churn_risk_prompt,
    followup_suggestion_prompt,
    rfm_prompt,
)

logger = logging.getLogger(__name__)


class CustomerAgent:
    """Analyzes customer data and provides insights."""

    @staticmethod
    async def rfm_analysis(customer_data: dict) -> dict:
        schema = {
            "r_score": "integer 1-5",
            "f_score": "integer 1-5",
            "m_score": "integer 1-5",
            "tier": "string: 重要价值/重要发展/重要保持/一般价值/流失风险",
            "suggestion": "string",
        }
        try:
            result = await ai_client.chat_structured(
                [
                    {"role": "system", "content": CUSTOMER_AGENT_SYSTEM},
                    {"role": "user", "content": rfm_prompt(customer_data)},
                ],
                schema,
            )
            return result
        except Exception as e:
            logger.error(f"RFM analysis failed: {e}")
            return {"r_score": 3, "f_score": 3, "m_score": 3, "tier": "未分析", "suggestion": "AI分析暂时不可用"}

    @staticmethod
    async def churn_risk(customer_data: dict) -> dict:
        schema = {
            "risk_score": "integer 0-100",
            "risk_level": "string: 低/中/高",
            "factors": "list of strings",
            "recommendation": "string",
        }
        try:
            result = await ai_client.chat_structured(
                [
                    {"role": "system", "content": CUSTOMER_AGENT_SYSTEM},
                    {"role": "user", "content": churn_risk_prompt(customer_data)},
                ],
                schema,
            )
            return result
        except Exception as e:
            logger.error(f"Churn risk analysis failed: {e}")
            return {"risk_score": 0, "risk_level": "未知", "factors": [], "recommendation": "AI分析暂时不可用"}

    @staticmethod
    async def followup_suggestion(customer_data: dict) -> dict:
        schema = {
            "topic": "string",
            "recommended_products": "list of strings",
            "risk_points": "list of strings",
        }
        try:
            result = await ai_client.chat_structured(
                [
                    {"role": "system", "content": CUSTOMER_AGENT_SYSTEM},
                    {"role": "user", "content": followup_suggestion_prompt(customer_data)},
                ],
                schema,
            )
            return result
        except Exception as e:
            logger.error(f"Followup suggestion failed: {e}")
            return {"topic": "", "recommended_products": [], "risk_points": []}

    @staticmethod
    async def chat(query: str, context: str = "", model: str | None = None) -> AsyncGenerator[str, None]:
        messages = [{"role": "system", "content": f"{CUSTOMER_AGENT_SYSTEM}\n\n当前上下文：{context}"}]
        messages.append({"role": "user", "content": query})
        async for chunk in ai_client.chat_stream(messages, model=model):
            yield chunk


class EmbeddingService:
    """Generates and manages vector embeddings for semantic search."""

    @staticmethod
    async def embed_customer(customer_data: dict) -> list[float]:
        text = f"客户：{customer_data.get('name')}，行业：{customer_data.get('industry', '')}，备注：{customer_data.get('notes', '')}"
        return await ai_client.embed_single(text)

    @staticmethod
    async def embed_product(product_data: dict) -> list[float]:
        text = f"型号：{product_data.get('part_number')}，描述：{product_data.get('description', '')}，品牌：{product_data.get('brand_name', '')}"
        return await ai_client.embed_single(text)

    @staticmethod
    async def similar_customers(embedding: list[float], db_session, top_k: int = 10) -> list:
        from sqlalchemy import text

        result = await db_session.execute(
            text(
                "SELECT id, name, 1 - (embedding <=> :emb) AS similarity FROM customers "
                "WHERE embedding IS NOT NULL AND deleted_at IS NULL "
                "ORDER BY embedding <=> :emb LIMIT :k"
            ),
            {"emb": str(embedding), "k": top_k},
        )
        return [{"id": r[0], "name": r[1], "similarity": round(float(r[2]), 4)} for r in result.fetchall()]
