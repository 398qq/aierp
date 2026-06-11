"""Quotation PDF generation.

Two renderers:
- ``generate_basic_pdf`` — the original simple-text-only PDF (no AI insights)
- ``generate_quotation_pdf`` — the full quotation PDF with risk text,
  AI insights, payment terms, and the rich row table

Both return ``bytes`` (the rendered PDF) and are safe to call without
ReportLab installed — they raise ImportError in that case.
"""

from __future__ import annotations

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

from app.services.pdf._formatters import (
    as_decimal,
    date_text,
    item_total,
    line_hint,
    margin_rate,
    money,
    money_upper_cn,
    percent,
    quote_risk_text,
    smart_summary_lines,
    status_label,
)
from app.services.pdf._fonts import _CHINESE_FONT
from app.services.pdf._shared import (
    default_terms,
    pdf_escape,
    pdf_options,
    pdf_text,
)

logger = logging.getLogger(__name__)


def generate_basic_pdf(quotation: Any, options: dict[str, Any] | None = None) -> bytes:
    """Generate a dependency-free fallback PDF when ReportLab is unavailable."""
    opts = pdf_options(options)
    customer = getattr(quotation, "customer", None)
    if not (options or {}).get("company_name") and getattr(customer, "name", None):
        opts["company_name"] = str(getattr(customer, "name"))
    items = getattr(quotation, "items", None) or []
    subtotal: Decimal = sum(
        (as_decimal(getattr(item, "total_price", None)) for item in items), Decimal("0")
    )
    risk_label, next_action = quote_risk_text(quotation, len(items), subtotal)
    quote_total = as_decimal(getattr(quotation, "total_amount", None)) or subtotal

    lines = [
        pdf_text(opts["company_name"]).upper(),
        pdf_text(opts["document_title"]).upper(),
        f"Quotation No: {getattr(quotation, 'quotation_no', None) or getattr(quotation, 'id', '-')}",
        f"Title: {getattr(quotation, 'title', None) or '-'}",
        f"Customer: {getattr(customer, 'name', None) or '-'}",
        f"Status: {status_label(getattr(quotation, 'status', None))}",
        f"Valid Until: {date_text(getattr(quotation, 'valid_until', None))}",
        "",
        "Items:",
    ]
    for index, item in enumerate(items, start=1):
        lines.append(
            f"{index}. {getattr(item, 'product_name', None) or '-'} "
            f"qty {getattr(item, 'quantity', 0) or 0} "
            f"unit {money(getattr(item, 'unit_price', None))} "
            f"subtotal {money(getattr(item, 'total_price', None))}"
        )
    lines.extend(
        [
            "",
            f"Subtotal: {money(subtotal)}",
            f"Quotation Total: {money(quote_total)}",
        ]
    )
    if opts["show_smart_summary"]:
        lines.extend([f"Smart Status: {risk_label}", f"Next Action: {next_action}", ""])
    if opts["show_terms"]:
        terms = (
            opts["terms"].splitlines()
            if opts["terms"]
            else [
                "Inventory, lead time, tax and payment terms are subject to final order confirmation."
            ]
        )
        lines.extend(["Terms:", *terms])
    if opts["show_signature"]:
        lines.extend(
            [
                "",
                "Prepared by: " + (opts["prepared_by"] or "-"),
                "Customer signature: __________________",
            ]
        )

    content_lines = ["BT", "/F1 10 Tf", "50 790 Td", "14 TL"]
    for line in lines[:52]:
        content_lines.append(f"({pdf_escape(line)}) Tj")
        content_lines.append("T*")
    content_lines.append("ET")
    stream = "\n".join(content_lines).encode("latin-1", "replace")

    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] /Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
        b"<< /Length "
        + str(len(stream)).encode("ascii")
        + b" >>\nstream\n"
        + stream
        + b"\nendstream",
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
        f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{xref_offset}\n%%EOF\n".encode(
            "ascii"
        )
    )
    return bytes(pdf)


