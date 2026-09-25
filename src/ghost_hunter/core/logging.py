"""Structured logging with secret redaction."""

from __future__ import annotations

import logging
import sys

from .config import redact_dict


def get_logger(name: str) -> logging.Logger:
    logger = logging.getLogger(name)
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s"))
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
    return logger


def log_safe(logger: logging.Logger, msg: str, extra: dict | None = None) -> None:
    if extra:
        logger.info("%s | %s", msg, redact_dict(extra))
    else:
        logger.info("%s", msg)
