"""Customer AI — OCR public entry points.

Thin facade that:
  1. Inspects a business-card image for quality issues.
  2. Runs all OCR engines against image variants.
  3. Merges and scores results.
  4. Returns the consolidated text + scoring payload.

The heavy lifting lives in ``_ocr_engines``, ``_ocr_merging``,
``_ocr_regions``. Public functions drop the leading underscore so
callers (and the test suite) get a stable name to monkeypatch.
"""

from __future__ import annotations

import io
import logging
from typing import Any

from app.api.v1.ai.customer import _ocr_engines
from app.api.v1.ai.customer._cleaners import round_metric
from app.api.v1.ai.customer._ocr_merging import merge_card_ocr_results

logger = logging.getLogger(__name__)


MAX_CARD_IMAGE_BYTES: int = 8 * 1024 * 1024


def analyze_business_card_image_quality(image: Any) -> dict[str, Any]:
    from PIL import ImageFilter, ImageStat

    width, height = image.size
    gray = image.convert("L")
    stat = ImageStat.Stat(gray)
    brightness = float(stat.mean[0])
    contrast = float(stat.stddev[0])
    edge_stat = ImageStat.Stat(gray.filter(ImageFilter.FIND_EDGES))
    sharpness = float(edge_stat.stddev[0])
    megapixels = (width * height) / 1_000_000

    warnings: list[str] = []
    if min(width, height) < 600 or megapixels < 0.5:
        warnings.append("名片图片分辨率偏低，建议使用更清晰的原图")
    if brightness < 45:
        warnings.append("图片偏暗，建议补光或提高曝光后重拍")
    elif brightness > 220:
        warnings.append("图片过亮，文字可能被过曝影响")
    if contrast < 25:
        warnings.append("图片对比度偏低，建议使用背景更干净的照片")
    if sharpness < 12:
        warnings.append("文字边缘偏弱，可能存在虚焦、抖动或压缩过度")

    return {
        "width": width,
        "height": height,
        "megapixels": round_metric(megapixels),
        "brightness": round_metric(brightness),
        "contrast": round_metric(contrast),
        "sharpness": round_metric(sharpness),
        "warnings": warnings,
    }


def extract_business_card_ocr(content: bytes) -> dict[str, Any]:
    """Multi-engine OCR of a business-card image, returning merged result.

    Public entry point used by the recognition endpoint. Exposed as a stable
    symbol so the test suite can monkeypatch it.
    """
    try:
        from PIL import Image, ImageOps
    except Exception as exc:
        raise RuntimeError("OCR依赖不可用，请安装 Pillow") from exc

    try:
        image = Image.open(io.BytesIO(content))
        image = ImageOps.exif_transpose(image)
        if image.mode not in ("RGB", "L"):
            image = image.convert("RGB")
        image_quality = analyze_business_card_image_quality(image)

        variants = _ocr_engines.business_card_image_variants(image)
        candidates: list[dict[str, Any]] = []
        easyocr_variants = [
            (name, variant)
            for name, variant in variants
            if name == "original"
            or name == "resized"
            or name.startswith("opencv_card_")
        ][:4]
        for variant_name, variant in easyocr_variants:
            try:
                easyocr_result = _ocr_engines.ocr_with_easyocr(variant)
                if easyocr_result["text"]:
                    easyocr_result["engine"] = f"easyocr:{variant_name}"
                    candidates.append(easyocr_result)
            except Exception as exc:
                logger.info("EasyOCR skipped on %s: %s", variant_name, exc)
                break

        for variant_name, variant in variants:
            try:
                rapid = _ocr_engines.ocr_with_rapidocr(variant)
                if rapid["text"]:
                    rapid["engine"] = f"rapidocr:{variant_name}"
                    candidates.append(rapid)
            except Exception as exc:
                logger.warning(
                    "RapidOCR failed on %s, fallback to tesseract: %s",
                    variant_name,
                    exc,
                )
                break

        try:
            tesseract = _ocr_engines.ocr_with_tesseract(image)
            if tesseract["text"]:
                candidates.append(tesseract)
        except Exception as exc:
            logger.warning("Tesseract OCR failed: %s", exc)

        if not candidates:
            return {
                "text": "",
                "engine": "none",
                "confidence": 0.0,
                "image_quality": image_quality,
            }

        result = merge_card_ocr_results(candidates)
        result["image_quality"] = image_quality
        return result
    except Exception as exc:
        raise RuntimeError("图片文字提取失败，请确认图片清晰且OCR依赖已安装") from exc


def extract_business_card_text(content: bytes) -> str:
    return str(extract_business_card_ocr(content).get("text") or "")


# Back-compat aliases — tests reference the original underscored names.
_analyze_business_card_image_quality = analyze_business_card_image_quality
_extract_business_card_ocr = extract_business_card_ocr
_extract_business_card_text = extract_business_card_text


__all__ = [
    "MAX_CARD_IMAGE_BYTES",
    "analyze_business_card_image_quality",
    "extract_business_card_ocr",
    "extract_business_card_text",
    "_analyze_business_card_image_quality",
    "_extract_business_card_ocr",
    "_extract_business_card_text",
]
