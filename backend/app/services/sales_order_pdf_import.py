"""PDF import helpers for customer sales orders."""

import io
import re
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from typing import Any

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.customer import Customer
from app.models.product import Product
from app.models.sales import SalesOrder
from app.services.sales_service import create_sales_order


def extract_pdf_text(content: bytes) -> str:
    """Extract searchable text from a PDF. Scanned PDFs may still need OCR."""
    try:
        from PyPDF2 import PdfReader

        reader = PdfReader(io.BytesIO(content))
        chunks = [page.extract_text() or "" for page in reader.pages]
        return "\n".join(chunk for chunk in chunks if chunk).strip()
    except Exception:
        return ""


def _clean_text(value: str | None) -> str:
    return re.sub(r"\s+", " ", value or "").strip(" \t\r\n:：")


def _to_float(value: Any, default: float = 0) -> float:
    try:
        if value is None:
            return default
        return float(
            Decimal(
                str(value).replace(",", "").replace("¥", "").replace("￥", "").strip()
            )
        )
    except (InvalidOperation, ValueError):
        return default


def _parse_date(value: str | None) -> datetime | None:
    if not value:
        return None
    raw = value.strip()
    patterns = [
        "%Y-%m-%d",
        "%Y/%m/%d",
        "%Y.%m.%d",
        "%Y年%m月%d日",
        "%d/%m/%Y",
        "%m/%d/%Y",
    ]
    for pattern in patterns:
        try:
            return datetime.strptime(raw, pattern).replace(tzinfo=timezone.utc)
        except ValueError:
            continue
    return None


def _field(patterns: list[str], text: str) -> str | None:
    for pattern in patterns:
        match = re.search(pattern, text, flags=re.IGNORECASE | re.MULTILINE)
        if match:
            value = _clean_text(match.group(1))
            if value:
                return value[:255]
    return None


def _is_number_token(token: str) -> bool:
    value = token.strip().strip(",，")
    return bool(re.fullmatch(r"[¥￥]?\d[\d,]*(?:\.\d+)?", value))


def _line_item_from_tokens(tokens: list[str]) -> dict[str, Any] | None:
    number_indices = [
        idx for idx, token in enumerate(tokens) if _is_number_token(token)
    ]
    if len(number_indices) < 2:
        return None

    total_idx = number_indices[-1]
    unit_idx = number_indices[-2]
    qty_idx = number_indices[-3] if len(number_indices) >= 3 else number_indices[-2]

    quantity = _to_float(tokens[qty_idx], 1)
    unit_price = _to_float(tokens[unit_idx], 0)
    total_price = _to_float(tokens[total_idx], 0)
    if qty_idx == unit_idx and quantity:
        unit_price = total_price / quantity

    if quantity <= 0 or total_price < 0:
        return None

    name_tokens = tokens[:qty_idx]
    if name_tokens and re.fullmatch(
        r"\d+|[A-Z]\d+", name_tokens[0], flags=re.IGNORECASE
    ):
        name_tokens = name_tokens[1:]
    product_name = _clean_text(" ".join(name_tokens))
    if not product_name or len(product_name) < 2:
        return None

    if unit_price and abs(quantity * unit_price - total_price) > max(
        1, total_price * 0.05
    ):
        return None

    return {
        "product_name": product_name[:255],
        "quantity": max(1, int(round(quantity))),
        "unit_price": round(unit_price, 6),
        "total_price": round(total_price, 6),
    }


def _parse_items(text: str) -> list[dict[str, Any]]:
    skip_words = (
        "合计",
        "总计",
        "小计",
        "税额",
        "金额合计",
        "total",
        "subtotal",
        "amount",
        "订单号",
        "客户",
        "买方",
        "卖方",
        "日期",
        "电话",
        "地址",
        "签字",
        "signature",
        "product",
        "description",
        "quantity",
        "unit price",
    )
    items: list[dict[str, Any]] = []
    seen: set[tuple[str, float, float, float]] = set()
    for raw_line in text.replace("|", " ").splitlines():
        line = _clean_text(raw_line)
        if not line:
            continue
        lower = line.lower()
        if any(word in lower for word in skip_words):
            continue
        tokens = [token for token in re.split(r"\s+", line) if token]
        item = _line_item_from_tokens(tokens)
        if not item:
            continue
        key = (
            item["product_name"].lower(),
            float(item["quantity"]),
            float(item["unit_price"]),
            float(item["total_price"]),
        )
        if key not in seen:
            seen.add(key)
            items.append(item)
    return items


