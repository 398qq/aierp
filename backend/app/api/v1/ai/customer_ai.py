"""Customer AI endpoints."""
import io
import logging
import re
import unicodedata
from datetime import datetime, timedelta, timezone
from typing import Any

from fastapi import APIRouter, Depends, File, Query, UploadFile
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.database import get_db
from app.schemas.common import fail, ok
from app.services.ai import CustomerAgent, EmbeddingService
from app.services.customer_service import calc_health

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ai", tags=["ai"])

FOLLOWUP_METHODS = {"phone", "visit", "video", "email", "wechat", "other"}
FOLLOWUP_STATUSES = {"planned", "in_progress", "completed", "cancelled"}
FOLLOWUP_PRIORITIES = {"high", "medium", "low"}
CUSTOMER_TYPES = {"终端", "贸易商", "方案商", "OEM"}
CUSTOMER_INDUSTRIES = {"汽车电子", "消费电子", "工业控制", "通信设备", "医疗器械", "安防监控", "其他"}
CUSTOMER_LEVELS = {"A", "B", "C", "D"}
CUSTOMER_REGIONS = {"华东", "华南", "华北", "华中", "西南", "西北", "东北", "海外"}
CUSTOMER_SOURCES = {"展会", "转介绍", "线上推广", "电话开发", "公司资源"}
MAX_CARD_IMAGE_BYTES = 8 * 1024 * 1024
_rapidocr_engine: Any | None = None

CARD_OCR_FIELD_PATTERNS = (
    r"1[3-9]\d{9}",
    r"0\d{2,3}-?\d{7,8}",
    r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}",
    r"(?:有限公司|股份|集团|公司|Co\.?|Ltd\.?|Inc\.?)",
    r"(?:地址|电话|手机|邮箱|联系人|职务|销售|经理|工程师|官网|网址|Address|Tel|Mobile|Email|Web|Manager|Engineer)",
)


class FollowUpRecognitionRequest(BaseModel):
    text: str = Field(min_length=1, max_length=4000)


class CustomerRecognitionRequest(BaseModel):
    text: str = Field(min_length=1, max_length=4000)


def _clean_choice(value: Any, allowed: set[str]) -> str | None:
    if not value:
        return None
    normalized = str(value).strip()
    return normalized if normalized in allowed else None


def _clean_text(value: Any) -> str | None:
    if value is None:
        return None
    normalized = str(value).strip()
    return normalized or None


def _clean_datetime_text(value: Any) -> str | None:
    if not value:
        return None
    normalized = str(value).strip().replace("T", " ")
    if not normalized:
        return None
    try:
        return datetime.fromisoformat(normalized).strftime("%Y-%m-%d %H:%M:%S")
    except ValueError:
        return None


def _clean_confidence(value: Any) -> float:
    try:
        confidence = float(value)
    except (TypeError, ValueError):
        return 0.0
    return max(0.0, min(1.0, confidence))


def _normalize_ocr_text(text: str) -> str:
    normalized = unicodedata.normalize("NFKC", text or "")
    normalized = normalized.replace("\r\n", "\n").replace("\r", "\n")
    normalized = re.sub(r"[ \t]+", " ", normalized)
    normalized = re.sub(r"\n{3,}", "\n\n", normalized)
    normalized = re.sub(r"(?<=\d)\s+(?=\d)", "", normalized)
    normalized = re.sub(r"(?i)\bE[-\s]*mail\b", "Email", normalized)
    normalized = re.sub(r"(?i)\bM(?:ob(?:ile)?)?\s*[:：]", "Mobile:", normalized)
    normalized = re.sub(r"(?i)\bT(?:el)?\s*[:：]", "Tel:", normalized)
    return normalized.strip()


def _score_card_ocr_text(text: str, confidence: Any = 0) -> float:
    normalized = _normalize_ocr_text(text)
    if not normalized:
        return 0.0

    score = min(len(normalized), 500) / 500
    lines = [line.strip() for line in normalized.splitlines() if line.strip()]
    score += min(len(lines), 8) * 0.08

    for pattern in CARD_OCR_FIELD_PATTERNS:
        if re.search(pattern, normalized, re.IGNORECASE):
            score += 0.45

    chinese_chars = len(re.findall(r"[\u4e00-\u9fff]", normalized))
    latin_words = len(re.findall(r"[A-Za-z]{2,}", normalized))
    score += min(chinese_chars, 80) / 160
    score += min(latin_words, 30) / 120
    score += _clean_confidence(confidence) * 0.6

    replacement_noise = normalized.count("?") + normalized.count("�")
    if replacement_noise:
        score -= min(replacement_noise * 0.2, 1.0)
    return round(max(score, 0.0), 4)


def _merge_card_ocr_results(candidates: list[dict[str, Any]]) -> dict[str, Any]:
    usable = [item for item in candidates if _normalize_ocr_text(str(item.get("text") or ""))]
    if not usable:
        return {"text": "", "engine": "none", "confidence": 0.0, "score": 0.0, "candidates": []}

    normalized_candidates = []
    for item in usable:
        text = _normalize_ocr_text(str(item.get("text") or ""))
        confidence = _clean_confidence(item.get("confidence"))
        normalized_candidates.append({
            **item,
            "text": text,
            "confidence": confidence,
            "score": _score_card_ocr_text(text, confidence),
        })

    best = max(normalized_candidates, key=lambda item: item["score"])
    best["candidates"] = [
        {
            "engine": item.get("engine") or "unknown",
            "confidence": _clean_confidence(item.get("confidence")),
            "score": item.get("score") or 0,
            "text_length": len(str(item.get("text") or "")),
        }
        for item in sorted(normalized_candidates, key=lambda item: item["score"], reverse=True)
    ]
    return best


def _clean_float(value: Any) -> float | None:
    if value in (None, ""):
        return None
    try:
        amount = float(value)
    except (TypeError, ValueError):
        return None
    return amount if amount >= 0 else None


