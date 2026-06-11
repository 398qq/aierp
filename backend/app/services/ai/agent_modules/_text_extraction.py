"""OCR / business-card text extraction helpers used by CustomerAgent."""

from __future__ import annotations

import logging
import re

logger = logging.getLogger(__name__)

# Job-title vocabulary used to identify the "contact_person" line on
# a business card (e.g. "经理", "Director", "Engineer"). Mixed CN/EN.
BUSINESS_CARD_TITLES = (
    "董事长",
    "总经理",
    "副总",
    "经理",
    "主管",
    "销售",
    "业务",
    "工程师",
    "采购",
    "负责人",
    "CEO",
    "CTO",
    "COO",
    "Founder",
    "Manager",
    "Director",
    "Engineer",
    "Sales",
)


def normalize_customer_source_text(text: str) -> str:
    raw = (text or "").strip()
    raw = re.sub(r"[ \t]+", " ", raw)
    raw = re.sub(r"(?<=\d)[\s\-]+(?=\d)", "", raw)
    raw = re.sub(r"(?i)\bE[-\s]*mail\b", "Email", raw)
    raw = re.sub(
        r"(?i)([A-Z0-9._%+-]+)\s*@\s*([A-Z0-9.-]+)\s*\.\s*([A-Z]{2,})", r"\1@\2.\3", raw
    )
    raw = re.sub(r"(?i)\b(?:Tel|Phone|Mobile|Mob|Cell)\s*[:：]?", "电话:", raw)
    raw = re.sub(r"(?i)\b(?:Address|Addr)\s*[:：]?", "地址:", raw)
    raw = re.sub(r"(?i)\b(?:Company|Company Name)\s*[:：]?", "公司:", raw)
    raw = re.sub(r"(?i)\b(?:Contact|Name)\s*[:：]?", "联系人:", raw)
    return raw


def text_lines(text: str) -> list[str]:
    return [
        line.strip(" \t,，;；:：")
        for line in text.splitlines()
        if line.strip(" \t,，;；:：")
    ]


