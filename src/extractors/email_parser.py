thonimport logging
import re
from html import unescape
from typing import Iterable, Set

from .utils_validation import is_valid_email, normalize_email

logger = logging.getLogger(__name__)

# Simple but robust email pattern
EMAIL_REGEX = re.compile(
    r"""
    [a-zA-Z0-9.!#$%&'*+/=?^_`{|}~-]+
    @
    [a-zA-Z0-9-]+
    (?:\.[a-zA-Z0-9-]+)+
    """,
    re.VERBOSE,
)

# Cloudflare email protection uses data-cfemail attributes containing hex strings.
CFEMAIL_REGEX = re.compile(r"data-cfemail=[\"']?([0-9a-fA-F]+)[\"']?")

def _decode_cfemail(encoded: str) -> str:
    """
    Decode Cloudflare email obfuscation if present.
    Returns decoded email or empty string on failure.
    """
    try:
        r = int(encoded[:2], 16)
        email_bytes = []
        for i in range(2, len(encoded), 2):
            b = int(encoded[i : i + 2], 16) ^ r
            email_bytes.append(b)
        return bytes(email_bytes).decode("utf-8")
    except Exception:  # noqa: BLE001
        logger.debug("Failed to decode Cloudflare email: %s", encoded, exc_info=True)
        return ""

def _extract_cfemails(html: str) -> Set[str]:
    results: Set[str] = set()
    for match in CFEMAIL_REGEX.finditer(html):
        decoded = _decode_cfemail(match.group(1))
        if decoded and is_valid_email(decoded):
            results.add(normalize_email(decoded))
    return results

def _extract_plain_emails(text: str) -> Set[str]:
    results: Set[str] = set()
    for match in EMAIL_REGEX.finditer(text):
        email = normalize_email(match.group(0))
        if is_valid_email(email):
            results.add(email)
    return results

def extract_emails(sources: Iterable[str]) -> Set[str]:
    """
    Extract unique, validated emails from an iterable of text/html snippets.
    This function combines standard email detection and Cloudflare decoding.
    """
    emails: Set[str] = set()

    for raw_source in sources:
        if not raw_source:
            continue
        source = unescape(raw_source)

        cf_emails = _extract_cfemails(source)
        if cf_emails:
            logger.debug("Found %d Cloudflare-protected emails", len(cf_emails))
        emails.update(cf_emails)

        plain_emails = _extract_plain_emails(source)
        if plain_emails:
            logger.debug("Found %d plain emails", len(plain_emails))
        emails.update(plain_emails)

    return emails