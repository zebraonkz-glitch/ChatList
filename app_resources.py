"""Пути к ресурсам приложения (dev и PyInstaller)."""

from __future__ import annotations

from pathlib import Path

from PyQt6.QtGui import QIcon

from app_paths import resource_dir, runtime_dir

ICON_FILENAME = "app.ico"


def app_base_dir() -> Path:
    return runtime_dir()


def icon_path() -> Path:
    bundled = resource_dir() / ICON_FILENAME
    if bundled.is_file():
        return bundled
    return runtime_dir() / ICON_FILENAME


def load_app_icon() -> QIcon | None:
    path = icon_path()
    if not path.is_file():
        return None
    icon = QIcon(str(path))
    return icon if not icon.isNull() else None
