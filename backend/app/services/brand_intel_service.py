"""Brand intelligence — AI-powered brand profile, portfolio analysis, comparison, import, health, risk, supplier matrix, recommendation."""

import datetime
import logging
from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.customer import Customer
from app.models.product import Brand, Inventory, Product, Supplier, SupplierProduct
from app.models.sales import SalesOrder, SalesOrderItem

logger = logging.getLogger(__name__)


async def _brand_context(db: AsyncSession, brand_id: int) -> dict:
    """Collect all context data about a brand."""
    brand = (await db.execute(
        select(Brand).where(Brand.id == brand_id, Brand.deleted_at.is_(None))
    )).scalar_one_or_none()
    if brand is None:
        raise ValueError("Brand not found")

    # Product stats
    products = (await db.execute(
        select(Product.id, Product.sku, Product.name, Product.category,
               Product.package_type, Product.specs)
        .where(Product.brand_id == brand_id, Product.deleted_at.is_(None))
    )).all()

    product_count = len(products)

    # Category distribution
    cat_counts: dict[str, int] = {}
    pkg_counts: dict[str, int] = {}
    for p in products:
        cat = p[3] if p[3] is not None else "未分类"
        pkg = p[4] if p[4] is not None else "未知"
        cat_counts[cat] = cat_counts.get(cat, 0) + 1
        pkg_counts[pkg] = pkg_counts.get(pkg, 0) + 1

    category_dist = ", ".join(f"{k}({v})" for k, v in sorted(cat_counts.items(), key=lambda x: -x[1])[:10])
    package_dist = ", ".join(f"{k}({v})" for k, v in sorted(pkg_counts.items(), key=lambda x: -x[1])[:8])

    # Sample products
    sample = ", ".join(
        f"{p[2] if p[2] is not None else p[1] if p[1] is not None else '#'+str(p[0])}" for p in products[:5]
    )

    # Supplier count
    supplier_ids_subq = select(SupplierProduct.supplier_id).where(
        SupplierProduct.product_id.in_([p[0] for p in products]),
        SupplierProduct.deleted_at.is_(None),
    ).distinct()
    supplier_count = (await db.execute(
        select(func.count()).select_from(supplier_ids_subq.subquery())
    )).scalar() or 0

    # Price range from supplier costs
    price_rows = (await db.execute(
        select(SupplierProduct.cost_price).where(
            SupplierProduct.product_id.in_([p[0] for p in products]),
            SupplierProduct.deleted_at.is_(None),
            SupplierProduct.cost_price.isnot(None),
        )
    )).all()
    prices = [float(r[0]) for r in price_rows if r[0]]
    price_range = f"¥{min(prices):.4f}~¥{max(prices):.4f}" if prices else "无数据"

    return {
        "id": brand.id, "name": brand.name, "name_cn": brand.name_cn,
        "category": brand.category or "未知", "website": brand.website or "未知",
        "notes": brand.notes or "",
        "product_count": product_count,
        "category_distribution": category_dist,
        "package_distribution": package_dist,
        "sample_products": sample,
        "supplier_count": supplier_count,
        "price_range": price_range,
    }


async def generate_brand_profile(db: AsyncSession, brand_id: int) -> dict:
    """AI-generated brand intelligence card."""
    ctx = await _brand_context(db, brand_id)

    from app.services.ai.client import ai_client
    from app.services.ai.prompts import brand_profile_prompt

    schema = {
        "market_position": "string",
        "brand_strength_score": "integer 0-100",
        "technology_advantages": ["string"],
        "target_markets": ["string"],
        "competitive_advantages": ["string"],
        "typical_applications": ["string"],
        "key_competitors": ["string"],
        "procurement_difficulty": "string",
        "price_positioning": "string",
        "recommendation": "string",
    }
    result = await ai_client.chat_structured(
        [{"role": "system", "content": "你是一个电子元器件行业品牌分析专家，精通全球元器件品牌格局、市场定位和供应链分析。"},
         {"role": "user", "content": brand_profile_prompt(ctx)}],
        schema,
    )
    result["context"] = ctx
    return result


async def import_brand_from_text(db: AsyncSession, text: str, auto_create: bool = False) -> dict:
    """AI extracts structured brand info from free text."""
    from app.services.ai.client import ai_client
    from app.services.ai.prompts import brand_import_prompt

    schema = {
        "name": "string: brand English name",
        "name_cn": "string | null",
        "category": "string: main product category",
        "website": "string | null",
        "description": "string: 1-2 sentence intro",
        "product_lines": "string: main product lines",
    }
    result = await ai_client.chat_structured(
        [{"role": "system", "content": "你是一个电子元器件数据专家，精确提取品牌信息。"},
         {"role": "user", "content": brand_import_prompt(text)}],
        schema,
    )

    if auto_create and result.get("name"):
        existing = (await db.execute(
            select(Brand).where(Brand.name == result["name"], Brand.deleted_at.is_(None))
        )).scalar_one_or_none()
        if not existing:
            brand = Brand(
                name=result["name"],
                name_cn=result.get("name_cn"),
                category=result.get("category"),
                website=result.get("website"),
                notes=result.get("description"),
            )
            db.add(brand)
            await db.flush()
            result["created_id"] = brand.id

    return result


async def analyze_brand_portfolio(db: AsyncSession, brand_id: int) -> dict:
    """AI analysis of brand product portfolio."""
    ctx = await _brand_context(db, brand_id)

    from app.services.ai.client import ai_client
    from app.services.ai.prompts import brand_portfolio_prompt

    schema = {
        "portfolio_strength": "string: 完整/较全/聚焦/单一",
        "category_analysis": [
            {"category": "string", "count": "integer", "pct": "number", "assessment": "string"}
        ],
        "growth_areas": ["string"],
        "gap_analysis": ["string"],
        "cross_sell_opportunities": ["string"],
        "inventory_health": "string",
    }
    result = await ai_client.chat_structured(
        [{"role": "system", "content": "你是一个电子元器件产品线管理专家，擅长产品组合分析和市场策略。"},
         {"role": "user", "content": brand_portfolio_prompt(ctx)}],
        schema,
    )
    result["context"] = ctx
    return result


