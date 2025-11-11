thonimport logging
from collections import deque
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Type
from urllib.parse import urljoin, urlparse

logger = logging.getLogger(__name__)

@dataclass
class PageResult:
    root_url: str
    url: str
    html: str

class DynamicCrawler:
    """
    JavaScript-capable crawler using requests-html (PyPPeteer under the hood).

    It behaves similarly to StaticCrawler but renders pages, which improves
    extraction on JavaScript-heavy websites.
    """

    def __init__(
        self,
        headers: Optional[Dict[str, str]] = None,
        timeout: int = 15,
        max_depth: int = 2,
        max_pages_per_site: int = 15,
        proxy: Optional[str] = None,
        render_timeout: int = 15,
    ) -> None:
        try:
            from requests_html import HTMLSession  # type: ignore
        except ImportError as exc:  # noqa: BLE001
            raise RuntimeError(
                "DynamicCrawler requires the 'requests-html' package. "
                "Install it with `pip install requests-html`.",
            ) from exc

        self._HTMLSession: Type[HTMLSession] = HTMLSession  # type: ignore[name-defined]
        self.headers = headers or {}
        self.timeout = timeout
        self.max_depth = max_depth
        self.max_pages_per_site = max_pages_per_site
        self.proxies = {"http": proxy, "https": proxy} if proxy else None
        self.render_timeout = render_timeout

    def _same_domain(self, root: str, url: str) -> bool:
        try:
            root_host = urlparse(root).netloc.lower()
            url_host = urlparse(url).netloc.lower()
            return root_host == url_host
        except Exception:  # noqa: BLE001
            return False

    def _extract_links_from_html(self, current_url: str, html: str) -> List[str]:
        # Simple href extraction without a full HTML parser to keep this lean.
        import re  # local import to keep dependencies minimal

        href_pattern = re.compile(r'href=["\'](.*?)["\']', re.IGNORECASE)
        links: List[str] = []
        for match in href_pattern.finditer(html):
            href = match.group(1).strip()
            if not href or href.startswith("#") or href.lower().startswith("mailto:"):
                continue
            abs_url = urljoin(current_url, href)
            links.append(abs_url)
        return links

    def _fetch(self, session, url: str) -> str:
        logger.debug("Dynamic crawler fetching %s", url)
        resp = session.get(url, timeout=self.timeout, allow_redirects=True, proxies=self.proxies)
        resp.html.render(timeout=self.render_timeout, reload=False, sleep=1)
        return resp.html.html

    def crawl(self, root_url: str) -> List[Dict[str, Any]]:
        session = self._HTMLSession()
        session.headers.update(self.headers)

        visited: set[str] = set()
        queue: deque[tuple[str, int]] = deque()
        queue.append((root_url, 0))
        pages: List[Dict[str, Any]] = []

        try:
            while queue and len(pages) < self.max_pages_per_site:
                current_url, depth = queue.popleft()
                if current_url in visited:
                    continue
                visited.add(current_url)

                if depth > self.max_depth:
                    continue

                if not self._same_domain(root_url, current_url):
                    continue

                try:
                    html = self._fetch(session, current_url)
                except Exception as exc:  # noqa: BLE001
                    logger.warning("Dynamic crawler failed to fetch %s: %s", current_url, exc)
                    continue

                pages.append(
                    {
                        "root_url": root_url,
                        "url": current_url,
                        "html": html,
                    }
                )

                links = self._extract_links_from_html(current_url, html)
                prioritized = []
                others = []
                for link in links:
                    lower = link.lower()
                    if any(key in lower for key in ("contact", "imprint", "about", "team")):
                        prioritized.append(link)
                    else:
                        others.append(link)

                for link in prioritized + others:
                    if link not in visited:
                        queue.append((link, depth + 1))
        finally:
            try:
                session.close()
            except Exception:  # noqa: BLE001
                pass

        logger.debug(
            "Dynamic crawler finished %s with %d page(s).",
            root_url,
            len(pages),
        )
        return pages