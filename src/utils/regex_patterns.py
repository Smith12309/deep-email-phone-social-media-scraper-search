thonimport re
from typing import Dict, Pattern

# Basic but practical email detection pattern
EMAIL_REGEX: Pattern[str] = re.compile(
r"[a-zA-Z0-9.!#$%&'*+/=?^_`{|}~-]+@"
r"[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?"
r"(?:\.[a-zA-Z]{2,})+"
)

# Phone pattern tuned for international formats and common European local formats
PHONE_REGEX: Pattern[str] = re.compile(
r"""
(?:
(?P<intl>\+\d{1,3}[\s./-]?)?      # optional country code like +49 or +1
(?:\(0\))?                        # optional (0) trunk
(?:\d[\s./-]?){6,14}\d           # local/national number
)
""",
re.VERBOSE,
)

# Keywords for pages that likely contain contact details
CONTACT_PAGE_KEYWORDS = [
"contact",
"kontakt",
"impressum",
"about",
"team",
"company",
"staff",
"people",
"crew",
]

SOCIAL_DOMAINS: Dict[str, str] = {
"linkedin": "linkedin.com",
"twitter": "twitter.com",
"x": "x.com",
"facebook": "facebook.com",
"instagram": "instagram.com",
"youtube": "youtube.com",
"tiktok": "tiktok.com",
"github": "github.com",
"gitlab": "gitlab.com",
"behance": "behance.net",
"dribbble": "dribbble.com",
}

# Social URL generic pattern (we still check the domain separately)
SOCIAL_URL_REGEX: Pattern[str] = re.compile(