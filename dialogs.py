"""Диалоговые окна: модели, настройки, история."""

from __future__ import annotations

import sqlite3

from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QButtonGroup,
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QFrame,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QRadioButton,
    QScrollArea,
    QSplitter,
    QTabWidget,
    QTableWidget,
    QTableWidgetItem,
    QTextBrowser,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

import network
from models import ChatService, HistoryResult, Model
from prompt_assistant import PromptSuggestion


MODEL_TYPES = ["openai", "deepseek", "groq", "openrouter"]
RESULT_ROW_HEIGHT = 150
HISTORY_RESULT_ROW_HEIGHT = 150


class MarkdownViewDialog(QDialog):
    def __init__(
        self,
        model_name: str,
        markdown_text: str,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle(f"Ответ — {model_name}")
        self.setMinimumSize(760, 560)

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel(f"Модель: {model_name}"))

        browser = QTextBrowser()
        browser.setOpenExternalLinks(True)
        browser.document().setDefaultStyleSheet(
            "body { font-family: Segoe UI, sans-serif; font-size: 11pt; line-height: 1.5; }"
            "pre { background-color: #f5f5f5; padding: 8px; border-radius: 4px; }"
            "code { background-color: #f0f0f0; padding: 2px 4px; border-radius: 3px; }"
            "h1, h2, h3, h4 { margin-top: 16px; margin-bottom: 8px; }"
            "ul, ol { margin-left: 20px; }"
            "blockquote { border-left: 3px solid #ccc; margin-left: 0; padding-left: 12px; color: #555; }"
        )
        browser.setMarkdown(markdown_text)
        layout.addWidget(browser, 1)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        buttons.rejected.connect(self.reject)
        close_button = buttons.button(QDialogButtonBox.StandardButton.Close)
        if close_button is not None:
            close_button.setText("Закрыть")
        layout.addWidget(buttons)


class HistoryResultRowWidget(QFrame):
    def __init__(
        self,
        item: HistoryResult,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.item = item
        self.setFrameShape(QFrame.Shape.StyledPanel)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)

        meta_box = QVBoxLayout()
        meta_box.addWidget(QLabel("Дата"))
        date_label = QLabel(item.created_at)
        date_label.setWordWrap(True)
        date_label.setMinimumWidth(120)
        date_label.setMaximumWidth(140)
        meta_box.addWidget(date_label)

        meta_box.addWidget(QLabel("Модель"))
        model_label = QLabel(item.model_name)
        model_label.setWordWrap(True)
        model_label.setMinimumWidth(120)
        model_label.setMaximumWidth(180)
        meta_box.addWidget(model_label)
        meta_box.addStretch()
        layout.addLayout(meta_box)

        content_box = QVBoxLayout()
        prompt_preview = item.prompt_text.replace("\n", " ")
        if len(prompt_preview) > 100:
            prompt_preview = prompt_preview[:97] + "..."
        content_box.addWidget(QLabel(f"Промт: {prompt_preview}"))
        content_box.addWidget(QLabel("Ответ"))
        editor = QTextEdit()
        editor.setReadOnly(True)
        editor.setPlainText(item.response)
        editor.setFixedHeight(HISTORY_RESULT_ROW_HEIGHT)
        editor.setLineWrapMode(QTextEdit.LineWrapMode.WidgetWidth)
        content_box.addWidget(editor)
        layout.addLayout(content_box, 1)

        actions_box = QVBoxLayout()
        open_btn = QPushButton("Открыть")
        open_btn.clicked.connect(self.on_open)
        actions_box.addWidget(open_btn)
        actions_box.addStretch()
        layout.addLayout(actions_box)

    def on_open(self) -> None:
        MarkdownViewDialog(self.item.model_name, self.item.response, self).exec()


def _readonly_item(text: str) -> QTableWidgetItem:
    item = QTableWidgetItem(text)
    item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
    return item


def _readonly_numeric_item(value: int | str) -> QTableWidgetItem:
    item = _readonly_item(str(value))
    item.setData(Qt.ItemDataRole.UserRole, int(value))
    return item


def _fill_table(table: QTableWidget, fill_callback) -> None:
    sorting = table.isSortingEnabled()
    table.setSortingEnabled(False)
    fill_callback()
    table.setSortingEnabled(sorting)


