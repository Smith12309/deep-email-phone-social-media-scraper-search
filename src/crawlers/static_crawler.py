thonimport logging
from collections import deque
from dataclasses import dataclass
from typing import Any, Dict, List, Optional
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

@dataclass
class PageResult:
    root_url: str
    url: str
    html: str

class StaticCrawler:
    """
    Lightweight HTML crawler using requests + BeautifulSoup.

    - Restricts crawling to the same domain as the root URL.
    - Breadth-first up to max_depth and max_pages_per_site.
    """

    def __init__(
        self,
        headers: Optional[Dict[str, str]] = None,
        timeout: int = 15,
        max_depth: int = 2,
        max_pages_per_site: int = 15,
        proxy: Optional[str] = None,
    ) -> None:
        self.headers = headers or {}
        self.timeout = timeout
        self.max_depth = max_depth
        self.max_pages_per_site = max_pages_per_site
        self.proxies = {"http": proxy, "https": proxy} if proxy else None
        self.session = requests.Session()
        self.session.headers.update(self.headers)

    def _same_domain(self, root: str, url: str) -> bool:
        try:
            root_host = urlparse(root).netloc.lower()
            url_host = urlparse(url).netloc.lower()
            return root_host == url_host
        except Exception:  # noqa: BLE001
            return False

    def _extract_links(self, current_url: str, html: str) -> List[str]:
        soup = BeautifulSoup(html, "html.parser")
        links: List[str] = []

        for a in soup.find_all("a", href=True):
            href = a["href"].strip()
            if not href or href.startswith("#") or href.lower().startswith("mailto:"):
                continue
            abs_url = urljoin(current_url, href)
            links.append(abs_url)

        return links

    def _fetch(self, url: str) -> str:
        logger.debug("Static crawler fetching %s", url)
        resp = self.session.get(url, timeout=self.timeout, allow_redirects=True, proxies=self.proxies)
        resp.raise_for_status()
        return resp.text

    def crawl(self, root_url: str) -> List[Dict[str, Any]]:
        visited: set[str] = set()
        queue: deque[tuple[str, int]] = deque()
        queue.append((root_url, 0))
        pages: List[Dict[str, Any]] = []

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
                html = self._fetch(current_url)
            except requests.RequestException as exc:
                logger.warning("Failed to fetch %s: %s", current_url, exc)
                continue

            pages.append(
                {
                    "root_url": root_url,
                    "url": current_url,
                    "html": html,
                }
            )

            # Prioritize likely contact pages by enqueuing them earlier
            links = self._extract_links(current_url, html)
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

        logger.debug(
            "Static crawler finished %s with %d page(s).",
            root_url,
            len(pages),
        )
        return pages