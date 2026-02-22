# Reader Clone — Spec Document (v0.1)

> Clon interno tipo r.jina.ai implementado con FastAPI + Docker Compose.

---

## Contexto previo

Sí. Y te conviene hacerlo como clon funcional interno (paridad de API) en vez de intentar copiar 1:1 el stack de Jina. Abajo te dejo un spec document "implementation-ready" para crear un repo desde cero con FastAPI + Docker Compose, con: arquitectura, contrato API, estructura del repo, compose, Dockerfiles, ejemplos, README base, roadmap y criterios de aceptación.

**Mini revisión de detalles** (para que el spec esté bien fundamentado):

- El repo público de Jina Reader existe, está en Apache-2.0, y su README dice explícitamente que es el mismo codebase detrás de r.jina.ai; también aclara que `thinapps-shared` es interno pero no integral.
- El repo oficial está implementado principalmente en **TypeScript/Node**, no en Python/FastAPI. El `package.json` y la página del repo lo reflejan.
- Su Dockerfile instala Google Chrome, usa puppeteer, define `PORT=8080` y arranca `build/stand-alone/crawl.js`; además usa `curl-impersonate` vía `LD_PRELOAD`.
- En su README/documentación aparecen funcionalidades que conviene decidir si replicas o no: GET con prefijo URL, POST para hash-routes SPA, headers como `x-wait-for-selector`, `x-target-selector`, `x-no-cache`, `x-cache-tolerance`, SSE streaming, JSON mode, y captions de imágenes.
- La UI/docs de Jina Reader también exponen opciones extra (selectores include/exclude, quitar imágenes, formato de citas, upload de PDF/HTML, "Run JavaScript Before Extraction", viewport, etc.), y mencionan integración con ReaderLM-v2.

---

## 1) Objetivo

Construir un servicio interno tipo r.jina.ai que:

1. Reciba una URL
2. Renderice (si hace falta JS)
3. Extraiga contenido principal
4. Lo convierta a formato amigable para LLM (Markdown / JSON / texto)
5. Exponga una API simple con headers de control (timeout, selectors, cache, etc.)
6. Se despliegue con Docker Compose en entorno local/QA/prod interna

### Objetivo de paridad (MVP)

Paridad de uso con el patrón:
- `GET /https://example.com/page`
- `POST /` con `{"url": "https://example.com/#/route"}`

### No objetivos (MVP)

- No replicar s.jina.ai (búsqueda web) en fase 1
- No OCR avanzado
- No captioning de imágenes por VLM (fase 2+)
- No compatibilidad 100% exacta con todos los headers de Jina (sí subset útil)

---

## 2) Alcance funcional (MVP vs Fase 2)

### MVP (recomendado)

- `GET /{target_url:path}` → devuelve Markdown (por defecto)
- `POST /` → body JSON con URL (para hash routes/SPA)
- `Accept: application/json` → respuesta JSON `{url, title, content, meta}`
- `Accept: text/event-stream` → streaming progresivo (SSE)
- Headers:
  - `x-timeout`
  - `x-wait-for-selector`
  - `x-target-selector`
  - `x-no-cache`
  - `x-cache-tolerance`
  - `x-respond-with` (markdown|html|text)
- Cache en Redis
- Rate limiting por API key interna
- `/healthz`, `/readyz`, `/metrics`
- Docs automáticas FastAPI (`/docs`, `/redoc`)

### Fase 2

- `x-set-cookie` (forward cookies)
- `x-exclude-selector`
- `x-remove-images`
- `x-respond-with: screenshot`
- Upload local HTML/PDF (`POST /upload`)
- Extracción PDF URL/archivo
- Captions de imágenes (VLM opcional)
- Resumen de links/imágenes
- "engine" pluggable (default, readerlm_v2_local, etc.)

---

## 3) Requisitos no funcionales

### Seguridad (interna por defecto)
- API key obligatoria (o reverse proxy con SSO)
- allowlist de dominios opcional
- bloqueo de IPs privadas / loopback (anti-SSRF)
- deshabilitar proxy arbitrario en MVP

