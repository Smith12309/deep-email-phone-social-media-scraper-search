thonimport logging
import re
from typing import Iterable, List, Set

import phonenumbers

from utils_cleaner import normalize_phone

logger = logging.getLogger(__name__)

# Rough candidate phone number pattern. Real validation is delegated to phonenumbers.
PHONE_CANDIDATE_REGEX = re.compile(
    r"""
    (?:
        \+?\d{1,3}[\s\-\(\)]*     # Country code (optional)
    )?
    (?:\d[\s\-\(\)]*){6,15}      # Main digits
    """,
    re.VERBOSE,
)

def _iter_phone_candidates(text: str | bytes | Iterable[str]) -> List[str]:
    if isinstance(text, bytes):
        source = text.decode("utf-8", errors="ignore")
    elif isinstance(text, str):
        source = text
    else:
        source = "\n".join(text)

    candidates = [m.group(0) for m in PHONE_CANDIDATE_REGEX.finditer(source)]
    logger.debug("Phone parser found %d candidate strings.", len(candidates))
    return candidates

def extract_phone_numbers(
    text: str | bytes | Iterable[str],
    regions: List[str] | None = None,
) -> Set[str]:
    """
    Extract normalized E.164 phone numbers from text.

    :param text: Source text.
    :param regions: List of ISO country codes to attempt parsing against.
                    Useful for DACH & Nordic or other regional formats.
    """
    regions = regions or ["US"]
    candidates = _iter_phone_candidates(text)
    numbers: Set[str] = set()

    for candidate in candidates:
        candidate_clean = re.sub(r"[^\d+]", "", candidate)
        if len(candidate_clean) < 6:
            continue

        parsed_number = None
        for region in regions:
            try:
                parsed = phonenumbers.parse(candidate_clean, region)
                if phonenumbers.is_possible_number(parsed) and phonenumbers.is_valid_number(parsed):
                    parsed_number = parsed
                    break
            except phonenumbers.NumberParseException:
                continue

        if parsed_number:
            e164 = phonenumbers.format_number(
                parsed_number,
                phonenumbers.PhoneNumberFormat.E164,
            )
            normalized = normalize_phone(e164)
            if normalized:
                numbers.add(normalized)

    logger.debug("Phone parser validated %d phone number(s).", len(numbers))
    return numbers