class ModelEditDialog(QDialog):
    def __init__(
        self,
        parent: QWidget | None = None,
        model: Model | None = None,
    ) -> None:
        super().__init__(parent)
        self.model = model
        self.setWindowTitle("Редактировать модель" if model else "Добавить модель")
        self.setMinimumWidth(480)

        layout = QFormLayout(self)

        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("gpt-4o-mini или openai/gpt-4o-mini")
        layout.addRow("Имя модели:", self.name_edit)

        self.url_edit = QLineEdit()
        self.url_edit.setPlaceholderText("https://api.openai.com/v1/chat/completions")
        layout.addRow("API URL:", self.url_edit)

        self.api_id_edit = QLineEdit()
        self.api_id_edit.setPlaceholderText("OPENAI_API_KEY")
        layout.addRow("Переменная .env:", self.api_id_edit)

        self.type_combo = QComboBox()
        self.type_combo.addItems(MODEL_TYPES)
        self.type_combo.currentTextChanged.connect(self.on_type_changed)
        layout.addRow("Тип API:", self.type_combo)

        self.active_check = QCheckBox("Активна")
        self.active_check.setChecked(True)
        layout.addRow("", self.active_check)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel,
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addRow(buttons)

        if model:
            self.name_edit.setText(model.name)
            self.url_edit.setText(model.api_url)
            self.api_id_edit.setText(model.api_id)
            index = self.type_combo.findText(model.model_type)
            if index >= 0:
                self.type_combo.setCurrentIndex(index)
            self.active_check.setChecked(model.is_active)
        else:
            self.on_type_changed(self.type_combo.currentText())

    def on_type_changed(self, model_type: str) -> None:
        if model_type != "openrouter":
            return
        if not self.url_edit.text().strip() or "openrouter.ai" in self.url_edit.text():
            self.url_edit.setText(network.OPENROUTER_API_URL)
        if not self.api_id_edit.text().strip() or self.api_id_edit.text() == "OPENAI_API_KEY":
            self.api_id_edit.setText(network.OPENROUTER_API_KEY_ENV)
        if not self.name_edit.text().strip():
            self.name_edit.setPlaceholderText("openai/gpt-4o-mini")

    def get_data(self) -> dict:
        return {
            "name": self.name_edit.text().strip(),
            "api_url": self.url_edit.text().strip(),
            "api_id": self.api_id_edit.text().strip(),
            "model_type": self.type_combo.currentText(),
            "is_active": self.active_check.isChecked(),
        }

    def accept(self) -> None:
        data = self.get_data()
        if not data["name"] or not data["api_url"] or not data["api_id"]:
            QMessageBox.warning(self, "ChatList", "Заполните все обязательные поля.")
            return
        super().accept()


