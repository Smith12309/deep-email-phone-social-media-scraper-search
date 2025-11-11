thonimport html
import logging
import re
from typing import Iterable, Set

from utils_cleaner import normalize_email

logger = logging.getLogger(__name__)

# Basic RFC 5322-like email regex (practical, not perfect)
EMAIL_REGEX = re.compile(
    r"""
    [a-zA-Z0-9.!#$%&'*+/=?^_`{|}~-]+
    @
    [a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?
    (?:\.[a-zA-Z]{2,63})+
    """,
    re.VERBOSE,
)

OBFUSCATED_PATTERNS = [
    (re.compile(r"\s*\[\s*at\s*\]\s*", re.IGNORECASE), "@"),
    (re.compile(r"\s*\(\s*at\s*\)\s*", re.IGNORECASE), "@"),
    (re.compile(r"\s+at\s+", re.IGNORECASE), "@"),
    (re.compile(r"\s*\[\s*dot\s*\]\s*", re.IGNORECASE), "."),
    (re.compile(r"\s*\(\s*dot\s*\)\s*", re.IGNORECASE), "."),
    (re.compile(r"\s+dot\s+", re.IGNORECASE), "."),
]

def _deobfuscate_email_text(text: str) -> str:
    """
    Try to convert common obfuscated email formats into standard form.
    Example: "info [at] example [dot] com" -> "info@example.com"
    """
    cleaned = html.unescape(text)
    for pattern, repl in OBFUSCATED_PATTERNS:
        cleaned = pattern.sub(repl, cleaned)
    return cleaned

def _decode_cloudflare_email(encoded: str) -> str:
    """
    Decode Cloudflare email protection if encountered.
    Format: /cdn-cgi/l/email-protection#<hex-string>
    """
    try:
        r = int(encoded[:2], 16)
        email = "".join(
            chr(int(encoded[i : i + 2], 16) ^ r)  # noqa: E203
            for i in range(2, len(encoded), 2)
        )
        return email
    except Exception as exc:  # noqa: BLE001
        logger.debug("Failed to decode Cloudflare email %s: %s", encoded, exc)
        return ""

def _find_cloudflare_emails(html_text: str) -> Set[str]:
    matches = re.findall(r"data-cfemail=\"([0-9a-fA-F]+)\"", html_text)
    decoded: Set[str] = set()
    for encoded in matches:
        email = _decode_cloudflare_email(encoded)
        if email:
            decoded.add(normalize_email(email))
    return decoded

def extract_emails(html_text: str | bytes | Iterable[str]) -> Set[str]:
    """
    Extract email addresses from HTML or text.

    Returns a set of normalized email strings.
    """
    if isinstance(html_text, bytes):
        text = html_text.decode("utf-8", errors="ignore")
    elif isinstance(html_text, str):
        text = html_text
    else:
        text = "\n".join(html_text)

    text = _deobfuscate_email_text(text)

    raw_emails = set(match.group(0) for match in EMAIL_REGEX.finditer(text))
    cf_emails = _find_cloudflare_emails(text)
    raw_emails.update(cf_emails)

    normalized = {normalize_email(e) for e in raw_emails if normalize_email(e)}
    logger.debug("Email detector found %d email(s).", len(normalized))
    return normalized