def _normalize_customer_recognition(recognized: dict[str, Any], fallback_text: str) -> dict[str, Any]:
    payload = {
        "name": _clean_text(recognized.get("name")),
        "short_name": _clean_text(recognized.get("short_name")),
        "customer_type": _clean_choice(recognized.get("customer_type"), CUSTOMER_TYPES),
        "industry": _clean_choice(recognized.get("industry"), CUSTOMER_INDUSTRIES),
        "level": _clean_choice(recognized.get("level"), CUSTOMER_LEVELS),
        "region": _clean_choice(recognized.get("region"), CUSTOMER_REGIONS),
        "source": _clean_choice(recognized.get("source"), CUSTOMER_SOURCES),
        "contact_person": _clean_text(recognized.get("contact_person")),
        "phone": _clean_text(recognized.get("phone")),
        "email": _clean_text(recognized.get("email")),
        "owner": _clean_text(recognized.get("owner")),
        "credit_limit": _clean_float(recognized.get("credit_limit")),
        "credit_level": _clean_choice(recognized.get("credit_level"), CUSTOMER_LEVELS),
        "address": _clean_text(recognized.get("address")),
        "notes": _clean_text(recognized.get("notes")),
        "confidence": _clean_confidence(recognized.get("confidence")),
        "summary": _clean_text(recognized.get("summary")) or "已识别客户资料",
    }
    if not payload["name"]:
        payload["notes"] = payload["notes"] or fallback_text
    return payload


def _customer_recognition_warnings(payload: dict[str, Any], *, is_card: bool = False) -> list[str]:
    warnings = []
    if not payload.get("name"):
        warnings.append("未识别到客户名称")
    if not payload.get("contact_person"):
        warnings.append("未识别到联系人")
    if not payload.get("phone"):
        warnings.append("未识别到电话")
    if is_card and not payload.get("email"):
        warnings.append("未识别到邮箱")
    if is_card and float(payload.get("ocr_score") or 0) < 1.2:
        warnings.append("OCR评分较低，建议上传更清晰、无遮挡的名片图片")
    return warnings


def _get_rapidocr_engine() -> Any:
    global _rapidocr_engine
    if _rapidocr_engine is None:
        from rapidocr import RapidOCR
        _rapidocr_engine = RapidOCR()
    return _rapidocr_engine


def _business_card_image_variants(image: Any) -> list[tuple[str, Any]]:
    from PIL import ImageEnhance, ImageFilter, ImageOps

    base = image.convert("RGB")
    variants: list[tuple[str, Any]] = [("original", base)]

    width, height = base.size
    longest = max(width, height)
    if longest and longest < 1600:
        scale = min(3, 1600 / longest)
        resized = base.resize((int(width * scale), int(height * scale)))
        variants.append(("resized", resized))
        base = resized

    gray = ImageOps.grayscale(base)
    variants.append(("gray_autocontrast", ImageOps.autocontrast(gray)))
    variants.append(("sharp_contrast", ImageEnhance.Contrast(gray.filter(ImageFilter.SHARPEN)).enhance(1.6)))
    variants.append(("threshold_160", gray.point(lambda p: 255 if p > 160 else 0)))
    variants.append(("threshold_190", gray.point(lambda p: 255 if p > 190 else 0)))
    return variants


def _ocr_with_rapidocr(image: Any) -> dict[str, Any]:
    try:
        import numpy as np
    except Exception as exc:
        raise RuntimeError("RapidOCR依赖不可用") from exc

    engine = _get_rapidocr_engine()
    np_image = np.array(image.convert("RGB"))
    result = engine(np_image)
    texts = [str(item).strip() for item in (getattr(result, "txts", None) or []) if str(item).strip()]
    scores = [float(item) for item in (getattr(result, "scores", None) or []) if item is not None]
    confidence = round(sum(scores) / len(scores), 4) if scores else 0.0
    return {
        "text": "\n".join(texts).strip(),
        "engine": "rapidocr",
        "confidence": confidence,
    }


def _ocr_with_tesseract(image: Any) -> dict[str, Any]:
    import pytesseract

    candidates: list[dict[str, Any]] = []
    configs = ("--oem 3 --psm 6", "--oem 3 --psm 11")
    for variant_name, variant in _business_card_image_variants(image):
        for config in configs:
            text = pytesseract.image_to_string(variant, lang="chi_sim+eng", config=config).strip()
            if not text:
                continue
            confidence = 0.0
            try:
                data = pytesseract.image_to_data(variant, lang="chi_sim+eng", config=config, output_type=pytesseract.Output.DICT)
                scores = []
                for score in data.get("conf", []):
                    try:
                        value = float(score)
                    except (TypeError, ValueError):
                        continue
                    if value >= 0:
                        scores.append(value / 100)
                confidence = round(sum(scores) / len(scores), 4) if scores else 0.0
            except Exception:
                confidence = 0.0
            candidates.append({
                "text": text,
                "engine": f"tesseract:{variant_name}:{config.split()[-1]}",
                "confidence": confidence,
            })

    best = _merge_card_ocr_results(candidates)

    return {
        "text": best.get("text") or "",
        "engine": best.get("engine") or "tesseract",
        "confidence": best.get("confidence") or 0.0,
    }


def _extract_business_card_ocr(content: bytes) -> dict[str, Any]:
    try:
        from PIL import Image, ImageOps
    except Exception as exc:
        raise RuntimeError("OCR依赖不可用，请安装 Pillow") from exc

    try:
        image = Image.open(io.BytesIO(content))
        image = ImageOps.exif_transpose(image)
        if image.mode not in ("RGB", "L"):
            image = image.convert("RGB")

        candidates: list[dict[str, Any]] = []
        for variant_name, variant in _business_card_image_variants(image):
            try:
                rapid = _ocr_with_rapidocr(variant)
                if rapid["text"]:
                    rapid["engine"] = f"rapidocr:{variant_name}"
                    candidates.append(rapid)
            except Exception as exc:
                logger.warning("RapidOCR failed on %s, fallback to tesseract: %s", variant_name, exc)
                break

        try:
            tesseract = _ocr_with_tesseract(image)
            if tesseract["text"]:
                candidates.append(tesseract)
        except Exception as exc:
            logger.warning("Tesseract OCR failed: %s", exc)

        if not candidates:
            return {"text": "", "engine": "none", "confidence": 0.0}

        return _merge_card_ocr_results(candidates)
    except Exception as exc:
        raise RuntimeError("图片文字提取失败，请确认图片清晰且OCR依赖已安装") from exc


def _extract_business_card_text(content: bytes) -> str:
    return str(_extract_business_card_ocr(content).get("text") or "")


