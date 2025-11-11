thonimport logging
import re
from typing import Iterable, Set

from .utils_validation import normalize_phone

logger = logging.getLogger(__name__)

# Flexible phone number pattern tuned for international formats,
# with special focus on Europe (DACH, Nordics).
PHONE_REGEX = re.compile(
    r"""
    (?:
        (?:(?:\+|00)\d{1,3}[\s\-]?)?     # Optional country code
        (?:\(0\)\s*)?                    # Optional (0)
        (?:\d[\s\-()]?){6,14}\d          # Local/national number
    )
    """,
    re.VERBOSE,
)

def _digit_count(s: str) -> int:
    return sum(ch.isdigit() for ch in s)

def extract_phone_numbers(sources: Iterable[str]) -> Set[str]:
    """
    Extract likely phone numbers from text sources.
    Filters by minimum digit count and normalizes formatting.
    """
    phones: Set[str] = set()

    for source in sources:
        if not source:
            continue

        for match in PHONE_REGEX.finditer(source):
            raw = match.group(0)
            if _digit_count(raw) < 7:
                continue
            phone = normalize_phone(raw)
            # very loose guard against obviously wrong patterns
            if 7 <= _digit_count(phone) <= 18:
                phones.add(phone)

    if phones:
        logger.debug("Extracted %d phone numbers", len(phones))
    return phones