thonimport logging
import re
from typing import Dict, Iterable, Set

logger = logging.getLogger(__name__)

SOCIAL_PATTERNS = {
"facebook": re.compile(r"https?://(?:www\.)?facebook\.com/[^\s\"'<>()]+", re.IGNORECASE),
"instagram": re.compile(r"https?://(?:www\.)?instagram\.com/[^\s\"'<>()]+", re.IGNORECASE),
"linkedin": re.compile(r"https?://(?:[a-z]{2,3}\.)?linkedin\.com/[^\s\"'<>()]+", re.IGNORECASE),
"twitter": re.compile(