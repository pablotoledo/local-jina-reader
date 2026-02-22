# DRIVEN SPEC — `intranet-reader` (ReaderLM-v2 Edition)

> Internal service that converts any URL into clean Markdown/JSON using **`jinaai/ReaderLM-v2`** running **100% locally**. No external calls. No API keys. FastAPI + Poetry + Docker Compose.

---

## 1. Context

### What is ReaderLM-v2?

[`jinaai/ReaderLM-v2`](https://huggingface.co/jinaai/ReaderLM-v2) is the model that **powers** `r.jina.ai` internally. It is open-weight, and we can run it on our own server.

| Feature | Detail |
|---|---|
| **Parameters** | 1.5B (base: Qwen2.5-1.5B-Instruction) |
| **Task** | Raw HTML → Markdown **or** JSON |
| **Context** | Up to 512K input + output tokens |
| **Languages** | 29 (including Spanish) |
| **License** | `cc-by-nc-4.0` ⚠️ — **non-commercial** use |
| **Weights** | ~3 GB (safetensors float32) |
| **CPU** | Works, slow (~5-15 s/simple page) |
| **Recommended GPU** | Free T4 (Colab), RTX 3090/4090 production |

> ⚠️ **cc-by-nc-4.0 License**: Free for internal/intranet non-commercial use. If your intranet is part of a business generating direct income with this service, check with your legal team.

---

### Full Pipeline

```
GET /r/{url}  ──▶  1. httpx fetch HTML
                   2. regex clean HTML    (official patterns from ReaderLM-v2 README)
                   3. ReaderLM-v2 infer   (run_in_executor → does not block event loop)
                   4. cache Redis
                        ▼
                   Markdown / JSON
```

The model is loaded **only once** at startup (`lifespan`) and stays in memory. Concurrent requests are queued via `asyncio.run_in_executor`.

---

## 2. Repository Structure

```
intranet-reader/
├── DRIVEN_SPEC.md
├── README.md
├── pyproject.toml
├── poetry.lock
├── .env.example
├── Dockerfile
├── docker-compose.yml
├── docker-compose.override.yml
├── app/
│   ├── __init__.py
│   ├── main.py
│   ├── config.py
│   ├── routers/
│   │   ├── __init__.py
│   │   ├── reader.py
│   │   └── health.py
│   ├── services/
│   │   ├── __init__.py
│   │   ├── reader_service.py
│   │   ├── html_fetcher.py
│   │   ├── ml_engine.py
│   │   └── cache.py
│   └── models/
│       ├── __init__.py
│       └── schemas.py
└── tests/
    ├── __init__.py
    ├── test_health.py
    └── test_reader.py
```

### Docker Compose Services

| Service | Role | Port |
|---|---|---|
| `api` | FastAPI + ReaderLM-v2 | `8000` |
| `redis` | Results cache | `6379` |

Model weights (~3 GB) are persisted in the `hf-cache` Docker volume. They are only downloaded the first time.

---

## 3. API

### `GET /r/{url:path}`

```
GET /r/https://example.com
Accept: text/markdown          # default — returns plain Markdown
Accept: application/json       # returns structured JSON
x-no-cache: true               # skip Redis cache
```

**Markdown Response (200):**
```
Title: Example Domain

# Example Domain

This domain is for use in illustrative examples...

Source: https://example.com
```

**JSON Response (200):**
```json
{
  "url": "https://example.com",
  "title": "Example Domain",
  "content": "# Example Domain\n\nThis domain is for...",
  "usage": { "tokens": 312 },
  "cached": false,
  "fetched_at": "2026-02-22T10:00:00+00:00"
}
```

### `POST /r`

For URLs with fragments (`#`) or special needs:

```json
{ "url": "https://example.com/#/path", "accept": "application/json", "no_cache": false }
```

### `GET /health`

```json
{
  "status": "ok",
  "model": "jinaai/ReaderLM-v2",
  "model_loaded": true,
  "device": "cpu",
  "redis": "connected",
  "version": "0.1.0"
}
```

---

## 4. Code Files

### `pyproject.toml`

```toml
[tool.poetry]
name = "intranet-reader"
version = "0.1.0"
description = "Self-hosted URL-to-Markdown using ReaderLM-v2"
authors = ["Your Name <your@email.com>"]
readme = "README.md"
packages = [{include = "app"}]

[tool.poetry.dependencies]
python           = "^3.11"
fastapi          = "^0.115"
uvicorn          = {extras = ["standard"], version = "^0.34"}
httpx            = "^0.27"
pydantic-settings = "^2.5"
redis            = {extras = ["hiredis"], version = "^5.0"}
# ML stack
torch            = {version = "^2.3", source = "pytorch-cpu"}
transformers     = "^4.44"
accelerate       = "^0.34"

[tool.poetry.group.dev.dependencies]
pytest           = "^8.3"
pytest-asyncio   = "^0.24"
ruff             = "^0.8"

[[tool.poetry.source]]
name     = "pytorch-cpu"
url      = "https://download.pytorch.org/whl/cpu"
priority = "explicit"

[build-system]
requires = ["poetry-core"]
build-backend = "poetry.core.masonry.api"

[tool.pytest.ini_options]
asyncio_mode = "auto"
```

> **GPU**: Change torch source to `https://download.pytorch.org/whl/cu121` and use `nvidia/cuda` base image in the Dockerfile.

---

### `.env.example`

```dotenv
# API
APP_PORT=8000
INTERNAL_TOKEN=

# Model
HF_MODEL_ID=jinaai/ReaderLM-v2
HF_HOME=/root/.cache/huggingface
DEVICE=cpu
MAX_NEW_TOKENS=4096
TORCH_DTYPE=float32

# Cache
REDIS_URL=redis://redis:6379/0
CACHE_TTL_SECONDS=3600

# Fetcher
FETCH_TIMEOUT_SECONDS=30
FETCH_USER_AGENT=intranet-reader/0.1
```

---

### `app/config.py`

```python
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    app_port: int = 8000
    internal_token: str = ""

    hf_model_id: str = "jinaai/ReaderLM-v2"
    hf_home: str = "/root/.cache/huggingface"
    device: str = "cpu"
    max_new_tokens: int = 4096
    torch_dtype: str = "float32"

    redis_url: str = "redis://redis:6379/0"
    cache_ttl_seconds: int = 3600

    fetch_timeout_seconds: int = 30
    fetch_user_agent: str = "intranet-reader/0.1"


settings = Settings()
```

---

### `app/services/html_fetcher.py`

Downloads and cleans HTML with the same regex patterns recommended by the official ReaderLM-v2 README.

```python
import re
import httpx
from app.config import settings

# Patterns extracted from jinaai/ReaderLM-v2 README
SCRIPT_PATTERN     = r"<[ ]*script.*?\/[ ]*script[ ]*>"
STYLE_PATTERN      = r"<[ ]*style.*?\/[ ]*style[ ]*>"
META_PATTERN       = r"<[ ]*meta.*?>"
COMMENT_PATTERN    = r"<[ ]*!--.*?--[ ]*>"
LINK_PATTERN       = r"<[ ]*link.*?>"
BASE64_IMG_PATTERN = r'<img[^>]+src="data:image/[^;]+;base64,[^"]+"[^>]*>'
SVG_PATTERN        = r"(<svg[^>]*>)(.*?)(<\/svg>)"
FLAGS              = re.IGNORECASE | re.DOTALL


def clean_html(html: str) -> str:
    html = re.sub(SCRIPT_PATTERN,     "",                           html, flags=FLAGS)
    html = re.sub(STYLE_PATTERN,      "",                           html, flags=FLAGS)
    html = re.sub(META_PATTERN,       "",                           html, flags=FLAGS)
    html = re.sub(COMMENT_PATTERN,    "",                           html, flags=FLAGS)
    html = re.sub(LINK_PATTERN,       "",                           html, flags=FLAGS)
    html = re.sub(BASE64_IMG_PATTERN, "<img/>",                     html, flags=FLAGS)
    html = re.sub(SVG_PATTERN,        r"\1this is a placeholder\3", html, flags=FLAGS)
    return html.strip()


async def fetch_html(url: str) -> tuple[str, str]:
    """Returns (clean_html, title)"""
    headers = {"User-Agent": settings.fetch_user_agent}
    async with httpx.AsyncClient(
        timeout=settings.fetch_timeout_seconds,
        follow_redirects=True,
    ) as client:
        r = await client.get(url, headers=headers)
        r.raise_for_status()

    title = ""
    m = re.search(r"<title[^>]*>(.*?)<\/title>", r.text, re.IGNORECASE | re.DOTALL)
    if m:
        title = re.sub(r"<[^>]+>", "", m.group(1)).strip()

    return clean_html(r.text), title
```

---

### `app/services/ml_engine.py`

```python
import asyncio
import os
from functools import partial
from typing import Literal

import torch
from transformers import AutoModelForCausalLM, AutoTokenizer

from app.config import settings

_tokenizer = None
_model = None


def load_model() -> None:
    global _tokenizer, _model
    os.environ["HF_HOME"] = settings.hf_home
    dtype = torch.float16 if settings.torch_dtype == "float16" else torch.float32

    print(f"[ml_engine] Loading {settings.hf_model_id} → device={settings.device} dtype={dtype}")
    _tokenizer = AutoTokenizer.from_pretrained(settings.hf_model_id)
    _model = AutoModelForCausalLM.from_pretrained(
        settings.hf_model_id,
        torch_dtype=dtype,
    ).to(settings.device)
    _model.eval()
    print("[ml_engine] Model ready ✓")


def _infer_sync(html: str, output_format: Literal["markdown", "json"]) -> str:
    """Blocking — always execute in run_in_executor."""
    if output_format == "json":
        prompt = (
            "Extract the main content of the following HTML and return a JSON object "
            "with keys: title, description, content (markdown string).\n\n" + html
        )
    else:
        prompt = html  # HTML→Markdown: no instruction, just the HTML

    messages = [{"role": "user", "content": prompt}]
    input_text = _tokenizer.apply_chat_template(
        messages, tokenize=False, add_generation_prompt=True
    )
    inputs = _tokenizer.encode(input_text, return_tensors="pt").to(settings.device)

    with torch.no_grad():
        outputs = _model.generate(
            inputs,
            max_new_tokens=settings.max_new_tokens,
            temperature=0,
            do_sample=False,
            repetition_penalty=1.08,
        )

    new_tokens = outputs[0][inputs.shape[1]:]
    return _tokenizer.decode(new_tokens, skip_special_tokens=True).strip()


async def html_to_markdown(html: str) -> str:
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, partial(_infer_sync, html, "markdown"))


async def html_to_json_str(html: str) -> str:
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, partial(_infer_sync, html, "json"))
```

---

### `app/services/cache.py`

```python
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
        await client.setex(_key(url), settings.cache_ttl_seconds, json.dumps(data, default=str))
    finally:
        await client.aclose()
```

---

### `app/services/reader_service.py`

```python
from datetime import datetime, timezone
from app.services.cache import get_cached, set_cached
from app.services.html_fetcher import fetch_html
from app.services.ml_engine import html_to_markdown, html_to_json_str


async def read_url(url: str, as_json: bool = False, no_cache: bool = False) -> dict:
    cache_key = f"{url}:{'json' if as_json else 'md'}"

    if not no_cache:
        cached = await get_cached(cache_key)
        if cached:
            cached["cached"] = True
            return cached

    html, title = await fetch_html(url)
    content = await html_to_json_str(html) if as_json else await html_to_markdown(html)

    data = {
        "url": url,
        "title": title,
        "content": content,
        "usage": {"tokens": len(content.split())},
        "cached": False,
        "fetched_at": datetime.now(timezone.utc).isoformat(),
    }
    await set_cached(cache_key, data)
    return data
```

---

### `app/routers/reader.py`

```python
from fastapi import APIRouter, Header
from fastapi.responses import PlainTextResponse, JSONResponse
from app.models.schemas import ReadRequest
from app.services.reader_service import read_url

router = APIRouter()


@router.get("/r/{url:path}")
async def read_get(
    url: str,
    accept: str = Header(default="text/markdown"),
    x_no_cache: bool = Header(default=False, alias="x-no-cache"),
):
    as_json = "application/json" in accept
    data = await read_url(url, as_json=as_json, no_cache=x_no_cache)
    if as_json:
        return JSONResponse(content=data)
    return PlainTextResponse(
        f"Title: {data['title']}\n\n{data['content']}\n\nSource: {data['url']}"
    )


@router.post("/r")
async def read_post(body: ReadRequest):
    as_json = body.accept == "application/json"
    data = await read_url(body.url, as_json=as_json, no_cache=body.no_cache)
    if as_json:
        return JSONResponse(content=data)
    return PlainTextResponse(
        f"Title: {data['title']}\n\n{data['content']}\n\nSource: {data['url']}"
    )
```

---

### `app/routers/health.py`

```python
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
```

---

### `app/main.py`

```python
from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
from app.routers import reader, health
from app.services import ml_engine


def _verify_token(authorization: str | None = None):
    if not settings.internal_token:
        return
    if authorization != f"Bearer {settings.internal_token}":
        raise HTTPException(status_code=401, detail="Unauthorized")


@asynccontextmanager
async def lifespan(app: FastAPI):
    ml_engine.load_model()   # blocks until the model is ready
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
```

---

### `Dockerfile`

```dockerfile
FROM python:3.11-slim AS builder

RUN pip install poetry==1.8.3
WORKDIR /app
COPY pyproject.toml poetry.lock* ./
RUN poetry config virtualenvs.in-project true \
    && poetry install --no-interaction --no-ansi --only main

FROM python:3.11-slim
WORKDIR /app
COPY --from=builder /app/.venv .venv
COPY app/ ./app/

ENV PATH="/app/.venv/bin:$PATH"
ENV PYTHONUNBUFFERED=1
ENV HF_HOME=/root/.cache/huggingface

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

---

### `docker-compose.yml`

```yaml
services:
  api:
    build: .
    container_name: intranet-reader-api
    restart: unless-stopped
    ports:
      - "${APP_PORT:-8000}:8000"
    env_file: .env
    volumes:
      - hf-cache:/root/.cache/huggingface   # persisted model weights
    depends_on:
      redis:
        condition: service_healthy
    networks:
      - reader-net
    # GPU — uncomment if you have NVIDIA Container Toolkit
    # deploy:
    #   resources:
    #     reservations:
    #       devices:
    #         - driver: nvidia
    #           count: 1
    #           capabilities: [gpu]

  redis:
    image: redis:7-alpine
    container_name: intranet-reader-redis
    restart: unless-stopped
    volumes:
      - redis-data:/data
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 5s
      timeout: 3s
      retries: 5
    networks:
      - reader-net

volumes:
  hf-cache:      # ~3 GB — ReaderLM-v2 weights
  redis-data:

networks:
  reader-net:
    driver: bridge
```

---

### `docker-compose.override.yml` (development)

```yaml
services:
  api:
    volumes:
      - ./app:/app/app
      - hf-cache:/root/.cache/huggingface
    command: uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
    environment:
      APP_ENV: development
```

---

## 5. Tests

### `tests/test_health.py`

```python
from unittest.mock import patch

with patch("app.services.ml_engine.load_model", return_value=None):
    from app.main import app

from fastapi.testclient import TestClient
client = TestClient(app)


def test_health():
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"
```

### `tests/test_reader.py`

```python
from unittest.mock import patch, AsyncMock

MOCK = {
    "url": "https://example.com",
    "title": "Example Domain",
    "content": "# Example\n\nThis domain is for illustrative examples.",
    "usage": {"tokens": 12},
    "cached": False,
    "fetched_at": "2026-02-22T10:00:00+00:00",
}

with patch("app.services.ml_engine.load_model", return_value=None):
    from app.main import app

from fastapi.testclient import TestClient
client = TestClient(app)


@patch("app.routers.reader.read_url", new_callable=AsyncMock, return_value=MOCK)
def test_markdown(mock_read):
    r = client.get("/r/https://example.com")
    assert r.status_code == 200
    assert "Example Domain" in r.text


@patch("app.routers.reader.read_url", new_callable=AsyncMock, return_value=MOCK)
def test_json(mock_read):
    r = client.get("/r/https://example.com", headers={"Accept": "application/json"})
    assert r.status_code == 200
    assert r.json()["title"] == "Example Domain"
```

---

## 6. Estimated Performance

| Scenario | p50 Latency | Notes |
|---|---|---|
| CPU — simple page (~500 tokens) | 5–15 s | Sufficient for intranet |
| CPU — long page (~5K tokens) | 30–90 s | Use aggressive caching |
| GPU T4 | ~3 s | Google Colab free tier |
| GPU RTX 3090/4090 | ~1 s | Recommended for production |
| Redis cache hit | < 50 ms | — |

**Intranet Tip:** with `CACHE_TTL_SECONDS=86400` (24h) most internal pages are served from cache in milliseconds.

---

## 7. Checklist

```
[ ] git init intranet-reader && cd intranet-reader
[ ] Create directory structure
[ ] Copy all spec files
[ ] poetry install  (installs dependencies locally for dev)
[ ] cp .env.example .env  → adjust DEVICE, MAX_NEW_TOKENS
[ ] docker compose up -d --build
[ ] Wait for the first model download (~3 GB, ~5 min)
[ ] curl http://localhost:8000/health  → "model_loaded": true
[ ] curl http://localhost:8000/r/https://example.com
[ ] poetry run pytest
[ ] (Optional) DEVICE=cuda + TORCH_DTYPE=float16 for GPU
[ ] (Optional) INTERNAL_TOKEN for internal auth
[ ] (Optional) Expose via nginx on the intranet
```

---

## 8. References

| Resource | URL |
|---|---|
| ReaderLM-v2 — HuggingFace | https://huggingface.co/jinaai/ReaderLM-v2 |
| Paper arXiv 2503.01151 | https://arxiv.org/abs/2503.01151 |
| jina-ai/reader — GitHub | https://github.com/jina-ai/reader |
| FastAPI | https://fastapi.tiangolo.com |
| Poetry | https://python-poetry.org |
| HuggingFace Transformers | https://huggingface.co/docs/transformers |

---

> **Spec Version:** 0.2.0 · Date: 2026-02-22 · Engine: Local ReaderLM-v2 (cc-by-nc-4.0)