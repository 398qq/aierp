"""Orchestration services — backward compatibility shim.

All orchestrators have been moved to submodules under app.services.orchestration/.
Import from there directly, or use this file for backward compatibility.
"""

from app.services.orchestration.customer_orchestrator import orchestrate_customer_360
from app.services.orchestration.global_orchestrator import orchestrate_global_360
from app.services.orchestration.helpers import _safe_json
from app.services.orchestration.product_orchestrator import orchestrate_product_360

__all__ = [
    "orchestrate_customer_360",
    "orchestrate_product_360",
    "orchestrate_global_360",
    "_safe_json",
]
