"""Finance API — shared cache keys, TTL constants, and helpers.

All finance route submodules import from this module to keep cache
invalidation behavior consistent across bounded contexts
(invoice / payment / contract / target).

Mirrors the v5 caching pattern documented in
``docs/reports/performance-optimization-v5-2026-06-03.md``.
"""

import hashlib
import json


# List endpoints: 5 min TTL, paginated/filterable
INVOICES_LIST_CACHE_TTL = 300
INVOICES_LIST_CACHE_VERSION = "v1"

PAYMENTS_LIST_CACHE_TTL = 300
PAYMENTS_LIST_CACHE_VERSION = "v1"

CONTRACTS_LIST_CACHE_TTL = 300
CONTRACTS_LIST_CACHE_VERSION = "v1"

TARGETS_LIST_CACHE_TTL = 300
TARGETS_LIST_CACHE_VERSION = "v1"

# Stats endpoints: shorter TTL for fresher aggregates
PAYMENTS_STATS_CACHE_TTL = 60
PAYMENTS_STATS_CACHE_VERSION = "v1"

TARGETS_STATS_CACHE_TTL = 120
TARGETS_STATS_CACHE_VERSION = "v1"


def _invoices_cache_key(**parts: object) -> str:
    canonical = json.dumps(parts, sort_keys=True, default=str)
    digest = hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:16]
    return f"invoices:list:{INVOICES_LIST_CACHE_VERSION}:{digest}"


def _payments_cache_key(**parts: object) -> str:
    canonical = json.dumps(parts, sort_keys=True, default=str)
    digest = hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:16]
    return f"payments:list:{PAYMENTS_LIST_CACHE_VERSION}:{digest}"


def _contracts_cache_key(**parts: object) -> str:
    canonical = json.dumps(parts, sort_keys=True, default=str)
    digest = hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:16]
    return f"contracts:list:{CONTRACTS_LIST_CACHE_VERSION}:{digest}"


def _targets_cache_key(**parts: object) -> str:
    canonical = json.dumps(parts, sort_keys=True, default=str)
    digest = hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:16]
    return f"targets:list:{TARGETS_LIST_CACHE_VERSION}:{digest}"
