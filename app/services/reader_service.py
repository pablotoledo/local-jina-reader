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
