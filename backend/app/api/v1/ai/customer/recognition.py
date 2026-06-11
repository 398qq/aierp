"""Customer AI — recognition endpoints.

Handles three operations that turn raw text or images into structured
customer / follow-up form fields:

* ``POST /customer/recognition``            — text → customer fields
* ``POST /customer/card-recognition``       — image → OCR → customer fields
* ``POST /customer/{id}/followup-recognition`` — text → follow-up fields

All three share the bounded vocabularies in ``_vocab`` and the cleaners
in ``_cleaners``. They talk to ``CustomerAgent`` (an AI agent from
``app.services.ai``) for the actual natural-language understanding.
"""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Depends, File, UploadFile
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.api.v1.ai.customer import _ocr
from app.api.v1.ai.customer._cleaners import (
    clean_choice,
    clean_confidence,
    clean_datetime_text,
    clean_float,
    clean_text,
)
from app.api.v1.ai.customer._vocab import (
    CUSTOMER_INDUSTRY_VALUES,
    CUSTOMER_LEVEL_VALUES,
    CUSTOMER_REGION_VALUES,
    CUSTOMER_SOURCE_VALUES,
    CUSTOMER_TYPE_VALUES,
    FOLLOWUP_METHOD_VALUES,
    FOLLOWUP_PRIORITY_VALUES,
    FOLLOWUP_STATUS_VALUES,
)
from app.database import get_db
from app.schemas.common import fail, ok
from app.services.ai import CustomerAgent

logger = logging.getLogger(__name__)


router = APIRouter(tags=["ai"])


class FollowUpRecognitionRequest(BaseModel):
    text: str = Field(min_length=1, max_length=4000)


class CustomerRecognitionRequest(BaseModel):
    text: str = Field(min_length=1, max_length=4000)


def _normalize_customer_recognition(
    recognized: dict[str, Any], fallback_text: str
) -> dict[str, Any]:
    payload = {
        "name": clean_text(recognized.get("name")),
        "short_name": clean_text(recognized.get("short_name")),
        "customer_type": clean_choice(
            recognized.get("customer_type"), CUSTOMER_TYPE_VALUES
        ),
        "industry": clean_choice(recognized.get("industry"), CUSTOMER_INDUSTRY_VALUES),
        "level": clean_choice(recognized.get("level"), CUSTOMER_LEVEL_VALUES),
        "region": clean_choice(recognized.get("region"), CUSTOMER_REGION_VALUES),
        "source": clean_choice(recognized.get("source"), CUSTOMER_SOURCE_VALUES),
        "contact_person": clean_text(recognized.get("contact_person")),
        "phone": clean_text(recognized.get("phone")),
        "email": clean_text(recognized.get("email")),
        "owner": clean_text(recognized.get("owner")),
        "credit_limit": clean_float(recognized.get("credit_limit")),
        "credit_level": clean_choice(
            recognized.get("credit_level"), CUSTOMER_LEVEL_VALUES
        ),
        "address": clean_text(recognized.get("address")),
        "notes": clean_text(recognized.get("notes")),
        "confidence": clean_confidence(recognized.get("confidence")),
        "summary": clean_text(recognized.get("summary")) or "已识别客户资料",
    }
    if not payload["name"]:
        payload["notes"] = payload["notes"] or fallback_text
    return payload


def _customer_recognition_warnings(
    payload: dict[str, Any], *, is_card: bool = False
) -> list[str]:
    warnings: list[str] = []
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
    if is_card:
        image_quality = payload.get("image_quality") or {}
        for warning in image_quality.get("warnings") or []:
            if warning not in warnings:
                warnings.append(warning)
    return warnings


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
    if len(content) > _ocr.MAX_CARD_IMAGE_BYTES:
        return fail("名片图片不能超过 8MB")

    try:
        ocr_result = _ocr.extract_business_card_ocr(content)
    except RuntimeError as exc:
        logger.warning("Business card OCR failed: %s", exc)
        return fail(f"名片OCR失败: {exc}")

    raw_text = str(ocr_result.get("text") or "").strip()
    if not raw_text:
        return fail("未识别到名片文字，请换一张更清晰的图片或改用文本识别")

    recognized = await CustomerAgent.recognize_customer(
        raw_text, ocr_candidates=ocr_result.get("candidate_texts") or []
    )
    payload = _normalize_customer_recognition(recognized, raw_text)
    payload["raw_text"] = raw_text
    payload["ocr_engine"] = ocr_result.get("engine") or "unknown"
    payload["ocr_confidence"] = clean_confidence(ocr_result.get("confidence"))
    payload["ocr_score"] = float(ocr_result.get("score") or 0)
    payload["ocr_candidates"] = ocr_result.get("candidates") or []
    payload["image_quality"] = ocr_result.get("image_quality") or {}
    payload["recognition_warnings"] = _customer_recognition_warnings(
        payload, is_card=True
    )
    return ok(payload)


@router.post("/customer/{customer_id}/followup-recognition")
async def recognize_followup(
    customer_id: int,
    body: FollowUpRecognitionRequest,
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(get_current_user),
):
    """AI-recognize natural-language follow-up text into form fields."""
    from datetime import datetime, timezone

    from app.models.customer import Customer, CustomerFollowUp

    result = await db.execute(
        select(Customer).where(
            Customer.id == customer_id, Customer.deleted_at.is_(None)
        )
    )
    customer = result.scalar_one_or_none()
    if customer is None:
        return fail("Customer not found", 404)

    last_fu = (
        await db.execute(
            select(CustomerFollowUp)
            .where(
                CustomerFollowUp.customer_id == customer_id,
                CustomerFollowUp.deleted_at.is_(None),
            )
            .order_by(CustomerFollowUp.created_at.desc())
            .limit(1)
        )
    ).scalar_one_or_none()

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

    planned_at = clean_datetime_text(recognized.get("planned_at"))
    completed_at = clean_datetime_text(recognized.get("completed_at"))
    status = clean_choice(recognized.get("status"), FOLLOWUP_STATUS_VALUES)
    if not status:
        if completed_at:
            status = "completed"
        elif planned_at:
            status = "planned"

    payload = {
        "method": clean_choice(recognized.get("method"), FOLLOWUP_METHOD_VALUES),
        "status": status,
        "priority": clean_choice(recognized.get("priority"), FOLLOWUP_PRIORITY_VALUES),
        "content": clean_text(recognized.get("content")) or body.text.strip(),
        "result": clean_text(recognized.get("result")),
        "planned_at": planned_at,
        "completed_at": completed_at,
        "assigned_to": clean_text(recognized.get("assigned_to")) or customer.owner,
        "confidence": clean_confidence(recognized.get("confidence")),
        "summary": clean_text(recognized.get("summary")) or "已识别跟进内容",
    }
    return ok(payload)


# Back-compat: the original module exported underscored helpers that tests
# monkeypatch through the ``app.api.v1.ai.customer_ai`` module path.
_normalize_customer_recognition = _normalize_customer_recognition
_customer_recognition_warnings = _customer_recognition_warnings
