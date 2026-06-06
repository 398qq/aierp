"""Customer AI — OCR text normalization, scoring, key-field detection, and
result merging.

Pure functions: no I/O, no global state. Used by ``_ocr_engines.py`` and
exercised directly by the test suite for scoring and selection rules.
"""
from __future__ import annotations

import re
import unicodedata
from typing import Any

from app.api.v1.ai.customer._cleaners import clean_confidence


MAX_OCR_CANDIDATE_TEXT_CHARS: int = 1200

CARD_OCR_FIELD_PATTERNS: tuple[str, ...] = (
    r"1[3-9]\d{9}",
    r"0\d{2,3}-?\d{7,8}",
    r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}",
    r"(?:有限公司|股份|集团|公司|Co\.?|Ltd\.?|Inc\.?)",
    r"(?:地址|电话|手机|邮箱|联系人|职务|销售|经理|工程师|官网|网址|Address|Tel|Mobile|Email|Web|Manager|Engineer)",
)


def normalize_ocr_text(text: str) -> str:
    normalized = unicodedata.normalize("NFKC", text or "")
    normalized = normalized.replace("\r\n", "\n").replace("\r", "\n")
    normalized = re.sub(r"[ \t]+", " ", normalized)
    normalized = re.sub(r"\n{3,}", "\n\n", normalized)
    normalized = re.sub(r"(?<=\d)\s+(?=\d)", "", normalized)
    normalized = re.sub(r"(?i)\bE[-\s]*mail\b", "Email", normalized)
    normalized = re.sub(r"(?i)\bM(?:ob(?:ile)?)?\s*[:：]", "Mobile:", normalized)
    normalized = re.sub(r"(?i)\bT(?:el)?\s*[:：]", "Tel:", normalized)
    return normalized.strip()


def score_card_ocr_text(text: str, confidence: Any = 0) -> float:
    normalized = normalize_ocr_text(text)
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
    score += clean_confidence(confidence) * 0.6

    replacement_noise = normalized.count("?") + normalized.count("�")
    if replacement_noise:
        score -= min(replacement_noise * 0.2, 1.0)
    return round(max(score, 0.0), 4)


