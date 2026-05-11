"""Redis cache service — provides async get/set/delete with graceful degradation."""
import json
import logging

from app.config import settings

logger = logging.getLogger(__name__)

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
    r = await get_redis()
    if r is None:
        return
    try:
        keys = await r.keys(f"aierp:{pattern}")
        if keys:
            await r.delete(*keys)
    except Exception:
        logger.debug("cache_delete failed for pattern=%s", pattern)


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