### Rendimiento
- timeout configurable (default 15s)
- respuesta caché para URLs repetidas
- pool de navegadores/páginas (Playwright)

### Observabilidad
- logs estructurados JSON
- métricas Prometheus
- request-id/correlation-id

### Operación
- Docker Compose local/servidor
- perfiles `minimal` y `full`

---

## 4) Decisiones técnicas (ADR resumidas)

**A. FastAPI (Python) para la capa API**
Muy buena DX, validación con Pydantic y docs OpenAPI integradas. La guía de FastAPI recomienda construir imágenes desde la imagen oficial de Python (en vez de imágenes antiguas/deprecadas específicas).

**B. Playwright para render JS**
Soporta motores modernos y puede usarse como herramienta general de automatización (sync/async en Python). Elegido sobre Selenium por simplicidad y estabilidad en render moderno.

**C. Redis para cache/rate limiting**
Separación simple, robusta, compatible con Compose.

**D. Docker Compose (spec moderna)**
La especificación Compose actual es la recomendada. El campo top-level `version` es obsoleto (se puede omitir).

---

## 5) Compatibilidad con Jina Reader (referencia)

Este proyecto no copia internamente el código de Jina; replica el contrato de uso principal con una implementación Python propia.

Funcionalidades de referencia observadas en Jina (para decidir paridad):
- prefijo URL en r.jina.ai
- POST para hash routes SPA
- headers de selectors/cache/timeout
- SSE streaming
- JSON mode
- image alt generation (opcional)

---

## 6) Arquitectura propuesta

### 6.1 Componentes (MVP)

1. **api** (FastAPI + Uvicorn)
   - recibe request
   - valida headers/parámetros
   - aplica auth / rate limit
   - consulta cache Redis
   - coordina render/extracción
   - responde markdown/json/sse

2. **redis**
   - cache de respuestas
   - rate-limit counters
   - locks para evitar thundering herd

3. **playwright runtime** (dentro del contenedor api)
   - Chromium headless
   - render de páginas SPA
   - espera por selector/network idle
   - captura HTML final

> **Nota**: en producción, puedes separar browser en un servicio aparte, pero para empezar el contenedor único api simplifica mucho.

### 6.2 Pipeline de request (MVP)

```
1. Parse target URL
2. Validación SSRF / scheme (http|https)
3. Cache lookup (key = URL + headers relevantes)
4. Fetch/render:
   - static-first (httpx) opcional
   - fallback a Playwright
5. Post-procesado:
   - selector target/exclude
   - extracción main content (readability/trafilatura/custom)
   - HTML → Markdown
6. Output:
   - markdown / json / text
   - stream SSE (si Accept: text/event-stream)
7. Cache write (si procede)
```

---

## 7) Contrato API (MVP)

### 7.1 Endpoint principal (GET)

```
GET /{target_url:path}
```

Ejemplo: `GET /https://example.com/blog/post`

**Headers soportados (MVP)**

| Header | Descripción |
|--------|-------------|
| `Authorization: Bearer <API_KEY>` | Opcional si red interna cerrada |
| `Accept` | `text/markdown` \| `application/json` \| `text/event-stream` |
| `x-timeout` | Segundos (int) |
| `x-wait-for-selector` | CSS selector a esperar |
| `x-target-selector` | CSS selector para extracción |
| `x-respond-with` | `markdown` \| `html` \| `text` |
| `x-no-cache` | `true` \| `false` |
| `x-cache-tolerance` | Segundos (int) |

**Respuesta por defecto**: `200 text/markdown; charset=utf-8`

### 7.2 Endpoint POST (hash routes / SPA)

```
POST /
```

Body:
```json
{
  "url": "https://example.com/#/dashboard",
  "headers": {
    "x-wait-for-selector": "#app"
  }
}
```

Respuesta igual que GET según `Accept`.

### 7.3 Endpoint upload (Fase 2)

```
POST /upload
```

- `multipart/form-data`
- `file` (html|pdf)
- `reference_url` (opcional, útil para HTML con relativos)

### 7.4 Endpoints operativos

| Endpoint | Descripción |
|----------|-------------|
| `GET /healthz` | Proceso vivo |
| `GET /readyz` | Redis + browser OK |
| `GET /metrics` | Prometheus |

