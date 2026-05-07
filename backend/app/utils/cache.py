"""Simple TTL cache for API endpoints."""

import time
from collections.abc import Callable
from functools import wraps


_cache: dict[str, tuple[float, object]] = {}


def ttl_cache(seconds: int = 30):
    """Decorator: caches async function results for `seconds` TTL."""
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            key = f"{func.__module__}.{func.__qualname__}:{args}:{sorted(kwargs.items())}"
            now = time.time()
            if key in _cache:
                expiry, value = _cache[key]
                if now < expiry:
                    return value
                del _cache[key]
            result = await func(*args, **kwargs)
            _cache[key] = (now + seconds, result)
            return result
        return wrapper
    return decorator


def invalidate_cache(prefix: str = ""):
    """Clear all cached entries, optionally filtered by key prefix."""
    if not prefix:
        _cache.clear()
    else:
        for key in list(_cache):
            if key.startswith(prefix):
                del _cache[key]
