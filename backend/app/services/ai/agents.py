"""AI Agents — each business domain has a specialized agent with structured output."""

import logging
import re
from collections.abc import AsyncGenerator

from sqlalchemy import select

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


class EmbeddingService:
    """Vector embeddings for semantic customer search — backed by pgvector."""

    @staticmethod
    async def embed_customer(customer_data: dict) -> list[float]:
        """Build rich embedding from key customer fields."""
        parts = [
            f"客户：{customer_data.get('name')}",
            f"行业：{customer_data.get('industry', '')}",
            f"区域：{customer_data.get('region', '')}",
            f"类型：{customer_data.get('customer_type', '')}",
            f"等级：{customer_data.get('level', '')}",
            f"信用等级：{customer_data.get('credit_level', '')}",
            f"来源：{customer_data.get('source', '')}",
            f"备注：{customer_data.get('notes', '')}",
        ]
        return await ai_client.embed_single("，".join(parts))

    @staticmethod
    async def embed_product(product_data: dict) -> list[float]:
        text = f"型号：{product_data.get('part_number')}，描述：{product_data.get('description', '')}，品牌：{product_data.get('brand_name', '')}"
        return await ai_client.embed_single(text)

    @staticmethod
    async def embed_supplier(supplier_data: dict) -> list[float]:
        parts = [
            f"供应商：{supplier_data.get('name')}",
            f"产品线：{supplier_data.get('product_lines', '')}",
            f"类型：{supplier_data.get('supplier_type', '')}",
            f"区域：{supplier_data.get('region', '')}",
            f"认证：{supplier_data.get('certifications', '')}",
            f"付款条件：{supplier_data.get('payment_terms', '')}",
            f"财务评级：{supplier_data.get('financial_rating', '')}",
            f"网站：{supplier_data.get('website', '')}",
            f"备注：{supplier_data.get('notes', '')}",
        ]
        return await ai_client.embed_single("，".join(parts))

    @staticmethod
    async def similar_customers(embedding: list[float], db_session, top_k: int = 10, exclude_id: int | None = None) -> list:
        """pgvector cosine-distance search — runs entirely in PostgreSQL."""
        from sqlalchemy import select

        from app.models.customer import Customer

        cond = [Customer.embedding.isnot(None), Customer.deleted_at.is_(None)]
        if exclude_id is not None:
            cond.append(Customer.id != exclude_id)

        result = await db_session.execute(
            select(
                Customer.id, Customer.name, Customer.industry, Customer.region,
                Customer.embedding.cosine_distance(embedding).label("distance"),
            )
            .where(*cond)
            .order_by(Customer.embedding.cosine_distance(embedding))
            .limit(top_k)
        )
        rows = result.all()
        return [
            {
                "id": r[0], "name": r[1], "industry": r[2], "region": r[3],
                "similarity": round(1 - float(r[4]) / 2, 4),  # cosine distance [0,2] → similarity [0,1]
            }
            for r in rows
        ]

    @staticmethod
    async def similar_by_text(query: str, db_session, top_k: int = 10) -> list:
        """Search similar customers by natural-language query."""
        embedding = await ai_client.embed_single(query)
        return await EmbeddingService.similar_customers(embedding, db_session, top_k)

    @staticmethod
    async def similar_suppliers(embedding: list[float], db_session, top_k: int = 10, exclude_id: int | None = None) -> list:
        """pgvector cosine-distance search for suppliers."""
        from app.models.product import Supplier
        cond = [Supplier.embedding.isnot(None), Supplier.deleted_at.is_(None)]
        if exclude_id is not None:
            cond.append(Supplier.id != exclude_id)
        result = await db_session.execute(
            select(Supplier.id, Supplier.name, Supplier.product_lines, Supplier.region,
                   Supplier.embedding.cosine_distance(embedding).label("distance"))
            .where(*cond)
            .order_by(Supplier.embedding.cosine_distance(embedding))
            .limit(top_k)
        )
        rows = result.all()
        return [{"id": r[0], "name": r[1], "product_lines": r[2], "region": r[3],
                 "similarity": round(1 - float(r[4]) / 2, 4)} for r in rows]

    @staticmethod
    async def similar_suppliers_by_text(query: str, db_session, top_k: int = 10) -> list:
        """Search similar suppliers by natural-language query."""
        embedding = await ai_client.embed_single(query)
        return await EmbeddingService.similar_suppliers(embedding, db_session, top_k)

    @staticmethod
    async def index_all_suppliers(db_session, batch_size: int = 50) -> dict:
        """Generate embeddings for all suppliers that lack them — cursor-paginated to avoid OOM."""
        from app.models.product import Supplier

        # 1. Fetch only IDs to avoid loading full objects into memory at once
        id_rows = (await db_session.execute(
            select(Supplier.id).where(Supplier.deleted_at.is_(None), Supplier.embedding.is_(None))
        )).scalars().all()

        indexed, errors = 0, 0
        total = len(id_rows)
        processed = 0

        while processed < total:
            batch_ids = id_rows[processed: processed + batch_size]
            batch = (await db_session.execute(
                select(Supplier).where(Supplier.id.in_(batch_ids))
            )).scalars().all()
            processed += len(batch_ids)

            texts = [f"供应商：{s.name}，产品线：{s.product_lines or ''}，类型：{s.supplier_type or ''}，"
                     f"区域：{s.region or ''}，认证：{s.certifications or ''}，"
                     f"付款条件：{s.payment_terms or ''}，备注：{s.notes or ''}"
                     for s in batch]
            try:
                embeddings = await ai_client.embed(texts)
                for s, emb in zip(batch, embeddings):
                    s.embedding = emb
                indexed += len(batch)
                await db_session.flush()
            except Exception:
                logger.exception(f"Embed supplier batch offset {processed - batch_size} failed")
                errors += len(batch)

        return {"indexed": indexed, "skipped": 0, "errors": errors}

    @staticmethod
    async def index_all_products(db_session, batch_size: int = 50) -> dict:
        """Generate embeddings for all products that lack them — cursor-paginated to avoid OOM."""
        from app.models.product import Product

        id_rows = (await db_session.execute(
            select(Product.id).where(Product.deleted_at.is_(None), Product.embedding.is_(None))
        )).scalars().all()

        indexed, errors = 0, 0
        total = len(id_rows)
        processed = 0

        while processed < total:
            batch_ids = id_rows[processed: processed + batch_size]
            batch = (await db_session.execute(
                select(Product).where(Product.id.in_(batch_ids))
            )).scalars().all()
            processed += len(batch_ids)

            texts = [f"型号：{p.sku or ''}，名称：{p.name}，品类：{p.category or ''}，"
                     f"规格：{p.specs or ''}，封装：{p.package_type or ''}，备注：{p.notes or ''}"
                     for p in batch]
            try:
                embeddings = await ai_client.embed(texts)
                for p, emb in zip(batch, embeddings):
                    p.embedding = emb
                indexed += len(batch)
                await db_session.flush()
            except Exception:
                logger.exception(f"Embed product batch offset {processed - batch_size} failed")
                errors += len(batch)

        return {"indexed": indexed, "skipped": 0, "errors": errors}

    @staticmethod
    async def index_all(db_session, batch_size: int = 50) -> dict:
        """Generate and store embeddings for all customers that lack them. Returns {indexed, skipped, errors}."""
        from sqlalchemy import select

        from app.models.customer import Customer

        id_rows = (await db_session.execute(
            select(Customer.id).where(Customer.deleted_at.is_(None), Customer.embedding.is_(None))
        )).scalars().all()

        indexed, errors = 0, 0
        total = len(id_rows)
        processed = 0

        while processed < total:
            batch_ids = id_rows[processed: processed + batch_size]
            batch = (await db_session.execute(
                select(Customer).where(Customer.id.in_(batch_ids))
            )).scalars().all()
            processed += len(batch_ids)

            texts = [
                f"客户：{c.name}，行业：{c.industry or ''}，区域：{c.region or ''}，"
                f"类型：{c.customer_type or ''}，等级：{c.level or ''}，"
                f"信用等级：{c.credit_level or ''}，来源：{c.source or ''}，备注：{c.notes or ''}"
                for c in batch
            ]
            try:
                embeddings = await ai_client.embed(texts)
                for c, emb in zip(batch, embeddings):
                    c.embedding = emb
                indexed += len(batch)
                await db_session.flush()
            except Exception:
                logger.exception(f"Embed batch offset {processed - batch_size} failed")
                errors += len(batch)

        return {"indexed": indexed, "skipped": total - indexed - errors, "errors": errors}

    @staticmethod
    async def segment_customers(db_session, n_clusters: int = 5) -> dict:
        """K-means clustering on customer embeddings, with LLM-generated cluster labels.

        Returns {clusters: [{id, label, size, avg_similarity, sample_names}]}
        """
        from collections import defaultdict
        import asyncio

        from app.models.customer import Customer

        result = await db_session.execute(
            select(Customer.id, Customer.name, Customer.embedding, Customer.industry, Customer.level)
            .where(Customer.embedding.isnot(None), Customer.deleted_at.is_(None))
        )
        rows = result.all()
        if len(rows) < n_clusters:
            return {"clusters": [], "error": f"Need at least {n_clusters} customers with embeddings"}

        embeddings = [list(r[2]) for r in rows]  # Convert pgvector/numpy to Python list

        # Run K-means in thread pool to avoid blocking the event loop
        labels, centroids = await asyncio.to_thread(_run_kmeans, embeddings, n_clusters)

        # Build clusters
        clusters = defaultdict(list)
        for i, r in enumerate(rows):
            clusters[labels[i]].append({
                "id": r[0], "name": r[1], "industry": r[3], "level": r[4],
            })

        # Compute avg intra-cluster similarity and pick top samples
        result_clusters = []
        dim = len(embeddings[0])
        for j, members in clusters.items():
            centroid = centroids[j]
            avg_sim = 0.0
            for e in [embeddings[i] for i, lbl in enumerate(labels) if lbl == j]:
                avg_sim += 1 - _euclidean_sq(e, centroid) ** 0.5 / dim
            avg_sim = round(avg_sim / len(members), 4) if members else 0

            # Pick top-5 representative samples nearest centroid
            sorted_members = sorted(members, key=lambda m: _euclidean_sq(
                embeddings[next(i for i, r in enumerate(rows) if r[0] == m["id"])], centroid
            ))
            sample_names = [m["name"] for m in sorted_members[:5]]

            common_industry = max(set(m["industry"] for m in members), key=lambda x: sum(1 for m in members if m["industry"] == x))
            common_level = max(set(m["level"] for m in members), key=lambda x: sum(1 for m in members if m["level"] == x))

            result_clusters.append({
                "id": j,
                "size": len(members),
                "avg_similarity": avg_sim,
                "sample_names": sample_names,
                "common_industry": common_industry,
                "common_level": common_level,
                "label": f"群组{j + 1} ({common_industry or '未知行业'}·{common_level or '未知等级'})",
            })

        result_clusters.sort(key=lambda x: -x["size"])
        return {"clusters": result_clusters, "total": len(rows)}


