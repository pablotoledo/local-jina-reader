"""Basic rate limiting using Redis sliding window counters."""
import time
import structlog
import redis.asyncio as aioredis
from app.core.cache import _get_redis

log = structlog.get_logger()


async def check_rate_limit(identifier: str, max_requests: int = 60, window_s: int = 60) -> bool:
    """Return True if request is allowed, False if rate limit exceeded."""
    try:
        redis = _get_redis()
        key = f"rl:{identifier}:{int(time.time()) // window_s}"
        count = await redis.incr(key)
        if count == 1:
            await redis.expire(key, window_s * 2)
        return count <= max_requests
    except Exception as exc:
        log.warning("rate_limit_error", identifier=identifier, error=str(exc))
        return True  # fail open