async def compare_brands(db: AsyncSession, brand_id_a: int, brand_id_b: int) -> dict:
    """AI-powered brand comparison."""
    ctx_a = await _brand_context(db, brand_id_a)
    ctx_b = await _brand_context(db, brand_id_b)

    # Overlap analysis
    prods_a = (await db.execute(
        select(Product.id, Product.category).where(
            Product.brand_id == brand_id_a, Product.deleted_at.is_(None)
        )
    )).all()
    prods_b = (await db.execute(
        select(Product.id, Product.category).where(
            Product.brand_id == brand_id_b, Product.deleted_at.is_(None)
        )
    )).all()

    cats_a = set(p[1] for p in prods_a if p[1])
    cats_b = set(p[1] for p in prods_b if p[1])
    shared_cats = ", ".join(cats_a & cats_b) if cats_a & cats_b else "无"

    overlap = {
        "shared_categories": shared_cats,
        "overlapping_products": 0,  # pgvector could find similar products across brands
    }

    from app.services.ai.client import ai_client
    from app.services.ai.prompts import brand_compare_prompt

    schema = {
        "comparison_summary": "string",
        "dimension_scores": [
            {"dimension": "string", "a_score": "integer 0-10", "b_score": "integer 0-10", "note": "string"}
        ],
        "switching_feasibility": "string: 容易/中等/困难",
        "switching_notes": ["string"],
        "recommended_strategy": "string: 以A为主/以B为主/双源/视产品而定",
    }
    result = await ai_client.chat_structured(
        [{"role": "system", "content": "你是一个电子元器件供应链策略专家，擅长品牌对比和替代分析。"},
         {"role": "user", "content": brand_compare_prompt(ctx_a, ctx_b, overlap)}],
        schema,
    )
    result["brand_a"] = ctx_a
    result["brand_b"] = ctx_b
    result["overlap"] = overlap
    return result


async def find_similar_brands(db: AsyncSession, brand_id: int, top_k: int = 5) -> list[dict]:
    """Find similar brands based on product category overlap."""
    target_cats = (await db.execute(
        select(func.distinct(Product.category)).where(
            Product.brand_id == brand_id, Product.deleted_at.is_(None),
            Product.category.isnot(None),
        )
    )).scalars().all()

    if not target_cats:
        return []

    # Find brands with overlapping categories
    similar = (await db.execute(
        select(
            Brand.id, Brand.name, Brand.name_cn, Brand.category,
            func.count(func.distinct(Product.id)).label("product_count"),
            func.count(func.distinct(Product.category)).label("shared_cats"),
        )
        .join(Product, Brand.id == Product.brand_id)
        .where(
            Brand.id != brand_id,
            Brand.deleted_at.is_(None),
            Product.deleted_at.is_(None),
            Product.category.in_(target_cats),
        )
        .group_by(Brand.id)
        .order_by(func.count(func.distinct(Product.category)).desc())
        .limit(top_k)
    )).all()

    return [
        {
            "id": r[0], "name": r[1], "name_cn": r[2], "category": r[3],
            "product_count": r[4], "shared_categories": r[5],
        }
        for r in similar
    ]


# ============================================================
#  Brand Health Dashboard
# ============================================================

async def get_brand_health(db: AsyncSession, brand_id: int) -> dict:
    """Compute brand health metrics from sales data + AI assessment."""
    ctx = await _brand_context(db, brand_id)

    product_ids = [r[0] for r in (
        await db.execute(
            select(Product.id).where(
                Product.brand_id == brand_id, Product.deleted_at.is_(None)
            )
        )
    ).all()]

    now = datetime.datetime.now(datetime.timezone.utc)
    twelve_months_ago = now - datetime.timedelta(days=365)

    if product_ids:
        # Monthly revenue from sales orders
        monthly_rows = (await db.execute(
            select(
                func.date_trunc('month', SalesOrder.created_at).label('month'),
                func.sum(SalesOrderItem.total_price).label('revenue'),
            )
            .select_from(SalesOrderItem)
            .join(SalesOrder, SalesOrderItem.order_id == SalesOrder.id)
            .where(
                SalesOrderItem.product_id.in_(product_ids),
                SalesOrder.status.in_(['confirmed', 'delivered', 'completed']),
                SalesOrder.created_at >= twelve_months_ago,
                SalesOrder.deleted_at.is_(None),
                SalesOrderItem.deleted_at.is_(None),
            )
            .group_by(text('month'))
            .order_by(text('month'))
        )).all()

        monthly_revenue = ", ".join(f"{r[0].strftime('%Y-%m')}: ¥{float(r[1]):,.0f}" for r in monthly_rows) if monthly_rows else "无"

        # Total orders and customers
        order_stats = (await db.execute(
            select(
                func.count(func.distinct(SalesOrder.id)),
                func.count(func.distinct(SalesOrder.customer_id)),
            )
            .select_from(SalesOrderItem)
            .join(SalesOrder, SalesOrderItem.order_id == SalesOrder.id)
            .where(
                SalesOrderItem.product_id.in_(product_ids),
                SalesOrder.status.in_(['confirmed', 'delivered', 'completed']),
                SalesOrder.created_at >= twelve_months_ago,
                SalesOrder.deleted_at.is_(None),
                SalesOrderItem.deleted_at.is_(None),
            )
        )).first()

        total_orders = order_stats[0] if order_stats else 0
        active_customers = order_stats[1] if order_stats else 0

        # Revenue growth (last 3 months vs previous 3 months)
        r3m = (await db.execute(
            select(func.sum(SalesOrderItem.total_price))
            .select_from(SalesOrderItem)
            .join(SalesOrder, SalesOrderItem.order_id == SalesOrder.id)
            .where(
                SalesOrderItem.product_id.in_(product_ids),
                SalesOrder.status.in_(['confirmed', 'delivered', 'completed']),
                SalesOrder.created_at >= now - datetime.timedelta(days=90),
                SalesOrder.deleted_at.is_(None),
                SalesOrderItem.deleted_at.is_(None),
            )
        )).scalar() or 0

        r3m_prev = (await db.execute(
            select(func.sum(SalesOrderItem.total_price))
            .select_from(SalesOrderItem)
            .join(SalesOrder, SalesOrderItem.order_id == SalesOrder.id)
            .where(
                SalesOrderItem.product_id.in_(product_ids),
                SalesOrder.status.in_(['confirmed', 'delivered', 'completed']),
                SalesOrder.created_at.between(
                    now - datetime.timedelta(days=180),
                    now - datetime.timedelta(days=90),
                ),
                SalesOrder.deleted_at.is_(None),
                SalesOrderItem.deleted_at.is_(None),
            )
        )).scalar() or 0

        revenue_growth = f"{((float(r3m) - float(r3m_prev)) / float(r3m_prev) * 100):.1f}" if float(r3m_prev) > 0 else "无数据"

        # Margin estimate (revenue - cost)
        cost_rows = (await db.execute(
            select(func.sum(SupplierProduct.cost_price * SalesOrderItem.quantity))
            .select_from(SalesOrderItem)
            .join(SalesOrder, SalesOrderItem.order_id == SalesOrder.id)
            .join(SupplierProduct, SalesOrderItem.product_id == SupplierProduct.product_id)
            .where(
                SalesOrderItem.product_id.in_(product_ids),
                SalesOrder.status.in_(['confirmed', 'delivered', 'completed']),
                SalesOrder.created_at >= twelve_months_ago,
                SalesOrder.deleted_at.is_(None),
                SalesOrderItem.deleted_at.is_(None),
                SupplierProduct.deleted_at.is_(None),
            )
        )).scalar() or 0

        total_revenue = sum(float(r[1]) for r in monthly_rows) if monthly_rows else 0
        margin_pct = f"{((total_revenue - float(cost_rows)) / total_revenue * 100):.1f}" if total_revenue > 0 else "无数据"

        # Inventory data
        stock_rows = (await db.execute(
            select(
                func.sum(Inventory.quantity),
                func.count(Inventory.id),
            ).where(
                Inventory.product_id.in_(product_ids),
                Inventory.deleted_at.is_(None),
            )
        )).first()
        total_stock = stock_rows[0] or 0 if stock_rows else 0
    else:
        monthly_revenue = "无"
        total_orders = 0
        active_customers = 0
        revenue_growth = "无数据"
        margin_pct = "无数据"
        total_stock = 0

    health_data = {
        **ctx,
        "monthly_revenue": monthly_revenue,
        "monthly_margin": margin_pct,
        "total_orders": total_orders,
        "active_customers": active_customers,
        "return_rate": "无数据",
        "revenue_growth": revenue_growth,
        "churn_rate": "无数据",
        "total_stock": total_stock,
        "turnover_rate": "无数据",
        "slow_moving_pct": "无数据",
    }

    from app.services.ai.client import ai_client
    from app.services.ai.prompts import brand_health_prompt

    schema = {
        "overall_health_score": "integer 0-100",
        "health_label": "string: 优秀/良好/一般/需关注/风险",
        "revenue_assessment": "string",
        "margin_assessment": "string",
        "customer_assessment": "string",
        "inventory_assessment": "string",
        "trend_direction": "string: 上升/稳定/下降",
        "risk_signals": ["string"],
        "improvement_suggestions": ["string"],
    }
    result = await ai_client.chat_structured(
        [{"role": "system", "content": "你是一个电子元器件供应链分析专家，擅长品牌经营健康度评估。"},
         {"role": "user", "content": brand_health_prompt(health_data)}],
        schema,
    )
    result["context"] = health_data
    return result


