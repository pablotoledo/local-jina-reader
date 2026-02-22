"""Playwright async renderer for JS-heavy pages."""
import structlog
from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeout
from app.core.config import settings

log = structlog.get_logger()


async def render_with_playwright(
    url: str,
    timeout: int | None = None,
    wait_for_selector: str | None = None,
) -> str:
    """Launch Chromium, navigate to URL, optionally wait for selector, return HTML."""
    t_ms = (timeout or settings.DEFAULT_TIMEOUT_S) * 1000

    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=settings.PLAYWRIGHT_HEADLESS)
        try:
            ctx = await browser.new_context(user_agent=settings.USER_AGENT)
            page = await ctx.new_page()
            await page.goto(url, timeout=t_ms, wait_until="networkidle")
            if wait_for_selector:
                try:
                    await page.wait_for_selector(wait_for_selector, timeout=t_ms)
                except PlaywrightTimeout:
                    log.warning("selector_timeout", selector=wait_for_selector, url=url)
            html = await page.content()
            return html
        finally:
            await browser.close()