def card_ocr_key_hits(text: str) -> dict[str, bool]:
    normalized = normalize_ocr_text(text)
    return {
        "phone": bool(re.search(r"(?<!\d)(?:1[3-9]\d{9}|0\d{2,3}-?\d{7,8})(?!\d)", normalized)),
        "email": bool(re.search(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", normalized)),
        "company": bool(re.search(r"(?:有限公司|股份|集团|公司|Co\.?|Ltd\.?|Inc\.?)", normalized, re.IGNORECASE)),
        "contact": bool(re.search(r"(?:联系人|经理|销售|工程师|Manager|Director|Engineer|Sales)", normalized, re.IGNORECASE)),
        "address": bool(re.search(r"(?:地址|Address|Addr|园区|大厦|路|街|号)", normalized, re.IGNORECASE)),
    }


def card_ocr_selection_rank(item: dict[str, Any]) -> tuple[int, int, float, float]:
    hits = card_ocr_key_hits(str(item.get("text") or ""))
    phone_email_hits = int(hits["phone"]) + int(hits["email"])
    key_hits = sum(1 for matched in hits.values() if matched)
    engine = str(item.get("engine") or "")
    primary_engine_bonus = 1 if engine.startswith("easyocr") else 0
    return phone_email_hits, key_hits, float(primary_engine_bonus), float(item.get("score") or 0)


def is_high_signal_ocr_line(line: str) -> bool:
    normalized = normalize_ocr_text(line)
    if not normalized:
        return False
    return any(re.search(pattern, normalized, re.IGNORECASE) for pattern in CARD_OCR_FIELD_PATTERNS) or bool(
        re.search(r"(?:地址|Address|Addr|园区|大厦|路|街|号|官网|网址|Web|www\.)", normalized, re.IGNORECASE)
    )


def merge_high_signal_ocr_lines(best_text: str, candidates: list[dict[str, Any]]) -> str:
    merged_lines = normalize_ocr_text(best_text).splitlines()
    seen = {line.lower() for line in merged_lines if line.strip()}

    for item in sorted(candidates, key=card_ocr_selection_rank, reverse=True):
        for line in normalize_ocr_text(str(item.get("text") or "")).splitlines():
            normalized_line = line.strip()
            if not normalized_line or normalized_line.lower() in seen:
                continue
            if not is_high_signal_ocr_line(normalized_line):
                continue
            merged_lines.append(normalized_line)
            seen.add(normalized_line.lower())

    return "\n".join(merged_lines).strip()


def card_ocr_candidate_for_ai(item: dict[str, Any]) -> dict[str, Any]:
    text = normalize_ocr_text(str(item.get("text") or ""))
    hits = card_ocr_key_hits(text)
    return {
        "engine": item.get("engine") or "unknown",
        "confidence": clean_confidence(item.get("confidence")),
        "score": float(item.get("score") or 0),
        "text_length": len(text),
        "key_hits": [key for key, matched in hits.items() if matched],
        "text": text[:MAX_OCR_CANDIDATE_TEXT_CHARS],
    }


def merge_card_ocr_results(candidates: list[dict[str, Any]]) -> dict[str, Any]:
    usable = [item for item in candidates if normalize_ocr_text(str(item.get("text") or ""))]
    if not usable:
        return {"text": "", "engine": "none", "confidence": 0.0, "score": 0.0, "candidates": []}

    normalized_candidates = []
    for item in usable:
        text = normalize_ocr_text(str(item.get("text") or ""))
        confidence = clean_confidence(item.get("confidence"))
        normalized_candidates.append({
            **item,
            "text": text,
            "confidence": confidence,
            "score": score_card_ocr_text(text, confidence),
        })

    sorted_candidates = sorted(normalized_candidates, key=card_ocr_selection_rank, reverse=True)
    best = max(normalized_candidates, key=card_ocr_selection_rank)
    best["text"] = merge_high_signal_ocr_lines(str(best.get("text") or ""), normalized_candidates)
    best["score"] = score_card_ocr_text(str(best.get("text") or ""), best.get("confidence"))
    best["candidate_texts"] = [card_ocr_candidate_for_ai(item) for item in sorted_candidates[:6]]
    best["candidates"] = [
        {
            "engine": item.get("engine") or "unknown",
            "confidence": clean_confidence(item.get("confidence")),
            "score": item.get("score") or 0,
            "text_length": len(str(item.get("text") or "")),
        }
        for item in sorted_candidates
    ]
    return best


# Back-compat private aliases — original module referenced underscored
# names. Keep them so existing tests still pass.
_normalize_ocr_text = normalize_ocr_text
_score_card_ocr_text = score_card_ocr_text
_card_ocr_key_hits = card_ocr_key_hits
_card_ocr_selection_rank = card_ocr_selection_rank
_is_high_signal_ocr_line = is_high_signal_ocr_line
_merge_high_signal_ocr_lines = merge_high_signal_ocr_lines
_card_ocr_candidate_for_ai = card_ocr_candidate_for_ai
_merge_card_ocr_results = merge_card_ocr_results


__all__ = [
    "MAX_OCR_CANDIDATE_TEXT_CHARS",
    "CARD_OCR_FIELD_PATTERNS",
    "normalize_ocr_text",
    "_normalize_ocr_text",
    "score_card_ocr_text",
    "_score_card_ocr_text",
    "card_ocr_key_hits",
    "_card_ocr_key_hits",
    "card_ocr_selection_rank",
    "_card_ocr_selection_rank",
    "is_high_signal_ocr_line",
    "_is_high_signal_ocr_line",
    "merge_high_signal_ocr_lines",
    "_merge_high_signal_ocr_lines",
    "card_ocr_candidate_for_ai",
    "_card_ocr_candidate_for_ai",
    "merge_card_ocr_results",
    "_merge_card_ocr_results",
]
