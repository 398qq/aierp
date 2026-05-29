"""PDF generation service for quotations using ReportLab."""

import io
import logging
from datetime import datetime, timezone
from decimal import Decimal, ROUND_HALF_UP
from typing import Any

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

logger = logging.getLogger(__name__)

# Known CJK fonts that ReportLab can embed on common Linux distributions. Prefer
# these over broad directory scanning so we do not accidentally pick a partial
# test font such as Unifont sample variants.
CHINESE_FONT_PATHS = [
    "/usr/share/fonts/truetype/wqy/wqy-microhei.ttc",
    "/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc",
    "/usr/share/fonts/truetype/arphic/uming.ttc",
    "/usr/share/fonts/truetype/arphic/ukai.ttc",
    "/usr/share/fonts/opentype/ipafont-gothic/ipagp.ttf",
    "/usr/share/fonts/opentype/ipafont-gothic/ipag.ttf",
]

# Font filename keywords to try in order. Keep these broad because distro font
# filenames often omit spaces, e.g. NotoSansCJK-Regular.otf.
CHINESE_FONT_KEYWORDS = [
    "notosanscjk",
    "noto sans cjk",
    "sourcehansans",
    "source han sans",
    "wenquanyi",
    "wqy",
    "uming",
    "ukai",
    "unifont",
    "ipag",
    "ipa",
]
PARTIAL_FONT_KEYWORDS = ["sample", "csur", "upper"]

# Fallback font if no Chinese font is available
FALLBACK_FONT = "Helvetica"


def _get_chinese_font() -> str:
    """Find an available Chinese font, falling back to Helvetica if none found."""
    if not REPORTLAB_AVAILABLE:
        return FALLBACK_FONT

    import os
    import subprocess

    font_dirs = [
        "/usr/share/fonts",
        "/usr/local/share/fonts",
    ]

    def register_font(font_path: str) -> str | None:
        try:
            from reportlab.pdfbase import pdfmetrics
            from reportlab.pdfbase.ttfonts import TTFont

            registered_name = "AIERP_CJK"
            pdfmetrics.registerFont(TTFont(registered_name, font_path))
            logger.info("Registered PDF CJK font: %s", font_path)
            return registered_name
        except Exception as e:
            logger.debug("Could not register CJK font %s: %s", font_path, e)
            return None

    for font_path in CHINESE_FONT_PATHS:
        if os.path.exists(font_path):
            registered = register_font(font_path)
            if registered:
                return registered

    try:
        fc_match = subprocess.run(
            ["fc-match", "-f", "%{file}\n", "sans:lang=zh-cn"],
            check=False,
            capture_output=True,
            text=True,
            timeout=2,
        )
        for font_path in fc_match.stdout.splitlines():
            if not font_path:
                continue
            registered = register_font(font_path)
            if registered:
                return registered
    except Exception as e:
        logger.debug("Could not query fontconfig for Chinese fonts: %s", e)

    try:
        for font_dir in font_dirs:
            if not os.path.exists(font_dir):
                continue
            for root, dirs, files in os.walk(font_dir):
                for f in files:
                    if f.endswith((".ttf", ".otf", ".ttc")):
                        font_path = os.path.join(root, f)
                        font_name = os.path.splitext(f)[0].replace("_", " ").replace("-", " ")
                        normalized_name = font_name.lower().replace(" ", "")
                        if any(keyword in normalized_name for keyword in PARTIAL_FONT_KEYWORDS):
                            continue
                        if not any(keyword.replace(" ", "") in normalized_name for keyword in CHINESE_FONT_KEYWORDS):
                            continue
                        registered = register_font(font_path)
                        if registered:
                            return registered
    except Exception as e:
        logger.warning(f"Could not register custom fonts: {e}")

    try:
        from reportlab.pdfbase import pdfmetrics
        from reportlab.pdfbase.cidfonts import UnicodeCIDFont

        # Built into ReportLab. It is not embedded, but PDF viewers generally
        # resolve it correctly and it avoids Helvetica/Latin-1 Chinese garbage.
        cid_font = "STSong-Light"
        pdfmetrics.registerFont(UnicodeCIDFont(cid_font))
        return cid_font
    except Exception as e:
        logger.warning("Could not register ReportLab CID Chinese font: %s", e)

    # Fallback to Helvetica for ASCII, will render boxes for Chinese
    return FALLBACK_FONT


# Cache the font name
_CHINESE_FONT = _get_chinese_font()
logger.info(f"PDF service using font: {_CHINESE_FONT}")


def _as_decimal(value: Any) -> Decimal:
    if value is None:
        return Decimal("0")
    if isinstance(value, Decimal):
        return value
    try:
        return Decimal(str(value))
    except Exception:
        return Decimal("0")


def _money(value: Any) -> str:
    return f"¥{float(_as_decimal(value)):,.2f}"


def _money_upper_cn(value: Any) -> str:
    amount = _as_decimal(value).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    if amount < 0:
        return "负" + _money_upper_cn(abs(amount))
    digits = "零壹贰叁肆伍陆柒捌玖"
    units = ["", "拾", "佰", "仟"]
    groups = ["", "万", "亿", "兆"]

    integer = int(amount)
    cents = int((amount - Decimal(integer)) * 100)

    def group_text(num: int) -> str:
        if num == 0:
            return ""
        text = ""
        zero_pending = False
        for index in range(4):
            divisor = 10 ** (3 - index)
            digit = num // divisor
            num %= divisor
            if digit:
                if zero_pending:
                    text += digits[0]
                    zero_pending = False
                text += digits[digit] + units[3 - index]
            elif text:
                zero_pending = True
        return text.rstrip(digits[0])

    if integer == 0:
        integer_text = digits[0] + "元"
    else:
        group_nums = []
        while integer:
            group_nums.append(integer % 10000)
            integer //= 10000
        parts = []
        zero_pending = False
        for group_index in range(len(group_nums) - 1, -1, -1):
            group_num = group_nums[group_index]
            if group_num == 0:
                if parts:
                    zero_pending = True
                continue
            if parts and (zero_pending or group_num < 1000):
                parts.append(digits[0])
            parts.append(group_text(group_num) + groups[group_index])
            zero_pending = False
        integer_text = "".join(parts) + "元"

    jiao = cents // 10
    fen = cents % 10
    if cents == 0:
        return integer_text + "整"
    decimal_text = ""
    if jiao:
        decimal_text += digits[jiao] + "角"
    elif fen:
        decimal_text += "零"
    if fen:
        decimal_text += digits[fen] + "分"
    return integer_text + decimal_text