---

## 8) Modelo de respuesta

### 8.1 Markdown (default)

```
Title: Example Post
URL Source: https://example.com/blog/post

# Example Post

Contenido extraído...

## Links
- [Link A](...)
```

### 8.2 JSON (`Accept: application/json`)

```json
{
  "url": "https://example.com/blog/post",
  "title": "Example Post",
  "content": "# Example Post\n\nContenido extraído...",
  "meta": {
    "content_type": "text/html",
    "status_code": 200,
    "from_cache": false,
    "elapsed_ms": 1820,
    "engine": "playwright+readability",
    "fetched_at": "2026-02-22T12:00:00Z"
  }
}
```

### 8.3 SSE (`Accept: text/event-stream`)

Eventos sugeridos: `phase`, `partial`, `final`, `error`

```
event: phase
data: {"phase":"rendered"}

event: partial
data: {"content":"# Título ..."}

event: final
data: {"content":"# Título completo..."}
```

---

## 9) Reglas de seguridad (críticas)

### 9.1 SSRF protection (obligatorio)

Bloquear:
- `localhost`, `127.0.0.0/8`, `::1`
- rangos privados: `10/8`, `172.16/12`, `192.168/16`
- metadata endpoints cloud
- `file://`, `ftp://`, `gopher://`

### 9.2 Autenticación

- **Opción A (simple)**: `Authorization: Bearer <API_KEY>` validado por lista en env
- **Opción B (empresa)**: Traefik/Nginx + SSO (OIDC) delante; API sin auth propia

### 9.3 Cookies / contenido autenticado

- MVP: deshabilitado (sin `x-set-cookie`)
- Fase 2: permitir solo si `ALLOW_COOKIE_FORWARDING=true` y con audit logs

---

## 10) Estrategia de cache

**Clave de cache** — Hash de:
- URL normalizada
- `x-target-selector`
- `x-wait-for-selector`
- `x-respond-with`
- `Accept`
- `x-remove-images` (fase 2)
- versión de extractor (`EXTRACTOR_VERSION`)

**TTL**:
- Default: 300s
- Override: `x-cache-tolerance`
- Bypass: `x-no-cache: true`

---

## 11) Repo layout propuesto

```
reader-clone/
├─ app/
│   ├─ __init__.py
│   ├─ main.py                # FastAPI app
│   ├─ api/
│   │   ├─ routes_reader.py
│   │   ├─ routes_ops.py
│   │   └─ deps.py
│   ├─ core/
│   │   ├─ config.py
│   │   ├─ logging.py
│   │   ├─ security.py
│   │   ├─ cache.py
│   │   └─ rate_limit.py
│   ├─ schemas/
│   │   ├─ request.py
│   │   └─ response.py
│   ├─ services/
│   │   ├─ fetcher.py         # httpx/static fetch
│   │   ├─ renderer.py        # Playwright
│   │   ├─ extractor.py       # main content extraction
│   │   ├─ markdowner.py      # html -> md
│   │   ├─ streamer.py        # SSE helpers
│   │   └─ url_guard.py       # SSRF protection
│   └─ utils/
│       ├─ url.py
│       └─ hashing.py
├─ tests/
│   ├─ test_api_read.py
│   ├─ test_ssrf.py
│   ├─ test_cache.py
│   └─ fixtures/
├─ docker/
│   ├─ api.Dockerfile
│   ├─ entrypoint.sh
│   └─ chromium-deps.txt
├─ docker-compose.yml
├─ .env.example
├─ pyproject.toml
├─ README.md
├─ Makefile
└─ docs/
    ├─ SPEC.md
    ├─ ADR-001-fastapi.md
    └─ ADR-002-playwright.md
```

---

## 12) Docker Compose (MVP + full profile)

