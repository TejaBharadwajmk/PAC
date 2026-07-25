"""
PAC — Redis Query Caching Module

Provides an async Redis caching layer and @cache_response decorator
for heavy analytical endpoints (Geo Hotspots, Graph Traversals, Predictions).
"""

import hashlib
import json
import logging
from functools import wraps
from typing import Any, Callable, Optional, Dict

import redis.asyncio as redis
from fastapi import Response
from pydantic import BaseModel

from app.config import settings

logger = logging.getLogger(__name__)

# Global Redis client singleton
_redis_client: Optional[redis.Redis] = None


def get_redis_client() -> Optional[redis.Redis]:
    """Retrieve or initialize the thread-safe async Redis client singleton."""
    global _redis_client
    if _redis_client is None and settings.REDIS_URL:
        try:
            _redis_client = redis.from_url(
                settings.REDIS_URL,
                encoding="utf-8",
                decode_responses=True,
                socket_timeout=2.0,
            )
        except Exception as exc:
            logger.warning(f"Failed to initialize Redis client: {exc}")
            return None
    return _redis_client


def _is_cacheable_val(val: Any) -> bool:
    return isinstance(val, (str, int, float, bool, type(None), list, dict)) or hasattr(val, "value") or hasattr(val, "hex")


def _make_cache_key(namespace: str, func_name: str, args: tuple, kwargs: dict) -> str:
    """Generate a deterministic Redis key: pac:cache:{namespace}:{md5_hash}."""
    clean_args = [str(a) for a in args if _is_cacheable_val(a)]
    clean_kwargs = {
        k: (v.value if hasattr(v, "value") else str(v))
        for k, v in sorted(kwargs.items())
        if _is_cacheable_val(v)
    }
    serialized = json.dumps({"args": clean_args, "kwargs": clean_kwargs}, sort_keys=True)
    digest = hashlib.md5(f"{func_name}:{serialized}".encode("utf-8")).hexdigest()
    return f"pac:cache:{namespace}:{digest}"


def cache_response(ttl_seconds: int = 300, namespace: str = "default"):
    """
    Decorator for FastAPI endpoints to cache JSON/Pydantic responses in Redis.

    Args:
        ttl_seconds: Cache time-to-live in seconds.
        namespace: Logical namespace for key grouping and pattern invalidation.
    """
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            client = get_redis_client()

            # If Redis client is unavailable, bypass caching and call live function
            if client is None:
                return await func(*args, **kwargs)

            cache_key = _make_cache_key(namespace, func.__name__, args, kwargs)

            # ── 1. Attempt Cache Read ──────────────────────────────────
            try:
                cached_data = await client.get(cache_key)
                if cached_data:
                    logger.info(f"[Redis Cache HIT] key={cache_key}")
                    parsed = json.loads(cached_data)
                    return parsed
            except Exception as exc:
                logger.warning(f"[Redis Cache Read Error] {exc} — falling through to live query")

            # ── 2. Execute Live Endpoint Handler ───────────────────────
            logger.info(f"[Redis Cache MISS] key={cache_key} — executing live handler")
            try:
                result = await func(*args, **kwargs)
            except Exception as exc:
                logger.error(f"[Redis Cache Handler Error] func={func.__name__} error={exc}", exc_info=True)
                raise exc

            # ── 3. Populate Redis Cache ───────────────────────────────
            try:
                if isinstance(result, BaseModel):
                    payload_json = result.model_dump_json()
                elif isinstance(result, list):
                    clean_list = [item.model_dump() if isinstance(item, BaseModel) else item for item in result]
                    payload_json = json.dumps(clean_list, default=str)
                elif isinstance(result, dict):
                    payload_json = json.dumps(result, default=str)
                else:
                    payload_json = str(result)

                await client.setex(cache_key, ttl_seconds, payload_json)
                logger.debug(f"[Redis Cache SET] key={cache_key} ttl={ttl_seconds}s")
            except Exception as exc:
                logger.warning(f"[Redis Cache Write Error] {exc}")

            return result

        return wrapper
    return decorator


async def invalidate_cache_pattern(pattern: str) -> int:
    """
    Scan and delete all Redis cache keys matching a glob pattern (e.g. 'pac:cache:geo:*').
    Returns count of deleted keys.
    """
    client = get_redis_client()
    if client is None:
        return 0

    deleted_count = 0
    try:
        keys = []
        async for key in client.scan_iter(match=pattern):
            keys.append(key)
        if keys:
            deleted_count = await client.delete(*keys)
            logger.info(f"[Redis Cache Invalidation] Pattern={pattern!r} deleted {deleted_count} keys")
    except Exception as exc:
        logger.warning(f"[Redis Cache Invalidation Error] {exc}")

    return deleted_count
