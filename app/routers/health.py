from fastapi import APIRouter
import redis.asyncio as aioredis
from app.config import settings
from app.services import ml_engine

router = APIRouter()


@router.get("/health")
async def health():
    redis_status = "disconnected"
    try:
        client = aioredis.from_url(settings.redis_url)
        await client.ping()
        await client.aclose()
        redis_status = "connected"
    except Exception:
        pass

    return {
        "status": "ok",
        "model": settings.hf_model_id,
        "model_loaded": ml_engine._model is not None,
        "device": settings.device,
        "redis": redis_status,
        "version": "0.1.0",
    }