class OpenRouterFetchWorker(QThread):
    finished = pyqtSignal(list)
    failed = pyqtSignal(str)

    def __init__(self, timeout: float, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.timeout = timeout

    def run(self) -> None:
        try:
            models = network.fetch_openrouter_models(timeout=self.timeout)
            self.finished.emit(models)
        except network.NetworkError as exc:
            self.failed.emit(str(exc))
        except Exception as exc:
            self.failed.emit(f"Ошибка: {exc}")


class OpenRouterImportDialog(QDialog):
    def __init__(self, service: ChatService, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.service = service
        self.worker: OpenRouterFetchWorker | None = None
        self._all_models: list[dict[str, str]] = []

        self.setWindowTitle("Импорт моделей OpenRouter")
        self.setMinimumSize(720, 520)

        layout = QVBoxLayout(self)
        layout.addWidget(
            QLabel(
                "Каталог моделей загружается с openrouter.ai. "
                f"Укажите {network.OPENROUTER_API_KEY_ENV} в файле .env.",
            ),
        )

        search_row = QHBoxLayout()
        search_row.addWidget(QLabel("Поиск:"))
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("openai, claude, llama...")
        self.search_edit.textChanged.connect(self.apply_filter)
        search_row.addWidget(self.search_edit)
        layout.addLayout(search_row)

        self.progress = QProgressBar()
        self.progress.setRange(0, 0)
        self.progress.setVisible(False)
        layout.addWidget(self.progress)

        self.models_list = QListWidget()
        self.models_list.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)
        layout.addWidget(self.models_list)

        select_row = QHBoxLayout()
        select_all_btn = QPushButton("Выбрать все")
        select_all_btn.clicked.connect(self.select_all)
        select_row.addWidget(select_all_btn)

        clear_btn = QPushButton("Снять выбор")
        clear_btn.clicked.connect(self.clear_selection)
        select_row.addWidget(clear_btn)

        reload_btn = QPushButton("Обновить каталог")
        reload_btn.clicked.connect(self.load_catalog)
        select_row.addWidget(reload_btn)
        select_row.addStretch()
        layout.addLayout(select_row)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel,
        )
        buttons.button(QDialogButtonBox.StandardButton.Ok).setText("Импортировать")
        buttons.accepted.connect(self.on_import)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        self.load_catalog()

    def load_catalog(self) -> None:
        self.progress.setVisible(True)
        self.models_list.clear()
        self.models_list.addItem("Загрузка каталога OpenRouter...")
        self.worker = OpenRouterFetchWorker(self.service.get_request_timeout(), self)
        self.worker.finished.connect(self.on_catalog_loaded)
        self.worker.failed.connect(self.on_catalog_failed)
        self.worker.start()

    def on_catalog_loaded(self, models: list) -> None:
        self.progress.setVisible(False)
        self._all_models = models
        self.apply_filter()

    def on_catalog_failed(self, message: str) -> None:
        self.progress.setVisible(False)
        self.models_list.clear()
        self.models_list.addItem(f"Ошибка: {message}")
        QMessageBox.warning(self, "ChatList", message)

    def apply_filter(self) -> None:
        query = self.search_edit.text().strip().lower()
        self.models_list.clear()
        for item in self._all_models:
            haystack = f"{item['id']} {item['name']} {item.get('description', '')}".lower()
            if query and query not in haystack:
                continue
            label = item["id"]
            if item.get("name") and item["name"] != item["id"]:
                label = f"{item['id']} — {item['name']}"
            list_item = QListWidgetItem(label)
            list_item.setFlags(
                list_item.flags()
                | Qt.ItemFlag.ItemIsUserCheckable
                | Qt.ItemFlag.ItemIsEnabled,
            )
            list_item.setCheckState(Qt.CheckState.Unchecked)
            list_item.setData(Qt.ItemDataRole.UserRole, item["id"])
            self.models_list.addItem(list_item)

    def select_all(self) -> None:
        for index in range(self.models_list.count()):
            item = self.models_list.item(index)
            if item and item.flags() & Qt.ItemFlag.ItemIsUserCheckable:
                item.setCheckState(Qt.CheckState.Checked)

    def clear_selection(self) -> None:
        for index in range(self.models_list.count()):
            item = self.models_list.item(index)
            if item and item.flags() & Qt.ItemFlag.ItemIsUserCheckable:
                item.setCheckState(Qt.CheckState.Unchecked)

    def on_import(self) -> None:
        selected_ids: list[str] = []
        for index in range(self.models_list.count()):
            item = self.models_list.item(index)
            if item and item.checkState() == Qt.CheckState.Checked:
                model_id = item.data(Qt.ItemDataRole.UserRole)
                if model_id:
                    selected_ids.append(str(model_id))

        if not selected_ids:
            QMessageBox.information(self, "ChatList", "Выберите хотя бы одну модель.")
            return

        imported = 0
        skipped = 0
        for model_id in selected_ids:
            try:
                self.service.create_model(
                    model_id,
                    network.OPENROUTER_API_URL,
                    network.OPENROUTER_API_KEY_ENV,
                    is_active=False,
                    model_type="openrouter",
                )
                imported += 1
            except sqlite3.IntegrityError:
                skipped += 1

        QMessageBox.information(
            self,
            "ChatList",
            f"Импортировано: {imported}\nПропущено (уже есть): {skipped}",
        )
        self.accept()


