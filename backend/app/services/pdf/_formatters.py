"""Formatters and amount helpers for PDF generation.

Decimal-safe money/date helpers, status labels, risk phrasing,
margin math, and a couple of smart-summary line generators shared
between the quotation and sales-order PDF builders.
"""
from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal, ROUND_HALF_UP
from typing import Any

def as_decimal(value: Any) -> Decimal:
    if value is None:
        return Decimal("0")
    if isinstance(value, Decimal):
        return value
    try:
        return Decimal(str(value))
    except Exception:
        return Decimal("0")


def money(value: Any) -> str:
    return f"¥{float(as_decimal(value)):,.2f}"


def money_upper_cn(value: Any) -> str:
    amount = as_decimal(value).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    if amount < 0:
        return "负" + money_upper_cn(abs(amount))
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
        parts: list[str] = []
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


def date_text(value: Any) -> str:
    if not value:
        return "-"
    if hasattr(value, "strftime"):
        return value.strftime("%Y-%m-%d")
    return str(value)[:10]


def days_until(value: Any) -> int | None:
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


def status_label(status: str | None) -> str:
    return {
        "draft": "草稿",
        "sent": "已发送",
        "won": "已成交",
        "lost": "已丢失",
    }.get(status or "", status or "-")


def quote_risk_text(quotation: Any, item_count: int, subtotal: Decimal) -> tuple[str, str]:
    days = days_until(getattr(quotation, "valid_until", None))
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


def order_risk_text(order: Any, item_count: int, subtotal: Decimal) -> tuple[str, str]:
    days = days_until(getattr(order, "delivery_date", None))
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


def line_hint(item: Any) -> str:
    quantity = int(getattr(item, "quantity", 0) or 0)
    unit_price = as_decimal(getattr(item, "unit_price", None))
    total_price = as_decimal(getattr(item, "total_price", None))
    sales_profit = as_decimal(getattr(item, "sales_profit", None))
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


def item_total(items: list[Any], field: str) -> Decimal:
    return sum((as_decimal(getattr(item, field, None)) for item in items), Decimal("0"))


def margin_rate(profit: Decimal, amount: Decimal) -> Decimal:
    if amount <= 0:
        return Decimal("0")
    return (profit / amount) * Decimal("100")


def percent(value: Decimal) -> str:
    return f"{float(value):.2f}%"


def smart_summary_lines(quotation: Any, items: list[Any], subtotal: Decimal) -> list[str]:
    quote_total = as_decimal(getattr(quotation, "total_amount", None)) or subtotal
    profit = item_total(items, "sales_profit")
    taxed_cost = item_total(items, "taxed_cost")
    margin = margin_rate(profit, quote_total)
    days = days_until(getattr(quotation, "valid_until", None))
    risk_label, next_action = quote_risk_text(quotation, len(items), subtotal)
    missing_price = sum(1 for item in items if as_decimal(getattr(item, "unit_price", None)) <= 0)
    negative_profit = sum(1 for item in items if as_decimal(getattr(item, "sales_profit", None)) < 0)

    lines = [
        f"报价健康：{risk_label}；产品行 {len(items)} 项，总数量 {sum(int(getattr(item, 'quantity', 0) or 0) for item in items)}。",
        f"金额摘要：明细金额 {money(subtotal)}，报价合计 {money(quote_total)}。",
    ]
    if taxed_cost > 0 or profit != 0:
        lines.append(f"内部毛利：含税成本 {money(taxed_cost)}，销售毛利 {money(profit)}，综合毛利率 {percent(margin)}。")
    if days is not None:
        lines.append(f"有效期判断：距到期 {days} 天；过期或临期报价建议重新核价。")
    if missing_price or negative_profit:
        lines.append(f"复核重点：{missing_price} 行缺少销售单价，{negative_profit} 行为负毛利。")
    lines.append(f"建议动作：{next_action}")
    return lines


def order_summary_lines(order: Any, items: list[Any], subtotal: Decimal) -> list[str]:
    quote_total = as_decimal(getattr(order, "total_amount", None)) or subtotal
    days = days_until(getattr(order, "delivery_date", None))
    risk_label, next_action = order_risk_text(order, len(items), subtotal)
    total_quantity = sum(int(getattr(item, "quantity", 0) or 0) for item in items)
    missing_price = sum(1 for item in items if as_decimal(getattr(item, "unit_price", None)) <= 0)
    lines = [
        f"订单状态：{risk_label}；产品行 {len(items)} 项，总数量 {total_quantity}。",
        f"金额摘要：明细金额 {money(subtotal)}，订单合计 {money(quote_total)}。",
    ]
    if days is not None:
        lines.append(f"交付计划：距预计交付 {days} 天；逾期或临近交付订单需优先跟进。")
    if missing_price:
        lines.append(f"复核重点：{missing_price} 行缺少销售单价。")
    lines.append(f"建议动作：{next_action}")
    return lines



__all__ = [
    "as_decimal",
    "money",
    "money_upper_cn",
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
]