@router.post("/customer/{customer_id}/rfm")
async def analyze_rfm(
    customer_id: int,
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(get_current_user),
):
    """RFM analysis for a customer (Recency, Frequency, Monetary)."""
    from app.models.customer import Customer, CustomerFollowUp
    from app.models.sales import SalesOrder

    result = await db.execute(
        select(Customer).where(Customer.id == customer_id, Customer.deleted_at.is_(None))
    )
    customer = result.scalar_one_or_none()
    if customer is None:
        return fail("Customer not found", 404)

    # Use cached result from batch job if available
    if customer.ai_insights and customer.ai_insights.get("rfm"):
        return ok(customer.ai_insights["rfm"])

    order_stats = (await db.execute(
        select(
            func.count(SalesOrder.id),
            func.coalesce(func.sum(SalesOrder.total_amount), 0),
            func.max(SalesOrder.created_at),
        ).where(SalesOrder.customer_id == customer_id, SalesOrder.deleted_at.is_(None))
    )).first()

    last_fu = (await db.execute(
        select(CustomerFollowUp).where(
            CustomerFollowUp.customer_id == customer_id,
            CustomerFollowUp.deleted_at.is_(None),
        ).order_by(CustomerFollowUp.created_at.desc()).limit(1)
    )).scalar_one_or_none()

    data = {
        "name": customer.name,
        "industry": customer.industry or "",
        "total_orders": order_stats[0] or 0,
        "total_revenue": float(order_stats[1]) if order_stats[1] else 0,
        "last_order_date": str(order_stats[2]) if order_stats[2] else None,
        "last_contacted_at": str(customer.last_contacted_at) if customer.last_contacted_at else None,
        "last_followup": str(last_fu.planned_at) if last_fu and last_fu.planned_at else None,
    }
    analysis = await CustomerAgent.rfm_analysis(data)
    return ok(analysis)


@router.post("/customer/{customer_id}/churn-risk")
async def analyze_churn(
    customer_id: int,
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(get_current_user),
):
    """Churn risk analysis for a customer."""
    from app.models.customer import Customer, CustomerFollowUp
    from app.models.finance import PaymentRecord
    from app.models.sales import Opportunity, Quotation, SalesOrder

    result = await db.execute(
        select(Customer).where(Customer.id == customer_id, Customer.deleted_at.is_(None))
    )
    customer = result.scalar_one_or_none()
    if customer is None:
        return fail("Customer not found", 404)

    # Use cached result from batch job if available
    if customer.ai_insights and customer.ai_insights.get("churn"):
        return ok(customer.ai_insights["churn"])

    now = datetime.now(timezone.utc)
    d90 = now - timedelta(days=90)
    d180 = now - timedelta(days=180)

    # Order stats
    order_stats = (await db.execute(
        select(
            func.count(SalesOrder.id),
            func.coalesce(func.sum(SalesOrder.total_amount), 0),
            func.max(SalesOrder.created_at),
            func.count(SalesOrder.id).filter(SalesOrder.created_at >= d90),
            func.count(SalesOrder.id).filter(SalesOrder.created_at >= d180),
        ).where(SalesOrder.customer_id == customer_id, SalesOrder.deleted_at.is_(None))
    )).first()

    # Opportunity & quotation counts
    active_opps = (await db.execute(
        select(func.count(Opportunity.id)).where(
            Opportunity.customer_id == customer_id,
            Opportunity.deleted_at.is_(None),
            Opportunity.stage.in_(["lead", "qualification", "proposal", "negotiation"]),
        )
    )).scalar() or 0

    active_quotations = (await db.execute(
        select(func.count(Quotation.id)).where(
            Quotation.customer_id == customer_id,
            Quotation.deleted_at.is_(None),
            Quotation.status.in_(["draft", "sent"]),
        )
    )).scalar() or 0

    # Credit & AR
    credit_util = "无数据"
    if customer.credit_limit and customer.credit_limit > 0:
        outstanding = (await db.execute(
            select(func.coalesce(func.sum(PaymentRecord.amount), 0)).where(
                PaymentRecord.customer_id == customer_id,
                PaymentRecord.deleted_at.is_(None),
                PaymentRecord.status != "paid",
            )
        )).scalar() or 0
        credit_util = f"{min(100, round(float(outstanding) / float(customer.credit_limit) * 100))}%"

    # AR overdue: unpaid payments older than 30 days
    ar_overdue_days = 0
    thirty_days_ago = now - timedelta(days=30)
    oldest_unpaid = (await db.execute(
        select(PaymentRecord).where(
            PaymentRecord.customer_id == customer_id,
            PaymentRecord.deleted_at.is_(None),
            PaymentRecord.status != "paid",
            PaymentRecord.created_at < thirty_days_ago,
        ).order_by(PaymentRecord.created_at.asc()).limit(1)
    )).scalar_one_or_none()
    if oldest_unpaid and oldest_unpaid.created_at:
        ar_overdue_days = (now - oldest_unpaid.created_at.replace(tzinfo=timezone.utc)).days

    # Health score
    payments_for_health = (await db.execute(
        select(PaymentRecord).where(
            PaymentRecord.customer_id == customer_id, PaymentRecord.deleted_at.is_(None)
        )
    )).scalars().all()
    orders_for_health = (await db.execute(
        select(SalesOrder).where(
            SalesOrder.customer_id == customer_id, SalesOrder.deleted_at.is_(None)
        )
    )).scalars().all()
    health_score, health_label = calc_health(customer, list(orders_for_health), list(payments_for_health), now)

    # Order trend
    orders_90d = order_stats[3] or 0
    orders_180d = order_stats[4] or 0
    orders_before = (orders_180d or 0) - (orders_90d or 0)
    order_trend = "稳定"
    if orders_90d > 0 and orders_before > 0:
        if orders_90d > orders_before * 1.3:
            order_trend = "增长"
        elif orders_90d < orders_before * 0.7:
            order_trend = "下降"

    last_fu = (await db.execute(
        select(CustomerFollowUp).where(
            CustomerFollowUp.customer_id == customer_id,
            CustomerFollowUp.deleted_at.is_(None),
        ).order_by(CustomerFollowUp.created_at.desc()).limit(1)
    )).scalar_one_or_none()

    data = {
        "name": customer.name,
        "industry": customer.industry or "",
        "level": customer.level or "",
        "lifecycle": customer.lifecycle or "未知",
        "total_orders": order_stats[0] or 0,
        "total_revenue": float(order_stats[1]) if order_stats[1] else 0,
        "last_order_date": str(order_stats[2]) if order_stats[2] else None,
        "orders_last_90d": orders_90d,
        "orders_last_180d": orders_180d,
        "order_trend": order_trend,
        "last_followup_date": str(last_fu.planned_at) if last_fu and last_fu.planned_at else None,
        "last_contacted_at": str(customer.last_contacted_at) if customer.last_contacted_at else None,
        "active_opportunities": active_opps,
        "active_quotations": active_quotations,
        "credit_utilization": credit_util,
        "ar_overdue_days": ar_overdue_days,
        "health_score": health_score,
        "health_label": health_label,
    }
    analysis = await CustomerAgent.churn_risk(data)
    return ok(analysis)


