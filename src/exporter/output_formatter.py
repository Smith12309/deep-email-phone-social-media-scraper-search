thonfrom __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Iterable, List, Dict

from utils.logger import get_logger

logger = get_logger(__name__)

def _ensure_parent(path: Path) -> None:
    if path.parent and not path.parent.exists():
        path.parent.mkdir(parents=True, exist_ok=True)

def write_json(records: Iterable[Dict], output_path: str) -> None:
    path = Path(output_path)
    _ensure_parent(path)
    data = list(records)
    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    logger.info("Wrote %d records to %s (JSON)", len(data), path)

def write_csv(records: Iterable[Dict], output_path: str) -> None:
    path = Path(output_path)
    _ensure_parent(path)
    data = list(records)
    if not data:
        logger.warning("No records to write to CSV: %s", path)
        return

    # Normalize keys across all records
    fieldnames = sorted({key for rec in data for key in rec.keys()})
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for rec in data:
            row = dict(rec)
            # Serialize nested structures for CSV
            for k, v in list(row.items()):
                if isinstance(v, (list, dict)):
                    row[k] = json.dumps(v, ensure_ascii=False)
            writer.writerow(row)
    logger.info("Wrote %d records to %s (CSV)", len(data), path)

def write_output(records: List[Dict], output_path: str, fmt: str = "json") -> None:
    fmt = fmt.lower()
    if fmt == "json":
        write_json(records, output_path)
    elif fmt == "csv":
        write_csv(records, output_path)
    elif fmt == "both":
        base = Path(output_path)
        write_json(records, str(base.with_suffix(".json")))
        write_csv(records, str(base.with_suffix(".csv")))
    else:
        raise ValueError(f"Unsupported output format: {fmt}")