def _euclidean_sq(a: list[float], b: list[float]) -> float:
    return float(sum((x - y) ** 2 for x, y in zip(a, b)))


def _run_kmeans(embeddings: list[list[float]], n_clusters: int, n_iter: int = 30) -> tuple[list[int], list[list[float]]]:
    """Pure synchronous K-means++ on a list of embedding vectors.
    Returns (labels, centroids).
    """
    import random

    dim = len(embeddings[0])

    # K-means++ initialization
    centroids = [random.choice(embeddings)[:]]
    for _ in range(1, n_clusters):
        dists = [min(_euclidean_sq(e, c) for c in centroids) for e in embeddings]
        total = sum(dists)
        pick = random.random() * total
        acc = 0
        for i, d in enumerate(dists):
            acc += d
            if acc >= pick:
                centroids.append(embeddings[i][:])
                break

    # Run K-means iterations
    labels = [0] * len(embeddings)
    for _ in range(n_iter):
        changed = False
        for i, e in enumerate(embeddings):
            best = min(range(n_clusters), key=lambda j: _euclidean_sq(e, centroids[j]))
            if best != labels[i]:
                labels[i] = best
                changed = True
        if not changed:
            break
        # Update centroids
        for j in range(n_clusters):
            members = [embeddings[i] for i, lbl in enumerate(labels) if lbl == j]
            if members:
                centroids[j] = [sum(x[d] for x in members) / len(members) for d in range(dim)]

    return labels, centroids


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