# ============================================================
#  Brand Risk Assessment
# ============================================================

async def assess_brand_risk(db: AsyncSession, brand_id: int) -> dict:
    """AI-powered brand risk assessment across supplier, lifecycle, customer, market dimensions."""
    ctx = await _brand_context(db, brand_id)

    product_ids = [r[0] for r in (
        await db.execute(
            select(Product.id).where(
                Product.brand_id == brand_id, Product.deleted_at.is_(None)
            )
        )
    ).all()]

    product_count = len(product_ids)

    if product_ids:
        # Supplier concentration: count products with exactly 1 supplier
        supplier_counts = (await db.execute(
            select(
                SupplierProduct.product_id,
                func.count(SupplierProduct.supplier_id).label('sc'),
            ).where(
                SupplierProduct.product_id.in_(product_ids),
                SupplierProduct.deleted_at.is_(None),
            ).group_by(SupplierProduct.product_id)
        )).all()

        single_source_count = sum(1 for r in supplier_counts if r[1] == 1)
        single_source_pct = round(single_source_count / product_count * 100, 1) if product_count > 0 else 0

        # Top supplier share — single query instead of N+1
        supplier_product_counts: dict[int, int] = {}
        if product_ids:
            sp_all = (await db.execute(
                select(SupplierProduct.supplier_id).where(
                    SupplierProduct.product_id.in_(product_ids),
                    SupplierProduct.deleted_at.is_(None),
                )
            )).all()
            for sp in sp_all:
                supplier_product_counts[sp[0]] = supplier_product_counts.get(sp[0], 0) + 1

        top_supplier_share = f"{max(supplier_product_counts.values()) / product_count * 100:.0f}%" if supplier_product_counts else "0%"

        # Customer concentration
        now = datetime.datetime.now(datetime.timezone.utc)
        cust_revenue = (await db.execute(
            select(
                SalesOrder.customer_id,
                func.sum(SalesOrderItem.total_price).label('rev'),
            )
            .select_from(SalesOrderItem)
            .join(SalesOrder, SalesOrderItem.order_id == SalesOrder.id)
            .where(
                SalesOrderItem.product_id.in_(product_ids),
                SalesOrder.status.in_(['confirmed', 'delivered', 'completed']),
                SalesOrder.created_at >= now - datetime.timedelta(days=365),
                SalesOrder.deleted_at.is_(None),
                SalesOrderItem.deleted_at.is_(None),
            )
            .group_by(SalesOrder.customer_id)
            .order_by(text('rev DESC'))
        )).all()

        total_rev = sum(float(r[1]) for r in cust_revenue) if cust_revenue else 0
        top1_share = round(float(cust_revenue[0][1]) / total_rev * 100, 1) if cust_revenue and total_rev > 0 else 0
        top3_share = round(sum(float(r[1]) for r in cust_revenue[:3]) / total_rev * 100, 1) if cust_revenue and total_rev > 0 else 0

        # Competitor count (other brands in same categories)
        brand_cats = [r[0] for r in (
            await db.execute(
                select(func.distinct(Product.category)).where(
                    Product.brand_id == brand_id,
                    Product.deleted_at.is_(None),
                    Product.category.isnot(None),
                )
            )
        ).all()]

        competitor_count = 0
        if brand_cats:
            competitor_count = (await db.execute(
                select(func.count(func.distinct(Product.brand_id))).where(
                    Product.category.in_(brand_cats),
                    Product.brand_id != brand_id,
                    Product.deleted_at.is_(None),
                )
            )).scalar() or 0
    else:
        single_source_count = 0
        single_source_pct = 0
        top_supplier_share = "0%"
        top1_share = 0
        top3_share = 0
        competitor_count = 0

    risk_data = {
        **ctx,
        "supplier_count": ctx.get("supplier_count", 0),
        "single_source_count": single_source_count,
        "single_source_pct": single_source_pct,
        "top_supplier_share": top_supplier_share,
        "product_count": product_count,
        "eol_count": 0,
        "new_products_6m": 0,
        "active_customers": 0,
        "top_customer_share": top1_share,
        "top3_customer_share": top3_share,
        "competitor_count": competitor_count,
        "substitutable_pct": 0,
    }

    from app.services.ai.client import ai_client
    from app.services.ai.prompts import brand_risk_prompt

    schema = {
        "risk_score": "integer 0-100",
        "risk_level": "string: 低/中/高/严重",
        "supplier_risk": "string",
        "lifecycle_risk": "string",
        "concentration_risk": "string",
        "market_risk": "string",
        "top_risks": ["string"],
        "mitigation_suggestions": ["string"],
    }
    result = await ai_client.chat_structured(
        [{"role": "system", "content": "你是一个电子元器件供应链风险管理专家。"},
         {"role": "user", "content": brand_risk_prompt(risk_data)}],
        schema,
    )
    result["context"] = risk_data
    return result


