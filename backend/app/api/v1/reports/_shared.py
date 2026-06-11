"""Reports API — shared cache keys, TTL constants, and helpers.

All reports route submodules import from this module to keep cache
invalidation behavior consistent across bounded contexts
(templates / predefined / export).
"""

TEMPLATES_LIST_CACHE_TTL = 600
TEMPLATES_LIST_CACHE_VERSION = "v1"

PREDEFINED_SALES_CACHE_TTL = 600
PREDEFINED_SALES_CACHE_VERSION = "v1"

PREDEFINED_AR_CACHE_TTL = 300
PREDEFINED_AR_CACHE_VERSION = "v1"

PREDEFINED_INVENTORY_CACHE_TTL = 300
PREDEFINED_INVENTORY_CACHE_VERSION = "v1"

PREDEFINED_PROCUREMENT_CACHE_TTL = 600
PREDEFINED_PROCUREMENT_CACHE_VERSION = "v1"


def _templates_cache_key() -> str:
    return f"reports:templates:list:{TEMPLATES_LIST_CACHE_VERSION}:global"


def _predefined_sales_cache_key(months: int) -> str:
    return f"reports:predefined:sales:{PREDEFINED_SALES_CACHE_VERSION}:{months}"


def _predefined_ar_cache_key() -> str:
    return f"reports:predefined:ar:{PREDEFINED_AR_CACHE_VERSION}:global"


def _predefined_inventory_cache_key() -> str:
    return f"reports:predefined:inventory:{PREDEFINED_INVENTORY_CACHE_VERSION}:global"


def _predefined_procurement_cache_key(months: int) -> str:
    return f"reports:predefined:procurement:{PREDEFINED_PROCUREMENT_CACHE_VERSION}:{months}"
