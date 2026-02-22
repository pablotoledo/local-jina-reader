import time
from fastapi import APIRouter
from fastapi.responses import PlainTextResponse
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST
from app.core.cache import ping_redis

router = APIRouter(tags=["ops"])


@router.get("/healthz", summary="Liveness probe")
async def healthz():
    return {"ok": True}


@router.get("/readyz", summary="Readiness probe")
async def readyz():
    redis_ok = await ping_redis()
    return {"ready": redis_ok, "redis": redis_ok}


@router.get("/metrics", summary="Prometheus metrics")
async def metrics():
    data = generate_latest()
    return PlainTextResponse(data.decode(), media_type=CONTENT_TYPE_LATEST)