def _date_text(value: Any) -> str:
    if not value:
        return "-"
    if hasattr(value, "strftime"):
        return value.strftime("%Y-%m-%d")
    return str(value)[:10]


def _days_until(value: Any) -> int | None:
    if not value:
        return None
    if isinstance(value, str):
        try:
            value = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return None
    if not isinstance(value, datetime):
        return None
    now = datetime.now(value.tzinfo or timezone.utc)
    return (value.date() - now.date()).days


def _status_label(status: str | None) -> str:
    return {
        "draft": "草稿",
        "sent": "已发送",
        "won": "已成交",
        "lost": "已丢失",
    }.get(status or "", status or "-")


def _quote_risk_text(quotation: Any, item_count: int, subtotal: Decimal) -> tuple[str, str]:
    days = _days_until(getattr(quotation, "valid_until", None))
    status = getattr(quotation, "status", None)
    if status == "won":
        return "已成交", "报价已成交，可进入订单与发货执行。"
    if status == "lost":
        return "已丢失", "建议复盘丢失原因，必要时复制报价生成新版本。"
    if item_count == 0:
        return "待完善", "报价缺少产品明细，请补充产品行后再发送。"
    if subtotal <= 0:
        return "待核价", "报价金额为零，请确认单价、数量和客户需求。"
    if days is not None and days < 0:
        return "已过期", "报价已超过有效期，建议重新核价后再发送给客户。"
    if days is not None and days <= 3:
        return "临期", "报价即将到期，建议尽快跟进客户确认。"
    if status == "draft":
        return "待发送", "报价内容已生成，建议确认交期、付款条件后发送。"
    return "可跟进", "报价已发送，建议围绕价格、交期和替代料进行跟进。"


def _order_risk_text(order: Any, item_count: int, subtotal: Decimal) -> tuple[str, str]:
    days = _days_until(getattr(order, "delivery_date", None))
    status = getattr(order, "status", None)
    if status == "cancelled":
        return "已取消", "订单已取消，请确认是否需要释放库存或关闭后续交付。"
    if status == "delivered":
        return "已交付", "订单已完成交付，可进入开票、回款和复盘流程。"
    if status == "shipped":
        return "已发货", "建议跟踪签收状态，并同步开票与回款计划。"
    if item_count == 0:
        return "待完善", "订单缺少产品明细，请补充产品行后再确认。"
    if subtotal <= 0:
        return "待核价", "订单金额为零，请确认单价、数量和客户 PO。"
    if days is not None and days < 0:
        return "交付逾期", "预计交付日期已过，建议立即复核交付计划。"
    if days is not None and days <= 3:
        return "临近交付", "订单即将交付，建议确认库存、发货资料和客户收货安排。"
    if status == "pending":
        return "待确认", "建议确认客户 PO、价格、交期和付款条件后锁定库存。"
    return "执行中", "订单已确认，建议按交付计划推进发货、开票和回款。"


def _line_hint(item: Any) -> str:
    quantity = int(getattr(item, "quantity", 0) or 0)
    unit_price = _as_decimal(getattr(item, "unit_price", None))
    total_price = _as_decimal(getattr(item, "total_price", None))
    sales_profit = _as_decimal(getattr(item, "sales_profit", None))
    if quantity <= 0:
        return "数量待确认"
    if unit_price <= 0:
        return "单价待确认"
    if total_price <= 0:
        return "小计待确认"
    if sales_profit < 0:
        return "负毛利，请复核销售价与成本"
    if quantity >= 1000:
        return "批量需求，建议确认阶梯价与交期"
    return "价格有效，建议确认库存与交期"


def _item_total(items: list[Any], field: str) -> Decimal:
    return sum(_as_decimal(getattr(item, field, None)) for item in items)


def _margin_rate(profit: Decimal, amount: Decimal) -> Decimal:
    if amount <= 0:
        return Decimal("0")
    return (profit / amount) * Decimal("100")


def _percent(value: Decimal) -> str:
    return f"{float(value):.2f}%"


def _smart_summary_lines(quotation: Any, items: list[Any], subtotal: Decimal) -> list[str]:
    quote_total = _as_decimal(getattr(quotation, "total_amount", None)) or subtotal
    profit = _item_total(items, "sales_profit")
    taxed_cost = _item_total(items, "taxed_cost")
    margin = _margin_rate(profit, quote_total)
    days = _days_until(getattr(quotation, "valid_until", None))
    risk_label, next_action = _quote_risk_text(quotation, len(items), subtotal)
    missing_price = sum(1 for item in items if _as_decimal(getattr(item, "unit_price", None)) <= 0)
    negative_profit = sum(1 for item in items if _as_decimal(getattr(item, "sales_profit", None)) < 0)

    lines = [
        f"报价健康：{risk_label}；产品行 {len(items)} 项，总数量 {sum(int(getattr(item, 'quantity', 0) or 0) for item in items)}。",
        f"金额摘要：明细金额 {_money(subtotal)}，报价合计 {_money(quote_total)}。",
    ]
    if taxed_cost > 0 or profit != 0:
        lines.append(f"内部毛利：含税成本 {_money(taxed_cost)}，销售毛利 {_money(profit)}，综合毛利率 {_percent(margin)}。")
    if days is not None:
        lines.append(f"有效期判断：距到期 {days} 天；过期或临期报价建议重新核价。")
    if missing_price or negative_profit:
        lines.append(f"复核重点：{missing_price} 行缺少销售单价，{negative_profit} 行为负毛利。")
    lines.append(f"建议动作：{next_action}")
    return lines


def _order_summary_lines(order: Any, items: list[Any], subtotal: Decimal) -> list[str]:
    quote_total = _as_decimal(getattr(order, "total_amount", None)) or subtotal
    days = _days_until(getattr(order, "delivery_date", None))
    risk_label, next_action = _order_risk_text(order, len(items), subtotal)
    total_quantity = sum(int(getattr(item, "quantity", 0) or 0) for item in items)
    missing_price = sum(1 for item in items if _as_decimal(getattr(item, "unit_price", None)) <= 0)
    lines = [
        f"订单状态：{risk_label}；产品行 {len(items)} 项，总数量 {total_quantity}。",
        f"金额摘要：明细金额 {_money(subtotal)}，订单合计 {_money(quote_total)}。",
    ]
    if days is not None:
        lines.append(f"交付计划：距预计交付 {days} 天；逾期或临近交付订单需优先跟进。")
    if missing_price:
        lines.append(f"复核重点：{missing_price} 行缺少销售单价。")
    lines.append(f"建议动作：{next_action}")
    return lines


