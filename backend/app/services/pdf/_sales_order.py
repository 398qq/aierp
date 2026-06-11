"""Sales-order PDF generation.

Mirrors the quotation layout: a simple ``generate_basic_order_pdf`` and
a full ``generate_sales_order_pdf`` that pulls in risk text, AI
insights, and the row table. Both render to ``bytes``.
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
    money,
    money_upper_cn,
    order_risk_text,
    order_summary_lines,
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


def generate_basic_order_pdf(
    order: Any, options: dict[str, Any] | None = None
) -> bytes:
    """Generate a dependency-free fallback sales order PDF."""
    opts = pdf_options(options)
    customer = getattr(order, "customer", None)
    if not (options or {}).get("company_name") and getattr(customer, "name", None):
        opts["company_name"] = str(getattr(customer, "name"))
    items = getattr(order, "items", None) or []
    subtotal: Decimal = sum(
        (as_decimal(getattr(item, "total_price", None)) for item in items), Decimal("0")
    )
    risk_label, next_action = order_risk_text(order, len(items), subtotal)
    order_total = as_decimal(getattr(order, "total_amount", None)) or subtotal

    lines = [
        pdf_text(opts["company_name"]).upper(),
        pdf_text(opts["document_title"]).upper(),
        f"Order No: {getattr(order, 'order_no', None) or getattr(order, 'id', '-')}",
        f"Customer: {getattr(customer, 'name', None) or '-'}",
        f"Status: {status_label(getattr(order, 'status', None))}",
        f"Order Date: {date_text(getattr(order, 'order_date', None))}",
        f"Delivery Date: {date_text(getattr(order, 'delivery_date', None))}",
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
    lines.extend(["", f"Order Total: {money(order_total)}"])
    if opts["show_smart_summary"]:
        lines.extend([f"Order Status: {risk_label}", f"Next Action: {next_action}", ""])
    if opts["show_terms"]:
        terms = opts["terms"].splitlines() if opts["terms"] else default_terms()
        lines.extend(["Terms:", *terms])

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


def generate_sales_order_pdf(
    order: Any, options: dict[str, Any] | None = None
) -> bytes:
    """Generate a formal PDF for a sales order."""
    raw_options = options or {}
    opts = pdf_options(
        {
            **raw_options,
            "document_title": raw_options.get("document_title")
            or "正式销售订单 / SALES ORDER",
        }
    )
    if not REPORTLAB_AVAILABLE:
        logger.warning(
            "ReportLab is not installed; using basic sales order PDF fallback"
        )
        return generate_basic_order_pdf(order, opts)

    buffer = io.BytesIO()
    compact = opts["template"] == "compact"
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
        if opts["contact_phone"]:
            footer += f" | 联系电话：{opts['contact_phone']}"
        canvas.drawString(document.leftMargin, 10 * mm, footer)
        canvas.drawRightString(
            A4[0] - document.rightMargin, 10 * mm, f"第 {document.page} 页"
        )
        canvas.restoreState()

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "OrderTitle",
        parent=styles["Heading1"],
        fontName=_CHINESE_FONT,
        fontSize=18,
        alignment=1,
        textColor=colors.white,
    )
    heading_style = ParagraphStyle(
        "OrderHeading",
        parent=styles["Heading2"],
        fontName=_CHINESE_FONT,
        fontSize=12,
        textColor=colors.HexColor("#111827"),
        spaceAfter=5 * mm,
    )
    normal_style = ParagraphStyle(
        "OrderNormal",
        parent=styles["Normal"],
        fontName=_CHINESE_FONT,
        fontSize=10,
        leading=14,
        spaceAfter=3 * mm,
    )
    small_style = ParagraphStyle(
        "OrderSmall",
        parent=styles["Normal"],
        fontName=_CHINESE_FONT,
        fontSize=9,
        leading=12,
        spaceAfter=2 * mm,
    )
    label_style = ParagraphStyle(
        "OrderLabel", parent=small_style, textColor=colors.HexColor("#64748b")
    )
    cell_style = ParagraphStyle("OrderCell", parent=small_style, wordWrap="CJK")
    white_style = ParagraphStyle(
        "OrderWhite", parent=small_style, textColor=colors.white, leading=13
    )
    total_style = ParagraphStyle(
        "OrderTotal",
        parent=normal_style,
        fontSize=12,
        leading=15,
        textColor=colors.HexColor("#111827"),
    )

    story = []
    customer = getattr(order, "customer", None)
    customer_name = getattr(customer, "name", None) or "-"
    if not raw_options.get("company_name") and customer_name != "-":
        opts["company_name"] = str(customer_name)
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
    order_date = date_text(getattr(order, "order_date", None))
    delivery_date = date_text(getattr(order, "delivery_date", None))

    header_table = Table(
        [
            [
                Paragraph(opts["company_name"], title_style),
                Paragraph(f"订单号<br/>{order_no}", white_style),
            ],
            [
                Paragraph(opts["document_title"], white_style),
                Paragraph(
                    f"制单日期<br/>{date_text(datetime.now(timezone.utc))}", white_style
                ),
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

    info_rows = [
        [
            Paragraph("销售订单号", label_style),
            Paragraph(str(order_no), normal_style),
            Paragraph("订单状态", label_style),
            Paragraph(status_text, normal_style),
        ],
        [
            Paragraph("下单日期", label_style),
            Paragraph(order_date, normal_style),
            Paragraph("预计交付", label_style),
            Paragraph(delivery_date, normal_style),
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
    if getattr(order, "quotation_id", None):
        info_rows.append(
            [
                Paragraph("来源报价", label_style),
                Paragraph(f"#{order.quotation_id}", normal_style),
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

    items = getattr(order, "items", None) or []
    subtotal = Decimal("0")
    if items:
        story.append(Paragraph("订单明细", heading_style))
        show_hints = bool(opts["show_line_hints"])
        table_data = [
            ["序号", "产品 / 型号", "数量", "销售单价", "订单金额"]
            + (["交付提示"] if show_hints else [])
        ]
        col_widths = [
            content_width * 0.07,
            content_width * (0.45 if show_hints else 0.52),
            content_width * 0.10,
            content_width * 0.15,
            content_width * 0.16,
        ]
        if show_hints:
            col_widths.append(content_width * 0.07)
        for index, item in enumerate(items, start=1):
            quantity = getattr(item, "quantity", 0) or 0
            unit_price = getattr(item, "unit_price", None) or 0
            total_price = getattr(item, "total_price", None) or (quantity * unit_price)
            subtotal += as_decimal(total_price)
            row = [
                str(index),
                Paragraph(str(getattr(item, "product_name", None) or "-"), cell_style),
                str(quantity),
                money(unit_price) if unit_price else "-",
                money(total_price) if total_price else "-",
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
            table_style.append(
                ("BACKGROUND", (0, row_index), (-1, row_index), color_soft_bg)
            )
        table.setStyle(TableStyle(table_style))
        story.append(table)
        story.append(Spacer(1, 5 * mm))

        order_total = as_decimal(getattr(order, "total_amount", None)) or subtotal
        totals_table = Table(
            [
                [
                    Paragraph("明细销售额", label_style),
                    Paragraph(money(subtotal), normal_style),
                ],
                [
                    Paragraph("订单合计", total_style),
                    Paragraph(money(order_total), total_style),
                ],
                [
                    Paragraph("人民币大写", label_style),
                    Paragraph(money_upper_cn(order_total), normal_style),
                ],
            ],
            colWidths=[content_width * 0.62, content_width * 0.38],
        )
        totals_table.setStyle(
            TableStyle(
                [
                    ("ALIGN", (0, 0), (-1, -1), "RIGHT"),
                    ("FONTNAME", (0, 0), (-1, -1), _CHINESE_FONT),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                    ("LINEABOVE", (0, -2), (-1, -2), 0.5, color_primary),
                ]
            )
        )
        story.append(totals_table)
    else:
        story.append(Paragraph("无订单明细", normal_style))

    story.append(Spacer(1, 6 * mm))
    if opts["show_smart_summary"]:
        summary_data = [[Paragraph("智能订单摘要", heading_style)]]
        for line in order_summary_lines(order, items, subtotal):
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

    if opts["show_terms"]:
        terms_lines = (
            opts["terms"].splitlines()
            if opts["terms"]
            else [
                "1. 本订单以双方确认的产品、数量、单价、交期及付款条件为准。",
                "2. 交付前请再次确认库存、包装、收货地址及客户验收要求。",
                "3. 如发生交期、价格或物料变更，应以双方确认的新订单或补充协议为准。",
            ]
        )
        terms_table = Table(
            [
                [Paragraph("交付条款与说明", heading_style)],
                *[
                    [Paragraph(line.strip(), small_style)]
                    for line in terms_lines
                    if line.strip()
                ],
            ],
            colWidths=[content_width],
        )
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

    if opts["show_notes"] and getattr(order, "notes", None):
        story.append(Spacer(1, 5 * mm))
        notes_table = Table(
            [
                [Paragraph("订单备注", heading_style)],
                [Paragraph(str(order.notes), small_style)],
            ],
            colWidths=[content_width],
        )
        notes_table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), color_soft_bg),
                    ("BOX", (0, 0), (-1, -1), 0.5, color_border),
                    ("LEFTPADDING", (0, 0), (-1, -1), 8),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                    ("TOPPADDING", (0, 0), (-1, -1), 6),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                ]
            )
        )
        story.append(notes_table)

    if opts["show_signature"]:
        story.append(Spacer(1, 8 * mm))
        signature_table = Table(
            [
                [
                    Paragraph("制单人", label_style),
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

    doc.build(story, onFirstPage=draw_footer, onLaterPages=draw_footer)
    pdf_bytes = buffer.getvalue()
    buffer.close()
    return pdf_bytes


__all__ = [
    "generate_basic_order_pdf",
    "generate_sales_order_pdf",
]
