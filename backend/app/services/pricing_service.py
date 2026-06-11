"""AI-native pricing intelligence — supplier matching, price benchmarking, quote optimization."""

import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.product import Brand, Product, Supplier, SupplierProduct
from app.models.sales import QuotationItem, SalesOrder, SalesOrderItem

logger = logging.getLogger(__name__)


async def match_supplier_to_products(
    db: AsyncSession,
    supplier_id: int,
    catalog_text: str | None = None,
) -> list[dict]:
    """AI matches a supplier's product lines text to known products in the system."""
    supplier = (
        await db.execute(
            select(Supplier).where(
                Supplier.id == supplier_id, Supplier.deleted_at.is_(None)
            )
        )
    ).scalar_one_or_none()
    if supplier is None:
        raise ValueError("Supplier not found")

    source_text = catalog_text or supplier.product_lines or ""
    if not source_text.strip():
        return []

    # Get all products with brand info for matching
    rows = (
        await db.execute(
            select(
                Product.id,
                Product.sku,
                Product.name,
                Product.category,
                Product.package_type,
                Brand.name,
                Brand.name_cn,
            )
            .outerjoin(Brand, Product.brand_id == Brand.id)
            .where(Product.deleted_at.is_(None))
            .order_by(Product.id)
        )
    ).all()

    if not rows:
        return []

    product_list = "\n".join(
        f"ID:{r[0]} | SKU:{r[1] or '-'} | 名称:{r[2]} | 分类:{r[3] or '-'} | "
        f"封装:{r[4] or '-'} | 品牌:{r[5] or r[6] or '-'}"
        for r in rows
    )

    from app.services.ai.client import ai_client
    from app.services.ai.prompts import supplier_match_prompt

    schema = {
        "matches": [
            {
                "product_id": "integer, matched product ID from system",
                "confidence": "integer 0-100",
                "supplier_pn": "string, supplier part number from catalog",
                "cost_price": "number | null, extracted from text",
                "lead_time_days": "integer | null",
                "moq": "integer | null",
                "match_reason": "string, brief reason",
            }
        ]
    }
    result = await ai_client.chat_structured(
        [
            {
                "role": "system",
                "content": "你是一个电子元器件数据匹配专家。精确匹配供应商型号与系统产品。",
            },
            {
                "role": "user",
                "content": supplier_match_prompt(source_text, product_list[:3000]),
            },
        ],
        schema,
    )
    return result.get("matches", [])


async def get_pricing_benchmark(
    db: AsyncSession,
    product_id: int,
) -> dict:
    """Get price benchmarks for a product from historical data and supplier costs."""
    # Historical sales prices (last 6 months)
    six_months_ago = datetime.now(timezone.utc) - timedelta(days=180)
    sales_prices = (
        await db.execute(
            select(
                SalesOrderItem.unit_price,
                SalesOrderItem.quantity,
                SalesOrderItem.created_at,
            )
            .where(
                SalesOrderItem.product_id == product_id,
                SalesOrderItem.deleted_at.is_(None),
                SalesOrderItem.created_at >= six_months_ago,
            )
            .order_by(SalesOrderItem.created_at.desc())
            .limit(50)
        )
    ).all()

    # Quotation prices (active)
    quote_prices = (
        await db.execute(
            select(QuotationItem.unit_price, QuotationItem.quantity)
            .where(
                QuotationItem.product_id == product_id,
                QuotationItem.deleted_at.is_(None),
            )
            .order_by(QuotationItem.created_at.desc())
            .limit(20)
        )
    ).all()

    # Supplier costs
    supplier_costs = (
        await db.execute(
            select(
                SupplierProduct.cost_price,
                SupplierProduct.lead_time_days,
                SupplierProduct.moq,
                Supplier.name,
            )
            .join(Supplier, SupplierProduct.supplier_id == Supplier.id)
            .where(
                SupplierProduct.product_id == product_id,
                SupplierProduct.deleted_at.is_(None),
                Supplier.deleted_at.is_(None),
            )
        )
    ).all()

    def _stats(prices: list[float]) -> dict:
        if not prices:
            return {"min": None, "max": None, "avg": None, "median": None}
        sorted_p = sorted(prices)
        mid = len(sorted_p) // 2
        return {
            "min": round(sorted_p[0], 4),
            "max": round(sorted_p[-1], 4),
            "avg": round(sum(sorted_p) / len(sorted_p), 4),
            "median": round(sorted_p[mid], 4),
        }

    sales_price_list = [float(r[0]) for r in sales_prices if r[0]]
    quote_price_list = [float(r[0]) for r in quote_prices if r[0]]
    cost_list = [float(r[0]) for r in supplier_costs if r[0]]

    return {
        "product_id": product_id,
        "sales_history": {
            "count": len(sales_price_list),
            "stats": _stats(sales_price_list),
            "recent": [
                {"price": float(r[0]), "qty": r[1], "date": str(r[2])}
                for r in sales_prices[:5]
            ],
        },
        "active_quotations": {
            "count": len(quote_price_list),
            "stats": _stats(quote_price_list),
        },
        "supplier_costs": {
            "count": len(supplier_costs),
            "stats": _stats(cost_list),
            "suppliers": [
                {
                    "name": r[3],
                    "cost_price": float(r[0]) if r[0] else None,
                    "lead_time_days": r[1],
                    "moq": r[2],
                }
                for r in supplier_costs
            ],
        },
    }


