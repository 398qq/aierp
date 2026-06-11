"""Brand product performance and customer penetration analysis."""

import datetime
from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.customer import Customer
from app.models.product import Product, SupplierProduct
from app.models.sales import SalesOrder, SalesOrderItem
from app.services.ai.client import ai_client
from app.services.ai.prompts import (
    brand_product_performance_prompt,
    brand_customer_penetration_prompt,
)
from app.services.brand_intel.context import _brand_context


async def get_brand_product_performance(db: AsyncSession, brand_id: int) -> dict:
    """Rank products within a brand by sales/margin, AI labels stars vs dogs."""
    ctx = await _brand_context(db, brand_id)

    now = datetime.datetime.now(datetime.timezone.utc)
    six_months_ago = now - datetime.timedelta(days=180)

    product_ids = [
        r[0]
        for r in (
            await db.execute(
                select(Product.id).where(
                    Product.brand_id == brand_id, Product.deleted_at.is_(None)
                )
            )
        ).all()
    ]

    total_revenue_6m = 0
    active_products = 0
    total_margin_6m = 0.0
    ranking_parts = []

    if product_ids:
        rev_rows = (
            await db.execute(
                select(
                    SalesOrderItem.product_id,
                    func.sum(SalesOrderItem.total_price).label("revenue"),
                    func.sum(SalesOrderItem.quantity).label("qty"),
                )
                .select_from(SalesOrderItem)
                .join(SalesOrder, SalesOrderItem.order_id == SalesOrder.id)
                .where(
                    SalesOrderItem.product_id.in_(product_ids),
                    SalesOrder.status.in_(["confirmed", "delivered", "completed"]),
                    SalesOrder.created_at >= six_months_ago,
                    SalesOrder.deleted_at.is_(None),
                    SalesOrderItem.deleted_at.is_(None),
                )
                .group_by(SalesOrderItem.product_id)
                .order_by(text("revenue DESC"))
            )
        ).all()

        cost_rows = dict(
            (
                await db.execute(
                    select(
                        SupplierProduct.product_id, func.avg(SupplierProduct.cost_price)
                    )
                    .where(
                        SupplierProduct.product_id.in_(product_ids),
                        SupplierProduct.cost_price.isnot(None),
                        SupplierProduct.deleted_at.is_(None),
                    )
                    .group_by(SupplierProduct.product_id)
                )
            ).all()
            or []
        )

        product_names = {
            p[0]: f"{p[2] or ''} {p[1]}".strip()
            for p in (
                await db.execute(
                    select(Product.id, Product.name, Product.sku).where(
                        Product.id.in_(product_ids), Product.deleted_at.is_(None)
                    )
                )
            ).all()
        }

        for r in rev_rows:
            pid, rev, qty = r[0], float(r[1]), r[2]
            name = product_names.get(pid, f"#{pid}")
            avg_cost = float(cost_rows.get(pid, 0) or 0)
            margin = rev - avg_cost * qty
            margin_pct = round(margin / rev * 100, 1) if rev > 0 else 0
            total_revenue_6m += rev
            total_margin_6m += margin
            active_products += 1
            ranking_parts.append(
                f"产品:{name} | 近6月销售额:¥{rev:,.0f} | 数量:{qty} | "
                f"成本:¥{avg_cost:.4f} | 毛利率:{margin_pct}%"
            )

    product_ranking = "\n".join(ranking_parts) if ranking_parts else "近6月无销售"

    perf_data = {
        **ctx,
        "product_ranking": product_ranking,
        "total_products": len(product_ids),
        "active_products": active_products,
        "total_revenue_6m": total_revenue_6m,
        "total_margin_6m": total_margin_6m,
    }

    schema = {
        "star_products": [
            {
                "product_name": "string",
                "revenue": "number",
                "margin_pct": "number",
                "growth": "string",
                "recommendation": "string",
            }
        ],
        "problem_products": [
            {"product_name": "string", "issue": "string", "suggestion": "string"}
        ],
        "portfolio_assessment": "string",
        "focus_recommendations": ["string"],
        "phase_out_candidates": ["string"],
    }
    result = await ai_client.chat_structured(
        [
            {
                "role": "system",
                "content": "你是一个电子元器件产品管理专家，擅长产品组合分析和绩效评估。",
            },
            {"role": "user", "content": brand_product_performance_prompt(perf_data)},
        ],
        schema,
    )
    result["context"] = perf_data
    return result


