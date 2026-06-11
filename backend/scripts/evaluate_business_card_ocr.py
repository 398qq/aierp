"""Evaluate business-card OCR recognition fixtures.

Default mode uses the deterministic local fallback extractor. Pass --use-ai to
exercise the configured AI provider with OCR candidates.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path
from typing import Any

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

DEFAULT_FIXTURE = (
    BACKEND_DIR / "tests" / "fixtures" / "business_card_eval" / "sample.jsonl"
)
FIELDS = ("name", "contact_person", "phone", "email", "address")


def _load_cases(path: Path) -> list[dict[str, Any]]:
    cases = []
    for line_number, line in enumerate(
        path.read_text(encoding="utf-8").splitlines(), start=1
    ):
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        try:
            cases.append(json.loads(line))
        except json.JSONDecodeError as exc:
            raise SystemExit(f"Invalid JSON at {path}:{line_number}: {exc}") from exc
    return cases


def _field_matches(actual: Any, expected: Any) -> bool:
    if expected in (None, ""):
        return True
    return str(actual or "").strip() == str(expected).strip()


def _score_case(case: dict[str, Any], actual: dict[str, Any]) -> dict[str, Any]:
    expected = case.get("expected") or {}
    field_results = {
        field: _field_matches(actual.get(field), expected.get(field))
        for field in FIELDS
        if field in expected
    }
    passed = sum(1 for ok in field_results.values() if ok)
    total = len(field_results)
    return {
        "id": case.get("id") or "",
        "passed": passed,
        "total": total,
        "accuracy": round(passed / total, 4) if total else 1.0,
        "fields": field_results,
        "actual": {field: actual.get(field) for field in FIELDS},
    }


async def _recognize(case: dict[str, Any], *, use_ai: bool) -> dict[str, Any]:
    from app.services.ai.agents import CustomerAgent, _heuristic_customer_recognition

    raw_text = str(case.get("raw_text") or "")
    candidates = case.get("ocr_candidates") or []
    if use_ai:
        return await CustomerAgent.recognize_customer(
            raw_text, ocr_candidates=candidates
        )

    combined_text = "\n".join(
        [raw_text, *[str(candidate.get("text") or "") for candidate in candidates]]
    )
    return _heuristic_customer_recognition(combined_text)


async def _main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--fixture", type=Path, default=DEFAULT_FIXTURE)
    parser.add_argument("--use-ai", action="store_true")
    args = parser.parse_args()

    cases = _load_cases(args.fixture)
    if not cases:
        print("No evaluation cases found.")
        return 1

    results = []
    for case in cases:
        actual = await _recognize(case, use_ai=args.use_ai)
        result = _score_case(case, actual)
        results.append(result)
        print(json.dumps(result, ensure_ascii=False))

    passed = sum(result["passed"] for result in results)
    total = sum(result["total"] for result in results)
    accuracy = round(passed / total, 4) if total else 1.0
    print(
        json.dumps(
            {
                "cases": len(results),
                "passed": passed,
                "total": total,
                "accuracy": accuracy,
            },
            ensure_ascii=False,
        )
    )
    return 0 if passed == total else 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(_main()))
