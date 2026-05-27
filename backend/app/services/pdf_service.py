"""PDF generation service for quotations using ReportLab."""

import io
import logging
from datetime import datetime, timezone
from decimal import Decimal
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

# Chinese fonts to try in order
CHINESE_FONTS = [
    "Noto Sans CJK SC",
    "Noto Sans CJK TC",
    "Noto Sans CJK JP",
    "Noto Sans CJK KR",
    "WenQuanYi Micro Hei",
    "WenQuanYi Zen Hei",
    "AR PL UMing TW MBE",
    "AR PL UMing CN",
    "AR PL UKai CN",
    "AR PL UKai HK",
    "AR PL UKai TW",
]

# Fallback font if no Chinese font is available
FALLBACK_FONT = "Helvetica"


def _get_chinese_font() -> str:
    """Find an available Chinese font, falling back to Helvetica if none found."""
    if not REPORTLAB_AVAILABLE:
        return FALLBACK_FONT

    import os

    font_dirs = [
        "/usr/share/fonts",
        "/usr/local/share/fonts",
    ]

    try:
        from reportlab.pdfbase import pdfmetrics
        from reportlab.pdfbase.ttfonts import TTFont

        for font_dir in font_dirs:
            if not os.path.exists(font_dir):
                continue
            for root, dirs, files in os.walk(font_dir):
                for f in files:
                    if f.endswith((".ttf", ".otf")):
                        font_path = os.path.join(root, f)
                        font_name = os.path.splitext(f)[0].replace("_", " ").replace("-", " ")
                        if not any(cjk.lower() in font_name.lower() for cjk in CHINESE_FONTS):
                            continue
                        try:
                            registered_name = "AIERP_CJK"
                            pdfmetrics.registerFont(TTFont(registered_name, font_path))
                            return registered_name
                        except Exception as e:
                            logger.debug("Could not register CJK font %s: %s", font_path, e)
    except Exception as e:
        logger.warning(f"Could not register custom fonts: {e}")

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


def _line_hint(item: Any) -> str:
    quantity = int(getattr(item, "quantity", 0) or 0)
    unit_price = _as_decimal(getattr(item, "unit_price", None))
    total_price = _as_decimal(getattr(item, "total_price", None))
    if quantity <= 0:
        return "数量待确认"
    if unit_price <= 0:
        return "单价待确认"
    if total_price <= 0:
        return "小计待确认"
    if quantity >= 1000:
        return "批量需求，建议确认阶梯价与交期"
    return "价格有效，建议确认库存与交期"


def _pdf_text(value: Any) -> str:
    text = str(value)
    return text.encode("latin-1", "replace").decode("latin-1")


def _pdf_escape(value: Any) -> str:
    text = _pdf_text(value)
    return text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def _generate_basic_pdf(quotation: Any) -> bytes:
    """Generate a dependency-free fallback PDF when ReportLab is unavailable."""
    customer = getattr(quotation, "customer", None)
    items = getattr(quotation, "items", None) or []
    subtotal = sum(_as_decimal(getattr(item, "total_price", None)) for item in items)
    risk_label, next_action = _quote_risk_text(quotation, len(items), subtotal)
    quote_total = _as_decimal(getattr(quotation, "total_amount", None)) or subtotal

    lines = [
        "AIERP SMART QUOTATION",
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
        f"Smart Status: {risk_label}",
        f"Next Action: {next_action}",
        "",
        "Terms: Inventory, lead time, tax and payment terms are subject to final order confirmation.",
    ])

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


