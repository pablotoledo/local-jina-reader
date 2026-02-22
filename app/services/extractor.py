"""Main content extraction using readability-lxml with optional CSS selector."""
import structlog
from bs4 import BeautifulSoup
from readability import Document

log = structlog.get_logger()


def extract_main_content(html: str, target_selector: str | None = None) -> tuple[str, str]:
    """
    Extract title and main content HTML from raw HTML.
    If target_selector is set, extract that element instead of readability output.
    Returns (title, body_html).
    """
    doc = Document(html)
    title = doc.title() or ""

    if target_selector:
        soup = BeautifulSoup(html, "lxml")
        el = soup.select_one(target_selector)
        if el:
            return title, str(el)
        log.warning("target_selector_not_found", selector=target_selector)

    return title, doc.summary(html_partial=True)
