import re
import httpx
from app.config import settings

# Patterns extracted from jinaai/ReaderLM-v2 README
SCRIPT_PATTERN = r"<[ ]*script.*?\/[ ]*script[ ]*>"
STYLE_PATTERN = r"<[ ]*style.*?\/[ ]*style[ ]*>"
META_PATTERN = r"<[ ]*meta.*?>"
COMMENT_PATTERN = r"<[ ]*!--.*?--[ ]*>"
LINK_PATTERN = r"<[ ]*link.*?>"
BASE64_IMG_PATTERN = r'<img[^>]+src="data:image/[^;]+;base64,[^"]+"[^>]*>'
SVG_PATTERN = r"(<svg[^>]*>)(.*?)(<\/svg>)"
FLAGS = re.IGNORECASE | re.DOTALL


def clean_html(html: str) -> str:
    html = re.sub(SCRIPT_PATTERN, "", html, flags=FLAGS)
    html = re.sub(STYLE_PATTERN, "", html, flags=FLAGS)
    html = re.sub(META_PATTERN, "", html, flags=FLAGS)
    html = re.sub(COMMENT_PATTERN, "", html, flags=FLAGS)
    html = re.sub(LINK_PATTERN, "", html, flags=FLAGS)
    html = re.sub(BASE64_IMG_PATTERN, "<img/>", html, flags=FLAGS)
    html = re.sub(SVG_PATTERN, r"\1this is a placeholder\3", html, flags=FLAGS)
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