# ============================================================
#  Brand-Supplier Matrix
# ============================================================

async def get_brand_supplier_matrix(db: AsyncSession, brand_id: int) -> dict:
    """Supplier coverage, pricing comparison, single-source detection for a brand."""
    ctx = await _brand_context(db, brand_id)

    product_ids = [r[0] for r in (
        await db.execute(
            select(Product.id).where(
                Product.brand_id == brand_id, Product.deleted_at.is_(None)
            )
        )
    ).all()]

    # Per-supplier details
    supplier_rows = (await db.execute(
        select(
            Supplier.id, Supplier.name,
            func.count(SupplierProduct.product_id).label('pc'),
            func.avg(SupplierProduct.cost_price).label('avg_cost'),
            func.min(SupplierProduct.cost_price).label('min_cost'),
            func.max(SupplierProduct.cost_price).label('max_cost'),
            func.avg(SupplierProduct.lead_time_days).label('avg_lt'),
            func.min(SupplierProduct.lead_time_days).label('min_lt'),
            func.max(SupplierProduct.lead_time_days).label('max_lt'),
        )
        .select_from(Supplier)
        .join(SupplierProduct, Supplier.id == SupplierProduct.supplier_id)
        .where(
            SupplierProduct.product_id.in_(product_ids),
            SupplierProduct.deleted_at.is_(None),
            Supplier.deleted_at.is_(None),
        )
        .group_by(Supplier.id)
        .order_by(text('pc DESC'))
    )).all()

    supplier_details = []
    for r in supplier_rows:
        supplier_details.append({
            "supplier_id": r[0],
            "supplier_name": r[1],
            "product_count": r[2],
            "avg_cost": float(r[3]) if r[3] else None,
            "min_cost": float(r[4]) if r[4] else None,
            "max_cost": float(r[5]) if r[5] else None,
            "avg_lead_time": round(float(r[6]), 1) if r[6] else None,
            "min_lead_time": r[7],
            "max_lead_time": r[8],
        })

    # Price ranking
    supplier_price_ranking = ", ".join(
        f"{s['supplier_name']}: ¥{s['avg_cost']:.4f}" if s['avg_cost'] else f"{s['supplier_name']}: 暂无报价"
        for s in sorted(supplier_details, key=lambda x: x['avg_cost'] or 999999)
    ) if supplier_details else "无数据"

    # Backup coverage
    supplier_count_per_product = (await db.execute(
        select(
            func.count(SupplierProduct.supplier_id).label('sc'),
        ).where(
            SupplierProduct.product_id.in_(product_ids),
            SupplierProduct.deleted_at.is_(None),
        ).group_by(SupplierProduct.product_id)
    )).all()

    products_with_backup = sum(1 for r in supplier_count_per_product if r[0] >= 2)
    backup_pct = round(products_with_backup / len(product_ids) * 100, 1) if product_ids else 0

    # Lead time stats
    lt_rows = [s['avg_lead_time'] for s in supplier_details if s['avg_lead_time']]
    avg_lt = round(sum(lt_rows) / len(lt_rows), 1) if lt_rows else None
    lt_range = f"{min(lt_rows)}~{max(lt_rows)}天" if lt_rows else "无数据"

    matrix_data = {
        **ctx,
        "supplier_details": ", ".join(
            f"{s['supplier_name']}({s['product_count']}个产品, 均价¥{s['avg_cost']:.4f}, 交期{s['avg_lead_time']}天)"
            if s['avg_cost'] and s['avg_lead_time']
            else f"{s['supplier_name']}({s['product_count']}个产品)"
            for s in supplier_details
        ) if supplier_details else "无",
        "avg_products_per_supplier": round(ctx.get("product_count", 0) / max(len(supplier_details), 1), 1),
        "backup_coverage_pct": backup_pct,
        "supplier_price_ranking": supplier_price_ranking,
        "avg_lead_time": avg_lt,
        "lead_time_range": lt_range,
    }

    from app.services.ai.client import ai_client
    from app.services.ai.prompts import brand_supplier_matrix_prompt

    schema = {
        "overall_assessment": "string",
        "coverage_score": "integer 0-100",
        "single_source_products": [
            {"product_name": "string", "supplier": "string", "cost_price": "number", "risk_reason": "string"}
        ],
        "backup_recommendations": [
            {"current": "string", "recommended": "string", "reason": "string"}
        ],
        "price_optimization": ["string"],
        "negotiation_leverage": "string",
    }
    result = await ai_client.chat_structured(
        [{"role": "system", "content": "你是一个电子元器件采购策略专家，擅长供应商矩阵分析和采购优化。"},
         {"role": "user", "content": brand_supplier_matrix_prompt(matrix_data)}],
        schema,
    )
    result["context"] = matrix_data
    result["supplier_details"] = supplier_details
    return result


# ============================================================
#  Brand Recommendation Engine
# ============================================================