def extract_email(text: str) -> str:
    email_match = re.search(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", text)
    return email_match.group(0) if email_match else ""


def extract_phone(text: str) -> str:
    mobile_list = re.findall(r"(?<!\d)(1[3-9]\d{9})(?!\d)", text)
    if mobile_list:
        return mobile_list[0]

    landline_list = re.findall(r"(?<!\d)(0\d{2,3}-?\d{7,8})(?!\d)", text)
    if landline_list:
        return landline_list[0]

    for line in text_lines(text):
        if not re.search(r"(电话|手机|Tel|Phone|Mobile)", line, re.IGNORECASE):
            continue
        digits = re.sub(r"\D", "", line)
        if 8 <= len(digits) <= 13:
            return digits
    return ""


def extract_contact_person(text: str) -> str:
    contact_match = re.search(
        r"(?:联系人|联系人姓名|contact)[:：\s]*([A-Za-z\u4e00-\u9fa5·]{2,20})",
        text,
        re.IGNORECASE,
    )
    if contact_match:
        return contact_match.group(1)

    for line in text_lines(text):
        if any(
            token in line
            for token in (
                "有限公司",
                "股份",
                "集团",
                "地址",
                "电话",
                "手机",
                "邮箱",
                "Email",
                "@",
            )
        ):
            continue
        if not any(title.lower() in line.lower() for title in BUSINESS_CARD_TITLES):
            continue
        zh_match = re.match(r"([\u4e00-\u9fa5·]{2,4})\s*(?:/|-|,|，|\s)*", line)
        if zh_match:
            return zh_match.group(1)
        title_words = {
            title.lower()
            for title in BUSINESS_CARD_TITLES
            if re.fullmatch(r"[A-Za-z]+", title)
        }
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

    for line in text_lines(text):
        if any(
            token in line
            for token in ("有限公司", "股份", "集团", "地址", "邮箱", "Email", "@")
        ):
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


def extract_company_name(text: str) -> str:
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
    for line in text_lines(text):
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

    first_line = next(
        (line for line in text_lines(text) if not re.search(r"[@\d]", line)), ""
    )
    return first_line[:60]


def heuristic_customer_recognition(text: str) -> dict:
    raw = normalize_customer_source_text(text)
    owner_match = re.search(
        r"(?:负责人|销售负责人|owner|sales owner)[:：\s]*([A-Za-z\u4e00-\u9fa5·]{2,20})",
        raw,
        re.IGNORECASE,
    )
    address_match = re.search(r"(?:地址|公司地址)[:：\s]*([^\n]{4,120})", raw)
    level_match = re.search(
        r"(?:等级|客户等级|level)[:：\s]*([ABCD])", raw, re.IGNORECASE
    )
    name = extract_company_name(raw)

    def pick(options: list[str]) -> str:
        return next((item for item in options if item in raw), "")

    def pick_by_keywords(mapping: dict[str, tuple[str, ...]]) -> str:
        lower = raw.lower()
        for value, keywords in mapping.items():
            if any(k.lower() in lower for k in keywords):
                return value
        return ""

    industry = pick(
        ["汽车电子", "消费电子", "工业控制", "通信设备", "医疗器械", "安防监控"]
    )
    if not industry:
        industry = pick_by_keywords(
            {
                "汽车电子": ("车规", "车载", "automotive"),
                "消费电子": ("消费类", "家电", "consumer electronics"),
                "工业控制": ("工控", "plc", "industrial control"),
                "通信设备": ("通信", "5g", "networking"),
                "医疗器械": ("医疗", "医械", "medical"),
                "安防监控": ("安防", "监控", "security camera"),
                "其他": ("其他", "others"),
            }
        )

    region = pick(["华东", "华南", "华北", "华中", "西南", "西北", "东北", "海外"])
    if not region:
        region = pick_by_keywords(
            {
                "华南": ("广东", "深圳", "广州", "东莞", "佛山", "珠海"),
                "华东": ("上海", "江苏", "浙江", "杭州", "苏州", "宁波"),
                "华北": ("北京", "天津", "河北", "山东", "青岛", "济南"),
                "华中": ("湖北", "湖南", "河南", "武汉", "长沙", "郑州"),
                "西南": ("四川", "重庆", "云南", "贵州", "成都"),
                "西北": ("陕西", "甘肃", "宁夏", "新疆", "西安"),
                "东北": ("辽宁", "吉林", "黑龙江", "沈阳", "大连", "哈尔滨"),
                "海外": ("海外", "香港", "澳门", "台湾", "overseas"),
            }
        )

    source = pick(["展会", "转介绍", "线上推广", "电话开发", "公司资源"])
    if not source:
        source = pick_by_keywords(
            {
                "展会": ("展会", "博览会", "expo", "fair"),
                "转介绍": ("转介绍", "介绍", "referral"),
                "线上推广": (
                    "线上",
                    "官网",
                    "公众号",
                    "抖音",
                    "小红书",
                    "广告",
                    "线索平台",
                    "网站留资",
                    "website",
                    "留资",
                    "seo",
                    "sem",
                ),
                "电话开发": ("电话开发", "cold call", "陌拜电话", "telemarketing"),
                "公司资源": ("公司资源", "历史客户", "老客户"),
            }
        )

    customer_type = pick(["终端", "贸易商", "方案商", "OEM"])
    if not customer_type:
        customer_type = pick_by_keywords(
            {
                "终端": ("终端", "终端客户", "end customer"),
                "贸易商": ("贸易商", "分销", "distributor", "代理"),
                "方案商": ("方案商", "系统集成", "方案公司", "si"),
                "OEM": ("oem", "贴牌", "代工"),
            }
        )

    credit_limit = None
    credit_match = re.search(
        r"(?:授信|信用额度|额度)[:：\s]*([0-9]+(?:\.[0-9]+)?)\s*(万|w|W|千|k|K|元)?",
        raw,
    )
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
        short_name = re.sub(
            r"^(深圳市|上海市|北京市|广州市|杭州市|苏州市|东莞市|宁波市)",
            "",
            short_name,
        ).strip()
        if not short_name:
            short_name = name

    credit_level_match = re.search(
        r"(?:信用等级|授信等级|等级)[:：\s]*([ABCD])(?:级|类)?", raw, re.IGNORECASE
    )
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

    phone_value = extract_phone(raw)
    email_value = extract_email(raw)
    contact_person = extract_contact_person(raw)

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


def merge_customer_recognition(ai_result: dict, text: str) -> dict:
    merged = dict(ai_result or {})
    fallback = heuristic_customer_recognition(text)
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


def compose_customer_recognition_context(
    text: str, ocr_candidates: list[dict] | None = None
) -> str:
    parts = [(text or "").strip()]
    for candidate in (ocr_candidates or [])[:6]:
        candidate_text = str(candidate.get("text") or "").strip()
        if candidate_text and candidate_text not in parts:
            parts.append(candidate_text)
    return "\n".join(part for part in parts if part)
