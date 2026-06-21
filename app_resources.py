"""Пути к ресурсам приложения (dev и PyInstaller)."""

from __future__ import annotations

import sys
from pathlib import Path

from PyQt6.QtGui import QIcon

ICON_FILENAME = "app.ico"


def app_base_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(getattr(sys, "_MEIPASS", Path(sys.executable).parent))
    return Path(__file__).resolve().parent


def icon_path() -> Path:
    return app_base_dir() / ICON_FILENAME


def load_app_icon() -> QIcon | None:
    path = icon_path()
    if not path.is_file():
        return None
    icon = QIcon(str(path))
    return icon if not icon.isNull() else None
