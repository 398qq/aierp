"""PDF generation service for quotations using ReportLab."""

import io
import logging
from decimal import Decimal
from typing import Any

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
    import os

    font_dirs = [
        "/usr/share/fonts",
        "/usr/local/share/fonts",
    ]

    # First check system fonts directory
    for font_dir in font_dirs:
        if not os.path.exists(font_dir):
            continue
        for root, dirs, files in os.walk(font_dir):
            for f in files:
                if f.endswith((".ttf", ".otf", ".ttc")):
                    name_lower = f.lower()
                    # Check if it's a CJK font
                    for cjk_name in CHINESE_FONTS:
                        if cjk_name.lower().replace(" ", "_") in name_lower or cjk_name.lower() in name_lower:
                            # Found a matching font, try to use it
                            return cjk_name

    # Try to register fonts from reportlab's standard paths
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
                        try:
                            # Try to register with a simple name
                            font_name = os.path.splitext(f)[0].replace("_", " ").replace("-", " ")
                            pdfmetrics.registerFont(TTFont(font_name, font_path))
                            # Check if it's likely a CJK font
                            for cjk in CHINESE_FONTS:
                                if cjk.lower() in font_name.lower():
                                    return font_name
                        except Exception:
                            pass
    except Exception as e:
        logger.warning(f"Could not register custom fonts: {e}")

    # Fallback to Helvetica for ASCII, will render boxes for Chinese
    return FALLBACK_FONT


# Cache the font name
_CHINESE_FONT = _get_chinese_font()
logger.info(f"PDF service using font: {_CHINESE_FONT}")


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
        fontSize=16,
        alignment=1,  # Center
        spaceAfter=10 * mm,
    )

    heading_style = ParagraphStyle(
        "ChineseHeading",
        parent=styles["Heading2"],
        fontName=_CHINESE_FONT,
        fontSize=12,
        spaceAfter=5 * mm,
    )

    normal_style = ParagraphStyle(
        "ChineseNormal",
        parent=styles["Normal"],
        fontName=_CHINESE_FONT,
        fontSize=10,
        spaceAfter=3 * mm,
    )

    small_style = ParagraphStyle(
        "ChineseSmall",
        parent=styles["Normal"],
        fontName=_CHINESE_FONT,
        fontSize=9,
        spaceAfter=2 * mm,
    )

    # Build content
    story = []

    # Company header
    story.append(Paragraph("深圳天允电子有限公司", title_style))
    story.append(Spacer(1, 5 * mm))

    # Quotation title
    quote_title = quotation.title or f"报价单 {quotation.quotation_no or quotation.id}"
    story.append(Paragraph(quote_title, heading_style))
    story.append(Spacer(1, 5 * mm))

    # Customer info section
    customer = quotation.customer
    if customer:
        customer_name = customer.name if customer.name else "-"
        story.append(Paragraph(f"客户: {customer_name}", normal_style))
        if customer.contact_person:
            story.append(Paragraph(f"联系人: {customer.contact_person}", normal_style))
        if customer.phone:
            story.append(Paragraph(f"电话: {customer.phone}", normal_style))
        if customer.address:
            story.append(Paragraph(f"地址: {customer.address}", normal_style))
    else:
        story.append(Paragraph("客户: -", normal_style))

    story.append(Spacer(1, 5 * mm))

    # Quotation details
    story.append(Paragraph(f"报价单号: {quotation.quotation_no or '-'} ", small_style))
    if quotation.valid_until:
        valid_until_str = (
            quotation.valid_until.strftime("%Y-%m-%d")
            if hasattr(quotation.valid_until, "strftime")
            else str(quotation.valid_until)
        )
        story.append(Paragraph(f"有效期至: {valid_until_str}", small_style))

    story.append(Spacer(1, 5 * mm))

    # Items table
    items = quotation.items or []
    if items:
        # Table header
        table_data = [["产品", "数量", "单价", "小计"]]

        subtotal = Decimal("0")

        for item in items:
            product_name = item.product_name or "-"
            quantity = item.quantity or 0
            unit_price = item.unit_price or 0
            total_price = item.total_price or (quantity * unit_price)

            if isinstance(total_price, (int, float)):
                subtotal += Decimal(str(total_price))
            else:
                subtotal += total_price

            table_data.append([
                str(product_name),
                str(quantity),
                f"¥{float(unit_price):,.2f}" if unit_price else "-",
                f"¥{float(total_price):,.2f}" if total_price else "-",
            ])

        # Create table
        col_widths = [200, 60, 100, 100]
        table = Table(table_data, colWidths=col_widths)
        table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.black),
                    ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                    ("ALIGN", (0, 1), (0, -1), "LEFT"),  # Product name left aligned
                    ("FONTNAME", (0, 0), (-1, -1), _CHINESE_FONT),
                    ("FONTSIZE", (0, 0), (-1, -1), 9),
                    ("BOTTOMPADDING", (0, 0), (-1, 0), 8),
                    ("BACKGROUND", (0, 1), (-1, -1), colors.white),
                    ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ]
            )
        )
        story.append(table)
        story.append(Spacer(1, 5 * mm))

        # Totals section
        tax_rate = Decimal("0.13")
        tax_amount = subtotal * tax_rate
        grand_total = subtotal + tax_amount

        # Format amounts
        subtotal_str = f"¥{float(subtotal):,.2f}"
        tax_str = f"¥{float(tax_amount):,.2f}"
        grand_total_str = f"¥{float(grand_total):,.2f}"

        totals_data = [
            ["小计:", subtotal_str],
            ["增值税 (13%):", tax_str],
            ["合计:", grand_total_str],
        ]

        totals_table = Table(totals_data, colWidths=[400, 100])
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
                    ("FONTNAME", (0, -2), (-1, -2), _CHINESE_FONT),
                    ("FONTNAME", (0, -3), (-1, -3), _CHINESE_FONT),
                ]
            )
        )
        story.append(totals_table)
    else:
        story.append(Paragraph("无报价明细", normal_style))

    story.append(Spacer(1, 10 * mm))

    # Payment terms / Notes
    story.append(Paragraph("付款条款:", normal_style))
    story.append(Paragraph("1. 预付 30% 定金，余款发货前付清。", small_style))
    story.append(Paragraph("2. 报价有效期至上述日期。", small_style))

    if quotation.notes:
        story.append(Spacer(1, 5 * mm))
        story.append(Paragraph(f"备注: {quotation.notes}", small_style))

    # Build PDF
    doc.build(story)
    pdf_bytes = buffer.getvalue()
    buffer.close()

    return pdf_bytes