def _pdf_text(value: Any) -> str:
    text = str(value)
    return text.encode("latin-1", "replace").decode("latin-1")


def _pdf_escape(value: Any) -> str:
    text = _pdf_text(value)
    return text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def _pdf_options(options: dict[str, Any] | None) -> dict[str, Any]:
    options = options or {}
    template = str(options.get("template") or "smart")
    show_smart_summary = bool(options.get("show_smart_summary", template == "smart"))
    show_line_hints = bool(options.get("show_line_hints", template == "smart"))
    show_terms = bool(options.get("show_terms", True))
    show_notes = bool(options.get("show_notes", True))
    show_internal_metrics = bool(options.get("show_internal_metrics", False))
    show_signature = bool(options.get("show_signature", True))
    company_name = str(options.get("company_name") or "深圳天允电子有限公司").strip() or "深圳天允电子有限公司"
    document_title = str(options.get("document_title") or "正式报价单 / QUOTATION").strip() or "正式报价单 / QUOTATION"
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


def _default_terms() -> list[str]:
    return [
        "1. 本报价以产品行、数量、单价及有效期为准；库存和交期需在下单前再次确认。",
        "2. 税率、付款方式、运输方式如未单独约定，以双方最终合同或订单确认为准。",
        "3. 如报价已过有效期，建议重新核价后再作为采购依据。",
    ]


def _generate_basic_pdf(quotation: Any, options: dict[str, Any] | None = None) -> bytes:
    """Generate a dependency-free fallback PDF when ReportLab is unavailable."""
    pdf_options = _pdf_options(options)
    customer = getattr(quotation, "customer", None)
    if not (options or {}).get("company_name") and getattr(customer, "name", None):
        pdf_options["company_name"] = str(getattr(customer, "name"))
    items = getattr(quotation, "items", None) or []
    subtotal = sum(_as_decimal(getattr(item, "total_price", None)) for item in items)
    risk_label, next_action = _quote_risk_text(quotation, len(items), subtotal)
    quote_total = _as_decimal(getattr(quotation, "total_amount", None)) or subtotal

    lines = [
        _pdf_text(pdf_options["company_name"]).upper(),
        _pdf_text(pdf_options["document_title"]).upper(),
        f"Quotation No: {getattr(quotation, 'quotation_no', None) or getattr(quotation, 'id', '-')}",
        f"Title: {getattr(quotation, 'title', None) or '-'}",
        f"Customer: {getattr(customer, 'name', None) or '-'}",
        f"Status: {_status_label(getattr(quotation, 'status', None))}",
        f"Valid Until: {_date_text(getattr(quotation, 'valid_until', None))}",
        "",
        "Items:",
    ]
    for index, item in enumerate(items, start=1):
        lines.append(
            f"{index}. {getattr(item, 'product_name', None) or '-'} "
            f"qty {getattr(item, 'quantity', 0) or 0} "
            f"unit {_money(getattr(item, 'unit_price', None))} "
            f"subtotal {_money(getattr(item, 'total_price', None))}"
        )
    lines.extend([
        "",
        f"Subtotal: {_money(subtotal)}",
        f"Quotation Total: {_money(quote_total)}",
    ])
    if pdf_options["show_smart_summary"]:
        lines.extend([f"Smart Status: {risk_label}", f"Next Action: {next_action}", ""])
    if pdf_options["show_terms"]:
        terms = pdf_options["terms"].splitlines() if pdf_options["terms"] else [
            "Inventory, lead time, tax and payment terms are subject to final order confirmation."
        ]
        lines.extend(["Terms:", *terms])
    if pdf_options["show_signature"]:
        lines.extend(["", "Prepared by: " + (pdf_options["prepared_by"] or "-"), "Customer signature: __________________"])

    content_lines = ["BT", "/F1 10 Tf", "50 790 Td", "14 TL"]
    for line in lines[:52]:
        content_lines.append(f"({_pdf_escape(line)}) Tj")
        content_lines.append("T*")
    content_lines.append("ET")
    stream = "\n".join(content_lines).encode("latin-1", "replace")

    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] /Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
        b"<< /Length " + str(len(stream)).encode("ascii") + b" >>\nstream\n" + stream + b"\nendstream",
    ]
    pdf = bytearray(b"%PDF-1.4\n")
    offsets = [0]
    for index, obj in enumerate(objects, start=1):
        offsets.append(len(pdf))
        pdf.extend(f"{index} 0 obj\n".encode("ascii"))
        pdf.extend(obj)
        pdf.extend(b"\nendobj\n")
    xref_offset = len(pdf)
    pdf.extend(f"xref\n0 {len(objects) + 1}\n".encode("ascii"))
    pdf.extend(b"0000000000 65535 f \n")
    for offset in offsets[1:]:
        pdf.extend(f"{offset:010d} 00000 n \n".encode("ascii"))
    pdf.extend(
        f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{xref_offset}\n%%EOF\n".encode("ascii")
    )
    return bytes(pdf)


