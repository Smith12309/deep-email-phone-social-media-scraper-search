thonfrom __future__ import annotations

from typing import Dict, List, Tuple
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup

from utils.logger import get_logger
from utils.regex_patterns import (
    EMAIL_REGEX,
    CONTACT_PAGE_KEYWORDS,
    SOCIAL_DOMAINS,
    SOCIAL_URL_REGEX,
)
from crawler.phone_detector import extract_phone_numbers

logger = get_logger(__name__)

def _decode_cfemail(cfemail: str)) -> str:
    """
    Decode Cloudflare email obfuscation.
    """
    r = int(cfemail[:2], 16)
    email = "".join(chr(int(cfemail[i : i + 2], 16) ^ r) for i in range(2, len(cfemail), 2))
    return email

def _extract_cf_emails(soup: BeautifulSoup) -> List[str]:
    emails: List[str] = []
    for el in soup.select("a.__cf_email__, span.__cf_email__"):
        cfemail = el.get("data-cfemail")
        if not cfemail:
            continue
        try:
            decoded = _decode_cfemail(cfemail)
            emails.append(decoded)
        except Exception as exc:  # pragma: no cover - extremely unlikely edge cases
            logger.debug("Failed to decode cfemail: %s", exc)
    return emails

def extract_contacts(html: str, base_url: str) -> Dict:
    soup = BeautifulSoup(html, "html.parser")

    text_content = soup.get_text(separator=" ", strip=True)
    title_tag = soup.find("title")
    page_title = title_tag.get_text(strip=True) if title_tag else ""

    # Emails: from text and mailto links
    emails = set()

    # 1) From mailto links
    for a in soup.find_all("a", href=True):
        href = a["href"]
        if href.startswith("mailto:"):
            candidate = href.split(":", 1)[1].split("?")[0]
            if EMAIL_REGEX.fullmatch(candidate):
                emails.add(candidate)

    # 2) From raw text
    for match in EMAIL_REGEX.finditer(text_content):
        emails.add(match.group(0))

    # 3) Cloudflare obfuscated emails
    for cf_email in _extract_cf_emails(soup):
        emails.add(cf_email)

    # Phone numbers
    phones = set(extract_phone_numbers(text_content))

    # Social profiles
    social_profiles: Dict[str, str] = {}
    for a in soup.find_all("a", href=True):
        href = a["href"].strip()
        if not href.lower().startswith("http"):
            href = urljoin(base_url, href)

        if not SOCIAL_URL_REGEX.match(href):
            continue

        for platform, domain in SOCIAL_DOMAINS.items():
            if domain in href.lower():
                social_profiles.setdefault(platform, href)
                break

    # Find candidate links for deeper crawling
    candidate_links = find_candidate_links(html, base_url)

    return {
        "emails": list(emails),
        "phoneNumbers": list(phones),
        "socialProfiles": social_profiles,
        "pageTitle": page_title,
        "candidateLinks": candidate_links,
    }

def _score_candidate(href: str, text: str) -> int:
    score = 0
    haystack = (href + " " + text).lower()
    for keyword in CONTACT_PAGE_KEYWORDS:
        if keyword in haystack:
            score += 1
    return score

def find_candidate_links(html: str, base_url: str, max_links: int = 15) -> List[str]:
    """
    Return a list of absolute URLs that are likely to contain contact information.
    """
    soup = BeautifulSoup(html, "html.parser")
    links: List[Tuple[int, str]] = []

    base_domain = urlparse(base_url).netloc

    for a in soup.find_all("a", href=True):
        href = a["href"]
        text = a.get_text(" ", strip=True)
        absolute = urljoin(base_url, href)

        parsed = urlparse(absolute)
        if not parsed.scheme.startswith("http"):
            continue
        if parsed.netloc and parsed.netloc != base_domain:
            # stay within same domain
            continue

        score = _score_candidate(parsed.path or "", text)
        if score <= 0:
            continue

        links.append((score, absolute))

    # Sort by score descending, then URL for stability
    links.sort(key=lambda t: (-t[0], t[1]))
    deduped: List[str] = []
    seen = set()
    for _, url in links:
        if url in seen:
            continue
        seen.add(url)
        deduped.append(url)
        if len(deduped) >= max_links:
            break

    return deduped