def parse_sales_order_text(text: str) -> dict[str, Any]:
    normalized = text.replace("\u00a0", " ")
    order_no = _field(
        [
            r"(?:销售订单号|订单编号|订单号|客户PO号|采购订单号|PO\s*No\.?|Order\s*No\.?)\s*[:：#]?\s*([^\n\r]+)",
        ],
        normalized,
    )
    customer_name = _field(
        [
            r"(?:客户公司|客户名称|客户|买方|采购方|收货单位|Customer|Buyer)\s*[:：]?\s*([^\n\r]+)",
        ],
        normalized,
    )
    order_date_raw = _field(
        [
            r"(?:下单日期|订单日期|日期|Order\s*Date)\s*[:：]?\s*([0-9]{4}[-/.年][0-9]{1,2}[-/.月][0-9]{1,2}日?)",
        ],
        normalized,
    )
    delivery_date_raw = _field(
        [
            r"(?:交货日期|交付日期|预计交货|Delivery\s*Date)\s*[:：]?\s*([0-9]{4}[-/.年][0-9]{1,2}[-/.月][0-9]{1,2}日?)",
        ],
        normalized,
    )
    total_raw = _field(
        [
            r"(?:订单总额|总金额|金额合计|Total\s*Amount|Grand\s*Total)\s*[:：]?\s*[¥￥]?\s*([0-9][0-9,]*(?:\.\d+)?)",
        ],
        normalized,
    )
    items = _parse_items(normalized)
    total_amount = _to_float(total_raw, 0) or sum(
        _to_float(item.get("total_price")) for item in items
    )

    return {
        "order_no": order_no,
        "customer_name": customer_name,
        "order_date": _parse_date(order_date_raw),
        "delivery_date": _parse_date(delivery_date_raw),
        "total_amount": total_amount,
        "items": items,
    }


async def _find_customer(
    db: AsyncSession, customer_name: str | None, customer_id: int | None
) -> Customer | None:
    if customer_id:
        result = await db.execute(
            select(Customer).where(
                Customer.id == customer_id, Customer.deleted_at.is_(None)
            )
        )
        return result.scalar_one_or_none()
    if not customer_name:
        return None

    name = customer_name.strip()
    result = await db.execute(
        select(Customer)
        .where(
            Customer.deleted_at.is_(None),
            or_(
                Customer.name == name,
                Customer.short_name == name,
                Customer.code == name,
            ),
        )
        .limit(1)
    )
    customer = result.scalar_one_or_none()
    if customer:
        return customer

    result = await db.execute(
        select(Customer)
        .where(
            Customer.deleted_at.is_(None),
            or_(
                Customer.name.ilike(f"%{name}%"),
                Customer.short_name.ilike(f"%{name}%"),
                Customer.code.ilike(f"%{name}%"),
            ),
        )
        .order_by(Customer.id)
        .limit(1)
    )
    return result.scalar_one_or_none()


async def _match_product(db: AsyncSession, product_name: str | None) -> Product | None:
    if not product_name:
        return None
    name = product_name.strip()
    result = await db.execute(
        select(Product)
        .where(
            Product.deleted_at.is_(None),
            or_(
                Product.sku == name,
                Product.name == name,
                Product.name.ilike(f"%{name}%"),
            ),
        )
        .order_by(Product.id)
        .limit(1)
    )
    return result.scalar_one_or_none()


async def import_sales_order_from_pdf(
    db: AsyncSession,
    content: bytes,
    *,
    filename: str | None = None,
    customer_id: int | None = None,
) -> dict[str, Any]:
    raw_text = extract_pdf_text(content)
    if not raw_text or len(raw_text) < 10:
        raise ValueError("无法从 PDF 中提取订单文字，请确认文件不是扫描件或图片 PDF")

    parsed = parse_sales_order_text(raw_text)
    customer = await _find_customer(db, parsed.get("customer_name"), customer_id)
    if not customer:
        name = parsed.get("customer_name") or "未识别"
        raise ValueError(f"未找到匹配客户: {name}，请先选择客户或维护客户档案")

    items: list[dict[str, Any]] = []
    product_matches: list[dict[str, Any]] = []
    for item in parsed["items"]:
        next_item = dict(item)
        product = await _match_product(db, next_item.get("product_name"))
        if product:
            next_item["product_id"] = product.id
            next_item["product_name"] = product.name
            product_matches.append(
                {
                    "source": item.get("product_name"),
                    "product_id": product.id,
                    "product_name": product.name,
                }
            )
        else:
            product_matches.append(
                {
                    "source": item.get("product_name"),
                    "product_id": None,
                    "product_name": None,
                }
            )
        items.append(next_item)

    if not items:
        raise ValueError("未识别到订单明细，请确认 PDF 中包含产品、数量、单价、金额列")

    notes = f"PDF导入：{filename or '未命名文件'}"
    order_data = {
        "order_no": parsed.get("order_no"),
        "customer_id": customer.id,
        "total_amount": parsed.get("total_amount") or 0,
        "status": "pending",
        "order_date": parsed.get("order_date") or datetime.now(timezone.utc),
        "delivery_date": parsed.get("delivery_date"),
        "notes": notes,
    }
    order: SalesOrder = await create_sales_order(db, order_data, items)

    return {
        "id": order.id,
        "order_no": order.order_no,
        "customer_id": customer.id,
        "parsed": {
            "order_no": parsed.get("order_no"),
            "customer_name": parsed.get("customer_name"),
            "item_count": len(items),
            "total_amount": float(order.total_amount or 0),
            "order_date": order.order_date.isoformat() if order.order_date else None,
            "delivery_date": order.delivery_date.isoformat()
            if order.delivery_date
            else None,
        },
        "matched": {
            "customer_name": customer.name,
            "products": product_matches,
        },
        "raw_text_preview": raw_text[:500],
    }
