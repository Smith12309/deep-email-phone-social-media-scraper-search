thonfrom __future__ import annotations

import asyncio
from typing import Optional

from utils.logger import get_logger

logger = get_logger(__name__)

try:  # optional dependency handling
    from playwright.async_api import async_playwright  # type: ignore

    _PLAYWRIGHT_AVAILABLE = True
except Exception:  # pragma: no cover - environment-specific
    async_playwright = None  # type: ignore
    _PLAYWRIGHT_AVAILABLE = False

def is_playwright_available() -> bool:
    return _PLAYWRIGHT_AVAILABLE

async def render_page(url: str, timeout_ms: int = 15000) -> str:
    """
    Render a page with Playwright and return the full HTML.
    If Playwright is not available, this will raise RuntimeError.
    """
    if not _PLAYWRIGHT_AVAILABLE or async_playwright is None:
        raise RuntimeError("Playwright is not installed or could not be imported.")

    logger.debug("Rendering %s with Playwright", url)
    async with async_playwright() as p:  # type: ignore
        browser = await p.chromium.launch(headless=True)
        try:
            page = await browser.new_page()
            await page.goto(url, wait_until="networkidle", timeout=timeout_ms)
            html = await page.content()
            return html
        finally:
            await browser.close()