async def recommend_brands(db: AsyncSession, brand_id: int, top_k: int = 5) -> dict:
    """Collaborative filtering: 'customers who bought this brand also bought...'"""
    ctx = await _brand_context(db, brand_id)

    # Find customers who bought this brand
    product_ids = [r[0] for r in (
        await db.execute(
            select(Product.id).where(
                Product.brand_id == brand_id, Product.deleted_at.is_(None)
            )
        )
    ).all()]

    if not product_ids:
        return {"recommendation_summary": "暂无足够数据", "recommended_brands": [], "context": ctx}

    # Customers who bought this brand
    customer_ids = [r[0] for r in (
        await db.execute(
            select(func.distinct(SalesOrder.customer_id))
            .select_from(SalesOrderItem)
            .join(SalesOrder, SalesOrderItem.order_id == SalesOrder.id)
            .where(
                SalesOrderItem.product_id.in_(product_ids),
                SalesOrder.deleted_at.is_(None),
                SalesOrderItem.deleted_at.is_(None),
            )
        )
    ).all()]

    if not customer_ids:
        return {"recommendation_summary": "暂无购买客户，无法生成推荐", "recommended_brands": [], "context": ctx}

    # What other brands did those customers buy?
    co_purchase_rows = (
        await db.execute(
            select(
                Brand.id, Brand.name, Brand.name_cn, Brand.category,
                func.count(func.distinct(SalesOrder.customer_id)).label('shared_customers'),
                func.count(func.distinct(Product.id)).label('shared_products'),
            )
            .select_from(SalesOrderItem)
            .join(SalesOrder, SalesOrderItem.order_id == SalesOrder.id)
            .join(Product, SalesOrderItem.product_id == Product.id)
            .join(Brand, Product.brand_id == Brand.id)
            .where(
                SalesOrder.customer_id.in_(customer_ids),
                Product.brand_id != brand_id,
                Product.deleted_at.is_(None),
                Brand.deleted_at.is_(None),
                SalesOrder.deleted_at.is_(None),
                SalesOrderItem.deleted_at.is_(None),
            )
            .group_by(Brand.id)
            .order_by(text('shared_customers DESC'))
            .limit(top_k * 3)
        )
    ).all()

    if not co_purchase_rows:
        return {"recommendation_summary": "未发现关联购买品牌", "recommended_brands": [], "context": ctx}

    co_purchase_data = (
        "\n".join(
            f"- {r[1]}{f' ({r[2]})' if r[2] else ''}: {r[4]} 共同客户, {r[5]} 共同产品"
            for r in co_purchase_rows
        )
    )

    candidate_brands = (
        "\n".join(
            f"- {r[1]}{f' ({r[2]})' if r[2] else ''} | 分类: {r[3] or '未知'} | "
            f"客户重叠: {r[4]} | 共同产品数: {r[5]}"
            for r in co_purchase_rows
        )
    )

    rec_data = {
        **ctx,
        "co_purchase_data": co_purchase_data,
        "candidate_brands": candidate_brands,
    }

    from app.services.ai.client import ai_client
    from app.services.ai.prompts import brand_recommendation_prompt

    schema = {
        "recommendation_summary": "string",
        "recommended_brands": [
            {"brand_name": "string", "overlap_score": "integer 0-100", "reason": "string", "priority": "string: 高/中/低"}
        ],
        "cross_sell_strategies": ["string"],
        "target_industries": ["string"],
        "expected_conversion": "string",
    }
    result = await ai_client.chat_structured(
        [{"role": "system", "content": "你是一个电子元器件销售策略专家，擅长交叉销售和品牌推荐。"},
         {"role": "user", "content": brand_recommendation_prompt(rec_data)}],
        schema,
    )
    result["context"] = rec_data
    result["co_purchase_raw"] = [
        {"id": r[0], "name": r[1], "name_cn": r[2], "category": r[3],
         "shared_customers": r[4], "shared_products": r[5]}
        for r in co_purchase_rows
    ]
    return result


# ============================================================
#  Brand Product Performance
# ============================================================

async def get_brand_product_performance(db: AsyncSession, brand_id: int) -> dict:
    """Rank products within a brand by sales/margin, AI labels stars vs dogs."""
    ctx = await _brand_context(db, brand_id)

    now = datetime.datetime.now(datetime.timezone.utc)
    six_months_ago = now - datetime.timedelta(days=180)

    product_ids = [r[0] for r in (
        await db.execute(
            select(Product.id).where(
                Product.brand_id == brand_id, Product.deleted_at.is_(None)
            )
        )
    ).all()]

    total_revenue_6m = 0
    active_products = 0
    total_margin_6m = 0.0
    ranking_parts = []

    if product_ids:
        rev_rows = (await db.execute(
            select(
                SalesOrderItem.product_id,
                func.sum(SalesOrderItem.total_price).label("revenue"),
                func.sum(SalesOrderItem.quantity).label("qty"),
            )
            .select_from(SalesOrderItem)
            .join(SalesOrder, SalesOrderItem.order_id == SalesOrder.id)
            .where(
                SalesOrderItem.product_id.in_(product_ids),
                SalesOrder.status.in_(['confirmed', 'delivered', 'completed']),
                SalesOrder.created_at >= six_months_ago,
                SalesOrder.deleted_at.is_(None),
                SalesOrderItem.deleted_at.is_(None),
            )
            .group_by(SalesOrderItem.product_id)
            .order_by(text("revenue DESC"))
        )).all()

        cost_rows = dict(
            (await db.execute(
                select(SupplierProduct.product_id, func.avg(SupplierProduct.cost_price))
                .where(
                    SupplierProduct.product_id.in_(product_ids),
                    SupplierProduct.cost_price.isnot(None),
                    SupplierProduct.deleted_at.is_(None),
                )
                .group_by(SupplierProduct.product_id)
            )).all() or []
        )

        product_names = {p[0]: f"{p[2] or ''} {p[1]}".strip() for p in (
            await db.execute(
                select(Product.id, Product.name, Product.sku)
                .where(Product.id.in_(product_ids), Product.deleted_at.is_(None))
            )
        ).all()}

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

    from app.services.ai.client import ai_client
    from app.services.ai.prompts import brand_product_performance_prompt

    schema = {
        "star_products": [
            {"product_name": "string", "revenue": "number", "margin_pct": "number", "growth": "string", "recommendation": "string"}
        ],
        "problem_products": [
            {"product_name": "string", "issue": "string", "suggestion": "string"}
        ],
        "portfolio_assessment": "string",
        "focus_recommendations": ["string"],
        "phase_out_candidates": ["string"],
    }
    result = await ai_client.chat_structured(
        [{"role": "system", "content": "你是一个电子元器件产品管理专家，擅长产品组合分析和绩效评估。"},
         {"role": "user", "content": brand_product_performance_prompt(perf_data)}],
        schema,
    )
    result["context"] = perf_data
    return result


# ============================================================
#  Brand Customer Penetration
# ============================================================

