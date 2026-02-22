# intranet-reader

Self-hosted URL-to-Markdown/JSON service powered by [`jinaai/ReaderLM-v2`](https://huggingface.co/jinaai/ReaderLM-v2) running **100% locally**. No external API calls, no API keys.

## Stack

- **FastAPI** — async HTTP server
- **ReaderLM-v2** — 1.5B model (Qwen2.5 base), HTML → Markdown / JSON
- **Redis** — results cache
- **Poetry** — dependency management
- **Docker Compose** — single-command deployment

## Quick Start

```bash
cp .env.example .env          # adjust DEVICE, MAX_NEW_TOKENS as needed
docker compose up -d --build  # first run downloads ~3 GB of model weights
```

Wait for the model to load (check logs: `docker compose logs -f api`), then:

```bash
# Health check
curl http://localhost:8000/health

# Fetch a URL as Markdown (default)
curl http://localhost:8000/r/https://example.com

# Fetch as JSON
curl -H "Accept: application/json" http://localhost:8000/r/https://example.com

# POST for URLs with fragments
curl -X POST http://localhost:8000/r \
  -H "Content-Type: application/json" \
  -d '{"url": "https://example.com/#section", "accept": "application/json"}'

# Skip cache
curl -H "x-no-cache: true" http://localhost:8000/r/https://example.com
```

## API

| Method | Path | Description |
|---|---|---|
| `GET` | `/r/{url:path}` | Convert URL to Markdown or JSON |
| `POST` | `/r` | Same, for URLs with `#` fragments |
| `GET` | `/health` | Service + model + Redis status |

### Headers for `GET /r/{url}`

| Header | Default | Description |
|---|---|---|
| `Accept` | `text/markdown` | Use `application/json` for JSON output |
| `x-no-cache` | `false` | Skip Redis cache lookup |

## Configuration (`.env`)

| Variable | Default | Description |
|---|---|---|
| `APP_PORT` | `8000` | Host port |
| `INTERNAL_TOKEN` | _(empty)_ | Bearer token auth (disabled if empty) |
| `HF_MODEL_ID` | `jinaai/ReaderLM-v2` | HuggingFace model ID |
| `DEVICE` | `cpu` | `cpu` or `cuda` |
| `MAX_NEW_TOKENS` | `4096` | Max generated tokens |
| `TORCH_DTYPE` | `float32` | `float32` or `float16` (GPU) |
| `REDIS_URL` | `redis://redis:6379/0` | Redis connection string |
| `CACHE_TTL_SECONDS` | `3600` | Cache TTL (set to 0 to disable) |
| `FETCH_TIMEOUT_SECONDS` | `30` | HTTP fetch timeout |

## GPU Setup

1. Edit `.env`: set `DEVICE=cuda` and `TORCH_DTYPE=float16`
2. In `pyproject.toml`, change the PyTorch source URL to `https://download.pytorch.org/whl/cu121`
3. In `docker-compose.yml`, uncomment the `deploy.resources` GPU section
4. Use `nvidia/cuda:12.1.0-runtime-ubuntu22.04` as the base image in `Dockerfile`

## Development

```bash
poetry install
poetry run pytest
```

Hot-reload with Docker:

```bash
docker compose up  # docker-compose.override.yml enables --reload automatically
```

## Performance

| Scenario | p50 Latency |
|---|---|
| CPU — simple page | 5–15 s |
| CPU — long page | 30–90 s |
| GPU T4 | ~3 s |
| GPU RTX 3090/4090 | ~1 s |
| Redis cache hit | < 50 ms |

## License

The application code is MIT. The model weights (`jinaai/ReaderLM-v2`) are licensed under **CC BY-NC 4.0** — non-commercial use only.
