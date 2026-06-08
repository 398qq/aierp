"""CustomerAgent — RFM, churn, recognition, follow-up analysis, alert enrichment.

The customer-domain AI agent. Powers the AI features on the customer
detail, workbench, and dashboard pages.
"""
from __future__ import annotations

import logging
from collections.abc import AsyncGenerator

from app.config import settings
from app.services.ai.agent_modules._text_extraction import (
    compose_customer_recognition_context,
    heuristic_customer_recognition,
    merge_customer_recognition,
)
from app.services.ai.client import ai_client
from app.services.ai.prompts import (
    CUSTOMER_AGENT_SYSTEM,
    alert_enrichment_prompt,
    churn_risk_prompt,
    customer_recognition_from_ocr_candidates_prompt,
    customer_recognition_prompt,
    followup_analysis_prompt,
    followup_recognition_prompt,
    followup_suggestion_prompt,
    rfm_prompt,
)

logger = logging.getLogger(__name__)


BUSINESS_CARD_TITLES = (
    "董事长", "总经理", "副总", "经理", "主管", "销售", "业务", "工程师", "采购", "负责人",
    "CEO", "CTO", "COO", "Founder", "Manager", "Director", "Engineer", "Sales",
)


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
    async def recognize_customer(text: str, ocr_candidates: list[dict] | None = None) -> dict:
        recognition_context = _compose_customer_recognition_context(text, ocr_candidates)
        schema = {
            "name": "string",
            "short_name": "string",
            "customer_type": "string: 终端/贸易商/方案商/OEM or empty",
            "industry": "string: 汽车电子/消费电子/工业控制/通信设备/医疗器械/安防监控/其他 or empty",
            "level": "string: A/B/C/D or empty",
            "region": "string: 华东/华南/华北/华中/西南/西北/东北/海外 or empty",
            "source": "string: 展会/转介绍/线上推广/电话开发/公司资源 or empty",
            "contact_person": "string",
            "phone": "string",
            "email": "string",
            "owner": "string",
            "credit_limit": "number or null",
            "credit_level": "string: A/B/C/D or empty",
            "address": "string",
            "notes": "string",
            "confidence": "number 0-1",
            "summary": "string",
        }
        try:
            user_prompt = (
                customer_recognition_from_ocr_candidates_prompt(text, ocr_candidates)
                if ocr_candidates
                else customer_recognition_prompt(text)
            )
            result = await ai_client.chat_structured(
                [
                    {"role": "system", "content": CUSTOMER_AGENT_SYSTEM},
                    {"role": "user", "content": user_prompt},
                ],
                schema,
                temperature=0.1,
            )
            return _merge_customer_recognition(result, recognition_context)
        except Exception as e:
            logger.error(f"Customer recognition failed: {e}")
            return _heuristic_customer_recognition(recognition_context)

    @staticmethod
    async def recognize_followup(text: str, customer_data: dict, now_text: str) -> dict:
        schema = {
            "method": "string: phone/visit/video/email/wechat/other or empty",
            "status": "string: planned/in_progress/completed/cancelled or empty",
            "priority": "string: high/medium/low or empty",
            "content": "string",
            "result": "string",
            "planned_at": "string: YYYY-MM-DD HH:mm:ss or empty",
            "completed_at": "string: YYYY-MM-DD HH:mm:ss or empty",
            "assigned_to": "string",
            "confidence": "number 0-1",
            "summary": "string",
        }
        try:
            result = await ai_client.chat_structured(
                [
                    {"role": "system", "content": CUSTOMER_AGENT_SYSTEM},
                    {"role": "user", "content": followup_recognition_prompt(text, customer_data, now_text)},
                ],
                schema,
                temperature=0.1,
                model=settings.AI_FOLLOWUP_MODEL or settings.AI_MODEL,
            )
            return result
        except Exception as e:
            logger.error(f"Followup recognition failed: {e}")
            return {
                "method": "",
                "status": "",
                "priority": "",
                "content": text,
                "result": "",
                "planned_at": "",
                "completed_at": "",
                "assigned_to": customer_data.get("owner") or "",
                "confidence": 0,
                "summary": "AI识别暂不可用，已保留原始内容",
            }

    @staticmethod
    async def analyze_followups(followups: list[dict], customer_name: str = "") -> dict:
        """Semantic analysis of follow-up records: sentiment, topics, action items, risk signals."""
        schema = {
            "sentiment": "string: 积极/中性/消极",
            "sentiment_reason": "string",
            "key_topics": "list of strings (max 5)",
            "action_items": "list of strings",
            "risk_signals": "list of strings",
            "summary": "string (2-3 sentences)",
        }
        text = "\n".join(
            f"- [{f.get('method', '')}] {f.get('content', '')} (结果: {f.get('result', '无')})"
            for f in followups[-20:]  # Last 20 followups
        )
        if not text.strip():
            return {
                "sentiment": "中性", "sentiment_reason": "无跟进记录",
                "key_topics": [], "action_items": [], "risk_signals": [],
                "summary": "暂无跟进记录可供分析",
            }
        try:
            result = await ai_client.chat_structured(
                [
                    {"role": "system", "content": CUSTOMER_AGENT_SYSTEM},
                    {"role": "user", "content": followup_analysis_prompt(text, customer_name)},
                ],
                schema,
            )
            return result
        except Exception as e:
            logger.error(f"Followup analysis failed: {e}")
            return {
                "sentiment": "中性", "sentiment_reason": "AI分析失败",
                "key_topics": [], "action_items": [], "risk_signals": [],
                "summary": "AI分析暂时不可用",
            }

    @staticmethod
    async def enrich_alert(alert_context: dict) -> dict:
        """Generate AI action suggestions and templates for an alert event."""
        schema = {
            "followup_method": "string: 电话/邮件/拜访",
            "followup_timing": "string: when to contact",
            "talking_points": "list of strings (2-3)",
            "message_template": "string: ready-to-use message",
            "worst_case": "string",
        }
        try:
            result = await ai_client.chat_structured(
                [
                    {"role": "system", "content": CUSTOMER_AGENT_SYSTEM},
                    {"role": "user", "content": alert_enrichment_prompt(alert_context)},
                ],
                schema,
            )
            return result
        except Exception as e:
            logger.error(f"Alert enrichment failed: {e}")
            return {
                "followup_method": "电话", "followup_timing": "尽快",
                "talking_points": [], "message_template": "",
                "worst_case": "AI分析暂时不可用",
            }

    @staticmethod
    async def chat(query: str, context: str = "", history: list[dict] | None = None, model: str | None = None) -> AsyncGenerator[str, None]:
        messages = [{"role": "system", "content": f"{CUSTOMER_AGENT_SYSTEM}\n\n当前上下文：{context}"}]
        if history:
            for msg in history:
                if msg.get("role") in ("user", "assistant") and msg.get("content"):
                    messages.append({"role": msg["role"], "content": msg["content"]})
        messages.append({"role": "user", "content": query})
        async for chunk in ai_client.chat_stream(messages, model=model):
            yield chunk


































































































































































































































































































































# Back-compat: original module exposed these with leading underscores.
_compose_customer_recognition_context = compose_customer_recognition_context
_heuristic_customer_recognition = heuristic_customer_recognition
_merge_customer_recognition = merge_customer_recognition