@router.post("/customer/{customer_id}/followup-suggestion")
async def suggest_followup(
    customer_id: int,
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(get_current_user),
):
    """AI-generated follow-up suggestion for a customer."""
    from app.models.customer import Customer, CustomerFollowUp

    result = await db.execute(
        select(Customer).where(Customer.id == customer_id, Customer.deleted_at.is_(None))
    )
    customer = result.scalar_one_or_none()
    if customer is None:
        return fail("Customer not found", 404)

    last_fu = (await db.execute(
        select(CustomerFollowUp).where(
            CustomerFollowUp.customer_id == customer_id,
            CustomerFollowUp.deleted_at.is_(None),
        ).order_by(CustomerFollowUp.created_at.desc()).limit(1)
    )).scalar_one_or_none()

    data = {
        "name": customer.name,
        "industry": customer.industry or "",
        "notes": customer.notes or "",
        "level": customer.level or "",
        "last_followup_content": last_fu.content if last_fu else None,
        "last_followup_date": str(last_fu.planned_at) if last_fu and last_fu.planned_at else None,
    }
    suggestion = await CustomerAgent.followup_suggestion(data)
    return ok(suggestion)


@router.post("/customer/recognition")
async def recognize_customer(
    body: CustomerRecognitionRequest,
    _user: dict = Depends(get_current_user),
):
    """AI-recognize natural-language customer profile text into create form fields."""
    raw_text = body.text.strip()
    recognized = await CustomerAgent.recognize_customer(raw_text)
    return ok(_normalize_customer_recognition(recognized, raw_text))


@router.post("/customer/card-recognition")
async def recognize_customer_card(
    file: UploadFile | None = File(default=None),
    body_file: UploadFile | None = File(default=None, alias="body.file"),
    _user: dict = Depends(get_current_user),
):
    """OCR a business-card image, then AI-recognize it into customer create fields."""
    upload = file or body_file
    if upload is None:
        return fail("缺少名片文件，请使用 file 字段上传")

    content_type = upload.content_type or ""
    if not content_type.startswith("image/"):
        return fail("请上传名片图片")

    content = await upload.read()
    if not content:
        return fail("名片图片不能为空")
    if len(content) > MAX_CARD_IMAGE_BYTES:
        return fail("名片图片不能超过 8MB")

    try:
        ocr_result = _extract_business_card_ocr(content)
    except RuntimeError as exc:
        logger.warning("Business card OCR failed: %s", exc)
        return fail(f"名片OCR失败: {exc}")

    raw_text = str(ocr_result.get("text") or "").strip()
    if not raw_text:
        return fail("未识别到名片文字，请换一张更清晰的图片或改用文本识别")

    recognized = await CustomerAgent.recognize_customer(raw_text)
    payload = _normalize_customer_recognition(recognized, raw_text)
    payload["raw_text"] = raw_text
    payload["ocr_engine"] = ocr_result.get("engine") or "unknown"
    payload["ocr_confidence"] = _clean_confidence(ocr_result.get("confidence"))
    payload["ocr_score"] = float(ocr_result.get("score") or 0)
    payload["ocr_candidates"] = ocr_result.get("candidates") or []
    payload["recognition_warnings"] = _customer_recognition_warnings(payload, is_card=True)
    return ok(payload)


@router.post("/customer/{customer_id}/followup-recognition")
async def recognize_followup(
    customer_id: int,
    body: FollowUpRecognitionRequest,
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(get_current_user),
):
    """AI-recognize natural-language follow-up text into form fields."""
    from app.models.customer import Customer, CustomerFollowUp

    result = await db.execute(
        select(Customer).where(Customer.id == customer_id, Customer.deleted_at.is_(None))
    )
    customer = result.scalar_one_or_none()
    if customer is None:
        return fail("Customer not found", 404)

    last_fu = (await db.execute(
        select(CustomerFollowUp).where(
            CustomerFollowUp.customer_id == customer_id,
            CustomerFollowUp.deleted_at.is_(None),
        ).order_by(CustomerFollowUp.created_at.desc()).limit(1)
    )).scalar_one_or_none()

    now = datetime.now(timezone.utc)
    customer_data = {
        "name": customer.name,
        "industry": customer.industry or "",
        "level": customer.level or "",
        "owner": customer.owner or "",
        "last_followup": last_fu.content if last_fu else "",
    }
    recognized = await CustomerAgent.recognize_followup(
        body.text.strip(),
        customer_data,
        now.strftime("%Y-%m-%d %H:%M:%S %Z"),
    )

    planned_at = _clean_datetime_text(recognized.get("planned_at"))
    completed_at = _clean_datetime_text(recognized.get("completed_at"))
    status = _clean_choice(recognized.get("status"), FOLLOWUP_STATUSES)
    if not status:
        if completed_at:
            status = "completed"
        elif planned_at:
            status = "planned"

    payload = {
        "method": _clean_choice(recognized.get("method"), FOLLOWUP_METHODS),
        "status": status,
        "priority": _clean_choice(recognized.get("priority"), FOLLOWUP_PRIORITIES),
        "content": _clean_text(recognized.get("content")) or body.text.strip(),
        "result": _clean_text(recognized.get("result")),
        "planned_at": planned_at,
        "completed_at": completed_at,
        "assigned_to": _clean_text(recognized.get("assigned_to")) or customer.owner,
        "confidence": _clean_confidence(recognized.get("confidence")),
        "summary": _clean_text(recognized.get("summary")) or "已识别跟进内容",
    }
    return ok(payload)


@router.post("/customer/{customer_id}/analyze-followups")
async def analyze_followups(
    customer_id: int,
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(get_current_user),
):
    """Semantic analysis of follow-up history: sentiment, topics, action items, risk signals."""
    from app.models.customer import Customer, CustomerFollowUp

    result = await db.execute(
        select(Customer).where(Customer.id == customer_id, Customer.deleted_at.is_(None))
    )
    customer = result.scalar_one_or_none()
    if customer is None:
        return fail("Customer not found", 404)

    followups = (await db.execute(
        select(CustomerFollowUp).where(
            CustomerFollowUp.customer_id == customer_id,
            CustomerFollowUp.deleted_at.is_(None),
        ).order_by(CustomerFollowUp.created_at.desc()).limit(20)
    )).scalars().all()

    analysis = await CustomerAgent.analyze_followups(
        [{"method": f.method, "content": f.content, "result": f.result} for f in followups],
        customer_name=customer.name,
    )
    return ok(analysis)