class WatchtowerService:
    """AI-powered cross-domain anomaly scanner."""

    @staticmethod
    async def scan_all(db) -> list[dict]:
        """Scan all domains for anomalies and return findings."""
        from datetime import datetime, timedelta, timezone
        from sqlalchemy import func, select
        from app.models.customer import Customer
        from app.models.product import Inventory
        from app.models.sales import Opportunity
        from app.models.finance import Invoice

        findings = []

        # 1. Inventory: low stock items
        low_stock = (await db.execute(
            select(func.count(Inventory.id)).where(
                Inventory.deleted_at.is_(None),
                Inventory.quantity <= Inventory.safety_stock,
                Inventory.quantity > 0,
            )
        )).scalar() or 0
        if low_stock > 0:
            findings.append({
                "domain": "库存", "severity": "high" if low_stock > 10 else "medium",
                "title": f"低库存预警：{low_stock} 个SKU", "detail": f"当前有 {low_stock} 个产品的库存低于安全库存线",
            })

        # 2. Inventory: dead stock (no movement in 180d)
        d180 = datetime.now(timezone.utc) - timedelta(days=180)
        dead = (await db.execute(
            select(func.count(Inventory.id)).where(
                Inventory.deleted_at.is_(None),
                Inventory.quantity > 0,
                Inventory.updated_at < d180,
            )
        )).scalar() or 0
        if dead > 0:
            findings.append({
                "domain": "库存", "severity": "medium",
                "title": f"滞销库存：{dead} 个SKU", "detail": f"{dead} 个产品超过180天无变动",
            })

        # 3. Finance: overdue invoices
        overdue = (await db.execute(
            select(func.count(Invoice.id), func.coalesce(func.sum(Invoice.amount), 0)).where(
                Invoice.deleted_at.is_(None),
                Invoice.status == "overdue",
            )
        )).first()
        if overdue and overdue[0] > 0:
            findings.append({
                "domain": "财务", "severity": "critical" if float(overdue[1]) > 100000 else "high",
                "title": f"逾期发票：{overdue[0]} 张", "detail": f"逾期金额 ¥{float(overdue[1]):,.0f}",
            })

        # 4. Sales: stale opportunities
        d30 = datetime.now(timezone.utc) - timedelta(days=30)
        stale_opps = (await db.execute(
            select(func.count(Opportunity.id), func.coalesce(func.sum(Opportunity.amount), 0)).where(
                Opportunity.deleted_at.is_(None),
                Opportunity.status == "open",
                Opportunity.updated_at < d30,
            )
        )).first()
        if stale_opps and stale_opps[0] > 0:
            findings.append({
                "domain": "销售", "severity": "high" if stale_opps[0] > 5 else "medium",
                "title": f"停滞商机：{stale_opps[0]} 个", "detail": f"{stale_opps[0]} 个开放商机超过30天未更新，合计 ¥{float(stale_opps[1]):,.0f}",
            })

        # 5. Customer: no contact in 90 days
        d90 = datetime.now(timezone.utc) - timedelta(days=90)
        silent = (await db.execute(
            select(func.count(Customer.id)).where(
                Customer.deleted_at.is_(None),
                Customer.level.in_(["A", "B"]),
                Customer.last_contacted_at.isnot(None),
                Customer.last_contacted_at < d90,
            )
        )).scalar() or 0
        if silent > 0:
            findings.append({
                "domain": "客户", "severity": "medium",
                "title": f"长期未联系客户：{silent} 个", "detail": f"{silent} 个A/B级客户超过90天未联系",
            })

        return findings

    @staticmethod
    async def scan_and_notify(db) -> dict:
        """Scan all domains and create notification entries for findings."""
        from app.services.notification_service import create_notification

        findings = await WatchtowerService.scan_all(db)
        created = 0
        for f in findings:
            try:
                await create_notification(
                    db, user_id=1,
                    type=f"watchtower_{f['domain']}",
                    title=f"[{f['severity'].upper()}] {f['title']}",
                    content=f["detail"],
                )
                created += 1
            except Exception as e:
                logger.warning(f"Watchtower notification creation failed: {e}")

        # Also create a summary if findings exist
        if findings:
            summary_lines = [f"- [{f['severity']}] [{f['domain']}] {f['title']}" for f in findings]
            try:
                await create_notification(
                    db, user_id=1,
                    type="watchtower_summary",
                    title=f"Watchtower 扫描报告 — {len(findings)} 个预警",
                    content="\n".join(summary_lines),
                )
            except Exception as e:
                logger.warning(f"Watchtower summary creation failed: {e}")

        return {"findings": len(findings), "notifications_created": created}
