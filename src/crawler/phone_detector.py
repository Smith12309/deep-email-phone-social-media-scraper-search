thonfrom typing import Iterable, List, Optional

from utils.regex_patterns import PHONE_REGEX

def extract_phone_numbers(text: str, default_country: Optional[str] = None) -> List[str]:
    """
    Extract phone numbers from text using a generic international pattern.
    The default_country is kept for future extensions (e.g., E.164 normalization),
    but we keep formatting as-is for readability.
    """
    if not text:
        return []
    matches = []
    for match in PHONE_REGEX.finditer(text):
        number = match.group(0)
        # Basic sanity filter: avoid catching years or postal codes by requiring at least 7 digits.
        digits = [ch for ch in number if ch.isdigit()]
        if len(digits) < 7:
            continue
        matches.append(number.strip())
    return matches