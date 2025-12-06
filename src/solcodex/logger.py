from __future__ import annotations

import logging
import sys

_LOG_FORMAT = "[%(levelname)s] %(asctime)s %(name)s: %(message)s"


def configure_logging(level: str = "INFO") -> None:
    handler = logging.StreamHandler(sys.stdout)
    formatter = logging.Formatter(_LOG_FORMAT)
    handler.setFormatter(formatter)

    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(level.upper())


__all__ = ["configure_logging"]