async def get_brand_customer_penetration(db: AsyncSession, brand_id: int) -> dict:
    """Analyze which customer segments buy this brand and identify untapped markets."""
    ctx = await _brand_context(db, brand_id)

    product_ids = [r[0] for r in (
        await db.execute(
            select(Product.id).where(
                Product.brand_id == brand_id, Product.deleted_at.is_(None)
            )
        )
    ).all()]

    customer_count = 0
    industry_dist = "无数据"
    level_dist = "无数据"
    repeat_rate: float | str = "无数据"
    avg_order_value = "无数据"
    untapped = "无数据"

    if product_ids:
        cust_rows = (await db.execute(
            select(
                SalesOrder.customer_id,
                func.count(SalesOrder.id).label("order_count"),
                func.sum(SalesOrder.total_amount).label("total"),
            )
            .select_from(SalesOrderItem)
            .join(SalesOrder, SalesOrderItem.order_id == SalesOrder.id)
            .where(
                SalesOrderItem.product_id.in_(product_ids),
                SalesOrder.status.in_(['confirmed', 'delivered', 'completed']),
                SalesOrder.deleted_at.is_(None),
                SalesOrderItem.deleted_at.is_(None),
            )
            .group_by(SalesOrder.customer_id)
        )).all()

        customer_count = len(cust_rows)

        if customer_count > 0:
            cust_details_list = (await db.execute(
                select(Customer.id, Customer.industry, Customer.level)
                .where(Customer.id.in_([r[0] for r in cust_rows]), Customer.deleted_at.is_(None))
            )).all()
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

            industry_dist = ", ".join(f"{k}({v})" for k, v in sorted(ind_counts.items(), key=lambda x: -x[1]))
            level_dist = ", ".join(f"{k}({v})" for k, v in sorted(lvl_counts.items(), key=lambda x: -x[1]))

            repeat_customers = sum(1 for r in cust_rows if r[1] and r[1] >= 2)
            repeat_rate = round(repeat_customers / customer_count * 100, 1) if customer_count > 0 else 0

            total_rev = sum(float(r[2]) for r in cust_rows if r[2])
            total_orders = sum(r[1] for r in cust_rows if r[1])
            avg_order_value = f"¥{total_rev / total_orders:,.0f}" if total_orders > 0 else "0"

            all_custs = set(
                (await db.execute(
                    select(Customer.id)
                    .where(Customer.deleted_at.is_(None))
                    .limit(100)
                )).scalars().all()
            )
            current_custs = set(r[0] for r in cust_rows)
            untapped_custs = all_custs - current_custs

            if untapped_custs:
                untapped_info = (await db.execute(
                    select(Customer.id, Customer.name, Customer.industry, Customer.level)
                    .where(Customer.id.in_(list(untapped_custs)), Customer.deleted_at.is_(None))
                    .limit(10)
                )).all()
                untapped = "\n".join(
                    f"- {r[1]} | 行业:{r[2] or '未知'} | 等级:{r[3] or '未知'}"
                    for r in untapped_info
                ) if untapped_info else "无明确未开发机会"
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

    from app.services.ai.client import ai_client
    from app.services.ai.prompts import brand_customer_penetration_prompt

    schema = {
        "penetration_score": "integer 0-100",
        "penetration_assessment": "string",
        "key_industries": [
            {"industry": "string", "customer_count": "integer", "contribution_pct": "number", "assessment": "string"}
        ],
        "untapped_industries": [
            {"industry": "string", "potential_customers": "integer", "strategy": "string"}
        ],
        "retention_strategy": ["string"],
        "expansion_strategy": ["string"],
    }
    result = await ai_client.chat_structured(
        [{"role": "system", "content": "你是一个电子元器件市场分析专家，擅长客户渗透率分析和市场开发策略。"},
         {"role": "user", "content": brand_customer_penetration_prompt(pen_data)}],
        schema,
    )
    result["context"] = pen_data
    return result


# ============================================================
#  Brand Lifecycle Prediction
# ============================================================

async def predict_brand_lifecycle(db: AsyncSession, brand_id: int) -> dict:
    """AI predicts brand lifecycle stage based on product, sales, and supplier trends."""
    ctx = await _brand_context(db, brand_id)

    now = datetime.datetime.now(datetime.timezone.utc)
    twelve_months_ago = now - datetime.timedelta(days=365)
    six_mo_ago = now - datetime.timedelta(days=180)

    prod_rows = (await db.execute(
        select(Product.id, Product.created_at).where(
            Product.brand_id == brand_id, Product.deleted_at.is_(None)
        )
    )).all()

    product_ids = [r[0] for r in prod_rows]
    new_6m = sum(1 for r in prod_rows if r[1] and r[1] >= six_mo_ago)

    revenue_growth = "无数据"
    if product_ids:
        rev_12m = (await db.execute(
            select(func.coalesce(func.sum(SalesOrderItem.total_price), 0))
            .select_from(SalesOrderItem)
            .join(SalesOrder, SalesOrderItem.order_id == SalesOrder.id)
            .where(
                SalesOrderItem.product_id.in_(product_ids),
                SalesOrder.status.in_(['confirmed', 'delivered', 'completed']),
                SalesOrder.created_at >= twelve_months_ago,
                SalesOrder.deleted_at.is_(None),
                SalesOrderItem.deleted_at.is_(None),
            )
        )).scalar() or 0

        rev_prev = (await db.execute(
            select(func.coalesce(func.sum(SalesOrderItem.total_price), 0))
            .select_from(SalesOrderItem)
            .join(SalesOrder, SalesOrderItem.order_id == SalesOrder.id)
            .where(
                SalesOrderItem.product_id.in_(product_ids),
                SalesOrder.status.in_(['confirmed', 'delivered', 'completed']),
                SalesOrder.created_at.between(
                    now - datetime.timedelta(days=730),
                    twelve_months_ago,
                ),
                SalesOrder.deleted_at.is_(None),
                SalesOrderItem.deleted_at.is_(None),
            )
        )).scalar() or 0

        revenue_growth = f"{((float(rev_12m) - float(rev_prev)) / float(rev_prev) * 100):.1f}" if float(rev_prev) > 0 else "无历史数据"

    lc_data = {
        **ctx,
        "new_products_6m": new_6m,
        "eol_pct": 0,
        "revenue_growth_12m": revenue_growth,
        "customer_growth_12m": "无数据",
        "supplier_trend": "无数据",
        "product_intro_rhythm": f"近6月{new_6m}新品" if new_6m > 0 else "近期无新品推出",
    }

    from app.services.ai.client import ai_client
    from app.services.ai.prompts import brand_lifecycle_prompt

    schema = {
        "lifecycle_stage": "string: 导入期/成长期/成熟期/衰退期",
        "stage_confidence": "integer 0-100",
        "stage_evidence": ["string"],
        "strategic_advice": "string",
        "next_12m_outlook": "string",
        "key_actions": ["string"],
        "risk_signals": ["string"],
    }
    result = await ai_client.chat_structured(
        [{"role": "system", "content": "你是一个电子元器件产品生命周期管理专家，擅长判断品牌所处阶段并给出战略建议。"},
         {"role": "user", "content": brand_lifecycle_prompt(lc_data)}],
        schema,
    )
    result["context"] = lc_data
    return result


# ============================================================
#  Brand Price Trends
# ============================================================

