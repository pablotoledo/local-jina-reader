from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends, HTTPException, Header
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
from app.routers import reader, health
from app.services import ml_engine


def _verify_token(authorization: str | None = Header(default=None)):
    if not settings.internal_token:
        return
    if authorization != f"Bearer {settings.internal_token}":
        raise HTTPException(status_code=401, detail="Unauthorized")


@asynccontextmanager
async def lifespan(app: FastAPI):
    ml_engine.load_model()  # blocks until the model is ready
    yield


app = FastAPI(
    title="intranet-reader",
    description="URL → Markdown/JSON using ReaderLM-v2 (100% local)",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(reader.router, dependencies=[Depends(_verify_token)])