def _generate_basic_order_pdf(order: Any, options: dict[str, Any] | None = None) -> bytes:
    """Generate a dependency-free fallback sales order PDF."""
    pdf_options = _pdf_options(options)
    customer = getattr(order, "customer", None)
    if not (options or {}).get("company_name") and getattr(customer, "name", None):
        pdf_options["company_name"] = str(getattr(customer, "name"))
    items = getattr(order, "items", None) or []
    subtotal = sum(_as_decimal(getattr(item, "total_price", None)) for item in items)
    risk_label, next_action = _order_risk_text(order, len(items), subtotal)
    order_total = _as_decimal(getattr(order, "total_amount", None)) or subtotal

    lines = [
        _pdf_text(pdf_options["company_name"]).upper(),
        _pdf_text(pdf_options["document_title"]).upper(),
        f"Order No: {getattr(order, 'order_no', None) or getattr(order, 'id', '-')}",
        f"Customer: {getattr(customer, 'name', None) or '-'}",
        f"Status: {_status_label(getattr(order, 'status', None))}",
        f"Order Date: {_date_text(getattr(order, 'order_date', None))}",
        f"Delivery Date: {_date_text(getattr(order, 'delivery_date', None))}",
        "",
        "Items:",
    ]
    for index, item in enumerate(items, start=1):
        lines.append(
            f"{index}. {getattr(item, 'product_name', None) or '-'} "
            f"qty {getattr(item, 'quantity', 0) or 0} "
            f"unit {_money(getattr(item, 'unit_price', None))} "
            f"subtotal {_money(getattr(item, 'total_price', None))}"
        )
    lines.extend(["", f"Order Total: {_money(order_total)}"])
    if pdf_options["show_smart_summary"]:
        lines.extend([f"Order Status: {risk_label}", f"Next Action: {next_action}", ""])
    if pdf_options["show_terms"]:
        terms = pdf_options["terms"].splitlines() if pdf_options["terms"] else _default_terms()
        lines.extend(["Terms:", *terms])

    content_lines = ["BT", "/F1 10 Tf", "50 790 Td", "14 TL"]
    for line in lines[:52]:
        content_lines.append(f"({_pdf_escape(line)}) Tj")
        content_lines.append("T*")
    content_lines.append("ET")
    stream = "\n".join(content_lines).encode("latin-1", "replace")

    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] /Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
        b"<< /Length " + str(len(stream)).encode("ascii") + b" >>\nstream\n" + stream + b"\nendstream",
    ]
    pdf = bytearray(b"%PDF-1.4\n")
    offsets = [0]
    for index, obj in enumerate(objects, start=1):
        offsets.append(len(pdf))
        pdf.extend(f"{index} 0 obj\n".encode("ascii"))
        pdf.extend(obj)
        pdf.extend(b"\nendobj\n")
    xref_offset = len(pdf)
    pdf.extend(f"xref\n0 {len(objects) + 1}\n".encode("ascii"))
    pdf.extend(b"0000000000 65535 f \n")
    for offset in offsets[1:]:
        pdf.extend(f"{offset:010d} 00000 n \n".encode("ascii"))
    pdf.extend(
        f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{xref_offset}\n%%EOF\n".encode("ascii")
    )
    return bytes(pdf)