```yaml
# docker-compose.yml
name: reader-clone

services:
  api:
    build:
      context: .
      dockerfile: docker/api.Dockerfile
    container_name: reader-api
    env_file:
      - .env
    environment:
      APP_ENV: ${APP_ENV:-dev}
      LOG_LEVEL: ${LOG_LEVEL:-INFO}
      HOST: 0.0.0.0
      PORT: 8080
      REDIS_URL: redis://redis:6379/0
      API_KEYS: ${API_KEYS:-devkey123}
      DEFAULT_TIMEOUT_S: ${DEFAULT_TIMEOUT_S:-15}
      DEFAULT_CACHE_TTL_S: ${DEFAULT_CACHE_TTL_S:-300}
      MAX_TIMEOUT_S: ${MAX_TIMEOUT_S:-60}
      USER_AGENT: ${USER_AGENT:-reader-clone/0.1}
      ENABLE_SSE: ${ENABLE_SSE:-true}
      ENABLE_COOKIE_FORWARDING: ${ENABLE_COOKIE_FORWARDING:-false}
      ALLOW_PRIVATE_NETS: ${ALLOW_PRIVATE_NETS:-false}
      PLAYWRIGHT_BROWSER: chromium
      PLAYWRIGHT_HEADLESS: "true"
      BROWSER_CONTEXTS_MAX: ${BROWSER_CONTEXTS_MAX:-4}
      PAGES_PER_CONTEXT_MAX: ${PAGES_PER_CONTEXT_MAX:-4}
    ports:
      - "8080:8080"
    depends_on:
      redis:
        condition: service_healthy
    healthcheck:
      test: ["CMD", "curl", "-fsS", "http://localhost:8080/healthz"]
      interval: 15s
      timeout: 5s
      retries: 5
    restart: unless-stopped

  redis:
    image: redis:7-alpine
    container_name: reader-redis
    command: ["redis-server", "--appendonly", "no"]
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 3s
      retries: 5
    restart: unless-stopped

  # Opcional (perfil full): Prometheus + Grafana
  prometheus:
    image: prom/prometheus:latest
    profiles: ["full"]
    volumes:
      - ./ops/prometheus.yml:/etc/prometheus/prometheus.yml:ro
    ports:
      - "9090:9090"
    depends_on:
      - api
    restart: unless-stopped

  grafana:
    image: grafana/grafana:latest
    profiles: ["full"]
    ports:
      - "3000:3000"
    depends_on:
      - prometheus
    restart: unless-stopped

volumes:
  redis_data:
```

> **Nota**: no incluyo `version:` porque la doc actual lo marca como obsoleto.

---

## 13) Dockerfile para FastAPI + Playwright

```dockerfile
# docker/api.Dockerfile
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# Dependencias del sistema (Playwright/Chromium)
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl ca-certificates wget gnupg \
    libnss3 libnspr4 libatk1.0-0 libatk-bridge2.0-0 libcups2 \
    libdrm2 libdbus-1-3 libxkbcommon0 libxcomposite1 libxdamage1 \
    libxfixes3 libxrandr2 libgbm1 libasound2 libpango-1.0-0 \
    libcairo2 libatspi2.0-0 libx11-6 libx11-xcb1 libxcb1 libxext6 \
    libxrender1 libxshmfence1 fonts-liberation \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml /app/pyproject.toml

RUN pip install --upgrade pip && pip install -e . \
    && python -m playwright install chromium

COPY . /app

EXPOSE 8080

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080"]
```

---

## 14) FastAPI: esqueleto mínimo funcional

### `app/main.py`

```python
from fastapi import FastAPI
from app.api.routes_reader import router as reader_router
from app.api.routes_ops import router as ops_router

app = FastAPI(
    title="Reader Clone API",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

app.include_router(ops_router, tags=["ops"])
app.include_router(reader_router, tags=["reader"])
```

### `app/api/routes_ops.py`

```python
from fastapi import APIRouter

router = APIRouter()

@router.get("/healthz")
async def healthz():
    return {"ok": True}

@router.get("/readyz")
async def readyz():
    # aquí validarías redis/browser pool
    return {"ready": True}
```

### `app/api/routes_reader.py` (MVP simplificado)

