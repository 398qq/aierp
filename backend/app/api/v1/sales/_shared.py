"""Sales API — shared cache keys, TTL constants, and helpers.

All sales route submodules import from this module to keep cache
invalidation behavior consistent across bounded contexts
(opportunity / quotation / sales-order / delivery-note / inquiry).

Mirrors the v3-v5 caching pattern documented in
``docs/reports/performance-optimization-v5-2026-06-03.md``.
"""

import hashlib
import json


SALES_ORDERS_LIST_CACHE_TTL = 300
SALES_ORDERS_LIST_CACHE_VERSION = "v1"

OPPORTUNITIES_LIST_CACHE_TTL = 300
OPPORTUNITIES_LIST_CACHE_VERSION = "v2"

QUOTATIONS_LIST_CACHE_TTL = 300
QUOTATIONS_LIST_CACHE_VERSION = "v1"

QUOTATIONS_STATS_CACHE_TTL = 300
QUOTATIONS_STATS_CACHE_VERSION = "v1"


def _sales_orders_cache_key(**parts: object) -> str:
    canonical = json.dumps(parts, sort_keys=True, default=str)
    digest = hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:16]
    return f"sales-orders:list:{SALES_ORDERS_LIST_CACHE_VERSION}:{digest}"


def _opportunities_cache_key(**parts: object) -> str:
    canonical = json.dumps(parts, sort_keys=True, default=str)
    digest = hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:16]
    return f"opportunities:list:{OPPORTUNITIES_LIST_CACHE_VERSION}:{digest}"


def _quotations_cache_key(**parts: object) -> str:
    canonical = json.dumps(parts, sort_keys=True, default=str)
    digest = hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:16]
    return f"quotations:list:{QUOTATIONS_LIST_CACHE_VERSION}:{digest}"