def generate_quotation_pdf(quotation: Any, options: dict[str, Any] | None = None) -> bytes:
    """
    Generate a PDF for a quotation.

    Args:
        quotation: A Quotation model object with:
            - quotation_no: quotation number string
            - title: quotation title
            - valid_until: datetime for expiry
            - notes: notes text
            - total_amount: decimal/float total
            - customer: Customer object with name, contact_person, phone, address
            - items: list of QuotationItem objects with product_name, quantity, unit_price, total_price

    Returns:
        PDF bytes
    """
    pdf_options = _pdf_options(options)
    if not REPORTLAB_AVAILABLE:
        logger.warning("ReportLab is not installed; using basic PDF fallback")
        return _generate_basic_pdf(quotation, pdf_options)

    buffer = io.BytesIO()
    template = pdf_options["template"]
    compact = template == "compact"

    # Create document
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=(14 if compact else 20) * mm,
        leftMargin=(14 if compact else 20) * mm,
        topMargin=(14 if compact else 20) * mm,
        bottomMargin=(14 if compact else 20) * mm,
    )
    content_width = A4[0] - doc.leftMargin - doc.rightMargin
    color_primary = colors.HexColor("#1d3557")
    color_primary_dark = colors.HexColor("#16324f")
    color_border = colors.HexColor("#cbd5e1")
    color_grid = colors.HexColor("#e2e8f0")
    color_soft_bg = colors.HexColor("#f8fafc")
    color_summary_bg = colors.HexColor("#eaf2fb")

    def draw_footer(canvas: Any, document: Any) -> None:
        canvas.saveState()
        canvas.setFont(_CHINESE_FONT, 8)
        canvas.setFillColor(colors.HexColor("#64748b"))
        footer = "系统生成报价文件，正式交易以双方确认订单/合同为准"
        if pdf_options["contact_phone"]:
            footer += f" | 联系电话：{pdf_options['contact_phone']}"
        canvas.drawString(document.leftMargin, 10 * mm, footer)
        canvas.drawRightString(A4[0] - document.rightMargin, 10 * mm, f"第 {document.page} 页")
        canvas.restoreState()

    # Get styles
    styles = getSampleStyleSheet()

    # Create custom styles with Chinese font
    title_style = ParagraphStyle(
        "ChineseTitle",
        parent=styles["Heading1"],
        fontName=_CHINESE_FONT,
        fontSize=18,
        alignment=1,  # Center
        textColor=colors.HexColor("#1f2937"),
        spaceAfter=5 * mm,
    )

    heading_style = ParagraphStyle(
        "ChineseHeading",
        parent=styles["Heading2"],
        fontName=_CHINESE_FONT,
        fontSize=12,
        textColor=colors.HexColor("#111827"),
        spaceAfter=5 * mm,
    )

    normal_style = ParagraphStyle(
        "ChineseNormal",
        parent=styles["Normal"],
        fontName=_CHINESE_FONT,
        fontSize=10,
        leading=14,
        spaceAfter=3 * mm,
    )

    small_style = ParagraphStyle(
        "ChineseSmall",
        parent=styles["Normal"],
        fontName=_CHINESE_FONT,
        fontSize=9,
        leading=12,
        spaceAfter=2 * mm,
    )

    label_style = ParagraphStyle(
        "ChineseLabel",
        parent=small_style,
        textColor=colors.HexColor("#6b7280"),
    )

    cell_style = ParagraphStyle(
        "ChineseCell",
        parent=small_style,
        wordWrap="CJK",
    )

    white_style = ParagraphStyle(
        "ChineseWhite",
        parent=small_style,
        textColor=colors.white,
        leading=13,
    )

    total_style = ParagraphStyle(
        "ChineseTotal",
        parent=normal_style,
        fontSize=12,
        leading=15,
        textColor=colors.HexColor("#111827"),
    )

    # Build content
    story = []

    customer = quotation.customer
    customer_name = getattr(customer, "name", None) or "-"
    contact_person = getattr(customer, "contact_person", None) or "-"
    customer_phone = getattr(customer, "phone", None) or "-"
    customer_address = getattr(customer, "address", None) or "-"
    quote_no = getattr(quotation, "quotation_no", None) or f"#{getattr(quotation, 'id', '-')}"
    quote_status = _status_label(getattr(quotation, "status", None))
    valid_until = _date_text(getattr(quotation, "valid_until", None))
    created_at = _date_text(getattr(quotation, "created_at", None) or datetime.now(timezone.utc))
    quote_title = quotation.title or f"报价单 {quotation.quotation_no or quotation.id}"
    if not (options or {}).get("company_name") and customer_name != "-":
        pdf_options["company_name"] = str(customer_name)

    header_table = Table(
        [
            [
                Paragraph(pdf_options["company_name"], ParagraphStyle(
                    "HeaderCompany",
                    parent=title_style,
                    alignment=0,
                    textColor=colors.white,
                    spaceAfter=1 * mm,
                )),
                Paragraph(f"报价单号<br/>{quote_no}", white_style),
            ],
            [
                Paragraph(pdf_options["document_title"], white_style),
                Paragraph(f"生成日期<br/>{created_at}", white_style),
            ],
        ],
        colWidths=[content_width * 0.70, content_width * 0.30],
    )
    header_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), color_primary),
        ("BOX", (0, 0), (-1, -1), 0.5, color_primary),
        ("INNERGRID", (0, 0), (-1, -1), 0.25, color_primary_dark),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ("TOPPADDING", (0, 0), (-1, -1), 7),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
    ]))
    story.append(header_table)
    story.append(Spacer(1, 5 * mm))
    story.append(Paragraph(quote_title, heading_style))

    info_rows = [
        [Paragraph("报价单号", label_style), Paragraph(str(quote_no), normal_style), Paragraph("报价状态", label_style), Paragraph(quote_status, normal_style)],
        [Paragraph("报价日期", label_style), Paragraph(created_at, normal_style), Paragraph("有效期至", label_style), Paragraph(valid_until, normal_style)],
        [Paragraph("客户名称", label_style), Paragraph(str(customer_name), normal_style), Paragraph("联系人", label_style), Paragraph(str(contact_person), normal_style)],
        [Paragraph("联系电话", label_style), Paragraph(str(customer_phone), normal_style), Paragraph("客户地址", label_style), Paragraph(str(customer_address), normal_style)],
    ]
    if pdf_options["prepared_by"] or pdf_options["contact_phone"]:
        info_rows.append([
            Paragraph("报价经办", label_style),
            Paragraph(pdf_options["prepared_by"] or "-", normal_style),
            Paragraph("经办电话", label_style),
            Paragraph(pdf_options["contact_phone"] or "-", normal_style),
        ])

    info_table = Table(
        info_rows,
        colWidths=[content_width * 0.155, content_width * 0.345, content_width * 0.155, content_width * 0.345],
    )
    info_table.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (-1, -1), _CHINESE_FONT),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("BACKGROUND", (0, 0), (-1, -1), color_soft_bg),
        ("BOX", (0, 0), (-1, -1), 0.5, color_border),
        ("INNERGRID", (0, 0), (-1, -1), 0.25, color_grid),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]))
    story.append(info_table)
    story.append(Spacer(1, 5 * mm))

    # Items table
    items = quotation.items or []
    subtotal = Decimal("0")
    if items:
        story.append(Paragraph("报价明细", heading_style))
        internal = bool(pdf_options["show_internal_metrics"])
        if internal and pdf_options["show_line_hints"]:
            table_data = [["序号", "产品 / 型号", "数量", "含税单价", "销售额", "含税成本", "毛利", "提示"]]
            col_widths = [
                content_width * 0.06,
                content_width * 0.23,
                content_width * 0.08,
                content_width * 0.12,
                content_width * 0.13,
                content_width * 0.12,
                content_width * 0.12,
                content_width * 0.14,
            ]
            hint_col = 7
            amount_cols = (3, 6)
        elif internal:
            table_data = [["序号", "产品 / 型号", "数量", "含税单价", "销售额", "含税成本", "毛利"]]
            col_widths = [
                content_width * 0.06,
                content_width * 0.32,
                content_width * 0.08,
                content_width * 0.13,
                content_width * 0.14,
                content_width * 0.13,
                content_width * 0.14,
            ]
            hint_col = None
            amount_cols = (3, 6)
        elif pdf_options["show_line_hints"]:
            table_data = [["序号", "产品 / 型号", "数量", "含税单价", "销售额", "智能提示"]]
            col_widths = [
                content_width * 0.07,
                content_width * 0.36,
                content_width * 0.10,
                content_width * 0.14,
                content_width * 0.16,
                content_width * 0.17,
            ]
            hint_col = 5
            amount_cols = (3, 4)
        else:
            table_data = [["序号", "产品 / 型号", "数量", "含税单价", "销售额"]]
            col_widths = [
                content_width * 0.07,
                content_width * 0.48,
                content_width * 0.11,
                content_width * 0.16,
                content_width * 0.18,
            ]
            hint_col = None
            amount_cols = (3, 4)

        for index, item in enumerate(items, start=1):
            product_name = item.product_name or "-"
            quantity = item.quantity or 0
            unit_price = item.unit_price or 0
            total_price = item.total_price or (quantity * unit_price)
            subtotal += _as_decimal(total_price)

            row = [
                str(index),
                Paragraph(str(product_name), cell_style),
                str(quantity),
                _money(unit_price) if unit_price else "-",
                _money(total_price) if total_price else "-",
            ]
            if internal:
                row.extend([
                    _money(getattr(item, "taxed_cost", None)),
                    _money(getattr(item, "sales_profit", None)),
                ])
            if pdf_options["show_line_hints"]:
                row.append(Paragraph(_line_hint(item), cell_style))
            table_data.append(row)

        table = Table(table_data, colWidths=col_widths, repeatRows=1)
        table_style = [
                    ("BACKGROUND", (0, 0), (-1, 0), color_primary),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                    ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                    ("ALIGN", (1, 1), (1, -1), "LEFT"),
                    ("FONTNAME", (0, 0), (-1, -1), _CHINESE_FONT),
                    ("FONTSIZE", (0, 0), (-1, -1), 9),
                    ("BOTTOMPADDING", (0, 0), (-1, 0), 8),
                    ("BACKGROUND", (0, 1), (-1, -1), colors.white),
                    ("GRID", (0, 0), (-1, -1), 0.5, color_border),
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ]
        table_style.extend([
            ("ALIGN", (amount_cols[0], 1), (amount_cols[1], -1), "RIGHT"),
            ("RIGHTPADDING", (amount_cols[0], 1), (amount_cols[1], -1), 6),
            ("LEFTPADDING", (1, 1), (1, -1), 6),
        ])
        for row_index in range(2, len(table_data), 2):
            table_style.append(("BACKGROUND", (0, row_index), (-1, row_index), color_soft_bg))
        if hint_col is not None:
            table_style.append(("ALIGN", (hint_col, 1), (hint_col, -1), "LEFT"))
        if internal:
            table_style.append(("TEXTCOLOR", (-1 if not pdf_options["show_line_hints"] else -2, 1), (-1 if not pdf_options["show_line_hints"] else -2, -1), colors.HexColor("#166534")))
        table.setStyle(TableStyle(table_style))
        story.append(table)
        story.append(Spacer(1, 5 * mm))

        # Totals section
        quote_total = _as_decimal(getattr(quotation, "total_amount", None)) or subtotal
        variance = quote_total - subtotal
        untaxed_cost = _item_total(items, "untaxed_cost")
        taxed_cost = _item_total(items, "taxed_cost")
        profit = _item_total(items, "sales_profit")
        margin = _margin_rate(profit, quote_total)

        totals_data = [
            [Paragraph("明细销售额", label_style), Paragraph(_money(subtotal), normal_style)],
            [Paragraph("报价合计", total_style), Paragraph(_money(quote_total), total_style)],
            [Paragraph("人民币大写", label_style), Paragraph(_money_upper_cn(quote_total), normal_style)],
        ]
        if abs(variance) >= Decimal("0.01"):
            totals_data.insert(1, [Paragraph("调整差额", label_style), Paragraph(_money(variance), normal_style)])
        if internal:
            totals_data.extend([
                [Paragraph("未税成本", label_style), Paragraph(_money(untaxed_cost), normal_style)],
                [Paragraph("含税成本", label_style), Paragraph(_money(taxed_cost), normal_style)],
                [Paragraph("销售毛利 / 毛利率", total_style), Paragraph(f"{_money(profit)} / {_percent(margin)}", total_style)],
            ])

        totals_table = Table(totals_data, colWidths=[content_width * 0.62, content_width * 0.38])
        totals_table.setStyle(
            TableStyle(
                [
                    ("ALIGN", (0, 0), (-1, -1), "RIGHT"),
                    ("FONTNAME", (0, 0), (-1, -1), _CHINESE_FONT),
                    ("FONTSIZE", (0, 0), (-1, -1), 10),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                    ("LINEABOVE", (0, -1), (-1, -1), 0.5, color_primary),
                    ("FONTNAME", (0, -1), (-1, -1), _CHINESE_FONT),
                    ("FONTSIZE", (0, -1), (-1, -1), 11),
                ]
            )
        )
        story.append(totals_table)
    else:
        story.append(Paragraph("无报价明细", normal_style))

    story.append(Spacer(1, 6 * mm))

    if pdf_options["show_smart_summary"]:
        summary_data = [[Paragraph("智能报价摘要", heading_style)]]
        for line in _smart_summary_lines(quotation, items, subtotal):
            if "内部毛利" in line and not pdf_options["show_internal_metrics"]:
                continue
            summary_data.append([Paragraph(line, normal_style)])
        summary_table = Table(summary_data, colWidths=[content_width])
        summary_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), color_summary_bg),
            ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#9db7d5")),
            ("LEFTPADDING", (0, 0), (-1, -1), 8),
            ("RIGHTPADDING", (0, 0), (-1, -1), 8),
            ("TOPPADDING", (0, 0), (-1, -1), 6),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ]))
        story.append(summary_table)
        story.append(Spacer(1, 6 * mm))

    # Payment terms / Notes
    if pdf_options["show_terms"]:
        terms_lines = pdf_options["terms"].splitlines() if pdf_options["terms"] else _default_terms()
        terms_data = [[Paragraph("商务条款与说明", heading_style)]]
        for line in terms_lines:
            if line.strip():
                terms_data.append([Paragraph(line.strip(), small_style)])
        terms_table = Table(terms_data, colWidths=[content_width])
        terms_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), color_soft_bg),
            ("BOX", (0, 0), (-1, -1), 0.5, color_border),
            ("INNERGRID", (0, 0), (-1, -1), 0.25, color_grid),
            ("LEFTPADDING", (0, 0), (-1, -1), 8),
            ("RIGHTPADDING", (0, 0), (-1, -1), 8),
            ("TOPPADDING", (0, 0), (-1, -1), 6),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ]))
        story.append(terms_table)

    if pdf_options["show_notes"] and quotation.notes:
        story.append(Spacer(1, 5 * mm))
        notes_table = Table(
            [
                [Paragraph("报价备注", heading_style)],
                [Paragraph(str(quotation.notes), small_style)],
            ],
            colWidths=[content_width],
        )
        notes_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), color_soft_bg),
            ("BOX", (0, 0), (-1, -1), 0.5, color_border),
            ("INNERGRID", (0, 0), (-1, -1), 0.25, color_grid),
            ("LEFTPADDING", (0, 0), (-1, -1), 8),
            ("RIGHTPADDING", (0, 0), (-1, -1), 8),
            ("TOPPADDING", (0, 0), (-1, -1), 6),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ]))
        story.append(notes_table)

    story.append(Spacer(1, 8 * mm))
    if pdf_options["show_signature"]:
        signature_table = Table(
            [
                [
                    Paragraph("报价经办", label_style),
                    Paragraph(pdf_options["prepared_by"] or "____________", normal_style),
                    Paragraph("客户确认", label_style),
                    Paragraph("____________", normal_style),
                ],
                [
                    Paragraph("确认日期", label_style),
                    Paragraph("____________", normal_style),
                    Paragraph("客户盖章/签字", label_style),
                    Paragraph("____________", normal_style),
                ],
            ],
            colWidths=[content_width * 0.14, content_width * 0.36, content_width * 0.17, content_width * 0.33],
        )
        signature_table.setStyle(TableStyle([
            ("FONTNAME", (0, 0), (-1, -1), _CHINESE_FONT),
            ("BOX", (0, 0), (-1, -1), 0.5, color_border),
            ("INNERGRID", (0, 0), (-1, -1), 0.25, color_grid),
            ("BACKGROUND", (0, 0), (0, -1), color_soft_bg),
            ("BACKGROUND", (2, 0), (2, -1), color_soft_bg),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("LEFTPADDING", (0, 0), (-1, -1), 6),
            ("RIGHTPADDING", (0, 0), (-1, -1), 6),
            ("TOPPADDING", (0, 0), (-1, -1), 7),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
        ]))
        story.append(signature_table)
        story.append(Spacer(1, 5 * mm))

    story.append(Paragraph("以上报价由系统根据客户、产品、数量、状态及有效期生成智能摘要，正式交易以双方确认的订单/合同为准。", small_style))

    # Build PDF
    doc.build(story, onFirstPage=draw_footer, onLaterPages=draw_footer)
    pdf_bytes = buffer.getvalue()
    buffer.close()

    return pdf_bytes


