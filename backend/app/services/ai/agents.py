"""AI Agents — each business domain has a specialized agent with structured output.

Note: WatchtowerService and EmbeddingService have been extracted to
`agent_modules/` for better maintainability. They remain importable from
this module for backward compatibility.
"""

import logging
import re
from collections.abc import AsyncGenerator

from app.config import settings
from app.services.ai.client import ai_client
from app.services.ai.prompts import (
    CUSTOMER_AGENT_SYSTEM,
    INVENTORY_AGENT_SYSTEM,
    PRODUCT_AGENT_SYSTEM,
    alert_enrichment_prompt,
    bom_parse_prompt,
    churn_risk_prompt,
    customer_recognition_from_ocr_candidates_prompt,
    customer_recognition_prompt,
    followup_analysis_prompt,
    followup_recognition_prompt,
    followup_suggestion_prompt,
    product_parse_prompt,
    rfm_prompt,
    substitute_prompt,
)

# Re-exports for backward compatibility (moved to agent_modules/)
from app.services.ai.agent_modules.embedding import (
    EmbeddingService,
    _euclidean_sq,
    _run_kmeans,
)
from app.services.ai.agent_modules.watchtower import WatchtowerService

__all__ = [
    "CustomerAgent",
    "InventoryAgent",
    "ProductAgent",
    "EmbeddingService",
    "WatchtowerService",
    "_run_kmeans",
    "_euclidean_sq",
]

logger = logging.getLogger(__name__)


BUSINESS_CARD_TITLES = (
    "董事长", "总经理", "副总", "经理", "主管", "销售", "业务", "工程师", "采购", "负责人",
    "CEO", "CTO", "COO", "Founder", "Manager", "Director", "Engineer", "Sales",
)


def _normalize_customer_source_text(text: str) -> str:
    raw = (text or "").strip()
    raw = re.sub(r"[ \t]+", " ", raw)
    raw = re.sub(r"(?<=\d)[\s\-]+(?=\d)", "", raw)
    raw = re.sub(r"(?i)\bE[-\s]*mail\b", "Email", raw)
    raw = re.sub(r"(?i)([A-Z0-9._%+-]+)\s*@\s*([A-Z0-9.-]+)\s*\.\s*([A-Z]{2,})", r"\1@\2.\3", raw)
    raw = re.sub(r"(?i)\b(?:Tel|Phone|Mobile|Mob|Cell)\s*[:：]?", "电话:", raw)
    raw = re.sub(r"(?i)\b(?:Address|Addr)\s*[:：]?", "地址:", raw)
    raw = re.sub(r"(?i)\b(?:Company|Company Name)\s*[:：]?", "公司:", raw)
    raw = re.sub(r"(?i)\b(?:Contact|Name)\s*[:：]?", "联系人:", raw)
    return raw


def _text_lines(text: str) -> list[str]:
    return [line.strip(" \t,，;；:：") for line in text.splitlines() if line.strip(" \t,，;；:：")]


