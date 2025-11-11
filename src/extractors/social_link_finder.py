thonimport logging
import re
from typing import Dict, List

from bs4 import BeautifulSoup

from utils_cleaner import normalize_url

logger = logging.getLogger(__name__)

SOCIAL_DOMAINS: Dict[str, List[str]] = {
    "LinkedIn": ["linkedin.com"],
    "Twitter": ["twitter.com", "x.com"],
    "Facebook": ["facebook.com"],
    "Instagram": ["instagram.com"],
    "YouTube": ["youtube.com", "youtu.be"],
    "TikTok": ["tiktok.com"],
    "GitHub": ["github.com"],
    "Dribbble": ["dribbble.com"],
    "Behance": ["behance.net"],
}

def _classify_platform(url: str) -> str | None:
    for platform, domains in SOCIAL_DOMAINS.items():
        for domain in domains:
            if domain.lower() in url.lower():
                return platform
    return None

def extract_social_links(html_text: str) -> List[Dict[str, str]]:
    """
    Extract social media profile links from HTML.

    Returns a list of dicts with keys: 'platform' and 'url'.
    """
    soup = BeautifulSoup(html_text, "html.parser")
    results: List[Dict[str, str]] = []
    seen: set[str] = set()

    for a in soup.find_all("a", href=True):
        href = a["href"].strip()
        if not href or href.startswith("#") or href.lower().startswith("mailto:"):
            continue

        norm = normalize_url(href)
        platform = _classify_platform(norm)
        if not platform:
            continue

        # Skip obvious share links (heuristic)
        if re.search(r"share|intent|tweet|sharer\.php", norm, re.IGNORECASE):
            continue

        if norm in seen:
            continue
        seen.add(norm)

        results.append({"platform": platform, "url": norm})

    logger.debug("Social link finder found %d social profile(s).", len(results))
    return results