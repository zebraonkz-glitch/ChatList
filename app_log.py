"""Логирование запросов в logs/chatlist.log."""

from __future__ import annotations

import logging
from pathlib import Path

from app_paths import runtime_dir

LOG_PATH = runtime_dir() / "logs" / "chatlist.log"


def setup_logging() -> logging.Logger:
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    logger = logging.getLogger("chatlist")
    if logger.handlers:
        return logger
    logger.setLevel(logging.INFO)
    handler = logging.FileHandler(LOG_PATH, encoding="utf-8")
    handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))
    logger.addHandler(handler)
    return logger