@router.post("/customer/{customer_id}/embed")
async def embed_customer(
    customer_id: int,
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(get_current_user),
):
    """Generate and store embedding vector for a single customer."""
    from app.models.customer import Customer

    result = await db.execute(
        select(Customer).where(Customer.id == customer_id, Customer.deleted_at.is_(None))
    )
    customer = result.scalar_one_or_none()
    if customer is None:
        return fail("Customer not found", 404)

    embedding = await EmbeddingService.embed_customer({
        "name": customer.name,
        "industry": customer.industry or "",
        "notes": customer.notes or "",
    })
    customer.embedding = embedding
    await db.commit()
    return ok({"customer_id": customer_id, "dimensions": len(embedding)})


@router.get("/customer/{customer_id}/similar")
async def similar_customers(
    customer_id: int,
    top_k: int = 10,
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(get_current_user),
):
    """Find similar customers based on embedding vector similarity."""
    from app.models.customer import Customer

    result = await db.execute(
        select(Customer).where(Customer.id == customer_id, Customer.deleted_at.is_(None))
    )
    customer = result.scalar_one_or_none()
    if customer is None:
        return fail("Customer not found", 404)
    if customer.embedding is None:
        return fail("Customer has no embedding, call POST embed first", 400)

    similar = await EmbeddingService.similar_customers(customer.embedding, db, top_k, exclude_id=customer_id)
    return ok(similar)


@router.get("/customer/similar/search")
async def search_similar_by_text(
    q: str = Query(...),
    top_k: int = 10,
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(get_current_user),
):
    """Natural-language semantic search for similar customers."""
    similar = await EmbeddingService.similar_by_text(q, db, top_k)
    return ok(similar)


@router.post("/customer/embed-all")
async def embed_all_customers(
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(get_current_user),
):
    """Batch generate embeddings for all customers that lack them."""
    stats = await EmbeddingService.index_all(db)
    await db.commit()
    return ok(stats)


@router.get("/customer/segments")
async def customer_segments(
    n_clusters: int = 5,
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(get_current_user),
):
    """AI-driven customer segmentation via K-means clustering on embeddings."""
    result = await EmbeddingService.segment_customers(db, n_clusters)
    return ok(result)


@router.post("/alert/{event_id}/enrich")
async def enrich_alert(
    event_id: int,
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(get_current_user),
):
    """Generate AI action suggestions for a specific alert event."""
    from app.models.customer import AlertEvent, Customer

    event_result = await db.execute(
        select(AlertEvent).where(AlertEvent.id == event_id)
    )
    event = event_result.scalar_one_or_none()
    if event is None:
        return fail("Alert event not found", 404)

    cust_result = await db.execute(
        select(Customer).where(Customer.id == event.customer_id, Customer.deleted_at.is_(None))
    )
    customer = cust_result.scalar_one_or_none()

    ctx = {
        "rule_type": event.rule_type,
        "rule_name": event.rule_name,
        "severity": event.severity,
        "message": event.message,
        "customer_name": customer.name if customer else "未知",
        "industry": customer.industry or "" if customer else "",
        "level": customer.level or "" if customer else "",
        "last_contact": str(customer.last_contacted_at) if customer and customer.last_contacted_at else "无",
    }
    enrichment = await CustomerAgent.enrich_alert(ctx)
    return ok(enrichment)


def _to_utc(dt_value: datetime | None) -> datetime | None:
    if dt_value is None:
        return None
    if dt_value.tzinfo is None:
        return dt_value.replace(tzinfo=timezone.utc)
    return dt_value.astimezone(timezone.utc)


def _days_since(dt_value: datetime | None, now: datetime) -> int:
    value = _to_utc(dt_value)
    if value is None:
        return 999
    return max(0, (now - value).days)


def _safe_float(value: Any) -> float:
    try:
        if value is None:
            return 0.0
        return float(value)
    except Exception:
        return 0.0


def _derive_value_score(level: str | None, monetary_180d: float, credit_level: str | None) -> float:
    level_map = {"A": 92.0, "B": 72.0, "C": 50.0, "D": 32.0}
    credit_map = {"AAA": 10.0, "AA": 8.0, "A": 6.0, "B": 3.0, "C": 0.0}
    base = level_map.get((level or "").upper(), 55.0)
    revenue_bonus = min(28.0, monetary_180d / 50000.0 * 8.0)
    credit_bonus = credit_map.get((credit_level or "").upper(), 2.0)
    return max(0.0, min(100.0, round(base * 0.72 + revenue_bonus + credit_bonus, 1)))


def _derive_risk_score(
    churn_risk_score: float,
    last_order_days: int,
    overdue_followups: int,
    outstanding_ratio: float,
) -> float:
    order_risk = min(100.0, last_order_days / 120.0 * 100.0)
    overdue_risk = min(100.0, overdue_followups * 25.0)
    credit_risk = min(100.0, outstanding_ratio * 120.0)
    score = churn_risk_score * 0.5 + order_risk * 0.2 + overdue_risk * 0.2 + credit_risk * 0.1
    return max(0.0, min(100.0, round(score, 1)))


def _derive_urgency_score(days_since_contact: int, overdue_followups: int, open_opportunities: int) -> float:
    contact_term = max(0.0, (days_since_contact - 30) * 0.9)
    overdue_term = overdue_followups * 20.0
    opportunity_term = 18.0 if open_opportunities > 0 else 0.0
    score = contact_term + overdue_term + opportunity_term
    return max(0.0, min(100.0, round(score, 1)))


