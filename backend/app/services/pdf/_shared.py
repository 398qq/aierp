"""Shared PDF utilities — text/option sanitization, default terms.

Helpers used by both the quotation and sales-order PDF builders:
- ``pdf_text`` / ``pdf_escape`` — safe string handling for ReportLab
- ``pdf_options`` — apply caller-supplied overrides to the default
  PDF option dict
- ``default_terms`` — stock "payment terms" footer text
"""

from __future__ import annotations

from typing import Any


def pdf_text(value: Any) -> str:
    text = str(value)
    return text.encode("latin-1", "replace").decode("latin-1")


def pdf_escape(value: Any) -> str:
    text = pdf_text(value)
    return text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def pdf_options(options: dict[str, Any] | None) -> dict[str, Any]:
    options = options or {}
    template = str(options.get("template") or "smart")
    show_smart_summary = bool(options.get("show_smart_summary", template == "smart"))
    show_line_hints = bool(options.get("show_line_hints", template == "smart"))
    show_terms = bool(options.get("show_terms", True))
    show_notes = bool(options.get("show_notes", True))
    show_internal_metrics = bool(options.get("show_internal_metrics", False))
    show_signature = bool(options.get("show_signature", True))
    company_name = (
        str(options.get("company_name") or "深圳天允电子有限公司").strip()
        or "深圳天允电子有限公司"
    )
    document_title = (
        str(options.get("document_title") or "正式报价单 / QUOTATION").strip()
        or "正式报价单 / QUOTATION"
    )
    prepared_by = str(options.get("prepared_by") or "").strip()
    contact_phone = str(options.get("contact_phone") or "").strip()
    terms_text = str(options.get("terms") or "").strip()
    return {
        "template": template,
        "company_name": company_name,
        "document_title": document_title,
        "show_smart_summary": show_smart_summary,
        "show_line_hints": show_line_hints,
        "show_terms": show_terms,
        "show_notes": show_notes,
        "show_internal_metrics": show_internal_metrics,
        "show_signature": show_signature,
        "prepared_by": prepared_by,
        "contact_phone": contact_phone,
        "terms": terms_text,
    }


def default_terms() -> list[str]:
    return [
        "1. 本报价以产品行、数量、单价及有效期为准；库存和交期需在下单前再次确认。",
        "2. 税率、付款方式、运输方式如未单独约定，以双方最终合同或订单确认为准。",
        "3. 如报价已过有效期，建议重新核价后再作为采购依据。",
    ]


__all__ = [
    "pdf_text",
    "pdf_escape",
    "pdf_options",
    "default_terms",
]
