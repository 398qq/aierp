"""Brand intelligence services — re-export from modular submodules for backward compatibility."""

from app.services.brand_intel.auto_complete import auto_complete_brand
from app.services.brand_intel.comparison import compare_brands, find_similar_brands
from app.services.brand_intel.context import _brand_context, _brand_cache_key, _cached_brand_ai
from app.services.brand_intel.eol import scan_eol_alerts, suggest_eol_alternatives
from app.services.brand_intel.health import get_brand_health
from app.services.brand_intel.import_brand import import_brand_from_text
from app.services.brand_intel.lifecycle import get_brand_price_trends, predict_brand_lifecycle
from app.services.brand_intel.performance import get_brand_customer_penetration, get_brand_product_performance
from app.services.brand_intel.portfolio import analyze_brand_portfolio
from app.services.brand_intel.profile import generate_brand_profile
from app.services.brand_intel.recommendation import recommend_brands
from app.services.brand_intel.risk import assess_brand_risk
from app.services.brand_intel.supplier_matrix import get_brand_supplier_matrix

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
    "_brand_context",
    "_brand_cache_key",
    "_cached_brand_ai",
]