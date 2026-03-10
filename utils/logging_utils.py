from __future__ import annotations

import logging
import os
from typing import Optional


def get_log_level(default: str = "INFO") -> int:
    """Resolve log level from LOG_LEVEL env var or default."""
    level_name = os.getenv("LOG_LEVEL", default).upper()
    return getattr(logging, level_name, logging.INFO)


def get_logger(name: Optional[str] = None) -> logging.Logger:
    """Return a configured logger with a consistent format."""
    logger = logging.getLogger(name if name else "enterprise_data_quality_monitor")
    if not logger.handlers:
        handler = logging.StreamHandler()
        formatter = logging.Formatter(
            "%(asctime)s | %(name)s | %(levelname)s | %(message)s"
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
    logger.setLevel(get_log_level())
    logger.propagate = False
    return logger