def _next_action(
    *,
    customer_name: str,
    overdue_followups: int,
    days_since_contact: int,
    open_opportunities: int,
    outstanding_ratio: float,
    outstanding_amount: float,
    risk_score: float,
) -> dict:
    if outstanding_ratio >= 0.85:
        return {
            "action_type": "credit_review",
            "title": "信用额度复核与回款推进",
            "reason": f"{customer_name} 当前应收占授信比例较高（{outstanding_ratio * 100:.0f}%），建议优先推进回款并复核授信。",
            "confidence": 0.87,
            "due_days": 1,
            "expected_impact": round(outstanding_amount * 0.15, 2),
        }
    if overdue_followups > 0:
        return {
            "action_type": "follow_up_call",
            "title": "逾期跟进回访",
            "reason": f"{customer_name} 存在 {overdue_followups} 条逾期跟进，建议立即电话或拜访回访。",
            "confidence": 0.83,
            "due_days": 1,
            "expected_impact": None,
        }
    if days_since_contact >= 45:
        return {
            "action_type": "relationship_reactivate",
            "title": "关系激活跟进",
            "reason": f"{customer_name} 已 {days_since_contact} 天未联系，建议发起关系激活动作并安排下一次沟通。",
            "confidence": 0.8,
            "due_days": 2,
            "expected_impact": None,
        }
    if open_opportunities > 0:
        return {
            "action_type": "opportunity_push",
            "title": "推进在途商机",
            "reason": f"{customer_name} 当前有 {open_opportunities} 个活跃商机，建议推进样品/报价/商务确认。",
            "confidence": 0.78,
            "due_days": 2,
            "expected_impact": None,
        }
    if risk_score >= 70:
        return {
            "action_type": "retention_plan",
            "title": "流失挽回方案",
            "reason": f"{customer_name} 综合流失风险较高，建议启动客户挽回计划并指定责任人。",
            "confidence": 0.74,
            "due_days": 3,
            "expected_impact": None,
        }
    return {
        "action_type": "routine_touch",
        "title": "常规经营触达",
        "reason": f"{customer_name} 当前风险可控，建议保持周期性触达并更新客户需求。",
        "confidence": 0.68,
        "due_days": 5,
        "expected_impact": None,
    }


class WorkQueueGenerateRequest(BaseModel):
    customer_ids: list[int] | None = None
    replace_open: bool = True
    dry_run: bool = False


class WorkQueueStatusRequest(BaseModel):
    status: str = Field(pattern="^(open|in_progress|done|dismissed|superseded)$")
    owner: str | None = None


class WorkQueueFeedbackRequest(BaseModel):
    verdict: str = Field(pattern="^(adopted|rejected|partial)$")
    usefulness: int | None = Field(default=None, ge=1, le=5)
    outcome: str | None = Field(default=None, max_length=50)
    revenue_impact: float | None = None
    cost_impact: float | None = None
    comment: str | None = Field(default=None, max_length=2000)


@router.post("/customer/work-queue/generate")
async def generate_work_queue(
    body: WorkQueueGenerateRequest,
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(get_current_user),
):
    """Generate next-best-action queue for customers."""
    from app.models.customer import Customer, CustomerAIRecommendation, CustomerAISnapshotDaily, CustomerFollowUp
    from app.models.finance import PaymentRecord
    from app.models.sales import Opportunity, SalesOrder

    now = datetime.now(timezone.utc)
    customer_stmt = select(Customer).where(Customer.deleted_at.is_(None))
    if body.customer_ids:
        customer_stmt = customer_stmt.where(Customer.id.in_(body.customer_ids))
    customers = (await db.execute(customer_stmt)).scalars().all()
    if not customers:
        return ok({"generated": 0, "replaced": 0, "items": []})

    customer_ids = [c.id for c in customers]

    replaced = 0
    if body.replace_open and not body.dry_run:
        open_recs = (await db.execute(
            select(CustomerAIRecommendation).where(
                CustomerAIRecommendation.customer_id.in_(customer_ids),
                CustomerAIRecommendation.deleted_at.is_(None),
                CustomerAIRecommendation.status.in_(["open", "in_progress"]),
            )
        )).scalars().all()
        for rec in open_recs:
            rec.status = "superseded"
            replaced += 1

    orders = (await db.execute(
        select(SalesOrder).where(
            SalesOrder.deleted_at.is_(None),
            SalesOrder.customer_id.in_(customer_ids),
        )
    )).scalars().all()
    opportunities = (await db.execute(
        select(Opportunity).where(
            Opportunity.deleted_at.is_(None),
            Opportunity.customer_id.in_(customer_ids),
            Opportunity.stage.in_(["lead", "qualification", "proposal", "negotiation"]),
        )
    )).scalars().all()
    followups = (await db.execute(
        select(CustomerFollowUp).where(
            CustomerFollowUp.deleted_at.is_(None),
            CustomerFollowUp.customer_id.in_(customer_ids),
        )
    )).scalars().all()
    payments = (await db.execute(
        select(PaymentRecord).where(
            PaymentRecord.deleted_at.is_(None),
            PaymentRecord.customer_id.in_(customer_ids),
            PaymentRecord.status != "paid",
        )
    )).scalars().all()

    order_map: dict[int, list[Any]] = {}
    for order in orders:
        order_map.setdefault(order.customer_id, []).append(order)

    opp_map: dict[int, int] = {}
    for opp in opportunities:
        opp_map[opp.customer_id] = opp_map.get(opp.customer_id, 0) + 1

    overdue_map: dict[int, int] = {}
    followup_last_map: dict[int, datetime] = {}
    for fu in followups:
        if fu.planned_at and fu.planned_at < now and fu.status != "completed":
            overdue_map[fu.customer_id] = overdue_map.get(fu.customer_id, 0) + 1
        created = _to_utc(fu.created_at)
        if created and (fu.customer_id not in followup_last_map or created > followup_last_map[fu.customer_id]):
            followup_last_map[fu.customer_id] = created

    outstanding_map: dict[int, float] = {}
    for pay in payments:
        outstanding_map[pay.customer_id] = outstanding_map.get(pay.customer_id, 0.0) + _safe_float(pay.amount)

    created_items: list[dict[str, Any]] = []
    username = _user.get("username")

    for customer in customers:
        cust_orders = order_map.get(customer.id, [])
        latest_order_at = None
        order_count_90d = 0
        order_amount_180d = 0.0

        for order in cust_orders:
            created_at = _to_utc(order.created_at)
            if created_at and (latest_order_at is None or created_at > latest_order_at):
                latest_order_at = created_at
            if created_at and created_at >= now - timedelta(days=90):
                order_count_90d += 1
            if created_at and created_at >= now - timedelta(days=180):
                order_amount_180d += _safe_float(order.total_amount)

        last_contact_at = _to_utc(customer.last_contacted_at) or followup_last_map.get(customer.id)
        days_since_contact = _days_since(last_contact_at, now)
        last_order_days = _days_since(latest_order_at, now)

        open_opportunities = opp_map.get(customer.id, 0)
        overdue_followups = overdue_map.get(customer.id, 0)
        outstanding_amount = outstanding_map.get(customer.id, 0.0)
        credit_limit = _safe_float(customer.credit_limit)
        outstanding_ratio = 0.0 if credit_limit <= 0 else min(2.0, outstanding_amount / credit_limit)

        churn_risk_score = _safe_float((customer.ai_insights or {}).get("churn", {}).get("risk_score"))
        if churn_risk_score <= 0:
            churn_risk_score = 45.0

        health_score = _safe_float((customer.ai_insights or {}).get("health_score"))
        if health_score <= 0:
            health_score = 55.0

        value_score = _derive_value_score(customer.level, order_amount_180d, customer.credit_level)
        risk_score = _derive_risk_score(churn_risk_score, last_order_days, overdue_followups, outstanding_ratio)
        urgency_score = _derive_urgency_score(days_since_contact, overdue_followups, open_opportunities)
        priority_score = round(risk_score * 0.45 + value_score * 0.35 + urgency_score * 0.2, 1)

        next_action = _next_action(
            customer_name=customer.name,
            overdue_followups=overdue_followups,
            days_since_contact=days_since_contact,
            open_opportunities=open_opportunities,
            outstanding_ratio=outstanding_ratio,
            outstanding_amount=outstanding_amount,
            risk_score=risk_score,
        )
        due_at = now + timedelta(days=int(next_action["due_days"]))

        snapshot_payload = {
            "customer_id": customer.id,
            "snapshot_date": now,
            "health_score": health_score,
            "churn_risk_score": churn_risk_score,
            "value_score": value_score,
            "urgency_score": urgency_score,
            "recency_days": days_since_contact,
            "frequency_90d": order_count_90d,
            "monetary_180d": round(order_amount_180d, 2),
            "overdue_followups": overdue_followups,
            "open_opportunities": open_opportunities,
            "outstanding_amount": round(outstanding_amount, 2),
            "feature_payload": {
                "last_order_days": last_order_days,
                "outstanding_ratio": round(outstanding_ratio, 3),
                "credit_limit": credit_limit,
            },
        }

        rec_payload = {
            "customer_id": customer.id,
            "model_version": "rule-v1",
            "action_type": next_action["action_type"],
            "title": next_action["title"],
            "reason": next_action["reason"],
            "confidence": float(next_action["confidence"]),
            "priority_score": priority_score,
            "expected_impact": next_action["expected_impact"],
            "due_at": due_at,
            "status": "open",
            "owner": username,
            "context_payload": {
                "risk_score": risk_score,
                "value_score": value_score,
                "urgency_score": urgency_score,
                "days_since_contact": days_since_contact,
                "overdue_followups": overdue_followups,
                "open_opportunities": open_opportunities,
                "outstanding_amount": round(outstanding_amount, 2),
                "order_amount_180d": round(order_amount_180d, 2),
            },
        }

        if body.dry_run:
            created_items.append({
                "customer_id": customer.id,
                "customer_name": customer.name,
                **rec_payload,
                "snapshot": snapshot_payload,
            })
            continue

        snapshot = CustomerAISnapshotDaily(**snapshot_payload)
        db.add(snapshot)
        await db.flush()

        recommendation = CustomerAIRecommendation(snapshot_id=snapshot.id, **rec_payload)
        db.add(recommendation)
        await db.flush()

        created_items.append({
            "id": recommendation.id,
            "customer_id": customer.id,
            "customer_name": customer.name,
            **rec_payload,
            "snapshot": snapshot_payload,
        })

    created_items.sort(key=lambda item: float(item.get("priority_score", 0)), reverse=True)
    preview_items = [{
        "id": item.get("id"),
        "customer_id": item["customer_id"],
        "customer_name": item["customer_name"],
        "action_type": item["action_type"],
        "title": item["title"],
        "priority_score": item["priority_score"],
        "due_at": str(item["due_at"]) if item.get("due_at") else None,
        "status": item["status"],
    } for item in created_items[:20]]
    return ok({
        "generated": len(created_items),
        "replaced": replaced,
        "items": preview_items,
    })


