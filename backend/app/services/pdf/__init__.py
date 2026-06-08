"""PDF service subpackage — re-exports the public surface.

Original monolithic ``app.services.pdf_service`` is split here into:

- ``_fonts``     — CJK font discovery (Tries curated paths, fontconfig,
                   directory walk, then STSong-Light CID fallback)
- ``_formatters`` — money / date / status / risk / summary line helpers
- ``_shared``    — text sanitization, default terms, option merging
- ``_quotation`` — quotation PDF (basic + full)
- ``_sales_order`` — sales-order PDF (basic + full)

The public API (``generate_quotation_pdf``, ``generate_sales_order_pdf``,
``money_upper_cn``) is re-exported so existing imports of
``app.services.pdf_service`` keep working unchanged.
"""
from __future__ import annotations

from app.services.pdf._fonts import (
    CHINESE_FONT_KEYWORDS,
    CHINESE_FONT_PATHS,
    FALLBACK_FONT,
    PARTIAL_FONT_KEYWORDS,
    get_chinese_font,
)

# Re-export ReportLab symbols (PDF rendering deps). When ReportLab
# is not installed these are `None` placeholders so callers can do
# ``if not REPORTLAB_AVAILABLE: return _generate_basic_pdf(...)``
# without crashing.
try:
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
    from reportlab.lib.units import mm
    from reportlab.platypus import (
        Paragraph,
        SimpleDocTemplate,
        Spacer,
        Table,
        TableStyle,
    )

    REPORTLAB_AVAILABLE = True
except ModuleNotFoundError:
    colors = None
    A4 = None
    ParagraphStyle = None
    getSampleStyleSheet = None
    mm = 1
    Paragraph = None
    SimpleDocTemplate = None
    Spacer = None
    Table = None
    TableStyle = None
    REPORTLAB_AVAILABLE = False
from app.services.pdf._formatters import (
    as_decimal,
    date_text,
    days_until,
    item_total,
    line_hint,
    margin_rate,
    money,
    money_upper_cn,
    order_risk_text,
    order_summary_lines,
    percent,
    quote_risk_text,
    smart_summary_lines,
    status_label,
)
from app.services.pdf._quotation import (
    REPORTLAB_AVAILABLE,  # noqa: F401  (re-exported for back-compat)
    generate_basic_pdf,
    generate_quotation_pdf,
)
from app.services.pdf._sales_order import (
    generate_basic_order_pdf,
    generate_sales_order_pdf,
)
from app.services.pdf._shared import (
    default_terms,
    pdf_escape,
    pdf_options,
    pdf_text,
)

# Back-compat aliases: original module exposed the functions with
# leading underscores. Re-export so existing imports keep working.
_money = money
_money_upper_cn = money_upper_cn
money_text = money
get_chinese_font = get_chinese_font
_money_text = money
_money_upper_cn_text = money_upper_cn
_as_decimal = as_decimal
_date_text = date_text
_days_until = days_until
_status_label = status_label
_quote_risk_text = quote_risk_text
_order_risk_text = order_risk_text
_line_hint = line_hint
_item_total = item_total
_margin_rate = margin_rate
_percent = percent
_smart_summary_lines = smart_summary_lines
_order_summary_lines = order_summary_lines
_pdf_text = pdf_text
_pdf_escape = pdf_escape
_pdf_options = pdf_options
_default_terms = default_terms
generate_basic_pdf = generate_basic_pdf
generate_basic_order_pdf = generate_basic_order_pdf
_get_chinese_font = get_chinese_font


__all__ = [
    "generate_quotation_pdf",
    "generate_sales_order_pdf",
    "generate_basic_pdf",
    "generate_basic_order_pdf",
    "money",
    "money_upper_cn",
    "money_text",
    "as_decimal",
    "date_text",
    "days_until",
    "status_label",
    "quote_risk_text",
    "order_risk_text",
    "line_hint",
    "item_total",
    "margin_rate",
    "percent",
    "smart_summary_lines",
    "order_summary_lines",
    "pdf_text",
    "pdf_escape",
    "pdf_options",
    "default_terms",
    "_money",
    "_money_upper_cn",
    "money_text",
    "_money_text",
    "_money_upper_cn_text",
    "_as_decimal",
    "_date_text",
    "_days_until",
    "_status_label",
    "_quote_risk_text",
    "_order_risk_text",
    "_line_hint",
    "_item_total",
    "_margin_rate",
    "_percent",
    "_smart_summary_lines",
    "_order_summary_lines",
    "_pdf_text",
    "_pdf_escape",
    "_pdf_options",
    "_default_terms",
    "generate_basic_pdf",
    "generate_basic_order_pdf",
    "_get_chinese_font",
    "CHINESE_FONT_PATHS",
    "CHINESE_FONT_KEYWORDS",
    "PARTIAL_FONT_KEYWORDS",
    "FALLBACK_FONT",
]