def generate_sales_order_pdf(order: Any, options: dict[str, Any] | None = None) -> bytes:
    """Generate a formal PDF for a sales order."""
    raw_options = options or {}
    pdf_options = _pdf_options({**raw_options, "document_title": raw_options.get("document_title") or "正式销售订单 / SALES ORDER"})
    if not REPORTLAB_AVAILABLE:
        logger.warning("ReportLab is not installed; using basic sales order PDF fallback")
        return _generate_basic_order_pdf(order, pdf_options)

    buffer = io.BytesIO()
    compact = pdf_options["template"] == "compact"
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=(14 if compact else 20) * mm,
        leftMargin=(14 if compact else 20) * mm,
        topMargin=(14 if compact else 20) * mm,
        bottomMargin=(14 if compact else 20) * mm,
    )
    content_width = A4[0] - doc.leftMargin - doc.rightMargin
    color_primary = colors.HexColor("#1d3557")
    color_primary_dark = colors.HexColor("#16324f")
    color_border = colors.HexColor("#cbd5e1")
    color_grid = colors.HexColor("#e2e8f0")
    color_soft_bg = colors.HexColor("#f8fafc")
    color_summary_bg = colors.HexColor("#eaf2fb")

    def draw_footer(canvas: Any, document: Any) -> None:
        canvas.saveState()
        canvas.setFont(_CHINESE_FONT, 8)
        canvas.setFillColor(colors.HexColor("#64748b"))
        footer = "系统生成销售订单文件，正式交付以双方确认订单/合同为准"
        if pdf_options["contact_phone"]:
            footer += f" | 联系电话：{pdf_options['contact_phone']}"
        canvas.drawString(document.leftMargin, 10 * mm, footer)
        canvas.drawRightString(A4[0] - document.rightMargin, 10 * mm, f"第 {document.page} 页")
        canvas.restoreState()

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle("OrderTitle", parent=styles["Heading1"], fontName=_CHINESE_FONT, fontSize=18, alignment=1, textColor=colors.white)
    heading_style = ParagraphStyle("OrderHeading", parent=styles["Heading2"], fontName=_CHINESE_FONT, fontSize=12, textColor=colors.HexColor("#111827"), spaceAfter=5 * mm)
    normal_style = ParagraphStyle("OrderNormal", parent=styles["Normal"], fontName=_CHINESE_FONT, fontSize=10, leading=14, spaceAfter=3 * mm)
    small_style = ParagraphStyle("OrderSmall", parent=styles["Normal"], fontName=_CHINESE_FONT, fontSize=9, leading=12, spaceAfter=2 * mm)
    label_style = ParagraphStyle("OrderLabel", parent=small_style, textColor=colors.HexColor("#64748b"))
    cell_style = ParagraphStyle("OrderCell", parent=small_style, wordWrap="CJK")
    white_style = ParagraphStyle("OrderWhite", parent=small_style, textColor=colors.white, leading=13)
    total_style = ParagraphStyle("OrderTotal", parent=normal_style, fontSize=12, leading=15, textColor=colors.HexColor("#111827"))

    story = []
    customer = getattr(order, "customer", None)
    customer_name = getattr(customer, "name", None) or "-"
    if not raw_options.get("company_name") and customer_name != "-":
        pdf_options["company_name"] = str(customer_name)
    contact_person = getattr(customer, "contact_person", None) or "-"
    customer_phone = getattr(customer, "phone", None) or "-"
    customer_address = getattr(customer, "address", None) or "-"
    order_no = getattr(order, "order_no", None) or f"#{getattr(order, 'id', '-')}"
    status_text = {
        "pending": "待确认",
        "confirmed": "已确认",
        "shipped": "已发货",
        "delivered": "已签收",
        "cancelled": "已取消",
    }.get(getattr(order, "status", None) or "", getattr(order, "status", None) or "-")
    order_date = _date_text(getattr(order, "order_date", None))
    delivery_date = _date_text(getattr(order, "delivery_date", None))

    header_table = Table(
        [
            [
                Paragraph(pdf_options["company_name"], title_style),
                Paragraph(f"订单号<br/>{order_no}", white_style),
            ],
            [
                Paragraph(pdf_options["document_title"], white_style),
                Paragraph(f"制单日期<br/>{_date_text(datetime.now(timezone.utc))}", white_style),
            ],
        ],
        colWidths=[content_width * 0.70, content_width * 0.30],
    )
    header_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), color_primary),
        ("BOX", (0, 0), (-1, -1), 0.5, color_primary),
        ("INNERGRID", (0, 0), (-1, -1), 0.25, color_primary_dark),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ("TOPPADDING", (0, 0), (-1, -1), 7),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
    ]))
    story.append(header_table)
    story.append(Spacer(1, 5 * mm))

    info_rows = [
        [Paragraph("销售订单号", label_style), Paragraph(str(order_no), normal_style), Paragraph("订单状态", label_style), Paragraph(status_text, normal_style)],
        [Paragraph("下单日期", label_style), Paragraph(order_date, normal_style), Paragraph("预计交付", label_style), Paragraph(delivery_date, normal_style)],
        [Paragraph("客户名称", label_style), Paragraph(str(customer_name), normal_style), Paragraph("联系人", label_style), Paragraph(str(contact_person), normal_style)],
        [Paragraph("联系电话", label_style), Paragraph(str(customer_phone), normal_style), Paragraph("客户地址", label_style), Paragraph(str(customer_address), normal_style)],
    ]
    if getattr(order, "quotation_id", None):
        info_rows.append([Paragraph("来源报价", label_style), Paragraph(f"#{order.quotation_id}", normal_style), Paragraph("经办电话", label_style), Paragraph(pdf_options["contact_phone"] or "-", normal_style)])

    info_table = Table(info_rows, colWidths=[content_width * 0.155, content_width * 0.345, content_width * 0.155, content_width * 0.345])
    info_table.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (-1, -1), _CHINESE_FONT),
        ("BACKGROUND", (0, 0), (-1, -1), color_soft_bg),
        ("BOX", (0, 0), (-1, -1), 0.5, color_border),
        ("INNERGRID", (0, 0), (-1, -1), 0.25, color_grid),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]))
    story.append(info_table)
    story.append(Spacer(1, 5 * mm))

    items = getattr(order, "items", None) or []
    subtotal = Decimal("0")
    if items:
        story.append(Paragraph("订单明细", heading_style))
        show_hints = bool(pdf_options["show_line_hints"])
        table_data = [["序号", "产品 / 型号", "数量", "销售单价", "订单金额"] + (["交付提示"] if show_hints else [])]
        col_widths = [content_width * 0.07, content_width * (0.45 if show_hints else 0.52), content_width * 0.10, content_width * 0.15, content_width * 0.16]
        if show_hints:
            col_widths.append(content_width * 0.07)
        for index, item in enumerate(items, start=1):
            quantity = getattr(item, "quantity", 0) or 0
            unit_price = getattr(item, "unit_price", None) or 0
            total_price = getattr(item, "total_price", None) or (quantity * unit_price)
            subtotal += _as_decimal(total_price)
            row = [
                str(index),
                Paragraph(str(getattr(item, "product_name", None) or "-"), cell_style),
                str(quantity),
                _money(unit_price) if unit_price else "-",
                _money(total_price) if total_price else "-",
            ]
            if show_hints:
                row.append(Paragraph("确认库存、包装与交期", cell_style))
            table_data.append(row)

        table = Table(table_data, colWidths=col_widths, repeatRows=1)
        table_style = [
            ("BACKGROUND", (0, 0), (-1, 0), color_primary),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
            ("ALIGN", (1, 1), (1, -1), "LEFT"),
            ("ALIGN", (3, 1), (4, -1), "RIGHT"),
            ("FONTNAME", (0, 0), (-1, -1), _CHINESE_FONT),
            ("FONTSIZE", (0, 0), (-1, -1), 9),
            ("BOTTOMPADDING", (0, 0), (-1, 0), 8),
            ("GRID", (0, 0), (-1, -1), 0.5, color_border),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("LEFTPADDING", (1, 1), (1, -1), 6),
            ("RIGHTPADDING", (3, 1), (4, -1), 6),
        ]
        for row_index in range(2, len(table_data), 2):
            table_style.append(("BACKGROUND", (0, row_index), (-1, row_index), color_soft_bg))
        table.setStyle(TableStyle(table_style))
        story.append(table)
        story.append(Spacer(1, 5 * mm))

        order_total = _as_decimal(getattr(order, "total_amount", None)) or subtotal
        totals_table = Table(
            [
                [Paragraph("明细销售额", label_style), Paragraph(_money(subtotal), normal_style)],
                [Paragraph("订单合计", total_style), Paragraph(_money(order_total), total_style)],
                [Paragraph("人民币大写", label_style), Paragraph(_money_upper_cn(order_total), normal_style)],
            ],
            colWidths=[content_width * 0.62, content_width * 0.38],
        )
        totals_table.setStyle(TableStyle([
            ("ALIGN", (0, 0), (-1, -1), "RIGHT"),
            ("FONTNAME", (0, 0), (-1, -1), _CHINESE_FONT),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ("LINEABOVE", (0, -2), (-1, -2), 0.5, color_primary),
        ]))
        story.append(totals_table)
    else:
        story.append(Paragraph("无订单明细", normal_style))

    story.append(Spacer(1, 6 * mm))
    if pdf_options["show_smart_summary"]:
        summary_data = [[Paragraph("智能订单摘要", heading_style)]]
        for line in _order_summary_lines(order, items, subtotal):
            summary_data.append([Paragraph(line, normal_style)])
        summary_table = Table(summary_data, colWidths=[content_width])
        summary_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), color_summary_bg),
            ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#9db7d5")),
            ("LEFTPADDING", (0, 0), (-1, -1), 8),
            ("RIGHTPADDING", (0, 0), (-1, -1), 8),
            ("TOPPADDING", (0, 0), (-1, -1), 6),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ]))
        story.append(summary_table)
        story.append(Spacer(1, 6 * mm))

    if pdf_options["show_terms"]:
        terms_lines = pdf_options["terms"].splitlines() if pdf_options["terms"] else [
            "1. 本订单以双方确认的产品、数量、单价、交期及付款条件为准。",
            "2. 交付前请再次确认库存、包装、收货地址及客户验收要求。",
            "3. 如发生交期、价格或物料变更，应以双方确认的新订单或补充协议为准。",
        ]
        terms_table = Table([[Paragraph("交付条款与说明", heading_style)], *[[Paragraph(line.strip(), small_style)] for line in terms_lines if line.strip()]], colWidths=[content_width])
        terms_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), color_soft_bg),
            ("BOX", (0, 0), (-1, -1), 0.5, color_border),
            ("INNERGRID", (0, 0), (-1, -1), 0.25, color_grid),
            ("LEFTPADDING", (0, 0), (-1, -1), 8),
            ("RIGHTPADDING", (0, 0), (-1, -1), 8),
            ("TOPPADDING", (0, 0), (-1, -1), 6),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ]))
        story.append(terms_table)

    if pdf_options["show_notes"] and getattr(order, "notes", None):
        story.append(Spacer(1, 5 * mm))
        notes_table = Table([[Paragraph("订单备注", heading_style)], [Paragraph(str(order.notes), small_style)]], colWidths=[content_width])
        notes_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), color_soft_bg),
            ("BOX", (0, 0), (-1, -1), 0.5, color_border),
            ("LEFTPADDING", (0, 0), (-1, -1), 8),
            ("RIGHTPADDING", (0, 0), (-1, -1), 8),
            ("TOPPADDING", (0, 0), (-1, -1), 6),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ]))
        story.append(notes_table)

    if pdf_options["show_signature"]:
        story.append(Spacer(1, 8 * mm))
        signature_table = Table(
            [
                [Paragraph("制单人", label_style), Paragraph(pdf_options["prepared_by"] or "____________", normal_style), Paragraph("客户确认", label_style), Paragraph("____________", normal_style)],
                [Paragraph("确认日期", label_style), Paragraph("____________", normal_style), Paragraph("客户盖章/签字", label_style), Paragraph("____________", normal_style)],
            ],
            colWidths=[content_width * 0.14, content_width * 0.36, content_width * 0.17, content_width * 0.33],
        )
        signature_table.setStyle(TableStyle([
            ("FONTNAME", (0, 0), (-1, -1), _CHINESE_FONT),
            ("BOX", (0, 0), (-1, -1), 0.5, color_border),
            ("INNERGRID", (0, 0), (-1, -1), 0.25, color_grid),
            ("BACKGROUND", (0, 0), (0, -1), color_soft_bg),
            ("BACKGROUND", (2, 0), (2, -1), color_soft_bg),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("LEFTPADDING", (0, 0), (-1, -1), 6),
            ("RIGHTPADDING", (0, 0), (-1, -1), 6),
            ("TOPPADDING", (0, 0), (-1, -1), 7),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
        ]))
        story.append(signature_table)

    doc.build(story, onFirstPage=draw_footer, onLaterPages=draw_footer)
    pdf_bytes = buffer.getvalue()
    buffer.close()
    return pdf_bytes