class ModelsDialog(QDialog):
    def __init__(self, service: ChatService, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.service = service
        self.setWindowTitle("Модели")
        self.setMinimumSize(820, 420)

        layout = QVBoxLayout(self)

        search_row = QHBoxLayout()
        search_row.addWidget(QLabel("Поиск:"))
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("Имя, URL, тип...")
        self.search_edit.textChanged.connect(self.refresh)
        search_row.addWidget(self.search_edit)
        layout.addLayout(search_row)

        self.table = QTableWidget(0, 6)
        self.table.setHorizontalHeaderLabels(
            ["ID", "Имя", "API URL", "Переменная .env", "Тип", "Активна"],
        )
        self.table.setSortingEnabled(True)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(5, QHeaderView.ResizeMode.ResizeToContents)
        layout.addWidget(self.table)

        buttons = QHBoxLayout()
        add_btn = QPushButton("Добавить")
        add_btn.clicked.connect(self.on_add)
        buttons.addWidget(add_btn)

        openrouter_btn = QPushButton("Из OpenRouter...")
        openrouter_btn.clicked.connect(self.on_import_openrouter)
        buttons.addWidget(openrouter_btn)

        edit_btn = QPushButton("Редактировать")
        edit_btn.clicked.connect(self.on_edit)
        buttons.addWidget(edit_btn)

        toggle_btn = QPushButton("Вкл/Выкл")
        toggle_btn.clicked.connect(self.on_toggle)
        buttons.addWidget(toggle_btn)

        delete_btn = QPushButton("Удалить")
        delete_btn.clicked.connect(self.on_delete)
        buttons.addWidget(delete_btn)

        refresh_btn = QPushButton("Обновить")
        refresh_btn.clicked.connect(self.refresh)
        buttons.addWidget(refresh_btn)

        buttons.addStretch()
        close_btn = QPushButton("Закрыть")
        close_btn.clicked.connect(self.accept)
        buttons.addWidget(close_btn)
        layout.addLayout(buttons)

        self.refresh()

    def on_import_openrouter(self) -> None:
        dialog = OpenRouterImportDialog(self.service, self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.refresh()

    def refresh(self) -> None:
        search = self.search_edit.text().strip().lower()

        def fill() -> None:
            self.table.setRowCount(0)
            for model in self.service.load_all_models():
                haystack = f"{model.name} {model.api_url} {model.api_id} {model.model_type}".lower()
                if search and search not in haystack:
                    continue
                row_index = self.table.rowCount()
                self.table.insertRow(row_index)
                id_item = _readonly_numeric_item(model.id)
                id_item.setData(Qt.ItemDataRole.UserRole, model.id)
                self.table.setItem(row_index, 0, id_item)
                self.table.setItem(row_index, 1, _readonly_item(model.name))
                self.table.setItem(row_index, 2, _readonly_item(model.api_url))
                self.table.setItem(row_index, 3, _readonly_item(model.api_id))
                self.table.setItem(row_index, 4, _readonly_item(model.model_type))
                self.table.setItem(row_index, 5, _readonly_item("Да" if model.is_active else "Нет"))

        _fill_table(self.table, fill)

    def _selected_model_id(self) -> int | None:
        rows = self.table.selectionModel().selectedRows()
        if not rows:
            return None
        item = self.table.item(rows[0].row(), 0)
        return int(item.data(Qt.ItemDataRole.UserRole)) if item else None

    def on_add(self) -> None:
        dialog = ModelEditDialog(self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        data = dialog.get_data()
        try:
            self.service.create_model(
                data["name"],
                data["api_url"],
                data["api_id"],
                is_active=data["is_active"],
                model_type=data["model_type"],
            )
        except sqlite3.IntegrityError:
            QMessageBox.warning(self, "ChatList", "Модель с таким именем уже существует.")
            return
        self.refresh()

    def on_edit(self) -> None:
        model_id = self._selected_model_id()
        if model_id is None:
            QMessageBox.information(self, "ChatList", "Выберите модель в таблице.")
            return
        model = self.service.get_model(model_id)
        if model is None:
            return
        dialog = ModelEditDialog(self, model)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        data = dialog.get_data()
        try:
            self.service.update_model(model_id, **data)
        except sqlite3.IntegrityError:
            QMessageBox.warning(self, "ChatList", "Модель с таким именем уже существует.")
            return
        self.refresh()

    def on_toggle(self) -> None:
        model_id = self._selected_model_id()
        if model_id is None:
            QMessageBox.information(self, "ChatList", "Выберите модель в таблице.")
            return
        try:
            self.service.toggle_model_active(model_id)
        except ValueError as exc:
            QMessageBox.warning(self, "ChatList", str(exc))
            return
        self.refresh()

    def on_delete(self) -> None:
        model_id = self._selected_model_id()
        if model_id is None:
            QMessageBox.information(self, "ChatList", "Выберите модель в таблице.")
            return
        answer = QMessageBox.question(
            self,
            "ChatList",
            "Удалить выбранную модель?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if answer != QMessageBox.StandardButton.Yes:
            return
        try:
            self.service.delete_model(model_id)
        except sqlite3.IntegrityError:
            QMessageBox.warning(
                self,
                "ChatList",
                "Нельзя удалить модель: есть сохранённые результаты.",
            )
            return
        self.refresh()


class ImprovePromptWorker(QThread):
    finished = pyqtSignal(dict)
    failed = pyqtSignal(str)

    def __init__(
        self,
        service: ChatService,
        prompt_text: str,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.service = service
        self.prompt_text = prompt_text

    def run(self) -> None:
        try:
            suggestion = self.service.improve_current_prompt(self.prompt_text)
            self.finished.emit(suggestion.to_dict())
        except Exception as exc:
            self.failed.emit(str(exc))


class PromptAssistantDialog(QDialog):
    ADAPTATION_LABELS = {
        "code": "Для кода",
        "analysis": "Для анализа",
        "creative": "Для креатива",
    }

    def __init__(
        self,
        suggestion: PromptSuggestion,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.suggestion = suggestion
        self._options: list[tuple[str, str]] = []
        self.setWindowTitle("AI-ассистент — улучшение промта")
        self.setMinimumSize(760, 620)

        layout = QVBoxLayout(self)

        layout.addWidget(QLabel("Исходный промт:"))
        original = QTextEdit()
        original.setReadOnly(True)
        original.setPlainText(suggestion.original)
        original.setMaximumHeight(100)
        layout.addWidget(original)

        layout.addWidget(QLabel("Выберите вариант для подстановки:"))
        self.option_group = QButtonGroup(self)
        options_layout = QVBoxLayout()

        self._add_option(options_layout, "improved", "Улучшенный", suggestion.improved, checked=True)
        for index, alt in enumerate(suggestion.alternatives, start=1):
            self._add_option(options_layout, f"alt_{index}", f"Альтернатива {index}", alt)
        for key, label in self.ADAPTATION_LABELS.items():
            text = suggestion.adaptations.get(key, "").strip()
            if text:
                self._add_option(options_layout, f"adapt_{key}", label, text)

        options_box = QGroupBox()
        options_box.setLayout(options_layout)
        layout.addWidget(options_box)

        preview_tabs = QTabWidget()
        preview_tabs.addTab(self._make_preview(suggestion.improved), "Улучшенный")
        for index, alt in enumerate(suggestion.alternatives, start=1):
            preview_tabs.addTab(self._make_preview(alt), f"Альт. {index}")
        adapt_widget = QWidget()
        adapt_layout = QVBoxLayout(adapt_widget)
        for key, label in self.ADAPTATION_LABELS.items():
            text = suggestion.adaptations.get(key, "")
            if text:
                adapt_layout.addWidget(QLabel(label + ":"))
                adapt_layout.addWidget(self._make_preview(text, height=80))
        if adapt_layout.count() == 0:
            adapt_layout.addWidget(QLabel("Адаптации не получены"))
        preview_tabs.addTab(adapt_widget, "Адаптации")
        layout.addWidget(preview_tabs, 1)

        buttons = QDialogButtonBox()
        apply_btn = buttons.addButton("Подставить в поле ввода", QDialogButtonBox.ButtonRole.AcceptRole)
        cancel_btn = buttons.addButton("Отмена", QDialogButtonBox.ButtonRole.RejectRole)
        apply_btn.clicked.connect(self.accept)
        cancel_btn.clicked.connect(self.reject)
        layout.addWidget(buttons)

    def _make_preview(self, text: str, height: int = 120) -> QTextEdit:
        editor = QTextEdit()
        editor.setReadOnly(True)
        editor.setPlainText(text)
        editor.setMinimumHeight(height)
        return editor

    def _add_option(
        self,
        layout: QVBoxLayout,
        key: str,
        title: str,
        text: str,
        *,
        checked: bool = False,
    ) -> None:
        preview = text.replace("\n", " ")
        if len(preview) > 120:
            preview = preview[:117] + "..."
        radio = QRadioButton(f"{title}: {preview}")
        radio.setChecked(checked)
        self.option_group.addButton(radio)
        layout.addWidget(radio)
        self._options.append((radio, text))

    def selected_text(self) -> str:
        for radio, text in self._options:
            if radio.isChecked():
                return text
        return self.suggestion.improved


class SettingsDialog(QDialog):
    def __init__(self, service: ChatService, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.service = service
        self.setWindowTitle("Настройки")
        self.setMinimumWidth(420)

        layout = QFormLayout(self)
        settings = self.service.get_settings()

        self.timeout_edit = QLineEdit(settings.get("request_timeout", "30"))
        layout.addRow("Таймаут запроса (с):", self.timeout_edit)

        self.tokens_edit = QLineEdit(settings.get("max_tokens", "2048"))
        layout.addRow("Макс. токенов:", self.tokens_edit)

        self.db_path_edit = QLineEdit(settings.get("db_path", "chatlist.db"))
        layout.addRow("Путь к БД:", self.db_path_edit)

        layout.addRow(QLabel("— AI-ассистент —"))

        self.assistant_enabled = QCheckBox("Включить AI-ассистент")
        self.assistant_enabled.setChecked(settings.get("assistant_enabled", "1") == "1")
        layout.addRow("", self.assistant_enabled)

        self.assistant_model_combo = QComboBox()
        self.assistant_model_combo.addItem("— не выбрана —", None)
        current_model_id = settings.get("assistant_model_id", "")
        for model in self.service.load_all_models():
            label = f"{model.name} ({model.model_type})"
            self.assistant_model_combo.addItem(label, model.id)
            if str(model.id) == str(current_model_id):
                self.assistant_model_combo.setCurrentIndex(self.assistant_model_combo.count() - 1)
        layout.addRow("Модель ассистента:", self.assistant_model_combo)

        self.assistant_prompt_edit = QLineEdit(settings.get("assistant_system_prompt", ""))
        self.assistant_prompt_edit.setPlaceholderText("Пусто — системный промт по умолчанию")
        layout.addRow("Системный промт:", self.assistant_prompt_edit)

        layout.addRow(
            QLabel("Рекомендуется быстрая модель OpenRouter для улучшения промтов."),
        )

        layout.addRow(
            QLabel("Изменение пути к БД вступит в силу после перезапуска программы."),
        )

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel,
        )
        buttons.button(QDialogButtonBox.StandardButton.Save).setText("Сохранить")
        buttons.accepted.connect(self.on_save)
        buttons.rejected.connect(self.reject)
        layout.addRow(buttons)

    def on_save(self) -> None:
        timeout = self.timeout_edit.text().strip()
        tokens = self.tokens_edit.text().strip()
        db_path = self.db_path_edit.text().strip()

        try:
            if float(timeout) <= 0:
                raise ValueError
        except ValueError:
            QMessageBox.warning(self, "ChatList", "Таймаут должен быть положительным числом.")
            return

        try:
            if int(tokens) <= 0:
                raise ValueError
        except ValueError:
            QMessageBox.warning(self, "ChatList", "Макс. токенов должно быть положительным целым.")
            return

        if not db_path:
            QMessageBox.warning(self, "ChatList", "Укажите путь к файлу базы данных.")
            return

        model_id = self.assistant_model_combo.currentData()
        self.service.save_settings(
            {
                "request_timeout": timeout,
                "max_tokens": tokens,
                "db_path": db_path,
                "assistant_enabled": "1" if self.assistant_enabled.isChecked() else "0",
                "assistant_model_id": "" if model_id is None else str(model_id),
                "assistant_system_prompt": self.assistant_prompt_edit.text().strip(),
            },
        )
        self.accept()


class HistoryDialog(QDialog):
    def __init__(self, service: ChatService, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.service = service
        self.setWindowTitle("История")
        self.setMinimumSize(960, 560)

        layout = QVBoxLayout(self)

        filter_row = QHBoxLayout()
        filter_row.addWidget(QLabel("Поиск промтов:"))
        self.prompt_search_edit = QLineEdit()
        self.prompt_search_edit.setPlaceholderText("Текст или теги...")
        self.prompt_search_edit.textChanged.connect(self.refresh_prompts)
        filter_row.addWidget(self.prompt_search_edit)
        filter_row.addWidget(QLabel("Поиск результатов:"))
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("Модель или ответ...")
        self.search_edit.textChanged.connect(self.refresh_results)
        filter_row.addWidget(self.search_edit)
        layout.addLayout(filter_row)

        splitter = QSplitter(Qt.Orientation.Horizontal)

        prompts_widget = QWidget()
        prompts_layout = QVBoxLayout(prompts_widget)
        prompts_layout.addWidget(QLabel("Промты:"))
        self.prompts_table = QTableWidget(0, 4)
        self.prompts_table.setHorizontalHeaderLabels(["ID", "Дата", "Промт", "Теги"])
        self.prompts_table.setSortingEnabled(True)
        self.prompts_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.prompts_table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.prompts_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.prompts_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.prompts_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self.prompts_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        self.prompts_table.itemSelectionChanged.connect(self.on_prompt_selected)
        prompts_layout.addWidget(self.prompts_table)

        delete_prompt_btn = QPushButton("Удалить промт")
        delete_prompt_btn.clicked.connect(self.on_delete_prompt)
        prompts_layout.addWidget(delete_prompt_btn)
        splitter.addWidget(prompts_widget)

        results_widget = QWidget()
        results_layout = QVBoxLayout(results_widget)
        results_layout.addWidget(QLabel("Результаты:"))

        self.results_scroll = QScrollArea()
        self.results_scroll.setWidgetResizable(True)
        self.results_scroll.setFrameShape(QFrame.Shape.StyledPanel)
        self.results_container = QWidget()
        self.results_cards_layout = QVBoxLayout(self.results_container)
        self.results_cards_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.results_cards_layout.setSpacing(8)
        self.results_scroll.setWidget(self.results_container)
        results_layout.addWidget(self.results_scroll)

        splitter.addWidget(results_widget)

        splitter.setSizes([360, 600])
        layout.addWidget(splitter)

        close_btn = QPushButton("Закрыть")
        close_btn.clicked.connect(self.accept)
        layout.addWidget(close_btn)

        self._selected_prompt_id: int | None = None
        self.refresh_prompts()
        self.refresh_results()

    def _clear_results_cards(self) -> None:
        while self.results_cards_layout.count():
            item = self.results_cards_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()

    def refresh_prompts(self) -> None:
        search = self.prompt_search_edit.text().strip()

        def fill() -> None:
            self.prompts_table.setRowCount(0)
            for prompt in self.service.load_prompts(search):
                row_index = self.prompts_table.rowCount()
                self.prompts_table.insertRow(row_index)
                preview = prompt.text.replace("\n", " ")
                if len(preview) > 60:
                    preview = preview[:57] + "..."
                id_item = _readonly_numeric_item(prompt.id)
                id_item.setData(Qt.ItemDataRole.UserRole, prompt.id)
                self.prompts_table.setItem(row_index, 0, id_item)
                self.prompts_table.setItem(row_index, 1, _readonly_item(prompt.created_at))
                self.prompts_table.setItem(row_index, 2, _readonly_item(preview))
                self.prompts_table.setItem(row_index, 3, _readonly_item(prompt.tags))

        _fill_table(self.prompts_table, fill)

    def on_prompt_selected(self) -> None:
        rows = self.prompts_table.selectionModel().selectedRows()
        if not rows:
            self._selected_prompt_id = None
        else:
            item = self.prompts_table.item(rows[0].row(), 0)
            self._selected_prompt_id = int(item.data(Qt.ItemDataRole.UserRole)) if item else None
        self.refresh_results()

    def refresh_results(self) -> None:
        search = self.search_edit.text().strip()
        results = self.service.load_history_results(self._selected_prompt_id, search)
        self._clear_results_cards()

        if not results:
            placeholder = QLabel("Нет сохранённых результатов")
            placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.results_cards_layout.addWidget(placeholder)
            return

        for item in results:
            self.results_cards_layout.addWidget(
                HistoryResultRowWidget(item, self.results_container),
            )

    def on_delete_prompt(self) -> None:
        rows = self.prompts_table.selectionModel().selectedRows()
        if not rows:
            QMessageBox.information(self, "ChatList", "Выберите промт для удаления.")
            return
        item = self.prompts_table.item(rows[0].row(), 0)
        if item is None:
            return
        prompt_id = int(item.data(Qt.ItemDataRole.UserRole))
        answer = QMessageBox.question(
            self,
            "ChatList",
            "Удалить промт и все связанные результаты?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if answer != QMessageBox.StandardButton.Yes:
            return
        self.service.delete_prompt(prompt_id)
        self._selected_prompt_id = None
        self.refresh_prompts()
        self.refresh_results()
