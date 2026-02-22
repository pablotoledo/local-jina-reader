import time
from typing import Annotated

import structlog
from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from fastapi.responses import JSONResponse, PlainTextResponse

from app.api.deps import require_api_key
from app.core.cache import get_cached, set_cached
from app.core.config import settings
from app.schemas.request import ReadPostBody
from app.schemas.response import ReaderResponse
from app.services.extractor import extract_main_content
from app.services.fetcher import fetch_static
from app.services.markdowner import html_to_markdown
from app.services.renderer import render_with_playwright
from app.services.url_guard import check_url
from app.utils.hashing import make_cache_key
from app.utils.url import normalize_url

log = structlog.get_logger()
router = APIRouter(tags=["reader"])


async def _process_url(
    target_url: str,
    accept: str | None,
    x_timeout: int | None,
    x_wait_for_selector: str | None,
    x_target_selector: str | None,
    x_respond_with: str | None,
    x_no_cache: str | None,
    x_cache_tolerance: int | None,
) -> dict:
    """Core pipeline: guard → cache → fetch/render → extract → markdown."""
    t0 = time.monotonic()

    # 1. Validate scheme + SSRF guard
    check_url(target_url)

    # 2. Normalize URL
    url = normalize_url(target_url)

    # 3. Cache lookup
    no_cache = (x_no_cache or "").lower() in ("true", "1", "yes")
    cache_key = make_cache_key(url, x_target_selector, x_wait_for_selector, x_respond_with, accept)
    from_cache = False

    if not no_cache:
        cached = await get_cached(cache_key)
        if cached is not None:
            log.debug("cache_hit", url=url)
            cached["meta"]["from_cache"] = True
            return cached

    # 4. Fetch / render
    timeout = min(x_timeout or settings.DEFAULT_TIMEOUT_S, settings.MAX_TIMEOUT_S)
    html: str | None = None

    try:
        html = await fetch_static(url, timeout=timeout)
    except Exception as exc:
        log.debug("static_fetch_failed", url=url, error=str(exc))

    if html is None or x_wait_for_selector:
        html = await render_with_playwright(
            url,
            timeout=timeout,
            wait_for_selector=x_wait_for_selector,
        )

    # 5. Extract main content
    title, body_html = extract_main_content(html, target_selector=x_target_selector)

    # 6. Convert to requested format
    respond_with = (x_respond_with or "markdown").lower()
    if respond_with == "html":
        content = body_html
    elif respond_with == "text":
        from bs4 import BeautifulSoup
        content = BeautifulSoup(body_html, "lxml").get_text(separator="\n", strip=True)
    else:  # markdown (default)
        content = html_to_markdown(body_html)

    elapsed_ms = int((time.monotonic() - t0) * 1000)

    result = {
        "url": url,
        "title": title,
        "content": content,
        "meta": {
            "from_cache": from_cache,
            "elapsed_ms": elapsed_ms,
            "engine": "playwright+readability" if x_wait_for_selector else "httpx+readability",
            "accept": accept or "text/markdown",
            "respond_with": respond_with,
        },
    }

    # 7. Cache write
    if not no_cache:
        ttl = x_cache_tolerance or settings.DEFAULT_CACHE_TTL_S
        await set_cached(cache_key, result, ttl=ttl)

    return result


@router.get("/{target_url:path}", summary="Read URL → Markdown/JSON")
async def read_url(
    target_url: str,
    request: Request,
    _auth: Annotated[str | None, Depends(require_api_key)] = None,
    accept: str | None = Header(default=None, alias="Accept"),
    x_timeout: int | None = Header(default=None, alias="x-timeout"),
    x_wait_for_selector: str | None = Header(default=None, alias="x-wait-for-selector"),
    x_target_selector: str | None = Header(default=None, alias="x-target-selector"),
    x_respond_with: str | None = Header(default=None, alias="x-respond-with"),
    x_no_cache: str | None = Header(default=None, alias="x-no-cache"),
    x_cache_tolerance: int | None = Header(default=None, alias="x-cache-tolerance"),
):
    if not target_url.startswith(("http://", "https://")):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="URL must start with http:// or https://")

    result = await _process_url(
        target_url, accept, x_timeout, x_wait_for_selector,
        x_target_selector, x_respond_with, x_no_cache, x_cache_tolerance,
    )

    if accept == "application/json":
        return JSONResponse(result)

    # Markdown plain text response with header block
    header_block = f"Title: {result['title']}\nURL Source: {result['url']}\n\n"
    return PlainTextResponse(header_block + result["content"], media_type="text/markdown")


@router.post("/", summary="Read URL (POST) → Markdown/JSON", status_code=200)
async def read_post(
    body: ReadPostBody,
    _auth: Annotated[str | None, Depends(require_api_key)] = None,
    accept: str | None = Header(default=None, alias="Accept"),
    x_timeout: int | None = Header(default=None, alias="x-timeout"),
    x_wait_for_selector: str | None = Header(default=None, alias="x-wait-for-selector"),
    x_target_selector: str | None = Header(default=None, alias="x-target-selector"),
    x_respond_with: str | None = Header(default=None, alias="x-respond-with"),
    x_no_cache: str | None = Header(default=None, alias="x-no-cache"),
    x_cache_tolerance: int | None = Header(default=None, alias="x-cache-tolerance"),
):
    # Merge per-request headers from body.headers if provided
    wfs = x_wait_for_selector or (body.headers or {}).get("x-wait-for-selector")
    ts = x_target_selector or (body.headers or {}).get("x-target-selector")

    result = await _process_url(
        body.url, accept, x_timeout, wfs, ts, x_respond_with, x_no_cache, x_cache_tolerance,
    )

    if accept == "application/json":
        return JSONResponse(result)

    header_block = f"Title: {result['title']}\nURL Source: {result['url']}\n\n"
    return PlainTextResponse(header_block + result["content"], media_type="text/markdown")