def generate_quotation_pdf(
    quotation: Any, options: dict[str, Any] | None = None
) -> bytes:
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
    opts = pdf_options(options)
    if not REPORTLAB_AVAILABLE:
        logger.warning("ReportLab is not installed; using basic PDF fallback")
        return generate_basic_pdf(quotation, opts)

    buffer = io.BytesIO()
    template = opts["template"]
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
        if opts["contact_phone"]:
            footer += f" | 联系电话：{opts['contact_phone']}"
        canvas.drawString(document.leftMargin, 10 * mm, footer)
        canvas.drawRightString(
            A4[0] - document.rightMargin, 10 * mm, f"第 {document.page} 页"
        )
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
    quote_no = (
        getattr(quotation, "quotation_no", None) or f"#{getattr(quotation, 'id', '-')}"
    )
    quote_status = status_label(getattr(quotation, "status", None))
    valid_until = date_text(getattr(quotation, "valid_until", None))
    created_at = date_text(
        getattr(quotation, "created_at", None) or datetime.now(timezone.utc)
    )
    quote_title = quotation.title or f"报价单 {quotation.quotation_no or quotation.id}"
    if not (options or {}).get("company_name") and customer_name != "-":
        opts["company_name"] = str(customer_name)

    header_table = Table(
        [
            [
                Paragraph(
                    opts["company_name"],
                    ParagraphStyle(
                        "HeaderCompany",
                        parent=title_style,
                        alignment=0,
                        textColor=colors.white,
                        spaceAfter=1 * mm,
                    ),
                ),
                Paragraph(f"报价单号<br/>{quote_no}", white_style),
            ],
            [
                Paragraph(opts["document_title"], white_style),
                Paragraph(f"生成日期<br/>{created_at}", white_style),
            ],
        ],
        colWidths=[content_width * 0.70, content_width * 0.30],
    )
    header_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), color_primary),
                ("BOX", (0, 0), (-1, -1), 0.5, color_primary),
                ("INNERGRID", (0, 0), (-1, -1), 0.25, color_primary_dark),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
                ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                ("TOPPADDING", (0, 0), (-1, -1), 7),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
            ]
        )
    )
    story.append(header_table)
    story.append(Spacer(1, 5 * mm))
    story.append(Paragraph(quote_title, heading_style))

    info_rows = [
        [
            Paragraph("报价单号", label_style),
            Paragraph(str(quote_no), normal_style),
            Paragraph("报价状态", label_style),
            Paragraph(quote_status, normal_style),
        ],
        [
            Paragraph("报价日期", label_style),
            Paragraph(created_at, normal_style),
            Paragraph("有效期至", label_style),
            Paragraph(valid_until, normal_style),
        ],
        [
            Paragraph("客户名称", label_style),
            Paragraph(str(customer_name), normal_style),
            Paragraph("联系人", label_style),
            Paragraph(str(contact_person), normal_style),
        ],
        [
            Paragraph("联系电话", label_style),
            Paragraph(str(customer_phone), normal_style),
            Paragraph("客户地址", label_style),
            Paragraph(str(customer_address), normal_style),
        ],
    ]
    if opts["prepared_by"] or opts["contact_phone"]:
        info_rows.append(
            [
                Paragraph("报价经办", label_style),
                Paragraph(opts["prepared_by"] or "-", normal_style),
                Paragraph("经办电话", label_style),
                Paragraph(opts["contact_phone"] or "-", normal_style),
            ]
        )

    info_table = Table(
        info_rows,
        colWidths=[
            content_width * 0.155,
            content_width * 0.345,
            content_width * 0.155,
            content_width * 0.345,
        ],
    )
    info_table.setStyle(
        TableStyle(
            [
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
            ]
        )
    )
    story.append(info_table)
    story.append(Spacer(1, 5 * mm))

    # Items table
    items = quotation.items or []
    subtotal = Decimal("0")
    if items:
        story.append(Paragraph("报价明细", heading_style))
        internal = bool(opts["show_internal_metrics"])
        if internal and opts["show_line_hints"]:
            table_data = [
                [
                    "序号",
                    "产品 / 型号",
                    "数量",
                    "含税单价",
                    "销售额",
                    "含税成本",
                    "毛利",
                    "提示",
                ]
            ]
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
            table_data = [
                [
                    "序号",
                    "产品 / 型号",
                    "数量",
                    "含税单价",
                    "销售额",
                    "含税成本",
                    "毛利",
                ]
            ]
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
        elif opts["show_line_hints"]:
            table_data = [
                ["序号", "产品 / 型号", "数量", "含税单价", "销售额", "智能提示"]
            ]
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
            subtotal += as_decimal(total_price)

            row = [
                str(index),
                Paragraph(str(product_name), cell_style),
                str(quantity),
                money(unit_price) if unit_price else "-",
                money(total_price) if total_price else "-",
            ]
            if internal:
                row.extend(
                    [
                        money(getattr(item, "taxed_cost", None)),
                        money(getattr(item, "sales_profit", None)),
                    ]
                )
            if opts["show_line_hints"]:
                row.append(Paragraph(line_hint(item), cell_style))
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
        table_style.extend(
            [
                ("ALIGN", (amount_cols[0], 1), (amount_cols[1], -1), "RIGHT"),
                ("RIGHTPADDING", (amount_cols[0], 1), (amount_cols[1], -1), 6),
                ("LEFTPADDING", (1, 1), (1, -1), 6),
            ]
        )
        for row_index in range(2, len(table_data), 2):
            table_style.append(
                ("BACKGROUND", (0, row_index), (-1, row_index), color_soft_bg)
            )
        if hint_col is not None:
            table_style.append(("ALIGN", (hint_col, 1), (hint_col, -1), "LEFT"))
        if internal:
            table_style.append(
                (
                    "TEXTCOLOR",
                    (-1 if not opts["show_line_hints"] else -2, 1),
                    (-1 if not opts["show_line_hints"] else -2, -1),
                    colors.HexColor("#166534"),
                )
            )
        table.setStyle(TableStyle(table_style))
        story.append(table)
        story.append(Spacer(1, 5 * mm))

        # Totals section
        quote_total = as_decimal(getattr(quotation, "total_amount", None)) or subtotal
        variance = quote_total - subtotal
        untaxed_cost = item_total(items, "untaxed_cost")
        taxed_cost = item_total(items, "taxed_cost")
        profit = item_total(items, "sales_profit")
        margin = margin_rate(profit, quote_total)

        totals_data = [
            [
                Paragraph("明细销售额", label_style),
                Paragraph(money(subtotal), normal_style),
            ],
            [
                Paragraph("报价合计", total_style),
                Paragraph(money(quote_total), total_style),
            ],
            [
                Paragraph("人民币大写", label_style),
                Paragraph(money_upper_cn(quote_total), normal_style),
            ],
        ]
        if abs(variance) >= Decimal("0.01"):
            totals_data.insert(
                1,
                [
                    Paragraph("调整差额", label_style),
                    Paragraph(money(variance), normal_style),
                ],
            )
        if internal:
            totals_data.extend(
                [
                    [
                        Paragraph("未税成本", label_style),
                        Paragraph(money(untaxed_cost), normal_style),
                    ],
                    [
                        Paragraph("含税成本", label_style),
                        Paragraph(money(taxed_cost), normal_style),
                    ],
                    [
                        Paragraph("销售毛利 / 毛利率", total_style),
                        Paragraph(f"{money(profit)} / {percent(margin)}", total_style),
                    ],
                ]
            )

        totals_table = Table(
            totals_data, colWidths=[content_width * 0.62, content_width * 0.38]
        )
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

    if opts["show_smart_summary"]:
        summary_data = [[Paragraph("智能报价摘要", heading_style)]]
        for line in smart_summary_lines(quotation, items, subtotal):
            if "内部毛利" in line and not opts["show_internal_metrics"]:
                continue
            summary_data.append([Paragraph(line, normal_style)])
        summary_table = Table(summary_data, colWidths=[content_width])
        summary_table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, -1), color_summary_bg),
                    ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#9db7d5")),
                    ("LEFTPADDING", (0, 0), (-1, -1), 8),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                    ("TOPPADDING", (0, 0), (-1, -1), 6),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                ]
            )
        )
        story.append(summary_table)
        story.append(Spacer(1, 6 * mm))

    # Payment terms / Notes
    if opts["show_terms"]:
        terms_lines = opts["terms"].splitlines() if opts["terms"] else default_terms()
        terms_data = [[Paragraph("商务条款与说明", heading_style)]]
        for line in terms_lines:
            if line.strip():
                terms_data.append([Paragraph(line.strip(), small_style)])
        terms_table = Table(terms_data, colWidths=[content_width])
        terms_table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), color_soft_bg),
                    ("BOX", (0, 0), (-1, -1), 0.5, color_border),
                    ("INNERGRID", (0, 0), (-1, -1), 0.25, color_grid),
                    ("LEFTPADDING", (0, 0), (-1, -1), 8),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                    ("TOPPADDING", (0, 0), (-1, -1), 6),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                ]
            )
        )
        story.append(terms_table)

    if opts["show_notes"] and quotation.notes:
        story.append(Spacer(1, 5 * mm))
        notes_table = Table(
            [
                [Paragraph("报价备注", heading_style)],
                [Paragraph(str(quotation.notes), small_style)],
            ],
            colWidths=[content_width],
        )
        notes_table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), color_soft_bg),
                    ("BOX", (0, 0), (-1, -1), 0.5, color_border),
                    ("INNERGRID", (0, 0), (-1, -1), 0.25, color_grid),
                    ("LEFTPADDING", (0, 0), (-1, -1), 8),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                    ("TOPPADDING", (0, 0), (-1, -1), 6),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                ]
            )
        )
        story.append(notes_table)

    story.append(Spacer(1, 8 * mm))
    if opts["show_signature"]:
        signature_table = Table(
            [
                [
                    Paragraph("报价经办", label_style),
                    Paragraph(opts["prepared_by"] or "____________", normal_style),
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
            colWidths=[
                content_width * 0.14,
                content_width * 0.36,
                content_width * 0.17,
                content_width * 0.33,
            ],
        )
        signature_table.setStyle(
            TableStyle(
                [
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
                ]
            )
        )
        story.append(signature_table)
        story.append(Spacer(1, 5 * mm))

    story.append(
        Paragraph(
            "以上报价由系统根据客户、产品、数量、状态及有效期生成智能摘要，正式交易以双方确认的订单/合同为准。",
            small_style,
        )
    )

    # Build PDF
    doc.build(story, onFirstPage=draw_footer, onLaterPages=draw_footer)
    pdf_bytes = buffer.getvalue()
    buffer.close()

    return pdf_bytes


__all__ = [
    "generate_basic_pdf",
    "generate_quotation_pdf",
]
