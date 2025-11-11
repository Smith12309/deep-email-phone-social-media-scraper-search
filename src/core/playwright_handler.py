thonimport asyncio
import logging
from typing import Optional

logger = logging.getLogger(__name__)

try:
    from playwright.async_api import async_playwright
except Exception:  # noqa: BLE001
    async_playwright = None
    logger.debug("Playwright is not installed; dynamic rendering will be disabled.")

async def _fetch_with_playwright(url: str, timeout: int, user_agent: str) -> Optional[str]:
    if async_playwright is None:
        logger.debug("async_playwright is unavailable.")
        return None

    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            try:
                context = await browser.new_context(user_agent=user_agent)
                page = await context.new_page()
                await page.goto(url, wait_until="networkidle", timeout=timeout * 1000)
                content = await page.content()
                await context.close()
                return content
            finally:
                await browser.close()
    except Exception as exc:  # noqa: BLE001
        logger.debug("Playwright failed for %s: %s", url, exc, exc_info=True)
        return None

def fetch_page_content(url: str, timeout: int = 10, user_agent: str = "DeepContactScraper/1.0") -> Optional[str]:
    """
    Synchronous wrapper for fetching a fully rendered page using Playwright.
    Returns the HTML or None on error.
    """
    if async_playwright is None:
        return None

    try:
        return asyncio.run(_fetch_with_playwright(url, timeout, user_agent))
    except RuntimeError:
        # This can happen if there's already a running event loop (e.g. in notebooks).
        # As a simple fallback, just log and disable Playwright in that context.
        logger.warning(
            "Cannot run Playwright inside an existing asyncio loop; skipping dynamic rendering for %s",
            url,
        )
        return None