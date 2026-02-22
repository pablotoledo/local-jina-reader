# Reader Clone

An internal Jina-Reader-compatible service that converts URLs to Markdown, JSON, or SSE streams.

## Overview

Reader Clone is a FastAPI service that fetches web pages (via httpx for static content or Playwright for JS-heavy pages), extracts main content using readability-lxml, and returns clean Markdown, HTML, plain text, or JSON.

## Features

- **GET `/{url}`** — Fetch and convert any URL to Markdown
- **POST `/`** — Same via JSON body (supports per-request headers)
- **Redis caching** — Configurable TTL, stable cache keys, `x-no-cache` override
- **SSRF protection** — Blocks private/loopback IPs, dangerous schemes
- **Prometheus metrics** — `/metrics` endpoint
- **Health probes** — `/healthz` (liveness) and `/readyz` (readiness)
- **Optional API key auth** — Bearer token via `Authorization` header

## Quick Start

```bash
# Copy and configure environment
cp .env.example .env

# Start with Docker Compose
docker compose up --build -d

# Or run locally
pip install -e ".[dev]"
python -m playwright install chromium
uvicorn app.main:app --host 0.0.0.0 --port 8080 --reload
```

## API Usage

### GET request

```bash
# Markdown (default)
curl http://localhost:8080/https://example.com

# JSON response
curl -H "Accept: application/json" http://localhost:8080/https://example.com

# With JS rendering (wait for selector)
curl -H "x-wait-for-selector: article" http://localhost:8080/https://example.com

# Extract specific element
curl -H "x-target-selector: main" http://localhost:8080/https://example.com

# Skip cache
curl -H "x-no-cache: true" http://localhost:8080/https://example.com
```

### POST request

```bash
curl -X POST http://localhost:8080/ \
  -H "Content-Type: application/json" \
  -H "Accept: application/json" \
  -d '{"url": "https://example.com", "headers": {"x-wait-for-selector": "article"}}'
```

## Request Headers

| Header | Type | Description |
|---|---|---|
| `Accept` | string | `text/markdown` (default) or `application/json` |
| `Authorization` | string | `Bearer <token>` — required if `API_KEYS` is set |
| `x-timeout` | int | Request timeout in seconds (max: `MAX_TIMEOUT_S`) |
| `x-wait-for-selector` | string | CSS selector to wait for before capturing (triggers Playwright) |
| `x-target-selector` | string | CSS selector to extract instead of readability main content |
| `x-respond-with` | string | `markdown` (default), `html`, or `text` |
| `x-no-cache` | string | `true`/`1`/`yes` to bypass cache |
| `x-cache-tolerance` | int | Cache TTL override in seconds |

## Configuration

All settings are via environment variables (or `.env` file):

| Variable | Default | Description |
|---|---|---|
| `APP_ENV` | `dev` | Environment name |
| `LOG_LEVEL` | `INFO` | Logging level |
| `HOST` | `0.0.0.0` | Bind host |
| `PORT` | `8080` | Bind port |
| `REDIS_URL` | `redis://localhost:6379/0` | Redis connection URL |
| `API_KEYS` | `` | Comma-separated API keys (empty = auth disabled) |
| `DEFAULT_TIMEOUT_S` | `15` | Default fetch timeout (seconds) |
| `MAX_TIMEOUT_S` | `60` | Maximum allowed timeout |
| `DEFAULT_CACHE_TTL_S` | `300` | Default cache TTL (seconds) |
| `ENABLE_SSE` | `true` | Enable SSE streaming (Phase 2) |
| `ALLOW_PRIVATE_NETS` | `false` | Allow private/loopback IPs (SSRF guard) |
| `BROWSER_CONTEXTS_MAX` | `4` | Max concurrent Playwright browser contexts |
| `PAGES_PER_CONTEXT_MAX` | `4` | Max pages per browser context |
| `USER_AGENT` | `reader-clone/0.1` | User-Agent header for outbound requests |
| `PLAYWRIGHT_BROWSER` | `chromium` | Browser for Playwright |
| `PLAYWRIGHT_HEADLESS` | `true` | Run browser headless |

## Development

```bash
# Install dev dependencies
pip install -e ".[dev]"
python -m playwright install chromium

# Run tests
pytest tests/ -v --tb=short

# Lint
ruff check app tests

# Format
ruff format app tests
```

## Architecture

```
app/
├── main.py              # FastAPI app, lifespan, middleware
├── api/
│   ├── deps.py          # Auth dependency
│   ├── routes_ops.py    # /healthz, /readyz, /metrics
│   └── routes_reader.py # GET /{url}, POST /
├── core/
│   ├── config.py        # Settings (pydantic-settings)
│   ├── cache.py         # Redis cache helpers
│   ├── logging.py       # structlog configuration
│   ├── rate_limit.py    # Sliding window rate limiter
│   └── security.py      # API key verification
├── schemas/
│   ├── request.py       # ReadPostBody
│   └── response.py      # ReaderResponse, ReaderMeta
├── services/
│   ├── url_guard.py     # SSRF protection
│   ├── fetcher.py       # httpx static fetch
│   ├── renderer.py      # Playwright JS renderer
│   ├── extractor.py     # readability-lxml extraction
│   ├── markdowner.py    # HTML → Markdown (markdownify)
│   └── streamer.py      # SSE stream helpers (Phase 2)
└── utils/
    ├── hashing.py       # Cache key generation
    └── url.py           # URL normalization
```

## Security

- **SSRF protection**: All outbound URLs are checked against private/loopback IP ranges before fetching. Blocked: `127.0.0.0/8`, `10.0.0.0/8`, `172.16.0.0/12`, `192.168.0.0/16`, `169.254.0.0/16`, IPv6 loopback/ULA/link-local.
- **Scheme allowlist**: Only `http://` and `https://` are permitted. `file://`, `ftp://`, `gopher://`, `data:`, `javascript:` are blocked.
- **API key auth**: Optional Bearer token authentication. Disabled when `API_KEYS` is empty.
