"""Redis cache service — provides async get/set/delete with graceful degradation.

Two-level cache:
    L1 = in-process LRU (cachetools, ~50-200 items, sub-ms access, per-worker)
    L2 = Redis (shared across workers, ms access, survives restart)

Version-bump invalidation:
    Instead of `KEYS pattern * DELETE` (O(N), blocks Redis), use atomic counter bumps.
    Each cache family has a `version` counter. Read uses `key@version`. On invalidation,
    `INCR version` — old L2 entries become unreachable and expire on their own;
    L1 entries use a per-family `epoch` that is checked on every read.
"""

import json
import logging
import os
import time

from app.config import settings
from app.core.observability.metrics import (
    cache_hits_total,
    cache_invalidations_total,
    cache_lookup_duration_seconds,
    cache_misses_total,
)

logger = logging.getLogger(__name__)


# ── L1 in-process LRU ─────────────────────────────────────────────────────


def _env_int(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None or not raw.strip():
        return default
    try:
        return int(raw)
    except ValueError:
        return default


L1_MAX_SIZE = _env_int("AIERP_CACHE_L1_SIZE", 256)
L1_ENABLED = os.getenv("AIERP_CACHE_L1_ENABLED", "1") not in ("0", "false", "False", "")

try:
    from cachetools import LRUCache as _LRUCache

    _l1_cache: _LRUCache | None = _LRUCache(maxsize=L1_MAX_SIZE) if L1_ENABLED else None
    # Per-family epoch: bumped on invalidation to invalidate L1 entries atomically
    _l1_epochs: dict[str, int] = {}
except ImportError:  # cachetools not installed → fall back to no L1
    _LRUCache = None  # type: ignore[assignment,misc]
    _l1_cache = None
    _l1_epochs = {}


def _l1_key(family: str, key_suffix: str) -> tuple[str, int, str]:
    """Composite L1 key includes the family's epoch so version-bumps invalidate it."""
    return (family, _l1_epochs.get(family, 0), key_suffix)


def _l1_get(family: str, key_suffix: str) -> str | None:
    if _l1_cache is None:
        return None
    item = _l1_cache.get(_l1_key(family, key_suffix))
    return item[0] if item is not None else None


def _l1_set(family: str, key_suffix: str, value: str) -> None:
    if _l1_cache is None:
        return
    # Bound by value size to prevent one huge payload from evicting everything useful
    if len(value) > 256 * 1024:  # 256KB
        return
    _l1_cache[_l1_key(family, key_suffix)] = (value, time.time())


def _l1_bump_epoch(family: str) -> None:
    """Atomically invalidate all L1 entries for a family by bumping its epoch."""
    if _l1_cache is None:
        return
    _l1_epochs[family] = _l1_epochs.get(family, 0) + 1
    # Drop entries from the old epoch. With maxsize=256 and ~5 families, the
    # stale entries naturally fall out under pressure. Bumping the epoch
    # makes them unreachable by key, so they're effectively dead.
    # For aggressive invalidation, clear the whole L1 (rare, single-process).
    if _l1_cache.currsize > L1_MAX_SIZE * 0.8:
        _l1_cache.clear()


def l1_stats() -> dict:
    if _l1_cache is None:
        return {"enabled": False}
    return {
        "enabled": True,
        "max_size": L1_MAX_SIZE,
        "curr_size": _l1_cache.currsize,
        "epochs": dict(_l1_epochs),
    }


_redis = None

try:
    import redis.asyncio as aioredis
    from redis.asyncio import Redis
except ImportError:
    aioredis = None
    Redis = None


async def get_redis():
    """Return shared Redis connection, or None if unavailable."""
    global _redis
    if _redis is not None:
        try:
            await _redis.ping()
            return _redis
        except Exception:
            _redis = None

    try:
        _redis = aioredis.from_url(
            settings.REDIS_URL,
            socket_connect_timeout=3,
            socket_timeout=3,
            decode_responses=True,
        )
        await _redis.ping()
        return _redis
    except Exception:
        logger.warning("Redis unavailable at %s — caching disabled", settings.REDIS_URL)
        _redis = None
        return None


async def cache_get(key: str) -> str | None:
    r = await get_redis()
    if r is None:
        return None
    try:
        return await r.get(f"aierp:{key}")
    except Exception:
        logger.debug("cache_get failed for key=%s", key)
        return None


async def cache_set(key: str, value: str, ttl: int = 300) -> None:
    r = await get_redis()
    if r is None:
        return
    try:
        await r.setex(f"aierp:{key}", ttl, value)
    except Exception:
        logger.debug("cache_set failed for key=%s", key)


async def cache_delete(pattern: str) -> None:
    """Legacy KEYS-based deletion. Prefer cache_bump_version for hot paths."""
    r = await get_redis()
    if r is None:
        return
    try:
        keys = await r.keys(f"aierp:{pattern}")
        if keys:
            await r.delete(*keys)
    except Exception:
        logger.debug("cache_delete failed for pattern=%s", pattern)


async def cache_bump_version(family: str) -> int:
    """Atomically bump a family's version counter; returns new value.

    Use this instead of `cache_delete(f"{family}:*")` to invalidate all entries
    of a family. Old entries stay in Redis but become unreachable; they expire
    on their TTL.
    """
    r = await get_redis()
    if r is None:
        _l1_bump_epoch(family)
        return 0
    try:
        new_value = int(await r.incr(f"aierp:v:{family}"))
        cache_invalidations_total.inc(family=family)
        _l1_bump_epoch(family)
        return new_value
    except Exception:
        logger.debug("cache_bump_version failed for family=%s", family)
        _l1_bump_epoch(family)
        return 0


async def cache_get_versioned(family: str, key_suffix: str) -> str | None:
    """Get a versioned entry: returns the value at `family:v{N}:key_suffix`.

    Bumping the family version atomically invalidates all entries.
    Two-level: L1 (in-process LRU) → L2 (Redis).
    """
    start = time.perf_counter()
    l1_value = _l1_get(family, key_suffix)
    if l1_value is not None:
        cache_hits_total.inc(family=family)
        elapsed = time.perf_counter() - start
        cache_lookup_duration_seconds.observe(elapsed, family=family, outcome="hit_l1")
        return l1_value
    r = await get_redis()
    if r is None:
        return None
    try:
        version = await r.get(f"aierp:v:{family}")
        if version is None:
            version = "1"
        value = await r.get(f"aierp:{family}:v{version}:{key_suffix}")
        if value is not None:
            _l1_set(family, key_suffix, value)
            cache_hits_total.inc(family=family)
            outcome = "hit_l2"
        else:
            cache_misses_total.inc(family=family)
            outcome = "miss"
        elapsed = time.perf_counter() - start
        cache_lookup_duration_seconds.observe(elapsed, family=family, outcome=outcome)
        return value
    except Exception:
        logger.debug(
            "cache_get_versioned failed for family=%s key=%s", family, key_suffix
        )
        return None


async def cache_set_versioned(
    family: str, key_suffix: str, value: str, ttl: int = 300
) -> None:
    """Set a versioned entry."""
    _l1_set(family, key_suffix, value)
    r = await get_redis()
    if r is None:
        return
    try:
        version = await r.get(f"aierp:v:{family}")
        if version is None:
            await r.set(f"aierp:v:{family}", "1")
            version = "1"
        await r.setex(f"aierp:{family}:v{version}:{key_suffix}", ttl, value)
    except Exception:
        logger.debug("cache_set_versioned failed for family=%s", family)


async def cached(key: str, ttl: int = 300, factory=None):
    """Get from cache, or compute and store. Returns (value, was_cached)."""
    cached_val = await cache_get(key)
    if cached_val is not None:
        return json.loads(cached_val), True
    if factory is None:
        return None, False
    result = await factory()
    if result is not None:
        await cache_set(key, json.dumps(result, default=str), ttl)
    return result, False
