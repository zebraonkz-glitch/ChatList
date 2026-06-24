"""Каталоги приложения и загрузка .env (dev и PyInstaller)."""

from __future__ import annotations

import os
import sys
from pathlib import Path

from dotenv import load_dotenv

ENV_FILENAME = ".env"
ENV_EXAMPLE_FILENAME = ".env.example"


def runtime_dir() -> Path:
    """Каталог для .env, БД и логов — рядом с exe или исходниками."""
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent


def resource_dir() -> Path:
    """Каталог встроенных ресурсов (PyInstaller _MEIPASS)."""
    if getattr(sys, "frozen", False):
        return Path(getattr(sys, "_MEIPASS", Path(sys.executable).parent))
    return Path(__file__).resolve().parent


def env_file_path() -> Path:
    return runtime_dir() / ENV_FILENAME


def env_example_path() -> Path:
    return runtime_dir() / ENV_EXAMPLE_FILENAME


def load_env() -> Path | None:
    """Загружает .env из каталога приложения, затем из текущей папки."""
    env_path = env_file_path()
    if env_path.is_file():
        load_dotenv(env_path, override=True)
        return env_path

    cwd_env = Path.cwd() / ENV_FILENAME
    if cwd_env.is_file() and cwd_env.resolve() != env_path.resolve():
        load_dotenv(cwd_env, override=True)
        return cwd_env

    load_dotenv()
    return None


def env_hint(api_id: str) -> str:
    env_path = env_file_path()
    example_path = env_example_path()
    lines = [f"Укажите ключ в файле: {env_path}"]
    if example_path.is_file() and not env_path.is_file():
        lines.append(f"Скопируйте шаблон: Copy-Item '{example_path}' '{env_path}'")
    lines.append(f"Добавьте строку: {api_id}=ваш-ключ")
    return " ".join(lines)
