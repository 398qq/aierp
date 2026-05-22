"""Multi-domain orchestration — aggregates data across all business domains, then calls AI for cross-domain insights.

This file is kept for backward compatibility.
All orchestrators have been moved to app.services.orchestration/.
"""

from app.services.orchestration import (
    _safe_json,
    orchestrate_customer_360,
    orchestrate_global_360,
    orchestrate_product_360,
)

__all__ = [
    "orchestrate_customer_360",
    "orchestrate_product_360",
    "orchestrate_global_360",
    "_safe_json",
]