async def get_brand_price_trends(db: AsyncSession, brand_id: int) -> dict:
    """Analyze brand price trends over 12 months with margin and competitiveness assessment."""
    ctx = await _brand_context(db, brand_id)

    now = datetime.datetime.now(datetime.timezone.utc)
    twelve_months_ago = now - datetime.timedelta(days=365)

    product_ids = [r[0] for r in (
        await db.execute(
            select(Product.id).where(
                Product.brand_id == brand_id, Product.deleted_at.is_(None)
            )
        )
    ).all()]

    monthly_avg_price = "无销售数据"
    monthly_margin = "无数据"
    current_avg = "无数据"
    price_12m_ago = "无数据"
    price_change_pct = "无数据"
    cost_trend = "无数据"

    if product_ids:
        price_rows = (await db.execute(
            select(
                func.date_trunc('month', SalesOrder.created_at).label('month'),
                func.avg(SalesOrderItem.unit_price).label('avg_price'),
            )
            .select_from(SalesOrderItem)
            .join(SalesOrder, SalesOrderItem.order_id == SalesOrder.id)
            .where(
                SalesOrderItem.product_id.in_(product_ids),
                SalesOrder.status.in_(['confirmed', 'delivered', 'completed']),
                SalesOrder.created_at >= twelve_months_ago,
                SalesOrder.deleted_at.is_(None),
                SalesOrderItem.deleted_at.is_(None),
            )
            .group_by(text('month'))
            .order_by(text('month'))
        )).all()

        if price_rows:
            monthly_avg_price = ", ".join(
                f"{r[0].strftime('%Y-%m')}: ¥{float(r[1]):.2f}" for r in price_rows
            )
            current_avg = f"¥{float(price_rows[-1][1]):.4f}"
            if len(price_rows) > 1:
                price_12m_ago = f"¥{float(price_rows[0][1]):.4f}"
                delta = (float(price_rows[-1][1]) - float(price_rows[0][1])) / float(price_rows[0][1]) * 100
                price_change_pct = f"{delta:.1f}"

        cost_rows = (await db.execute(
            select(
                func.date_trunc('month', SupplierProduct.created_at).label('month'),
                func.avg(SupplierProduct.cost_price).label('avg_cost'),
            )
            .where(
                SupplierProduct.product_id.in_(product_ids),
                SupplierProduct.cost_price.isnot(None),
                SupplierProduct.created_at >= twelve_months_ago,
                SupplierProduct.deleted_at.is_(None),
            )
            .group_by(text('month'))
            .order_by(text('month'))
        )).all()

        if cost_rows:
            cost_trend = ", ".join(
                f"{r[0].strftime('%Y-%m')}: ¥{float(r[1]):.4f}" for r in cost_rows
            )

    trend_data = {
        **ctx,
        "monthly_avg_price": monthly_avg_price,
        "monthly_margin": monthly_margin,
        "current_avg_price": current_avg,
        "price_12m_ago": price_12m_ago,
        "price_change_pct": price_change_pct,
        "market_benchmark": "暂无市场基准数据",
        "cost_trend": cost_trend,
    }

    from app.services.ai.client import ai_client
    from app.services.ai.prompts import brand_price_trends_prompt

    schema = {
        "price_trend": "string: 上涨/稳定/下降",
        "trend_score": "integer 0-100",
        "margin_assessment": "string",
        "competitiveness": "string",
        "pricing_issues": ["string"],
        "optimization_suggestions": ["string"],
        "opportunity_alert": "string | null",
    }
    result = await ai_client.chat_structured(
        [{"role": "system", "content": "你是一个电子元器件定价策略专家，擅长价格趋势分析和定价优化。"},
         {"role": "user", "content": brand_price_trends_prompt(trend_data)}],
        schema,
    )
    result["context"] = trend_data
    return result


async def auto_complete_brand(db: AsyncSession, brand_id: int) -> dict:
    """AI auto-completes missing brand fields based on existing data and industry knowledge."""
    from app.services.ai.client import ai_client

    brand = (await db.execute(
        select(Brand).where(Brand.id == brand_id, Brand.deleted_at.is_(None))
    )).scalar_one_or_none()
    if brand is None:
        raise ValueError("Brand not found")

    existing = {
        "name": brand.name, "name_cn": brand.name_cn, "short_name": brand.short_name,
        "code": brand.code, "brand_type": brand.brand_type, "status": brand.status,
        "category": brand.category, "description": brand.description,
        "level": brand.level, "positioning": brand.positioning, "owner": brand.owner,
        "product_lines": brand.product_lines, "target_markets": brand.target_markets,
        "website": brand.website,
        "manufacturer_name": brand.manufacturer_name, "authorization_status": brand.authorization_status,
        "lifecycle_stage": brand.lifecycle_stage, "is_automotive": brand.is_automotive,
        "moq": brand.moq, "lead_time_days": brand.lead_time_days,
        "risk_level": brand.risk_level, "rohs_status": brand.rohs_status,
        "ai_keywords": brand.ai_keywords, "risk_score": brand.risk_score,
        "alternative_brands": brand.alternative_brands,
    }

    missing_fields = [k for k, v in existing.items() if v is None and k not in ("short_name", "logo")]

    if not missing_fields:
        return {"brand_id": brand_id, "filled": {}, "message": "所有字段已完整，无需补全"}

    prompt = f"""你是电子元器件品牌数据专家。根据你对 {existing['name']} ({existing.get('name_cn', '')}) 的了解，补全以下字段。

已知信息：{existing['name']} 是 {existing.get('category', '未知品类')} 领域的品牌{existing.get('description', '')}。

请用以下格式逐行返回（只返回需要补全的字段，一行一个）：
{chr(10).join(f'{f}: <值>' for f in missing_fields)}

规则：
- 所有信息必须基于真实行业知识
- 不确定的填"未知"
- 数值字段只填数字
- 多个值之间必须用逗号分隔，不要用其他符号
- risk_score: 0-100整数，综合缺货/停产/交期风险"""

    try:
        text = await ai_client.chat(
            [{"role": "system", "content": "你是电子元器件行业专家。只返回指定格式的数据，不要解释。"},
             {"role": "user", "content": prompt}],
            temperature=0.3,
            max_tokens=1024,
        )

        # Parse line-by-line response: "field: value"
        filled = {}
        for line in text.strip().split("\n"):
            line = line.strip()
            if ":" not in line:
                continue
            key, _, val = line.partition(":")
            key = key.strip().lower()
            val = val.strip()
            if key in missing_fields and val and val not in ("None", "none", "null", "未知", "无", "-"):
                filled[key] = val
                if key == "risk_score":
                    try:
                        setattr(brand, key, float(val))
                    except (ValueError, TypeError):
                        pass
                elif key == "moq":
                    try:
                        setattr(brand, key, int(float(val)))
                    except (ValueError, TypeError):
                        pass
                elif key == "lead_time_days":
                    try:
                        setattr(brand, key, int(float(val)))
                    except (ValueError, TypeError):
                        pass
                elif key == "is_automotive":
                    setattr(brand, key, val.lower() in ("true", "yes", "是", "1"))
                else:
                    setattr(brand, key, val)

        await db.flush()

        return {
            "brand_id": brand_id,
            "filled": filled,
            "message": f"已补全 {len(filled)} 个字段" if filled else "AI 未能补全任何字段，可能是缺失字段信息不足",
        }

    except Exception as e:
        logger.error(f"auto_complete_brand failed: {e}")
        raise