def generate_quotation_pdf(quotation: Any) -> bytes:
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
    if not REPORTLAB_AVAILABLE:
        logger.warning("ReportLab is not installed; using basic PDF fallback")
        return _generate_basic_pdf(quotation)

    buffer = io.BytesIO()

    # Create document
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=20 * mm,
        leftMargin=20 * mm,
        topMargin=20 * mm,
        bottomMargin=20 * mm,
    )

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

    # Build content
    story = []

    # Company header
    story.append(Paragraph("深圳天允电子有限公司", title_style))
    story.append(Paragraph("智能报价单 / SMART QUOTATION", ParagraphStyle(
        "QuoteSubTitle",
        parent=small_style,
        alignment=1,
        textColor=colors.HexColor("#6b7280"),
    )))
    story.append(Spacer(1, 4 * mm))

    # Quotation title
    quote_title = quotation.title or f"报价单 {quotation.quotation_no or quotation.id}"
    story.append(Paragraph(quote_title, heading_style))

    customer = quotation.customer
    customer_name = getattr(customer, "name", None) or "-"
    contact_person = getattr(customer, "contact_person", None) or "-"
    customer_phone = getattr(customer, "phone", None) or "-"
    customer_address = getattr(customer, "address", None) or "-"
    quote_no = getattr(quotation, "quotation_no", None) or f"#{getattr(quotation, 'id', '-')}"
    quote_status = _status_label(getattr(quotation, "status", None))
    valid_until = _date_text(getattr(quotation, "valid_until", None))
    created_at = _date_text(getattr(quotation, "created_at", None) or datetime.now(timezone.utc))

    info_table = Table(
        [
            [Paragraph("报价单号", label_style), Paragraph(str(quote_no), normal_style), Paragraph("报价状态", label_style), Paragraph(quote_status, normal_style)],
            [Paragraph("报价日期", label_style), Paragraph(created_at, normal_style), Paragraph("有效期至", label_style), Paragraph(valid_until, normal_style)],
            [Paragraph("客户名称", label_style), Paragraph(str(customer_name), normal_style), Paragraph("联系人", label_style), Paragraph(str(contact_person), normal_style)],
            [Paragraph("联系电话", label_style), Paragraph(str(customer_phone), normal_style), Paragraph("客户地址", label_style), Paragraph(str(customer_address), normal_style)],
        ],
        colWidths=[26 * mm, 58 * mm, 26 * mm, 58 * mm],
    )
    info_table.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (-1, -1), _CHINESE_FONT),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f9fafb")),
        ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#d1d5db")),
        ("INNERGRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#e5e7eb")),
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
        # Table header
        table_data = [["序号", "产品 / 型号", "数量", "单价", "小计", "智能提示"]]

        for index, item in enumerate(items, start=1):
            product_name = item.product_name or "-"
            quantity = item.quantity or 0
            unit_price = item.unit_price or 0
            total_price = item.total_price or (quantity * unit_price)
            subtotal += _as_decimal(total_price)

            table_data.append([
                str(index),
                Paragraph(str(product_name), cell_style),
                str(quantity),
                _money(unit_price) if unit_price else "-",
                _money(total_price) if total_price else "-",
                Paragraph(_line_hint(item), cell_style),
            ])

        # Create table
        col_widths = [13 * mm, 58 * mm, 18 * mm, 26 * mm, 28 * mm, 35 * mm]
        table = Table(table_data, colWidths=col_widths)
        table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1f2937")),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                    ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                    ("ALIGN", (1, 1), (1, -1), "LEFT"),
                    ("ALIGN", (5, 1), (5, -1), "LEFT"),
                    ("FONTNAME", (0, 0), (-1, -1), _CHINESE_FONT),
                    ("FONTSIZE", (0, 0), (-1, -1), 9),
                    ("BOTTOMPADDING", (0, 0), (-1, 0), 8),
                    ("BACKGROUND", (0, 1), (-1, -1), colors.white),
                    ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#d1d5db")),
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ]
            )
        )
        story.append(table)
        story.append(Spacer(1, 5 * mm))

        # Totals section
        quote_total = _as_decimal(getattr(quotation, "total_amount", None)) or subtotal
        variance = quote_total - subtotal

        totals_data = [
            ["明细小计:", _money(subtotal)],
            ["报价合计:", _money(quote_total)],
        ]
        if abs(variance) >= Decimal("0.01"):
            totals_data.insert(1, ["调整差额:", _money(variance)])

        totals_table = Table(totals_data, colWidths=[128 * mm, 40 * mm])
        totals_table.setStyle(
            TableStyle(
                [
                    ("ALIGN", (0, 0), (-1, -1), "RIGHT"),
                    ("FONTNAME", (0, 0), (-1, -1), _CHINESE_FONT),
                    ("FONTSIZE", (0, 0), (-1, -1), 10),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                    ("LINEABOVE", (0, -1), (-1, -1), 0.5, colors.black),
                    ("FONTNAME", (0, -1), (-1, -1), _CHINESE_FONT),
                    ("FONTSIZE", (0, -1), (-1, -1), 11),
                ]
            )
        )
        story.append(totals_table)
    else:
        story.append(Paragraph("无报价明细", normal_style))

    story.append(Spacer(1, 6 * mm))

    risk_label, next_action = _quote_risk_text(quotation, len(items), subtotal)
    quote_total = _as_decimal(getattr(quotation, "total_amount", None)) or subtotal
    summary_data = [
        [Paragraph("智能报价摘要", heading_style)],
        [Paragraph(f"报价状态：{risk_label}", normal_style)],
        [Paragraph(f"产品行数：{len(items)} 项；明细金额：{_money(subtotal)}；报价合计：{_money(quote_total)}", normal_style)],
        [Paragraph(f"建议动作：{next_action}", normal_style)],
    ]
    summary_table = Table(summary_data, colWidths=[168 * mm])
    summary_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#eff6ff")),
        ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#93c5fd")),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    story.append(summary_table)
    story.append(Spacer(1, 6 * mm))

    # Payment terms / Notes
    story.append(Paragraph("商务条款与说明", heading_style))
    story.append(Paragraph("1. 本报价以产品行、数量、单价及有效期为准；库存和交期需在下单前再次确认。", small_style))
    story.append(Paragraph("2. 税率、付款方式、运输方式如未单独约定，以双方最终合同或订单确认为准。", small_style))
    story.append(Paragraph("3. 如报价已过有效期，建议重新核价后再作为采购依据。", small_style))

    if quotation.notes:
        story.append(Spacer(1, 5 * mm))
        story.append(Paragraph(f"备注: {quotation.notes}", small_style))

    story.append(Spacer(1, 8 * mm))
    story.append(Paragraph("以上报价由系统根据客户、产品、数量、状态及有效期生成智能摘要，正式交易以双方确认的订单/合同为准。", small_style))

    # Build PDF
    doc.build(story)
    pdf_bytes = buffer.getvalue()
    buffer.close()

    return pdf_bytes