```python
from fastapi import APIRouter, Request, Header, HTTPException
from fastapi.responses import PlainTextResponse, JSONResponse
from pydantic import BaseModel

router = APIRouter()

class ReadPostBody(BaseModel):
    url: str

@router.get("/{target_url:path}")
async def read_url(
    target_url: str,
    request: Request,
    accept: str | None = Header(default=None, alias="Accept"),
    x_timeout: int | None = Header(default=None, alias="x-timeout"),
    x_wait_for_selector: str | None = Header(default=None, alias="x-wait-for-selector"),
    x_target_selector: str | None = Header(default=None, alias="x-target-selector"),
    x_respond_with: str | None = Header(default=None, alias="x-respond-with"),
    x_no_cache: str | None = Header(default=None, alias="x-no-cache"),
    x_cache_tolerance: int | None = Header(default=None, alias="x-cache-tolerance"),
):
    if not target_url.startswith(("http://", "https://")):
        raise HTTPException(status_code=400, detail="Path debe contener URL http(s) completa")

    # TODO: SSRF guard + cache + render + extract + markdown
    content = f"# Placeholder\n\nURL: {target_url}\n"

    if accept == "application/json":
        return JSONResponse({
            "url": target_url,
            "title": "Placeholder",
            "content": content,
            "meta": {
                "from_cache": False,
                "accept": accept or "text/markdown",
                "x_timeout": x_timeout,
                "x_wait_for_selector": x_wait_for_selector,
                "x_target_selector": x_target_selector,
                "x_respond_with": x_respond_with,
                "x_no_cache": x_no_cache,
                "x_cache_tolerance": x_cache_tolerance,
            }
        })

    return PlainTextResponse(content, media_type="text/markdown")

@router.post("/")
async def read_post(body: ReadPostBody):
    return JSONResponse({"url": body.url, "todo": "Implement render/extract pipeline"})
```

---

## 15) Dependencias Python sugeridas

```toml
# pyproject.toml
[project]
name = "reader-clone"
version = "0.1.0"
requires-python = ">=3.12"
dependencies = [
    "fastapi>=0.115",
    "uvicorn[standard]>=0.30",
    "pydantic>=2.7",
    "redis>=5.0",
    "httpx>=0.27",
    "playwright>=1.50",
    "beautifulsoup4>=4.12",
    "lxml>=5.2",
    "markdownify>=0.13",
    "readability-lxml>=0.8.1",
    "prometheus-client>=0.20",
    "structlog>=24.1",
    "orjson>=3.10"
]

[project.optional-dependencies]
dev = [
    "pytest>=8.0",
    "pytest-asyncio>=0.23",
    "pytest-cov>=5.0",
    "ruff>=0.6",
    "mypy>=1.10"
]

[build-system]
requires = ["setuptools>=68", "wheel"]
build-backend = "setuptools.build_meta"
```

---

## 16) README (plantilla)

```markdown
# Reader Clone (FastAPI)

Clon interno tipo r.jina.ai: "engine" para convertir URLs en contenido amigable
para LLM (Markdown/JSON/SSE), con render JS (Playwright) y cache (Redis).

## Características (MVP)

- `GET /https://example.com/page`
- `POST /` para SPA/hash routes
- Markdown por defecto
- JSON (`Accept: application/json`)
- SSE (`Accept: text/event-stream`) *(WIP)*
- Headers de control (`x-timeout`, `x-wait-for-selector`, `x-target-selector`, cache)
- Redis cache
- FastAPI docs (`/docs`, `/redoc`)

## Requisitos

- Docker + Docker Compose v2

## Quickstart

\`\`\`bash
cp .env.example .env
docker compose up --build
\`\`\`

API disponible en:
- http://localhost:8080/docs
- http://localhost:8080/redoc

## Ejemplos

\`\`\`bash
# 1) Markdown
curl "http://localhost:8080/https://example.com"

# 2) JSON mode
curl -H "Accept: application/json" "http://localhost:8080/https://example.com"

# 3) SPA / hash route (POST)
curl -X POST "http://localhost:8080/" \
  -H "Content-Type: application/json" \
  -d '{"url":"https://example.com/#/dashboard"}'

# 4) Esperar selector
curl "http://localhost:8080/https://example.com" \
  -H "x-wait-for-selector: main"

# 5) Extraer un selector específico
curl "http://localhost:8080/https://example.com" \
  -H "x-target-selector: article"

# 6) Sin cache
curl "http://localhost:8080/https://example.com" \
  -H "x-no-cache: true"
\`\`\`

## Variables de entorno

Ver `.env.example`.

## Seguridad

- Bloqueo SSRF (IPs privadas/localhost)
- API key opcional/obligatoria según entorno
- Cookie forwarding deshabilitado por defecto

## Roadmap

- `x-respond-with: screenshot`
- Upload HTML/PDF
- Captions de imágenes
- Motor alternativo (readerlm_v2_local)
- Endpoint de búsqueda (/search) tipo s.jina.ai

## Licencia

Apache-2.0
```

