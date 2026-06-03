"""Finance accounts API — shared cache keys, TTL constants, and helpers.

All finance_accounts route submodules import from this module to keep
cache invalidation behavior consistent across bounded contexts
(account / journal / bank / reports).
"""

import hashlib
import json


ACCOUNTS_LIST_CACHE_TTL = 600
ACCOUNTS_LIST_CACHE_VERSION = "v1"

JOURNAL_ENTRIES_LIST_CACHE_TTL = 300
JOURNAL_ENTRIES_LIST_CACHE_VERSION = "v1"

BANK_RECONCILIATIONS_LIST_CACHE_TTL = 300
BANK_RECONCILIATIONS_LIST_CACHE_VERSION = "v1"

PNL_REPORT_CACHE_TTL = 600
PNL_REPORT_CACHE_VERSION = "v1"

AP_REPORT_CACHE_TTL = 600
AP_REPORT_CACHE_VERSION = "v1"


def _accounts_cache_key(**parts: object) -> str:
    canonical = json.dumps(parts, sort_keys=True, default=str)
    digest = hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:16]
    return f"accounts:list:{ACCOUNTS_LIST_CACHE_VERSION}:{digest}"


def _journal_entries_cache_key(**parts: object) -> str:
    canonical = json.dumps(parts, sort_keys=True, default=str)
    digest = hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:16]
    return f"journal-entries:list:{JOURNAL_ENTRIES_LIST_CACHE_VERSION}:{digest}"


def _bank_reconciliations_cache_key(**parts: object) -> str:
    canonical = json.dumps(parts, sort_keys=True, default=str)
    digest = hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:16]
    return f"bank-reconciliations:list:{BANK_RECONCILIATIONS_LIST_CACHE_VERSION}:{digest}"


def _pnl_cache_key(month: str) -> str:
    return f"finance:reports:pnl:{PNL_REPORT_CACHE_VERSION}:{month}"
