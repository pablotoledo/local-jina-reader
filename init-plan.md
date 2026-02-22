# DRIVEN SPEC — `intranet-reader`

> Internal service that replicates the functionality of **r.jina.ai**: converts any URL into clean, structured text ready for LLMs. Built with FastAPI + Poetry + Docker Compose. Zero mandatory external dependencies in production.

---

## 1. Context and Motivation

### What is r.jina.ai?

[Jina Reader](https://jina.ai/reader/) is a public service (Apache-2.0) by Jina AI that converts any URL into clean Markdown/JSON, optimized for RAG and LLM agents. Using it is as simple as prefixing the destination URL:

```
GET https://r.jina.ai/https://example.com
```

It returns the main content of the page as Markdown, removing noise (navbars, scripts, ads). It supports:

- Static pages and SPAs (via Puppeteer/headless Chrome)
- Native PDFs
- Search mode (`s.jina.ai`)
- JSON response (`Accept: application/json`)
- Streaming (`Accept: text/event-stream`)

### Why self-hosted?

| Reason | Detail |
|---|---|
| **Privacy** | Intranet URLs never leave the network |
| **Rate limits** | No external limits (RPM/TPM per IP) |
| **Latency** | No round-trip to external servers |
| **Control** | You can cache, audit, and extend |
| **No API key** | No quota usage for internal use |

### HuggingFace — Optional local model

[`jinaai/ReaderLM-v2`](https://huggingface.co/jinaai/ReaderLM-v2) is a 1.5B parameter model trained to convert raw HTML → Markdown/JSON. It enables a **completely offline** mode without calling `r.jina.ai`. It is the alternative when:

- The destination URL is accessible from the server but there is no internet access
- Total control of the extraction pipeline is needed

---

## 2. Architecture

```
┌─────────────────────────────────────────────────────┐
│                  intranet-reader                    │
│                                                     │
│  ┌──────────────┐     ┌────────────────────────┐   │
│  │   FastAPI    │────▶│   ReaderService        │   │
│  │   :8000      │     │  (strategy pattern)    │   │
│  └──────────────┘     └─────────┬──────────────┘   │
│                                 │                   │
│              ┌──────────────────┼──────────┐        │
│              ▼                  ▼          ▼        │
│        ┌──────────┐  ┌──────────────┐  ┌───────┐   │
│        │ JinaProxy│  │ LocalFetcher │  │ Cache │   │
│        │(r.jina.ai│  │(httpx+bs4)   │  │(Redis)│   │
│        │ fallback)│  │              │  │       │   │
│        └──────────┘  └──────────────┘  └───────┘   │
└─────────────────────────────────────────────────────┘
         Docker Compose — internal network
```

### Docker Compose Services

| Service | Image | Port | Role |
|---|---|---|---|
| `api` | local build | `8000` | Main FastAPI |
| `redis` | `redis:7-alpine` | `6379` | Results cache |

> **Note:** The ReaderLM-v2 model is optional (`profiles: [ml]`) and requires a GPU. For CPU-only, the local fetcher or the proxy to Jina Cloud is used.

---

## 3. Repository Structure

```
intranet-reader/
├── DRIVEN_SPEC.md          ← this document
├── README.md
├── pyproject.toml          ← Poetry
├── poetry.lock
├── .env.example
├── docker-compose.yml
├── docker-compose.override.yml   ← dev overrides
├── Dockerfile
├── app/
│   ├── __init__.py
│   ├── main.py             ← FastAPI app, lifespan
│   ├── config.py           ← Settings (pydantic-settings)
│   ├── routers/
│   │   ├── __init__.py
│   │   ├── reader.py       ← GET/POST /r/{url}
│   │   └── health.py       ← GET /health
│   ├── services/
│   │   ├── __init__.py
│   │   ├── reader_service.py    ← orchestrator
│   │   ├── jina_proxy.py        ← calls r.jina.ai
│   │   ├── local_fetcher.py     ← httpx + bs4 + markdownify
│   │   └── cache.py             ← Redis wrapper
│   ├── models/
│   │   ├── __init__.py
│   │   └── schemas.py      ← Pydantic models I/O
│   └── utils/
│       ├── __init__.py
│       └── html_cleaner.py ← optional HTML cleaning
└── tests/
    ├── __init__.py
    ├── test_reader.py
    └── test_health.py
```

---

## 4. API Contracts

### `GET /r/{url:path}`

Converts a URL into Markdown/JSON. Exactly mimics `r.jina.ai`.

**Request:**

```
GET /r/https://example.com
Authorization: Bearer <OPTIONAL_INTERNAL_TOKEN>
Accept: text/markdown          # default
Accept: application/json       # JSON mode
x-no-cache: true               # skip cache
x-timeout: 30                  # seconds
```

**Response 200 (Markdown):**

```
Title: Example Domain

This domain is for use in illustrative examples...

URL Source: https://example.com
```

**Response 200 (JSON):**

```json
{
  "url": "https://example.com",
  "title": "Example Domain",
  "content": "This domain is for use in illustrative examples...",
  "description": "...",
  "usage": { "tokens": 312 },
  "cached": false,
  "fetched_at": "2026-02-22T10:00:00Z"
}
```

**Errors:**

| Code | Cause |
|---|---|
| `422` | Invalid URL |
| `504` | Timeout retrieving the URL |
| `502` | Backend (Jina/fetcher) failed |

---

### `POST /r`

For URLs with fragments (`#`) or special parameters.

```json
{
  "url": "https://example.com/#/path",
  "accept": "application/json",
  "no_cache": false
}
```

---

### `GET /health`

```json
{
  "status": "ok",
  "redis": "connected",
  "version": "0.1.0"
}
```

---

## 5. Configuration — `.env.example`

```dotenv
# ── Application ─────────────────────────────────────
APP_ENV=production
APP_PORT=8000
INTERNAL_TOKEN=              # leave empty = no auth

# ── Reading Strategy ────────────────────────────────
# "proxy"  → delegate to r.jina.ai (requires internet access)
# "local"  → httpx + bs4 + markdownify (no internet)
# "auto"   → tries local, fallback to proxy
READER_STRATEGY=auto

# ── Jina Cloud (only if READER_STRATEGY=proxy or auto) ─
JINA_API_KEY=                # optional; no key = free tier

# ── Cache ───────────────────────────────────────────
REDIS_URL=redis://redis:6379/0
CACHE_TTL_SECONDS=3600       # 0 = disabled

# ── Local Fetcher ───────────────────────────────────
FETCH_TIMEOUT_SECONDS=30
FETCH_USER_AGENT=intranet-reader/0.1
```

---

## 6. Code Files — complete specification

### `pyproject.toml`

```toml
[tool.poetry]
name = "intranet-reader"
version = "0.1.0"
description = "Self-hosted r.jina.ai for intranet"
authors = ["Your Name <your@email.com>"]
readme = "README.md"
packages = [{include = "app"}]

[tool.poetry.dependencies]
python = "^3.11"
fastapi = "^0.115"
uvicorn = {extras = ["standard"], version = "^0.34"}
httpx = "^0.27"
beautifulsoup4 = "^4.12"
markdownify = "^0.13"
redis = {extras = ["hiredis"], version = "^5.0"}
pydantic-settings = "^2.5"
lxml = "^5.3"

[tool.poetry.group.dev.dependencies]
pytest = "^8.3"
pytest-asyncio = "^0.24"
httpx = "^0.27"          # async TestClient
ruff = "^0.8"
mypy = "^1.13"

[build-system]
requires = ["poetry-core"]
build-backend = "poetry.core.masonry.api"

[tool.pytest.ini_options]
asyncio_mode = "auto"

[tool.ruff]
line-length = 100
```

---

### `app/config.py`

```python
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Literal


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    app_env: str = "production"
    app_port: int = 8000
    internal_token: str = ""

    reader_strategy: Literal["proxy", "local", "auto"] = "auto"

    jina_api_key: str = ""
    jina_reader_base: str = "https://r.jina.ai"

    redis_url: str = "redis://redis:6379/0"
    cache_ttl_seconds: int = 3600

    fetch_timeout_seconds: int = 30
    fetch_user_agent: str = "intranet-reader/0.1"


settings = Settings()
```

---

### `app/models/schemas.py`

```python
from pydantic import BaseModel, HttpUrl
from datetime import datetime
from typing import Literal


class ReadRequest(BaseModel):
    url: str
    accept: Literal["text/markdown", "application/json"] = "text/markdown"
    no_cache: bool = False


class UsageInfo(BaseModel):
    tokens: int


class ReadResponse(BaseModel):
    url: str
    title: str
    content: str
    description: str = ""
    usage: UsageInfo
    cached: bool = False
    fetched_at: datetime
```

---

### `app/services/cache.py`

```python
import json
import hashlib
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
        await client.setex(_key(url), settings.cache_ttl_seconds, json.dumps(data))
    finally:
        await client.aclose()
```

---

### `app/services/local_fetcher.py`

```python
import httpx
from bs4 import BeautifulSoup
from markdownify import markdownify as md
from app.config import settings


async def fetch_as_markdown(url: str) -> dict:
    headers = {"User-Agent": settings.fetch_user_agent}
    async with httpx.AsyncClient(timeout=settings.fetch_timeout_seconds, follow_redirects=True) as client:
        resp = client.build_request("GET", url, headers=headers)
        r = await client.send(resp)
        r.raise_for_status()
        html = r.text

    soup = BeautifulSoup(html, "lxml")

    # clean noise
    for tag in soup(["script", "style", "nav", "footer", "aside", "header"]):
        tag.decompose()

    title = soup.title.string.strip() if soup.title else ""
    description = ""
    meta_desc = soup.find("meta", attrs={"name": "description"})
    if meta_desc and meta_desc.get("content"):
        description = meta_desc["content"]

    main = soup.find("main") or soup.find("article") or soup.body or soup
    content = md(str(main), heading_style="ATX", strip=["a"]).strip()
    tokens = len(content.split())

    return {
        "url": url,
        "title": title,
        "content": content,
        "description": description,
        "usage": {"tokens": tokens},
    }
```

---

### `app/services/jina_proxy.py`

```python
import httpx
from app.config import settings


async def fetch_via_jina(url: str) -> dict:
    target = f"{settings.jina_reader_base}/{url}"
    headers = {"Accept": "application/json"}
    if settings.jina_api_key:
        headers["Authorization"] = f"Bearer {settings.jina_api_key}"

    async with httpx.AsyncClient(timeout=settings.fetch_timeout_seconds) as client:
        r = await client.get(target, headers=headers)
        r.raise_for_status()
        data = r.json()

    # normalize Jina response
    return {
        "url": url,
        "title": data.get("data", {}).get("title", ""),
        "content": data.get("data", {}).get("content", ""),
        "description": data.get("data", {}).get("description", ""),
        "usage": {"tokens": data.get("data", {}).get("usage", {}).get("tokens", 0)},
    }
```

---

### `app/services/reader_service.py`

```python
from datetime import datetime, timezone
from app.config import settings
from app.services.cache import get_cached, set_cached
from app.services.local_fetcher import fetch_as_markdown
from app.services.jina_proxy import fetch_via_jina
import httpx


async def read_url(url: str, no_cache: bool = False) -> dict:
    if not no_cache:
        cached = await get_cached(url)
        if cached:
            cached["cached"] = True
            return cached

    data = await _fetch(url)
    data["cached"] = False
    data["fetched_at"] = datetime.now(timezone.utc).isoformat()

    await set_cached(url, data)
    return data


async def _fetch(url: str) -> dict:
    strategy = settings.reader_strategy

    if strategy == "local":
        return await fetch_as_markdown(url)

    if strategy == "proxy":
        return await fetch_via_jina(url)

    # auto: tries local, fallback to proxy
    try:
        return await fetch_as_markdown(url)
    except (httpx.HTTPError, Exception):
        return await fetch_via_jina(url)
```

---

### `app/routers/reader.py`

```python
from fastapi import APIRouter, Request, Header
from fastapi.responses import PlainTextResponse, JSONResponse
from app.services.reader_service import read_url
from app.models.schemas import ReadRequest

router = APIRouter()


@router.get("/r/{url:path}")
async def read_get(
    url: str,
    accept: str = Header(default="text/markdown"),
    x_no_cache: bool = Header(default=False),
):
    data = await read_url(url, no_cache=x_no_cache)
    if "application/json" in accept:
        return JSONResponse(content=data)
    # plain markdown
    return PlainTextResponse(
        content=f"Title: {data['title']}\n\n{data['content']}\n\nURL Source: {data['url']}"
    )


@router.post("/r")
async def read_post(body: ReadRequest):
    data = await read_url(body.url, no_cache=body.no_cache)
    if body.accept == "application/json":
        return JSONResponse(content=data)
    return PlainTextResponse(
        content=f"Title: {data['title']}\n\n{data['content']}\n\nURL Source: {data['url']}"
    )
```

---

### `app/routers/health.py`

```python
from fastapi import APIRouter
import redis.asyncio as aioredis
from app.config import settings

router = APIRouter()


@router.get("/health")
async def health():
    redis_status = "disconnected"
    try:
        client = aioredis.from_url(settings.redis_url)
        await client.ping()
        redis_status = "connected"
        await client.aclose()
    except Exception:
        pass

    return {
        "status": "ok",
        "redis": redis_status,
        "strategy": settings.reader_strategy,
        "version": "0.1.0",
    }
```

---

### `app/main.py`

```python
from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from app.routers import reader, health
from app.config import settings


def verify_token(authorization: str | None = None):
    if not settings.internal_token:
        return  # auth disabled
    if authorization != f"Bearer {settings.internal_token}":
        raise HTTPException(status_code=401, detail="Unauthorized")


@asynccontextmanager
async def lifespan(app: FastAPI):
    print(f"[intranet-reader] strategy={settings.reader_strategy}")
    yield


app = FastAPI(
    title="intranet-reader",
    description="Self-hosted r.jina.ai for internal use",
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
app.include_router(reader.router, dependencies=[Depends(verify_token)])
```

---

### `Dockerfile`

```dockerfile
FROM python:3.11-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl build-essential \
    && rm -rf /var/lib/apt/lists/*

RUN pip install poetry==1.8.3

WORKDIR /app

COPY pyproject.toml poetry.lock* ./

RUN poetry config virtualenvs.create false \
    && poetry install --no-interaction --no-ansi --only main

COPY app/ ./app/

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
    depends_on:
      redis:
        condition: service_healthy
    networks:
      - reader-net

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
      - ./app:/app/app       # hot-reload
    command: uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
    environment:
      APP_ENV: development
```

---

## 7. Reference README

*(The repo's `README.md` should contain this)*

```markdown
# intranet-reader

Self-hosted reader service inspired by [r.jina.ai](https://r.jina.ai).  
Converts any URL into clean Markdown/JSON, ready for LLMs and RAG.

## Quick Start

    cp .env.example .env
    docker compose up -d

## Usage

### cURL — Markdown
    curl http://localhost:8000/r/https://example.com

### cURL — JSON
    curl -H "Accept: application/json" http://localhost:8000/r/https://example.com

### Python — httpx
    import httpx
    r = httpx.get("http://localhost:8000/r/https://example.com",
                  headers={"Accept": "application/json"})
    print(r.json()["content"])

### Skip cache
    curl -H "x-no-cache: true" http://localhost:8000/r/https://example.com

## Key Environment Variables

| Variable | Default | Description |
|---|---|---|
| `READER_STRATEGY` | `auto` | `local`, `proxy`, `auto` |
| `JINA_API_KEY` | — | Jina Cloud API key (optional) |
| `CACHE_TTL_SECONDS` | `3600` | Redis cache TTL; `0` = off |
| `INTERNAL_TOKEN` | — | Internal Bearer token; empty = no auth |

## Reading Strategies

- **`local`** — no internet access. Uses httpx + BeautifulSoup + markdownify. Ideal for intranet URLs.
- **`proxy`** — delegates to `r.jina.ai`. Requires internet access. Better quality on complex webs/SPAs.
- **`auto`** — tries `local`, if it fails uses `proxy` as fallback.

## Useful Commands

    # tests
    poetry run pytest

    # lint
    poetry run ruff check app/

    # shell in the container
    docker compose exec api bash
```

---

## 8. Minimum Tests

### `tests/test_health.py`

```python
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_health():
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"
```

### `tests/test_reader.py`

```python
import pytest
from unittest.mock import AsyncMock, patch
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

MOCK_DATA = {
    "url": "https://example.com",
    "title": "Example",
    "content": "Hello world",
    "description": "",
    "usage": {"tokens": 2},
    "cached": False,
    "fetched_at": "2026-01-01T00:00:00+00:00",
}


@patch("app.routers.reader.read_url", new_callable=AsyncMock, return_value=MOCK_DATA)
def test_read_markdown(mock_read):
    r = client.get("/r/https://example.com")
    assert r.status_code == 200
    assert "Example" in r.text


@patch("app.routers.reader.read_url", new_callable=AsyncMock, return_value=MOCK_DATA)
def test_read_json(mock_read):
    r = client.get("/r/https://example.com", headers={"Accept": "application/json"})
    assert r.status_code == 200
    assert r.json()["title"] == "Example"
```

---

## 9. Implementation Checklist

```
[ ] Create repo: git init intranet-reader
[ ] poetry new . --name intranet-reader (or poetry init)
[ ] Copy file structure according to §3
[ ] cp .env.example .env and adjust variables
[ ] docker compose up -d --build
[ ] curl http://localhost:8000/health  →  {"status":"ok"}
[ ] curl http://localhost:8000/r/https://example.com
[ ] poetry run pytest
[ ] Adjust READER_STRATEGY according to network (local/proxy/auto)
[ ] (Optional) Configure INTERNAL_TOKEN for internal auth
[ ] (Optional) Expose via nginx/traefik on the intranet
```

---

## 10. References

| Resource | URL |
|---|---|
| Jina Reader — API Docs | https://jina.ai/reader/ |
| jina-ai/reader — GitHub (Apache-2.0) | https://github.com/jina-ai/reader |
| jinaai/ReaderLM-v2 — HuggingFace | https://huggingface.co/jinaai/ReaderLM-v2 |
| Community Docker fork | https://github.com/intergalacticalvariable/reader |
| FastAPI | https://fastapi.tiangolo.com |
| Poetry | https://python-poetry.org |
| markdownify | https://github.com/matthewwithanm/python-markdownify |
| pydantic-settings | https://docs.pydantic.dev/latest/concepts/pydantic_settings/ |

---

> **Spec Version:** 0.1.0 · Date: 2026-02-22  
> Minimalist but functional — for intranet, without forced external dependencies.