async def get_brand_customer_penetration(db: AsyncSession, brand_id: int) -> dict:
    """Analyze which customer segments buy this brand and identify untapped markets."""
    ctx = await _brand_context(db, brand_id)

    product_ids = [
        r[0]
        for r in (
            await db.execute(
                select(Product.id).where(
                    Product.brand_id == brand_id, Product.deleted_at.is_(None)
                )
            )
        ).all()
    ]

    customer_count = 0
    industry_dist = "无数据"
    level_dist = "无数据"
    repeat_rate: float | str = "无数据"
    avg_order_value = "无数据"
    untapped = "无数据"

    if product_ids:
        cust_rows = (
            await db.execute(
                select(
                    SalesOrder.customer_id,
                    func.count(SalesOrder.id).label("order_count"),
                    func.sum(SalesOrder.total_amount).label("total"),
                )
                .select_from(SalesOrderItem)
                .join(SalesOrder, SalesOrderItem.order_id == SalesOrder.id)
                .where(
                    SalesOrderItem.product_id.in_(product_ids),
                    SalesOrder.status.in_(["confirmed", "delivered", "completed"]),
                    SalesOrder.deleted_at.is_(None),
                    SalesOrderItem.deleted_at.is_(None),
                )
                .group_by(SalesOrder.customer_id)
            )
        ).all()

        customer_count = len(cust_rows)

        if customer_count > 0:
            cust_details_list = (
                await db.execute(
                    select(Customer.id, Customer.industry, Customer.level).where(
                        Customer.id.in_([r[0] for r in cust_rows]),
                        Customer.deleted_at.is_(None),
                    )
                )
            ).all()
            cust_details = {(r[0] or 0): (r[1], r[2]) for r in cust_details_list}

            ind_counts: dict[str, int] = {}
            lvl_counts: dict[str, int] = {}
            for r in cust_rows:
                cid = r[0] or 0
                ind, lvl = cust_details.get(cid, ("未知", "未知"))
                ind = ind if ind is not None else "未知"
                lvl = lvl if lvl is not None else "未知"
                ind_counts[ind] = ind_counts.get(ind, 0) + 1
                lvl_counts[lvl] = lvl_counts.get(lvl, 0) + 1

            industry_dist = ", ".join(
                f"{k}({v})" for k, v in sorted(ind_counts.items(), key=lambda x: -x[1])
            )
            level_dist = ", ".join(
                f"{k}({v})" for k, v in sorted(lvl_counts.items(), key=lambda x: -x[1])
            )

            repeat_customers = sum(1 for r in cust_rows if r[1] and r[1] >= 2)
            repeat_rate = (
                round(repeat_customers / customer_count * 100, 1)
                if customer_count > 0
                else 0
            )

            total_rev = sum(float(r[2]) for r in cust_rows if r[2])
            total_orders = sum(r[1] for r in cust_rows if r[1])
            avg_order_value = (
                f"¥{total_rev / total_orders:,.0f}" if total_orders > 0 else "0"
            )

            all_custs = set(
                (
                    await db.execute(
                        select(Customer.id)
                        .where(Customer.deleted_at.is_(None))
                        .limit(100)
                    )
                )
                .scalars()
                .all()
            )
            current_custs = set(r[0] for r in cust_rows)
            untapped_custs = all_custs - current_custs

            if untapped_custs:
                untapped_info = (
                    await db.execute(
                        select(
                            Customer.id,
                            Customer.name,
                            Customer.industry,
                            Customer.level,
                        )
                        .where(
                            Customer.id.in_(list(untapped_custs)),
                            Customer.deleted_at.is_(None),
                        )
                        .limit(10)
                    )
                ).all()
                untapped = (
                    "\n".join(
                        f"- {r[1]} | 行业:{r[2] or '未知'} | 等级:{r[3] or '未知'}"
                        for r in untapped_info
                    )
                    if untapped_info
                    else "无明确未开发机会"
                )
            else:
                untapped = "已全面覆盖"

    pen_data = {
        **ctx,
        "customer_count": customer_count,
        "industry_distribution": industry_dist,
        "level_distribution": level_dist,
        "repeat_rate": repeat_rate,
        "avg_order_value": avg_order_value,
        "untapped_opportunities": untapped,
    }

    schema = {
        "penetration_score": "integer 0-100",
        "penetration_assessment": "string",
        "key_industries": [
            {
                "industry": "string",
                "customer_count": "integer",
                "contribution_pct": "number",
                "assessment": "string",
            }
        ],
        "untapped_industries": [
            {
                "industry": "string",
                "potential_customers": "integer",
                "strategy": "string",
            }
        ],
        "retention_strategy": ["string"],
        "expansion_strategy": ["string"],
    }
    result = await ai_client.chat_structured(
        [
            {
                "role": "system",
                "content": "你是一个电子元器件市场分析专家，擅长客户渗透率分析和市场开发策略。",
            },
            {"role": "user", "content": brand_customer_penetration_prompt(pen_data)},
        ],
        schema,
    )
    result["context"] = pen_data
    return result
