thonimport json
import logging
from typing import Any, Dict, List

logger = logging.getLogger(__name__)

def export_to_json(records: List[Dict[str, Any]], path: str) -> None:
    """
    Export contact records as a JSON array to the given file path.
    """
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(records, f, indent=2, ensure_ascii=False)
        logger.info("Exported %d record(s) to %s", len(records), path)
    except Exception as exc:  # noqa: BLE001
        logger.error("Failed to export JSON to %s: %s", path, exc)
        raise