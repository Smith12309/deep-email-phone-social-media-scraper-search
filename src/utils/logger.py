thonimport logging
import sys
from typing import Optional

_LOGGER_CONFIGURED = False

def _configure_root_logger(level: int = logging.INFO) -> None:
    global _LOGGER_CONFIGURED
    if _LOGGER_CONFIGURED:
        return

    handler = logging.StreamHandler(sys.stdout)
    formatter = logging.Formatter(
        fmt="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    handler.setFormatter(formatter)

    root = logging.getLogger()
    root.setLevel(level)
    root.addHandler(handler)

    _LOGGER_CONFIGURED = True

def get_logger(name: Optional[str] = None) -> logging.Logger:
    """
    Get a module-level logger with sane defaults.
    """
    _configure_root_logger()
    return logging.getLogger(name if name else __name__)