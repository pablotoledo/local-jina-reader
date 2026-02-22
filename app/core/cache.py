import orjson
from typing import Any

import redis.asyncio as aioredis
import structlog

from app.core.config import settings

log = structlog.get_logger()
_redis: aioredis.Redis | None = None


def _get_redis() -> aioredis.Redis:
    global _redis
    if _redis is None:
        _redis = aioredis.from_url(settings.REDIS_URL, encoding="utf-8", decode_responses=False)
    return _redis


async def ping_redis() -> bool:
    try:
        return await _get_redis().ping()
    except Exception as exc:
        log.warning("redis_ping_failed", error=str(exc))
        return False


async def get_cached(key: str) -> dict | None:
    try:
        raw = await _get_redis().get(key)
        if raw is not None:
            return orjson.loads(raw)
    except Exception as exc:
        log.warning("cache_get_error", key=key, error=str(exc))
    return None


async def set_cached(key: str, value: Any, ttl: int = 300) -> None:
    try:
        await _get_redis().set(key, orjson.dumps(value), ex=ttl)
    except Exception as exc:
        log.warning("cache_set_error", key=key, error=str(exc))


async def invalidate(key: str) -> None:
    try:
        await _get_redis().delete(key)
    except Exception as exc:
        log.warning("cache_invalidate_error", key=key, error=str(exc))
