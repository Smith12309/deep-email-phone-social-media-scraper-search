thonfrom typing import Dict, Iterable, List

def _normalize_email(email: str) -> str:
    return email.strip().lower()

def dedupe_emails(emails: Iterable[str]) -> List[str]:
    seen = set()
    result: List[str] = []
    for e in emails:
        norm = _normalize_email(e)
        if not norm or norm in seen:
            continue
        seen.add(norm)
        result.append(e.strip())
    return result

def _normalize_phone(number: str) -> str:
    # Keep leading +, strip spaces and punctuation, keep digits
    number = number.strip()
    if not number:
        return ""
    sign = "+" if number.startswith("+") else ""
    digits = "".join(ch for ch in number if ch.isdigit())
    return sign + digits

def dedupe_phone_numbers(numbers: Iterable[str]) -> List[str]:
    seen = set()
    result: List[str] = []
    for n in numbers:
        norm = _normalize_phone(n)
        if not norm or norm in seen:
            continue
        seen.add(norm)
        result.append(n.strip())
    return result

def dedupe_social_profiles(profiles: Dict[str, str]) -> Dict[str, str]:
    """
    Deduplicate social profile URLs by platform.
    If multiple URLs are provided for a platform, keep the first.
    """
    deduped: Dict[str, str] = {}
    for platform, url in profiles.items():
        if platform not in deduped and url:
            deduped[platform] = url.strip()
    return deduped