"""Customer AI — OCR engine wrappers (rapidocr, easyocr, tesseract) and
image-variant generation.

Each ``_ocr_with_*`` function returns ``{"text", "engine", "confidence"}``
for a single image variant. The engines themselves are cached at module
scope so we don't re-load the model on every request.

Public surface:
    - ``business_card_image_variants``  — produce grayscale / thresholded
      / sharpened variants from a PIL image
    - ``ocr_with_rapidocr`` / ``ocr_with_easyocr`` / ``ocr_with_tesseract``
      — run a single engine on a single image
    - ``_merge_card_ocr_results``        — pick the best candidate (re-exported
      for compatibility with the existing test suite)
"""
from __future__ import annotations

import logging
from typing import Any

from app.api.v1.ai.customer._ocr_merging import (
    _merge_card_ocr_results,
)
from app.api.v1.ai.customer._ocr_regions import opencv_business_card_region_variants

logger = logging.getLogger(__name__)


_rapidocr_engine: Any | None = None
_easyocr_reader: Any | None = None


def _get_rapidocr_engine() -> Any:
    global _rapidocr_engine
    if _rapidocr_engine is None:
        from rapidocr import RapidOCR

        _rapidocr_engine = RapidOCR()
    return _rapidocr_engine


def _get_easyocr_reader() -> Any:
    global _easyocr_reader
    if _easyocr_reader is None:
        import easyocr

        _easyocr_reader = easyocr.Reader(["ch_sim", "en"], gpu=False, verbose=False)
    return _easyocr_reader


def business_card_image_variants(image: Any) -> list[tuple[str, Any]]:
    from PIL import ImageEnhance, ImageFilter, ImageOps

    base = image.convert("RGB")
    variants: list[tuple[str, Any]] = [("original", base)]
    variants.extend(opencv_business_card_region_variants(base))

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


def ocr_with_rapidocr(image: Any) -> dict[str, Any]:
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


def ocr_with_easyocr(image: Any) -> dict[str, Any]:
    try:
        import numpy as np
    except Exception as exc:
        raise RuntimeError("EasyOCR依赖不可用") from exc

    reader = _get_easyocr_reader()
    np_image = np.array(image.convert("RGB"))
    result = reader.readtext(np_image, detail=1, paragraph=False)

    texts: list[str] = []
    scores: list[float] = []
    for item in result or []:
        if len(item) < 2:
            continue
        text = str(item[1]).strip()
        if not text:
            continue
        texts.append(text)
        if len(item) >= 3:
            try:
                scores.append(float(item[2]))
            except (TypeError, ValueError):
                pass

    confidence = round(sum(scores) / len(scores), 4) if scores else 0.0
    return {
        "text": "\n".join(texts).strip(),
        "engine": "easyocr",
        "confidence": confidence,
    }


def ocr_with_tesseract(image: Any) -> dict[str, Any]:
    import pytesseract

    candidates: list[dict[str, Any]] = []
    configs = ("--oem 3 --psm 6", "--oem 3 --psm 11")
    for variant_name, variant in business_card_image_variants(image):
        for config in configs:
            text = pytesseract.image_to_string(variant, lang="chi_sim+eng", config=config).strip()
            if not text:
                continue
            confidence = 0.0
            try:
                data = pytesseract.image_to_data(
                    variant, lang="chi_sim+eng", config=config, output_type=pytesseract.Output.DICT
                )
                scores: list[float] = []
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


# Re-exports under the legacy private names (with leading underscore) for
# test back-compat — ``monkeypatch.setattr`` paths point to these names.
_ocr_with_rapidocr = ocr_with_rapidocr
_ocr_with_easyocr = ocr_with_easyocr
_ocr_with_tesseract = ocr_with_tesseract
_business_card_image_variants = business_card_image_variants
_opencv_business_card_region_variants = opencv_business_card_region_variants


__all__ = [
    "_rapidocr_engine",
    "_easyocr_reader",
    "_get_rapidocr_engine",
    "_get_easyocr_reader",
    "business_card_image_variants",
    "_business_card_image_variants",
    "ocr_with_rapidocr",
    "_ocr_with_rapidocr",
    "ocr_with_easyocr",
    "_ocr_with_easyocr",
    "ocr_with_tesseract",
    "_ocr_with_tesseract",
    "_opencv_business_card_region_variants",
]
