from __future__ import annotations

import logging
import sys
from typing import Optional


def configure_logging(level: str = "INFO") -> None:
    """Configure app-wide structured-ish logging.

    We keep dependencies minimal (standard library only) but format logs so they are
    easy to grep and feed into a log aggregator.
    """

    root = logging.getLogger()
    if root.handlers:
        # Avoid double handlers when running in reload / tests.
        return

    numeric_level = getattr(logging, level.upper(), logging.INFO)
    root.setLevel(numeric_level)

    handler = logging.StreamHandler(stream=sys.stdout)
    handler.setLevel(numeric_level)
    formatter = logging.Formatter(
        fmt="%(asctime)s %(levelname)s %(name)s %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S%z",
    )
    handler.setFormatter(formatter)
    root.addHandler(handler)


def get_logger(name: Optional[str] = None) -> logging.Logger:
    return logging.getLogger(name or "agentic-ai")
