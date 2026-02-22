"""Convert HTML to Markdown using markdownify."""
from markdownify import markdownify


def html_to_markdown(html: str) -> str:
    """Convert HTML fragment to clean Markdown."""
    return markdownify(html, heading_style="ATX", strip=["script", "style"]).strip()