@router.get("/customer/work-queue")
async def get_work_queue(
    status: str = Query("open"),
    owner: str | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(get_current_user),
):
    from app.models.customer import Customer, CustomerAIFeedback, CustomerAIRecommendation, CustomerAISnapshotDaily

    base = (
        select(CustomerAIRecommendation, Customer.name, Customer.level, Customer.industry, Customer.owner, CustomerAISnapshotDaily)
        .join(Customer, Customer.id == CustomerAIRecommendation.customer_id)
        .outerjoin(CustomerAISnapshotDaily, CustomerAISnapshotDaily.id == CustomerAIRecommendation.snapshot_id)
        .where(
            CustomerAIRecommendation.deleted_at.is_(None),
            Customer.deleted_at.is_(None),
        )
    )
    count_base = select(func.count(CustomerAIRecommendation.id)).where(CustomerAIRecommendation.deleted_at.is_(None))
    if status != "all":
        base = base.where(CustomerAIRecommendation.status == status)
        count_base = count_base.where(CustomerAIRecommendation.status == status)
    if owner:
        base = base.where(CustomerAIRecommendation.owner == owner)
        count_base = count_base.where(CustomerAIRecommendation.owner == owner)

    total = (await db.execute(count_base)).scalar() or 0
    rows = (await db.execute(
        base.order_by(CustomerAIRecommendation.priority_score.desc(), CustomerAIRecommendation.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )).all()

    rec_ids = [row[0].id for row in rows]
    feedback_map: dict[int, int] = {}
    if rec_ids:
        fb_rows = (await db.execute(
            select(CustomerAIFeedback.recommendation_id, func.count(CustomerAIFeedback.id))
            .where(
                CustomerAIFeedback.deleted_at.is_(None),
                CustomerAIFeedback.recommendation_id.in_(rec_ids),
            )
            .group_by(CustomerAIFeedback.recommendation_id)
        )).all()
        feedback_map = {int(r[0]): int(r[1]) for r in fb_rows}

    items = []
    for rec, customer_name, customer_level, customer_industry, customer_owner, snapshot in rows:
        snapshot_payload = {
            "health_score": snapshot.health_score if snapshot else None,
            "churn_risk_score": snapshot.churn_risk_score if snapshot else None,
            "value_score": snapshot.value_score if snapshot else None,
            "urgency_score": snapshot.urgency_score if snapshot else None,
            "recency_days": snapshot.recency_days if snapshot else None,
            "frequency_90d": snapshot.frequency_90d if snapshot else None,
            "monetary_180d": snapshot.monetary_180d if snapshot else None,
            "overdue_followups": snapshot.overdue_followups if snapshot else None,
            "open_opportunities": snapshot.open_opportunities if snapshot else None,
            "outstanding_amount": snapshot.outstanding_amount if snapshot else None,
        }
        items.append({
            "id": rec.id,
            "customer_id": rec.customer_id,
            "customer_name": customer_name,
            "customer_level": customer_level,
            "customer_industry": customer_industry,
            "customer_owner": customer_owner,
            "action_type": rec.action_type,
            "title": rec.title,
            "reason": rec.reason,
            "confidence": rec.confidence,
            "priority_score": rec.priority_score,
            "expected_impact": rec.expected_impact,
            "due_at": str(rec.due_at) if rec.due_at else None,
            "status": rec.status,
            "owner": rec.owner,
            "model_version": rec.model_version,
            "snapshot": snapshot_payload,
            "feedback_count": feedback_map.get(rec.id, 0),
            "created_at": str(rec.created_at) if rec.created_at else None,
        })

    status_rows = (await db.execute(
        select(CustomerAIRecommendation.status, func.count(CustomerAIRecommendation.id))
        .where(CustomerAIRecommendation.deleted_at.is_(None))
        .group_by(CustomerAIRecommendation.status)
    )).all()
    status_stats = {str(row[0]): int(row[1]) for row in status_rows}

    return ok({
        "list": items,
        "total": total,
        "page": page,
        "page_size": page_size,
        "status_stats": status_stats,
    })


@router.get("/customer/{customer_id}/summary")
async def customer_ai_summary(
    customer_id: int,
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(get_current_user),
):
    from app.models.customer import Customer, CustomerAIRecommendation, CustomerAISnapshotDaily

    customer = (await db.execute(
        select(Customer).where(Customer.id == customer_id, Customer.deleted_at.is_(None))
    )).scalar_one_or_none()
    if customer is None:
        return fail("Customer not found", 404)

    latest_snapshot = (await db.execute(
        select(CustomerAISnapshotDaily)
        .where(CustomerAISnapshotDaily.customer_id == customer_id, CustomerAISnapshotDaily.deleted_at.is_(None))
        .order_by(CustomerAISnapshotDaily.snapshot_date.desc())
        .limit(1)
    )).scalar_one_or_none()

    next_actions = (await db.execute(
        select(CustomerAIRecommendation)
        .where(
            CustomerAIRecommendation.customer_id == customer_id,
            CustomerAIRecommendation.deleted_at.is_(None),
            CustomerAIRecommendation.status.in_(["open", "in_progress"]),
        )
        .order_by(CustomerAIRecommendation.priority_score.desc())
        .limit(5)
    )).scalars().all()

    return ok({
        "customer": {
            "id": customer.id,
            "name": customer.name,
            "level": customer.level,
            "industry": customer.industry,
            "owner": customer.owner,
            "health_score": _safe_float((customer.ai_insights or {}).get("health_score")) or None,
            "health_label": (customer.ai_insights or {}).get("health_label"),
            "last_contacted_at": str(customer.last_contacted_at) if customer.last_contacted_at else None,
        },
        "snapshot": {
            "snapshot_date": str(latest_snapshot.snapshot_date) if latest_snapshot else None,
            "health_score": latest_snapshot.health_score if latest_snapshot else None,
            "churn_risk_score": latest_snapshot.churn_risk_score if latest_snapshot else None,
            "value_score": latest_snapshot.value_score if latest_snapshot else None,
            "urgency_score": latest_snapshot.urgency_score if latest_snapshot else None,
            "overdue_followups": latest_snapshot.overdue_followups if latest_snapshot else None,
            "open_opportunities": latest_snapshot.open_opportunities if latest_snapshot else None,
            "outstanding_amount": latest_snapshot.outstanding_amount if latest_snapshot else None,
        },
        "next_actions": [{
            "id": rec.id,
            "action_type": rec.action_type,
            "title": rec.title,
            "reason": rec.reason,
            "priority_score": rec.priority_score,
            "status": rec.status,
            "due_at": str(rec.due_at) if rec.due_at else None,
        } for rec in next_actions],
    })


@router.post("/customer/recommendation/{recommendation_id}/status")
async def update_recommendation_status(
    recommendation_id: int,
    body: WorkQueueStatusRequest,
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(get_current_user),
):
    from app.models.customer import CustomerAIAction, CustomerAIRecommendation

    rec = (await db.execute(
        select(CustomerAIRecommendation).where(
            CustomerAIRecommendation.id == recommendation_id,
            CustomerAIRecommendation.deleted_at.is_(None),
        )
    )).scalar_one_or_none()
    if rec is None:
        return fail("Recommendation not found", 404)

    rec.status = body.status
    if body.owner:
        rec.owner = body.owner
    elif not rec.owner:
        rec.owner = _user.get("username")

    if body.status == "done":
        action = CustomerAIAction(
            recommendation_id=rec.id,
            customer_id=rec.customer_id,
            action_type=rec.action_type,
            payload=rec.context_payload,
            status="done",
            assignee=rec.owner,
            executed_at=datetime.now(timezone.utc),
            result_summary="Marked done from work queue",
        )
        db.add(action)
    await db.flush()
    return ok({"id": rec.id, "status": rec.status, "owner": rec.owner})


@router.post("/customer/recommendation/{recommendation_id}/feedback")
async def submit_recommendation_feedback(
    recommendation_id: int,
    body: WorkQueueFeedbackRequest,
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(get_current_user),
):
    from app.models.customer import CustomerAIFeedback, CustomerAIRecommendation

    rec = (await db.execute(
        select(CustomerAIRecommendation).where(
            CustomerAIRecommendation.id == recommendation_id,
            CustomerAIRecommendation.deleted_at.is_(None),
        )
    )).scalar_one_or_none()
    if rec is None:
        return fail("Recommendation not found", 404)

    feedback = CustomerAIFeedback(
        recommendation_id=rec.id,
        customer_id=rec.customer_id,
        verdict=body.verdict,
        usefulness=body.usefulness,
        outcome=body.outcome,
        revenue_impact=body.revenue_impact,
        cost_impact=body.cost_impact,
        comment=body.comment,
        operator=_user.get("username"),
    )
    db.add(feedback)

    if body.verdict == "adopted":
        rec.status = "done"
    elif body.verdict == "rejected":
        rec.status = "dismissed"
    else:
        rec.status = "in_progress"

    await db.flush()
    return ok({"recommendation_id": rec.id, "status": rec.status})