async def recommend_price(
    db: AsyncSession,
    product_id: int,
    customer_id: int | None = None,
    quantity: int = 1,
    is_sample: bool = False,
) -> dict:
    """AI price recommendation combining cost data, market context, and customer profile."""
    from app.models.customer import Customer

    # Product with brand
    prod_row = (
        await db.execute(
            select(
                Product.sku, Product.name, Product.category, Brand.name, Brand.name_cn
            )
            .outerjoin(Brand, Product.brand_id == Brand.id)
            .where(Product.id == product_id, Product.deleted_at.is_(None))
        )
    ).first()
    if prod_row is None:
        raise ValueError("Product not found")

    # Supplier costs
    supplier_rows = (
        await db.execute(
            select(
                SupplierProduct.cost_price,
                SupplierProduct.lead_time_days,
                SupplierProduct.moq,
            ).where(
                SupplierProduct.product_id == product_id,
                SupplierProduct.deleted_at.is_(None),
            )
        )
    ).all()
    cost_price = min((float(r[0]) for r in supplier_rows if r[0]), default=None)
    lead_time = min((r[1] for r in supplier_rows if r[1]), default=None)
    supplier_count = len(supplier_rows)

    # Current stock
    from app.models.product import Inventory

    stock_qty = (
        await db.execute(
            select(func.coalesce(func.sum(Inventory.quantity), 0)).where(
                Inventory.product_id == product_id, Inventory.deleted_at.is_(None)
            )
        )
    ).scalar() or 0

    # Customer info
    customer_name, customer_level, customer_industry = "未知", "未知", "未知"
    if customer_id:
        cust = (
            await db.execute(
                select(Customer).where(
                    Customer.id == customer_id, Customer.deleted_at.is_(None)
                )
            )
        ).scalar_one_or_none()
        if cust:
            customer_name = cust.name
            customer_level = cust.level or "未知"
            customer_industry = cust.industry or "未知"

    # Historical prices for this product-customer combo
    historical = []
    if customer_id:
        hist_rows = (
            await db.execute(
                select(SalesOrderItem.unit_price, SalesOrderItem.quantity)
                .join(SalesOrder, SalesOrderItem.order_id == SalesOrder.id)
                .where(
                    SalesOrderItem.product_id == product_id,
                    SalesOrderItem.deleted_at.is_(None),
                    SalesOrder.customer_id == customer_id,
                    SalesOrder.deleted_at.is_(None),
                )
                .order_by(SalesOrderItem.created_at.desc())
                .limit(5)
            )
        ).all()
        historical = [f"{float(r[0])}元 (x{r[1]})" for r in hist_rows if r[0]]

    # Determine market condition
    market_condition = "正常"
    if stock_qty == 0:
        market_condition = "缺货"
    elif supplier_count == 0:
        market_condition = "供应紧张"
    elif stock_qty < quantity:
        market_condition = "库存不足"

    from app.services.ai.client import ai_client
    from app.services.ai.prompts import pricing_recommend_prompt

    context = {
        "part_number": f"{prod_row[0] or ''} {prod_row[1]}".strip(),
        "category": prod_row[2] or "未知",
        "brand": prod_row[3] or prod_row[4] or "未知",
        "cost_price": f"{cost_price}元" if cost_price else None,
        "supplier_count": supplier_count,
        "stock_qty": stock_qty,
        "lead_time_days": lead_time,
        "customer_name": customer_name,
        "customer_level": customer_level,
        "customer_industry": customer_industry,
        "quantity": quantity,
        "is_sample": is_sample,
        "historical_prices": "; ".join(historical) if historical else "无",
        "market_condition": market_condition,
    }

    schema = {
        "recommended_price": "number, suggested unit price in CNY",
        "price_range": "[min, max] as array of two numbers",
        "margin_pct": "number, estimated profit margin percentage",
        "confidence": "string: high/medium/low",
        "rationale": "string, 2-3 sentence pricing rationale",
        "negotiation_floor": "number, minimum acceptable price",
        "upsell_suggestion": "string | null, cross-sell or upsell suggestion",
    }
    result = await ai_client.chat_structured(
        [
            {
                "role": "system",
                "content": "你是一个电子元器件分销行业定价专家。基于成本、市场和客户关系给出精准定价。",
            },
            {"role": "user", "content": pricing_recommend_prompt(context)},
        ],
        schema,
    )
    result["context"] = context
    return result
