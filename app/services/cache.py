import hashlib
import json
import redis.asyncio as aioredis
from app.config import settings


def _key(url: str) -> str:
    return f"reader:v1:{hashlib.sha256(url.encode()).hexdigest()}"


async def get_cached(url: str) -> dict | None:
    if not settings.cache_ttl_seconds:
        return None
    client = aioredis.from_url(settings.redis_url, decode_responses=True)
    try:
        raw = await client.get(_key(url))
        return json.loads(raw) if raw else None
    finally:
        await client.aclose()


async def set_cached(url: str, data: dict) -> None:
    if not settings.cache_ttl_seconds:
        return
    client = aioredis.from_url(settings.redis_url, decode_responses=True)
    try:
        await client.setex(
            _key(url), settings.cache_ttl_seconds, json.dumps(data, default=str)
        )
    finally:
        await client.aclose()
