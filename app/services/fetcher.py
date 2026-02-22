"""Static HTTP fetch using httpx."""
import httpx
import structlog
from app.core.config import settings

log = structlog.get_logger()


async def fetch_static(url: str, timeout: int | None = None) -> str:
    """Fetch URL with httpx. Returns HTML string or raises on error."""
    t = timeout or settings.DEFAULT_TIMEOUT_S
    headers = {"User-Agent": settings.USER_AGENT}
    async with httpx.AsyncClient(follow_redirects=True, timeout=t) as client:
        resp = await client.get(url, headers=headers)
        resp.raise_for_status()
        ct = resp.headers.get("content-type", "")
        html_types = ("text/html", "application/xhtml+xml", "application/xml", "text/xml")
        if not any(t in ct.lower() for t in html_types):
            raise ValueError(f"Non-HTML content-type: {ct}")
        return resp.text