# ============================================================
# EOL / 新料号追踪
# ============================================================

async def scan_eol_alerts(db: AsyncSession, urgency_threshold: str = "warning") -> dict:
    """
    Scan all brands/products for EOL (End-of-Life) and NRND (Not Recommended for New Designs) risks.
    Returns structured alerts with alternative brand recommendations.

    urgency_threshold: filter by minimum severity — info / warning / critical
    """
    severity_order = {"info": 0, "warning": 1, "critical": 2}

    # 1. Find at-risk brands
    at_risk_brands = (await db.execute(
        select(Brand).where(
            Brand.deleted_at.is_(None),
            Brand.lifecycle_stage.in_(["eol", "nrnd"]),
        )
    )).scalars().all()

    alerts = []

    for brand in at_risk_brands:
        # Products from this brand
        prods = (await db.execute(
            select(Product.id, Product.sku, Product.name, Product.lifecycle_stage)
            .where(Product.brand_id == brand.id, Product.deleted_at.is_(None))
        )).all()

        if not prods:
            continue

        # Recent sales volume for these products
        prod_ids = [p.id for p in prods]
        sales_q = (await db.execute(
            select(func.coalesce(func.sum(SalesOrderItem.total_price), 0))
            .where(SalesOrderItem.product_id.in_(prod_ids), SalesOrderItem.deleted_at.is_(None))
        )).scalar() or 0

        # Alternative brands in same category
        alt_brands = (await db.execute(
            select(Brand.id, Brand.name)
            .where(
                Brand.deleted_at.is_(None),
                Brand.category == brand.category,
                Brand.lifecycle_stage == "active",
                Brand.id != brand.id,
            )
            .limit(3)
        )).all()

        alt_names = [b.name for b in alt_brands] if alt_brands else []

        stage_label = "已停产(EOL)" if brand.lifecycle_stage == "eol" else "不推荐新设计(NRND)"
        severity = "critical" if brand.lifecycle_stage == "eol" and float(sales_q) > 0 else "warning"

        alerts.append({
            "brand_id": brand.id,
            "brand_name": brand.name,
            "lifecycle_stage": brand.lifecycle_stage,
            "stage_label": stage_label,
            "severity": severity,
            "affected_products": len(prods),
            "product_list": [f"{p.sku or ''} {p.name}".strip() for p in prods[:10]],
            "sales_exposure": float(sales_q),
            "alternative_brands": alt_names,
            "recommended_action": (
                f"立即为 {len(prods)} 个在售型号寻找替代品牌"
                if alt_names else "需人工评估替代方案"
            ),
        })

    # Sort by severity then by sales exposure
    alerts.sort(
        key=lambda a: (
            -severity_order.get(a["severity"], 0),
            -a["sales_exposure"],
        )
    )

    total = len(alerts)
    critical = sum(1 for a in alerts if a["severity"] == "critical")
    warning = sum(1 for a in alerts if a["severity"] == "warning")

    return {
        "scanned_at": datetime.datetime.now().isoformat(),
        "total_alerts": total,
        "critical_count": critical,
        "warning_count": warning,
        "alerts": alerts,
        "summary": (
            f"发现 {total} 个EOL/NRND品牌风险"
            f"（{critical} 紧急，{warning} 关注）"
            if total > 0 else "未发现EOL/NRND风险"
        ),
    }


async def suggest_eol_alternatives(db: AsyncSession, product_id: int) -> dict:
    """
    Given a product that is or might be EOL, suggest alternative products/brands.
    """
    product = (await db.execute(
        select(Product).where(Product.id == product_id)
    )).scalars().first()

    if not product:
        return {"error": "产品不存在"}

    brand = None
    if product.brand_id:
        brand = (await db.execute(
            select(Brand).where(Brand.id == product.brand_id)
        )).scalars().first()

    # Find active brands in same category, excluding the original product's brand
    cond = [Brand.deleted_at.is_(None), Brand.lifecycle_stage == "active"]
    if brand and brand.category:
        cond.append(Brand.category == brand.category)

    active_brands = (await db.execute(
        select(Brand).where(*cond).limit(5)
    )).scalars().all()

    alternatives = []
    for b in active_brands:
        prods = (await db.execute(
            select(Product)
            .where(Product.brand_id == b.id, Product.deleted_at.is_(None))
            .limit(5)
        )).scalars().all()

        for p in prods:
            # Skip the original product itself
            if p.id == product.id:
                continue
            inv = (await db.execute(
                select(Inventory).where(Inventory.product_id == p.id)
            )).scalars().first()
            # Only include products that have positive inventory
            if not inv or inv.quantity <= 0:
                continue
            alternatives.append({
                "product_id": p.id,
                "sku": p.sku,
                "name": p.name,
                "brand_id": b.id,
                "brand_name": b.name,
                "stock_qty": inv.quantity if inv else 0,
                "match_reason": f"同品类({b.category or '未知'})替代",
            })

    # Fallback: if no same-category alternatives, try same-brand active products with inventory
    if not alternatives and brand:
        same_brand_prods = (await db.execute(
            select(Product)
            .where(Product.brand_id == brand.id, Product.deleted_at.is_(None), Product.id != product.id)
            .limit(10)
        )).scalars().all()
        for p in same_brand_prods:
            inv = (await db.execute(
                select(Inventory).where(Inventory.product_id == p.id)
            )).scalars().first()
            if not inv or inv.quantity <= 0:
                continue
            alternatives.append({
                "product_id": p.id,
                "sku": p.sku,
                "name": p.name,
                "brand_id": brand.id,
                "brand_name": brand.name,
                "stock_qty": inv.quantity if inv else 0,
                "match_reason": f"同品牌({brand.name})其他型号",
            })

    return {
        "original": {
            "product_id": product.id,
            "sku": product.sku,
            "name": product.name,
            "brand_name": brand.name if brand else None,
            "lifecycle_stage": brand.lifecycle_stage if brand else None,
        },
        "alternatives": alternatives[:10],
        "count": len(alternatives),
    }
