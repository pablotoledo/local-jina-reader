from contextlib import asynccontextmanager
import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes_reader import router as reader_router
from app.api.routes_ops import router as ops_router
from app.core.config import settings
from app.core.logging import configure_logging


@asynccontextmanager
async def lifespan(app: FastAPI):
    configure_logging()
    log = structlog.get_logger()
    log.info("startup", env=settings.APP_ENV)
    yield
    log.info("shutdown")


app = FastAPI(
    title="Reader Clone",
    description="Internal Jina-Reader-compatible service: URL → Markdown/JSON/SSE",
    version="0.1.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(ops_router)
app.include_router(reader_router)
