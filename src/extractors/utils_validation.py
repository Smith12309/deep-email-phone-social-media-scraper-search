thonimport logging
import re
from typing import Optional
from urllib.parse import urlparse

logger = logging.getLogger(__name__)

BASIC_EMAIL_REGEX = re.compile(
    r"^[^@\s]+@[^@\s]+\.[^@\s]+$",
)

def normalize_email(email: str) -> str:
    return email.strip().lower()

def is_valid_email(email: str) -> bool:
    return bool(BASIC_EMAIL_REGEX.match(email))

def normalize_phone(phone: str) -> str:
    """
    Normalize phone numbers by collapsing whitespace and separators.
    Keeps leading '+' or '00' for country code when present.
    """
    phone = phone.strip()
    if not phone:
        return phone

    # Preserve leading '+' or '00'
    prefix = ""
    if phone.startswith("+"):
        prefix = "+"
        phone = phone[1:]
    elif phone.startswith("00"):
        prefix = "00"
        phone = phone[2:]

    digits_and_zero = re.sub(r"[^\d]", "", phone)
    normalized = prefix + digits_and_zero
    return normalized

def is_valid_url(url: str) -> bool:
    try:
        parsed = urlparse(url)
        return parsed.scheme in {"http", "https"} and bool(parsed.netloc)
    except Exception:  # noqa: BLE001
        return False

def ensure_url_has_scheme(url: str, default_scheme: str = "https") -> str:
    parsed = urlparse(url)
    if not parsed.scheme:
        return f"{default_scheme}://{url}"
    return url

def safe_int(value: Optional[int], fallback: int) -> int:
    try:
        if value is None:
            return fallback
        return int(value)
    except (TypeError, ValueError):
        logger.debug("Failed to cast %r to int, using fallback %d", value, fallback)
        return fallback