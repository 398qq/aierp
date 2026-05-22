"""Brand intelligence — shared context and caching utilities."""

import logging

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.product import Brand, Product, SupplierProduct

logger = logging.getLogger(__name__)


def _brand_cache_key(brand_id: int, func_name: str) -> str:
    return f"brand_ai:{brand_id}:{func_name}"


async def _cached_brand_ai(brand_id: int, func_name: str, factory, ttl: int = 3600):
    """Get cached AI result for brand, or compute and cache it."""
    from app.services import cache_service

    key = _brand_cache_key(brand_id, func_name)
    cached, was_cached = await cache_service.cached(key, ttl=ttl, factory=factory)
    if was_cached:
        logger.debug("cache hit for brand AI: %s", key)
    return cached


async def _brand_context(db: AsyncSession, brand_id: int) -> dict:
    """Collect all context data about a brand."""
    brand = (await db.execute(
        select(Brand).where(Brand.id == brand_id, Brand.deleted_at.is_(None))
    )).scalar_one_or_none()
    if brand is None:
        raise ValueError("Brand not found")

    products = (await db.execute(
        select(Product.id, Product.sku, Product.name, Product.category,
               Product.package_type, Product.specs)
        .where(Product.brand_id == brand_id, Product.deleted_at.is_(None))
    )).all()

    product_count = len(products)

    cat_counts: dict[str, int] = {}
    pkg_counts: dict[str, int] = {}
    for p in products:
        cat = p[3] if p[3] is not None else "未分类"
        pkg = p[4] if p[4] is not None else "未知"
        cat_counts[cat] = cat_counts.get(cat, 0) + 1
        pkg_counts[pkg] = pkg_counts.get(pkg, 0) + 1

    category_dist = ", ".join(f"{k}({v})" for k, v in sorted(cat_counts.items(), key=lambda x: -x[1])[:10])
    package_dist = ", ".join(f"{k}({v})" for k, v in sorted(pkg_counts.items(), key=lambda x: -x[1])[:8])

    sample = ", ".join(
        f"{p[2] if p[2] is not None else p[1] if p[1] is not None else '#'+str(p[0])}" for p in products[:5]
    )

    supplier_ids_subq = select(SupplierProduct.supplier_id).where(
        SupplierProduct.product_id.in_([p[0] for p in products]),
        SupplierProduct.deleted_at.is_(None),
    ).distinct()
    supplier_count = (await db.execute(
        select(func.count()).select_from(supplier_ids_subq.subquery())
    )).scalar() or 0

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