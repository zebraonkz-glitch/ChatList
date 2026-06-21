"""Тема оформления и размер шрифта интерфейса."""

from __future__ import annotations

from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import QApplication

APP_NAME = "ChatList"
APP_VERSION = "1.0"
APP_DESCRIPTION = (
    "Приложение для отправки одного промта в несколько нейросетей "
    "и сравнения их ответов."
)

THEME_LIGHT = "light"
THEME_DARK = "dark"
DEFAULT_THEME = THEME_LIGHT
DEFAULT_FONT_SIZE = 10
FONT_SIZE_OPTIONS = (9, 10, 11, 12, 14)


def parse_font_size(value: str | None) -> int:
    try:
        size = int(str(value or DEFAULT_FONT_SIZE))
    except ValueError:
        size = DEFAULT_FONT_SIZE
    if size not in FONT_SIZE_OPTIONS:
        return DEFAULT_FONT_SIZE
    return size


def parse_theme(value: str | None) -> str:
    theme = (value or DEFAULT_THEME).strip().lower()
    return theme if theme in (THEME_LIGHT, THEME_DARK) else DEFAULT_THEME


def _base_rules(font_size: int) -> str:
    return f"""
    QWidget {{
        font-family: "Segoe UI", sans-serif;
        font-size: {font_size}pt;
    }}
    QToolTip {{
        font-size: {font_size}pt;
    }}
    """


def _light_stylesheet(font_size: int) -> str:
    return _base_rules(font_size) + """
    QWidget {
        color: #1a1a1a;
        background-color: #f5f5f5;
    }
    QMainWindow, QDialog {
        background-color: #ececec;
    }
    QMenuBar {
        background-color: #ececec;
        color: #1a1a1a;
    }
    QMenuBar::item:selected {
        background-color: #d0d0d0;
    }
    QMenu {
        background-color: #ffffff;
        color: #1a1a1a;
        border: 1px solid #c0c0c0;
    }
    QMenu::item:selected {
        background-color: #0078d4;
        color: #ffffff;
    }
    QPushButton {
        background-color: #ffffff;
        color: #1a1a1a;
        border: 1px solid #adadad;
        border-radius: 4px;
        padding: 4px 12px;
    }
    QPushButton:hover {
        background-color: #e5f1fb;
        border-color: #0078d4;
    }
    QPushButton:disabled {
        color: #888888;
        background-color: #f0f0f0;
    }
    QLineEdit, QTextEdit, QPlainTextEdit, QComboBox, QSpinBox {
        background-color: #ffffff;
        color: #1a1a1a;
        border: 1px solid #c0c0c0;
        border-radius: 3px;
        selection-background-color: #0078d4;
        selection-color: #ffffff;
    }
    QComboBox::drop-down {
        border: none;
    }
    QTableWidget, QTableView {
        background-color: #ffffff;
        alternate-background-color: #f7f7f7;
        gridline-color: #d0d0d0;
    }
    QHeaderView::section {
        background-color: #e8e8e8;
        color: #1a1a1a;
        border: 1px solid #c0c0c0;
        padding: 4px;
    }
    QScrollArea, QFrame, QSplitter::handle {
        background-color: #f5f5f5;
    }
    QProgressBar {
        border: 1px solid #c0c0c0;
        border-radius: 3px;
        text-align: center;
        background-color: #ffffff;
    }
    QProgressBar::chunk {
        background-color: #0078d4;
    }
    QGroupBox {
        border: 1px solid #c0c0c0;
        border-radius: 4px;
        margin-top: 8px;
        padding-top: 8px;
    }
    QGroupBox::title {
        subcontrol-origin: margin;
        left: 8px;
        padding: 0 4px;
    }
    QTabWidget::pane {
        border: 1px solid #c0c0c0;
        background-color: #ffffff;
    }
    QTabBar::tab {
        background-color: #e0e0e0;
        border: 1px solid #c0c0c0;
        padding: 6px 12px;
    }
    QTabBar::tab:selected {
        background-color: #ffffff;
    }
    """


