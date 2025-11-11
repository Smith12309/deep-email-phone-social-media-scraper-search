thonimport logging
import time
from collections import deque
from typing import Any, Deque, Dict, List, Set, Tuple
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup

from extractors.email_parser import extract_emails
from extractors.phone_detector import extract_phone_numbers
from extractors.social_media_finder import find_social_media_links
from extractors.utils_validation import (
    ensure_url_has_scheme,
    is_valid_url,
    normalize_email,
    normalize_phone,
    safe_int,
)
from core.playwright_handler import fetch_page_content

logger = logging.getLogger(__name__)

class Crawler:
    """
    Simple breadth-first crawler that stays within a single domain per seed URL,
    prioritizing likely contact pages.
    """

    PRIORITY_KEYWORDS = ("contact", "kontakt", "about", "impressum", "team")

    def __init__(self, settings: Dict[str, Any]) -> None:
        self.settings = settings
        self.max_depth = safe_int(settings.get("max_depth"), 2)
        self.max_pages_per_site = safe_int(settings.get("max_pages_per_site"), 15)
        self.request_timeout = safe_int(settings.get("request_timeout"), 10)
        self.user_agent = settings.get("user_agent", "DeepContactScraper/1.0")
        self.use_playwright_fallback = bool(settings.get("use_playwright_fallback", True))
        self.allowed_content_types = settings.get("allowed_content_types") or ["text/html"]

    # ------- Public API -------

    def crawl(self, urls: List[str]) -> List[Dict[str, Any]]:
        all_results: List[Dict[str, Any]] = []

        for raw_url in urls:
            url = ensure_url_has_scheme(raw_url.strip())
            if not is_valid_url(url):
                logger.warning("Skipping invalid URL: %s", raw_url)
                continue

            logger.info("Crawling site: %s", url)
            try:
                site_results = self._crawl_site(url)
                all_results.extend(site_results)
            except Exception as exc:  # noqa: BLE001
                logger.exception("Failed to crawl %s: %s", url, exc)

        # Deduplicate overall results based on url + source_page + email + phone
        deduped: Dict[Tuple[str, str, str, str], Dict[str, Any]] = {}
        for record in all_results:
            key = (
                record.get("url", ""),
                record.get("source_page", ""),
                str(record.get("email", "")),
                str(record.get("phone", "")),
            )
            if key not in deduped:
                deduped[key] = record

        logger.info("Total unique records collected: %d", len(deduped))
        return list(deduped.values())

    # ------- Internal helpers -------

    def _crawl_site(self, start_url: str) -> List[Dict[str, Any]]:
        parsed_start = urlparse(start_url)
        start_domain = parsed_start.netloc

        queue: Deque[Tuple[str, int]] = deque()
        visited: Set[str] = set()

        queue.append((start_url, 0))
        visited.add(start_url)

        results: List[Dict[str, Any]] = []
        pages_crawled = 0

        while queue and pages_crawled < self.max_pages_per_site:
            url, depth = queue.popleft()
            logger.debug("Fetching %s (depth=%d)", url, depth)

            html = self._fetch_page(url)
            if html is None:
                continue

            pages_crawled += 1
            page_results = self._extract_from_page(start_url, url, html)
            results.extend(page_results)

            if depth >= self.max_depth:
                continue

            for next_url in self._extract_links(url, html):
                if next_url in visited:
                    continue
                parsed_next = urlparse(next_url)
                if parsed_next.netloc != start_domain:
                    continue  # stay within same domain
                visited.add(next_url)
                # Prioritize likely contact/about pages by pushing them to the left of the deque
                lower_path = parsed_next.path.lower()
                if any(keyword in lower_path for keyword in self.PRIORITY_KEYWORDS):
                    queue.appendleft((next_url, depth + 1))
                else:
                    queue.append((next_url, depth + 1))

        logger.info("Crawled %d pages for %s", pages_crawled, start_url)
        return results

    def _fetch_page(self, url: str) -> str | None:
        headers = {"User-Agent": self.user_agent}
        try:
            resp = requests.get(url, headers=headers, timeout=self.request_timeout)
        except requests.RequestException as exc:
            logger.warning("Request to %s failed: %s", url, exc)
            return self._playwright_fallback(url) if self.use_playwright_fallback else None

        content_type = resp.headers.get("Content-Type", "")
        if not any(ct in content_type for ct in self.allowed_content_types):
            logger.debug("Skipping %s due to unsupported content-type: %s", url, content_type)
            return None

        if resp.status_code >= 400:
            logger.warning("Got HTTP %s for %s", resp.status_code, url)
            if self.use_playwright_fallback:
                return self._playwright_fallback(url)
            return None

        logger.debug("Fetched %s via requests with status %s", url, resp.status_code)
        return resp.text

    def _playwright_fallback(self, url: str) -> str | None:
        if not self.use_playwright_fallback:
            return None
        try:
            start = time.time()
            html = fetch_page_content(url, timeout=self.request_timeout, user_agent=self.user_agent)
            elapsed = time.time() - start
            if html:
                logger.info("Fetched %s via Playwright in %.2fs", url, elapsed)
            return html
        except Exception as exc:  # noqa: BLE001
            logger.warning("Playwright fallback failed for %s: %s", url, exc)
            return None

    def _extract_from_page(self, site_url: str, page_url: str, html: str) -> List[Dict[str, Any]]:
        soup = BeautifulSoup(html, "html.parser")
        text = soup.get_text(" ", strip=True)

        email_set = extract_emails([html, text])
        phone_set = extract_phone_numbers([html, text])
        social_map = find_social_media_links([html, text])

        if not email_set and not phone_set and not any(social_map.values()):
            return []

        # normalize emails and phones for output consistency
        email_list = sorted({normalize_email(e) for e in email_set})
        phone_list = sorted({normalize_phone(p) for p in phone_set})

        path = urlparse(page_url).path or "/"

        base_record: Dict[str, Any] = {
            "url": site_url,
            "source_page": path,
        }

        # record may contain single items or lists if multiple per page
        if email_list:
            base_record["email"] = email_list[0] if len(email_list) == 1 else email_list
        if phone_list:
            base_record["phone"] = phone_list[0] if len(phone_list) == 1 else phone_list

        for platform, urls in social_map.items():
            if not urls:
                continue
            sorted_urls = sorted(urls)
            base_record[platform] = sorted_urls[0] if len(sorted_urls) == 1 else sorted_urls

        logger.debug(
            "Extracted from %s: emails=%d phones=%d socials=%s",
            page_url,
            len(email_list),
            len(phone_list),
            {k: len(v) for k, v in social_map.items()},
        )

        return [base_record]

    def _extract_links(self, base_url: str, html: str) -> List[str]:
        soup = BeautifulSoup(html, "html.parser")
        links: List[str] = []

        for a in soup.find_all("a", href=True):
            href = a["href"].strip()
            if href.startswith("#") or href.lower().startswith("mailto:") or href.lower().startswith(
                "tel:"
            ):
                continue
            absolute = urljoin(base_url, href)
            if is_valid_url(absolute):
                links.append(absolute)

        logger.debug("Found %d candidate links on %s", len(links), base_url)
        return links