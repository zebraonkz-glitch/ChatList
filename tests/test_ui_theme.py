"""Тесты темы оформления."""

from __future__ import annotations

import unittest

from ui_theme import (
    DEFAULT_FONT_SIZE,
    DEFAULT_THEME,
    THEME_DARK,
    THEME_LIGHT,
    build_stylesheet,
    markdown_document_stylesheet,
    parse_font_size,
    parse_theme,
)


class UiThemeTestCase(unittest.TestCase):
    def test_parse_theme_defaults(self) -> None:
        self.assertEqual(parse_theme(None), DEFAULT_THEME)
        self.assertEqual(parse_theme("dark"), THEME_DARK)
        self.assertEqual(parse_theme("unknown"), DEFAULT_THEME)

    def test_parse_font_size(self) -> None:
        self.assertEqual(parse_font_size(None), DEFAULT_FONT_SIZE)
        self.assertEqual(parse_font_size("12"), 12)
        self.assertEqual(parse_font_size("99"), DEFAULT_FONT_SIZE)

    def test_build_stylesheet_contains_font_size(self) -> None:
        stylesheet = build_stylesheet(THEME_LIGHT, 12)
        self.assertIn("12pt", stylesheet)

    def test_markdown_stylesheet_dark_theme(self) -> None:
        css = markdown_document_stylesheet({"theme": "dark", "font_size": "11"})
        self.assertIn("#1e1e1e", css)
        self.assertIn("11pt", css)


if __name__ == "__main__":
    unittest.main()
