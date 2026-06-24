"""Тест версии приложения."""

from __future__ import annotations

import re
import unittest

from version import __version__


class VersionTestCase(unittest.TestCase):
    def test_version_format(self) -> None:
        self.assertRegex(__version__, r"^\d+\.\d+\.\d+$")

    def test_version_not_empty(self) -> None:
        self.assertTrue(__version__.strip())


if __name__ == "__main__":
    unittest.main()
