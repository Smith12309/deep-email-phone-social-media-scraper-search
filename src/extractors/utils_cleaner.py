thonimport logging
import re
from typing import Iterable, List, Sequence, TypeVar

from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

T = TypeVar("T")

def normalize_email(email: str | None) -> str:
    if not email:
        return ""
    email = email.strip().strip(".,;")
    email = email.replace("mailto:", "").replace("MAILTO:", "")
    return email.lower()

def normalize_phone(phone: str | None) -> str:
    if not phone:
        return ""
    phone = phone.strip()
    # E.164 style: +4912345...
    phone = re.sub(r"[^\d+]", "", phone)
    if not phone.startswith("+") and phone:
        phone = "+" + phone
    return phone

def normalize_url(url: str | None) -> str:
    if not url:
        return ""
    url = url.strip()

    # Handle protocol-relative URLs
    if url.startswith("//"):
        url = "https:" + url

    # Add scheme if missing
    if not re.match(r"^[a-zA-Z][a-zA-Z0-9+.-]*://", url):
        url = "https://" + url

    # Remove trailing slashes (but keep root)
    if url.endswith("/") and len(url) > len("https://x.xx/"):
        url = url.rstrip("/")

    return url

def html_to_text(html_text: str) -> str:
    soup = BeautifulSoup(html_text, "html.parser")
    # Remove script and style to reduce noise
    for tag in soup(["script", "style", "noscript"]):
        tag.decompose()
    text = soup.get_text(separator=" ", strip=True)
    logger.debug("Converted HTML to text of length %d.", len(text))
    return text

def deduplicate_preserve_order(seq: Sequence[T] | Iterable[T]) -> List[T]:
    seen: set[T] = set()
    out: List[T] = []
    for item in seq:
        if item in seen:
            continue
        seen.add(item)
        out.append(item)
    return out