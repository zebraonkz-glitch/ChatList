"""Тесты путей и загрузки .env."""

from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from app_paths import ENV_FILENAME, env_file_path, env_hint, load_env, runtime_dir


class AppPathsTestCase(unittest.TestCase):
    def test_runtime_dir_is_directory(self) -> None:
        self.assertTrue(runtime_dir().is_dir())

    def test_load_env_from_runtime(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            runtime = Path(tmp)
            env_path = runtime / ENV_FILENAME
            env_path.write_text("TEST_ENV_KEY=secret-value\n", encoding="utf-8")
            with patch("app_paths.runtime_dir", return_value=runtime):
                with patch.dict(os.environ, {}, clear=False):
                    os.environ.pop("TEST_ENV_KEY", None)
                    loaded = load_env()
                    self.assertEqual(loaded, env_path)
                    self.assertEqual(os.getenv("TEST_ENV_KEY"), "secret-value")

    def test_env_hint_shows_path(self) -> None:
        hint = env_hint("OPENROUTER_API_KEY")
        self.assertIn("OPENROUTER_API_KEY", hint)
        self.assertIn(str(env_file_path()), hint)


if __name__ == "__main__":
    unittest.main()