def _dark_stylesheet(font_size: int) -> str:
    return _base_rules(font_size) + """
    QWidget {
        color: #e8e8e8;
        background-color: #2d2d2d;
    }
    QMainWindow, QDialog {
        background-color: #252525;
    }
    QMenuBar {
        background-color: #252525;
        color: #e8e8e8;
    }
    QMenuBar::item:selected {
        background-color: #3d3d3d;
    }
    QMenu {
        background-color: #2d2d2d;
        color: #e8e8e8;
        border: 1px solid #555555;
    }
    QMenu::item:selected {
        background-color: #094771;
        color: #ffffff;
    }
    QPushButton {
        background-color: #3c3c3c;
        color: #e8e8e8;
        border: 1px solid #555555;
        border-radius: 4px;
        padding: 4px 12px;
    }
    QPushButton:hover {
        background-color: #4a4a4a;
        border-color: #0078d4;
    }
    QPushButton:disabled {
        color: #777777;
        background-color: #333333;
    }
    QLineEdit, QTextEdit, QPlainTextEdit, QComboBox, QSpinBox {
        background-color: #1e1e1e;
        color: #e8e8e8;
        border: 1px solid #555555;
        border-radius: 3px;
        selection-background-color: #094771;
        selection-color: #ffffff;
    }
    QComboBox::drop-down {
        border: none;
    }
    QTableWidget, QTableView {
        background-color: #1e1e1e;
        alternate-background-color: #2a2a2a;
        gridline-color: #444444;
        color: #e8e8e8;
    }
    QHeaderView::section {
        background-color: #333333;
        color: #e8e8e8;
        border: 1px solid #555555;
        padding: 4px;
    }
    QScrollArea, QFrame, QSplitter::handle {
        background-color: #2d2d2d;
    }
    QProgressBar {
        border: 1px solid #555555;
        border-radius: 3px;
        text-align: center;
        background-color: #1e1e1e;
        color: #e8e8e8;
    }
    QProgressBar::chunk {
        background-color: #0078d4;
    }
    QGroupBox {
        border: 1px solid #555555;
        border-radius: 4px;
        margin-top: 8px;
        padding-top: 8px;
        color: #e8e8e8;
    }
    QGroupBox::title {
        subcontrol-origin: margin;
        left: 8px;
        padding: 0 4px;
    }
    QTabWidget::pane {
        border: 1px solid #555555;
        background-color: #2d2d2d;
    }
    QTabBar::tab {
        background-color: #333333;
        color: #e8e8e8;
        border: 1px solid #555555;
        padding: 6px 12px;
    }
    QTabBar::tab:selected {
        background-color: #2d2d2d;
    }
    QLabel {
        background-color: transparent;
    }
    """


def build_stylesheet(theme: str, font_size: int) -> str:
    if theme == THEME_DARK:
        return _dark_stylesheet(font_size)
    return _light_stylesheet(font_size)


def markdown_document_stylesheet(settings: dict[str, str]) -> str:
    theme = parse_theme(settings.get("theme"))
    font_size = parse_font_size(settings.get("font_size"))
    if theme == THEME_DARK:
        return (
            f"body {{ font-family: Segoe UI, sans-serif; font-size: {font_size}pt; "
            f"line-height: 1.5; color: #e8e8e8; background-color: #1e1e1e; }}"
            "pre { background-color: #2d2d2d; padding: 8px; border-radius: 4px; }"
            "code { background-color: #333333; padding: 2px 4px; border-radius: 3px; }"
            "h1, h2, h3, h4 { margin-top: 16px; margin-bottom: 8px; }"
            "ul, ol { margin-left: 20px; }"
            "blockquote { border-left: 3px solid #666; margin-left: 0; padding-left: 12px; color: #bbb; }"
        )
    return (
        f"body {{ font-family: Segoe UI, sans-serif; font-size: {font_size}pt; line-height: 1.5; }}"
        "pre { background-color: #f5f5f5; padding: 8px; border-radius: 4px; }"
        "code { background-color: #f0f0f0; padding: 2px 4px; border-radius: 3px; }"
        "h1, h2, h3, h4 { margin-top: 16px; margin-bottom: 8px; }"
        "ul, ol { margin-left: 20px; }"
        "blockquote { border-left: 3px solid #ccc; margin-left: 0; padding-left: 12px; color: #555; }"
    )


def apply_appearance(app: QApplication | None, settings: dict[str, str]) -> None:
    if app is None:
        return
    theme = parse_theme(settings.get("theme"))
    font_size = parse_font_size(settings.get("font_size"))
    app.setStyleSheet(build_stylesheet(theme, font_size))
    font = QFont("Segoe UI", font_size)
    app.setFont(font)