---

## 17) .env.example

```dotenv
APP_ENV=dev
LOG_LEVEL=INFO
API_KEYS=devkey123
DEFAULT_TIMEOUT_S=15
MAX_TIMEOUT_S=60
DEFAULT_CACHE_TTL_S=300
ENABLE_SSE=true
ENABLE_COOKIE_FORWARDING=false
ALLOW_PRIVATE_NETS=false
BROWSER_CONTEXTS_MAX=4
PAGES_PER_CONTEXT_MAX=4
USER_AGENT=reader-clone/0.1
```

---

## 18) Criterios de aceptación (Definition of Done)

### MVP DoD

- [ ] `docker compose up --build` levanta api y redis
- [ ] `/healthz` responde 200
- [ ] `GET` con URL devuelve texto markdown
- [ ] `POST` con hash route acepta body JSON
- [ ] `Accept: application/json` devuelve estructura JSON válida
- [ ] `x-target-selector` altera la extracción
- [ ] `x-no-cache` fuerza bypass de cache
- [ ] Bloqueo SSRF probado con `127.0.0.1`
- [ ] `/docs` y `/redoc` visibles
- [ ] Tests básicos pasan en CI

### Tests mínimos

**Unit tests:**
- normalización URL
- hash cache key
- parse headers
- SSRF guard

**Integration tests:**
- API GET/POST
- cache hit/miss
- selector wait (sitio de prueba controlado)

**Smoke tests:**
- `compose up` + curl ejemplos

---

## 19) Roadmap por fases

### Fase 1 (2–4 días)
- Esqueleto FastAPI
- Compose
- Redis cache
- Render Playwright
- Extracción markdown básica
- Docs + README

### Fase 2 (3–6 días)
- SSE streaming
- JSON enriquecido
- Métricas/logs
- Rate limiting
- Seguridad SSRF robusta

### Fase 3 (4–8 días)
- Upload HTML/PDF
- Screenshot mode
- Captions opcionales
- Plugin engine (readerlm_v2_local)
- Endpoint de búsqueda interno

---

## 20) Referencias (oficiales y relevantes)

- **Jina Reader (repo oficial)**: funcionalidades r.jina.ai / s.jina.ai, headers, streaming, JSON mode, nota sobre thinapps-shared, licencia Apache-2.0.
- **Dockerfile / stack del repo Jina Reader**: Node + Chrome + entrypoint `crawl.js`.
- **Reader API docs (UI/Jina)**: selectors, timeout, JSON response, upload PDF/HTML, JS before extraction, opciones avanzadas.
- **ReaderLM-v2 en Hugging Face**: uso local e integración con Reader API vía header `x-engine`.
- **FastAPI en Docker (docs oficiales)**: imagen desde Python oficial, despliegue en contenedores.
- **Docker Compose docs**: Compose Specification actual y `version` top-level obsoleto.
- **Playwright Python docs**: uso general, soporte de motores, API sync/async.

---

## 21) Recomendación final (práctica)

Para un repo interno, arrancar con este enfoque:

1. FastAPI + Playwright + Redis (single api container + redis)
2. Paridad de headers subset (los más útiles)
3. SSRF hardening desde el día 1
4. Añadir SSE y PDF/upload después

Eso da algo utilizable rápido, sin cargar la complejidad del stack completo oficial de Jina (que además está en Node/TS y trae piezas específicas como `curl-impersonate` y componentes internos no esenciales).
