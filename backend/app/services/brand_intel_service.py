"""Backward-compatible exports for brand intelligence services."""

from app.services.brand_intel import (
    analyze_brand_portfolio,
    assess_brand_risk,
    auto_complete_brand,
    compare_brands,
    find_similar_brands,
    generate_brand_profile,
    get_brand_customer_penetration,
    get_brand_health,
    get_brand_price_trends,
    get_brand_product_performance,
    get_brand_supplier_matrix,
    import_brand_from_text,
    predict_brand_lifecycle,
    recommend_brands,
    scan_eol_alerts,
    suggest_eol_alternatives,
)

__all__ = [
    "generate_brand_profile",
    "import_brand_from_text",
    "analyze_brand_portfolio",
    "compare_brands",
    "find_similar_brands",
    "get_brand_health",
    "assess_brand_risk",
    "get_brand_supplier_matrix",
    "recommend_brands",
    "get_brand_product_performance",
    "get_brand_customer_penetration",
    "predict_brand_lifecycle",
    "get_brand_price_trends",
    "auto_complete_brand",
    "scan_eol_alerts",
    "suggest_eol_alternatives",
]