def _extract_email(text: str) -> str:
    email_match = re.search(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", text)
    return email_match.group(0) if email_match else ""


def _extract_phone(text: str) -> str:
    mobile_list = re.findall(r"(?<!\d)(1[3-9]\d{9})(?!\d)", text)
    if mobile_list:
        return mobile_list[0]

    landline_list = re.findall(r"(?<!\d)(0\d{2,3}-?\d{7,8})(?!\d)", text)
    if landline_list:
        return landline_list[0]

    for line in _text_lines(text):
        if not re.search(r"(电话|手机|Tel|Phone|Mobile)", line, re.IGNORECASE):
            continue
        digits = re.sub(r"\D", "", line)
        if 8 <= len(digits) <= 13:
            return digits
    return ""


def _extract_contact_person(text: str) -> str:
    contact_match = re.search(r"(?:联系人|联系人姓名|contact)[:：\s]*([A-Za-z\u4e00-\u9fa5·]{2,20})", text, re.IGNORECASE)
    if contact_match:
        return contact_match.group(1)

    for line in _text_lines(text):
        if any(token in line for token in ("有限公司", "股份", "集团", "地址", "电话", "手机", "邮箱", "Email", "@")):
            continue
        if not any(title.lower() in line.lower() for title in BUSINESS_CARD_TITLES):
            continue
        zh_match = re.match(r"([\u4e00-\u9fa5·]{2,4})\s*(?:/|-|,|，|\s)*", line)
        if zh_match:
            return zh_match.group(1)
        title_words = {title.lower() for title in BUSINESS_CARD_TITLES if re.fullmatch(r"[A-Za-z]+", title)}
        name_words = []
        for word in re.findall(r"[A-Z][A-Za-z]+", line):
            if word.lower() in title_words:
                break
            name_words.append(word)
        if name_words:
            return " ".join(name_words[:3])
        en_match = re.match(r"([A-Z][A-Za-z]+(?:\s+[A-Z][A-Za-z]+){0,2})", line)
        if en_match:
            return en_match.group(1)

    for line in _text_lines(text):
        if any(token in line for token in ("有限公司", "股份", "集团", "地址", "邮箱", "Email", "@")):
            continue
        if not re.search(r"(?<!\d)(?:1[3-9]\d{9}|0\d{2,3}-?\d{7,8})(?!\d)", line):
            continue
        zh_match = re.match(r"([\u4e00-\u9fa5·]{2,4})\b", line)
        if zh_match:
            return zh_match.group(1)
        en_match = re.match(r"([A-Z][A-Za-z]+(?:\s+[A-Z][A-Za-z]+){0,2})", line)
        if en_match:
            return en_match.group(1)
    return ""


def _extract_company_name(text: str) -> str:
    company_field_match = re.search(
        r"(?:公司名称|客户名称|名称|公司)[:：]+[ \t]*([^\n,，]{2,80}?)(?=[,，\s]*(?:联系人|手机|电话|邮箱|行业|区域|来源|负责人|授信|地址|$))",
        text,
    )
    if company_field_match:
        return company_field_match.group(1).strip()

    name_match = re.search(
        r"([A-Za-z0-9\u4e00-\u9fa5（）()·\-\s]{2,60}(?:股份有限公司|有限公司|集团|公司|Inc\.?|Ltd\.?|Co\.?))",
        text,
    )
    if name_match:
        return name_match.group(1).strip()

    company_lines = []
    for line in _text_lines(text):
        line_match = re.search(
            r"([A-Za-z0-9\u4e00-\u9fa5（）()·\-\s]{2,60}(?:股份有限公司|有限公司|集团|公司|Inc\.?|Ltd\.?|Co\.?))",
            line,
        )
        if line_match:
            company_lines.append(line_match.group(1).strip())
        elif re.search(r"(?i)\b(?:technology|electronics|industrial)\b", line):
            company_lines.append(line)
    if company_lines:
        return max(company_lines, key=len)[:80]

    first_line = next((line for line in _text_lines(text) if not re.search(r"[@\d]", line)), "")
    return first_line[:60]


def _heuristic_customer_recognition(text: str) -> dict:
    raw = _normalize_customer_source_text(text)
    owner_match = re.search(r"(?:负责人|销售负责人|owner|sales owner)[:：\s]*([A-Za-z\u4e00-\u9fa5·]{2,20})", raw, re.IGNORECASE)
    address_match = re.search(r"(?:地址|公司地址)[:：\s]*([^\n]{4,120})", raw)
    level_match = re.search(r"(?:等级|客户等级|level)[:：\s]*([ABCD])", raw, re.IGNORECASE)
    name = _extract_company_name(raw)

    def pick(options: list[str]) -> str:
        return next((item for item in options if item in raw), "")

    def pick_by_keywords(mapping: dict[str, tuple[str, ...]]) -> str:
        lower = raw.lower()
        for value, keywords in mapping.items():
            if any(k.lower() in lower for k in keywords):
                return value
        return ""

    industry = pick(["汽车电子", "消费电子", "工业控制", "通信设备", "医疗器械", "安防监控"])
    if not industry:
        industry = pick_by_keywords({
            "汽车电子": ("车规", "车载", "automotive"),
            "消费电子": ("消费类", "家电", "consumer electronics"),
            "工业控制": ("工控", "plc", "industrial control"),
            "通信设备": ("通信", "5g", "networking"),
            "医疗器械": ("医疗", "医械", "medical"),
            "安防监控": ("安防", "监控", "security camera"),
            "其他": ("其他", "others"),
        })

    region = pick(["华东", "华南", "华北", "华中", "西南", "西北", "东北", "海外"])
    if not region:
        region = pick_by_keywords({
            "华南": ("广东", "深圳", "广州", "东莞", "佛山", "珠海"),
            "华东": ("上海", "江苏", "浙江", "杭州", "苏州", "宁波"),
            "华北": ("北京", "天津", "河北", "山东", "青岛", "济南"),
            "华中": ("湖北", "湖南", "河南", "武汉", "长沙", "郑州"),
            "西南": ("四川", "重庆", "云南", "贵州", "成都"),
            "西北": ("陕西", "甘肃", "宁夏", "新疆", "西安"),
            "东北": ("辽宁", "吉林", "黑龙江", "沈阳", "大连", "哈尔滨"),
            "海外": ("海外", "香港", "澳门", "台湾", "overseas"),
        })

    source = pick(["展会", "转介绍", "线上推广", "电话开发", "公司资源"])
    if not source:
        source = pick_by_keywords({
            "展会": ("展会", "博览会", "expo", "fair"),
            "转介绍": ("转介绍", "介绍", "referral"),
            "线上推广": ("线上", "官网", "公众号", "抖音", "小红书", "广告", "线索平台", "网站留资", "website", "留资", "seo", "sem"),
            "电话开发": ("电话开发", "cold call", "陌拜电话", "telemarketing"),
            "公司资源": ("公司资源", "历史客户", "老客户"),
        })

    customer_type = pick(["终端", "贸易商", "方案商", "OEM"])
    if not customer_type:
        customer_type = pick_by_keywords({
            "终端": ("终端", "终端客户", "end customer"),
            "贸易商": ("贸易商", "分销", "distributor", "代理"),
            "方案商": ("方案商", "系统集成", "方案公司", "si"),
            "OEM": ("oem", "贴牌", "代工"),
        })

    credit_limit = None
    credit_match = re.search(r"(?:授信|信用额度|额度)[:：\s]*([0-9]+(?:\.[0-9]+)?)\s*(万|w|W|千|k|K|元)?", raw)
    if credit_match:
        amount = float(credit_match.group(1))
        unit = (credit_match.group(2) or "").lower()
        if unit in ("万", "w"):
            amount *= 10000
        elif unit in ("千", "k"):
            amount *= 1000
        credit_limit = int(amount)

    short_name = ""
    if name:
        short_name = re.sub(r"(股份有限公司|有限公司|集团|公司)$", "", name).strip()
        short_name = re.sub(r"^(深圳市|上海市|北京市|广州市|杭州市|苏州市|东莞市|宁波市)", "", short_name).strip()
        if not short_name:
            short_name = name

    credit_level_match = re.search(r"(?:信用等级|授信等级|等级)[:：\s]*([ABCD])(?:级|类)?", raw, re.IGNORECASE)
    credit_level = credit_level_match.group(1).upper() if credit_level_match else ""
    if credit_limit is not None:
        if not credit_level:
            if credit_limit >= 500000:
                credit_level = "A"
            elif credit_limit >= 200000:
                credit_level = "B"
            elif credit_limit >= 50000:
                credit_level = "C"
            else:
                credit_level = "D"

    phone_value = _extract_phone(raw)
    email_value = _extract_email(raw)
    contact_person = _extract_contact_person(raw)

    return {
        "name": name,
        "short_name": short_name,
        "customer_type": customer_type,
        "industry": industry,
        "level": (level_match.group(1).upper() if level_match else ""),
        "region": region,
        "source": source,
        "contact_person": contact_person,
        "phone": phone_value,
        "email": email_value,
        "owner": (owner_match.group(1) if owner_match else ""),
        "credit_limit": credit_limit,
        "credit_level": credit_level,
        "address": (address_match.group(1).strip() if address_match else ""),
        "notes": raw,
        "confidence": 0.35,
        "summary": "AI结构化失败，已按规则提取关键信息",
    }


def _merge_customer_recognition(ai_result: dict, text: str) -> dict:
    merged = dict(ai_result or {})
    fallback = _heuristic_customer_recognition(text)
    for key, value in fallback.items():
        if key in ("confidence", "summary"):
            continue
        if merged.get(key) in (None, "") and value not in (None, ""):
            merged[key] = value
    try:
        ai_conf = float(merged.get("confidence") or 0)
    except Exception:
        ai_conf = 0.0
    merged["confidence"] = max(ai_conf, float(fallback.get("confidence") or 0))
    if not merged.get("summary"):
        merged["summary"] = "已识别客户资料"
    return merged


def _compose_customer_recognition_context(text: str, ocr_candidates: list[dict] | None = None) -> str:
    parts = [(text or "").strip()]
    for candidate in (ocr_candidates or [])[:6]:
        candidate_text = str(candidate.get("text") or "").strip()
        if candidate_text and candidate_text not in parts:
            parts.append(candidate_text)
    return "\n".join(part for part in parts if part)


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
































































































































































































































































































































class InventoryAgent:
    """Analyzes inventory data and provides stock recommendations."""

    @staticmethod
    async def analyze(inventory_data: list[dict]) -> dict:
        schema = {
            "urgent_purchases": "list of dicts: {product_name, current_stock, safety_stock, suggested_qty, reason}",
            "slow_moving": "list of dicts: {product_name, stock, days_untouched, suggestion}",
            "stockout_risks": "list of dicts: {product_name, current_stock, monthly_usage, months_remaining, suggestion}",
            "overall_assessment": "string",
        }
        try:
            import json
            data_text = json.dumps(inventory_data, ensure_ascii=False, default=str)
            result = await ai_client.chat_structured(
                [
                    {"role": "system", "content": INVENTORY_AGENT_SYSTEM},
                    {"role": "user", "content": f"分析以下库存数据，给出采购建议和预警：\n{data_text}"},
                ],
                schema,
            )
            return result
        except Exception as e:
            logger.error(f"Inventory analysis failed: {e}")
            return {
                "urgent_purchases": [],
                "slow_moving": [],
                "stockout_risks": [],
                "overall_assessment": f"AI分析暂时不可用: {e}",
            }


class ProductAgent:
    """AI-powered product data extraction, BOM parsing, and substitute matching."""

    @staticmethod
    async def parse_product(raw_text: str) -> dict:
        """Extract structured product fields from unstructured text."""
        schema = {
            "name": "string: standardized product name",
            "sku": "string | null",
            "category": "string: 电容/电阻/IC/连接器/电感/二三极管/晶振/其他",
            "package_type": "string | null",
            "specs": "object: key-value parameter pairs",
            "brand_name": "string | null",
            "unit": "string | null",
            "description": "string: one-line summary",
        }
        try:
            return await ai_client.chat_structured(
                [
                    {"role": "system", "content": PRODUCT_AGENT_SYSTEM},
                    {"role": "user", "content": product_parse_prompt(raw_text)},
                ],
                schema,
            )
        except Exception as e:
            logger.error(f"Product parse failed: {e}")
            return {"name": "", "sku": None, "category": None, "package_type": None,
                    "specs": {}, "brand_name": None, "unit": None, "description": f"解析失败: {e}"}

    @staticmethod
    async def parse_bom(bom_text: str) -> list[dict]:
        """Parse a BOM list into an array of product entries."""
        schema = {
            "items": "list of dicts: {line_no, customer_pn, mfr_pn, description, reference, quantity, package, category}"
        }
        try:
            result = await ai_client.chat_structured(
                [
                    {"role": "system", "content": PRODUCT_AGENT_SYSTEM},
                    {"role": "user", "content": bom_parse_prompt(bom_text)},
                ],
                schema,
            )
            return result.get("items", [])
        except Exception as e:
            logger.error(f"BOM parse failed: {e}")
            return []

    @staticmethod
    async def suggest_substitutes(product_info: dict) -> dict:
        """Recommend substitute parts based on product specs."""
        schema = {
            "direct_substitutes": "list of strings: pin-to-pin compatible alternatives",
            "functional_substitutes": "list of strings: functionally equivalent alternatives",
            "verification_notes": "list of strings: things to verify before substitution",
        }
        try:
            return await ai_client.chat_structured(
                [
                    {"role": "system", "content": PRODUCT_AGENT_SYSTEM},
                    {"role": "user", "content": substitute_prompt(product_info)},
                ],
                schema,
            )
        except Exception as e:
            logger.error(f"Substitute suggestion failed: {e}")
            return {"direct_substitutes": [], "functional_substitutes": [], "verification_notes": [f"AI分析失败: {e}"]}


WATCHTOWER_SYSTEM = """你是ERP系统的AI监控分析师。你需要扫描整个ERP系统的异常信号并生成预警报告。
请检测以下领域：
1. 库存风险：滞销库存、短缺风险、库存周转异常
2. 财务风险：逾期应收账款、现金流紧张、利润异常
3. 客户风险：客户流失信号、长期未联系客户、信用风险
4. 销售风险：商机流失、报价转化率下降、管道停滞
5. 供应链风险：供应商延迟、单一供应源、成本波动

对每个异常，给出严重程度（critical/high/medium/low）、摘要和影响描述。"""





























































































































