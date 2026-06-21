import sys

from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtWidgets import (
    QApplication,
    QComboBox,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMainWindow,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

import network
from dialogs import HistoryDialog, ModelsDialog, SettingsDialog
from models import ChatService, TempResult


class FetchWorker(QThread):
    finished = pyqtSignal(list)
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
            active_models = self.service.load_active_models()
            if not active_models:
                self.failed.emit("Нет активных моделей. Включите модели в базе данных.")
                return
            results = network.send_to_all_models(
                active_models,
                self.prompt_text,
                timeout=self.service.get_request_timeout(),
                max_tokens=self.service.get_max_tokens(),
            )
            payload = [
                {
                    "model_id": item.model_id,
                    "model_name": item.model_name,
                    "response": item.response,
                    "selected": item.selected,
                }
                for item in results
            ]
            self.finished.emit(payload)
        except Exception as exc:
            self.failed.emit(str(exc))


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.service = ChatService()
        self.worker: FetchWorker | None = None
        self._loading = False

        self.setWindowTitle("ChatList")
        self.setMinimumSize(900, 600)

        self._create_menu()

        root = QWidget()
        self.setCentralWidget(root)
        layout = QVBoxLayout(root)

        layout.addWidget(QLabel("Сохранённые промты:"))
        self.prompt_combo = QComboBox()
        self.prompt_combo.currentIndexChanged.connect(self.on_prompt_selected)
        layout.addWidget(self.prompt_combo)

        layout.addWidget(QLabel("Промт:"))
        self.prompt_edit = QTextEdit()
        self.prompt_edit.setPlaceholderText("Введите запрос для нейросетей...")
        self.prompt_edit.setMinimumHeight(120)
        layout.addWidget(self.prompt_edit)

        buttons = QHBoxLayout()
        self.send_button = QPushButton("Отправить")
        self.send_button.clicked.connect(self.on_send)
        buttons.addWidget(self.send_button)

        self.save_button = QPushButton("Сохранить")
        self.save_button.setEnabled(False)
        self.save_button.clicked.connect(self.on_save)
        buttons.addWidget(self.save_button)

        self.refresh_button = QPushButton("Обновить промты")
        self.refresh_button.clicked.connect(self.refresh_prompts)
        buttons.addWidget(self.refresh_button)

        buttons.addStretch()
        layout.addLayout(buttons)

        self.progress = QProgressBar()
        self.progress.setRange(0, 0)
        self.progress.setVisible(False)
        layout.addWidget(self.progress)

        self.status_label = QLabel("Готово")
        layout.addWidget(self.status_label)

        layout.addWidget(QLabel("Результаты:"))
        self.results_table = QTableWidget(0, 3)
        self.results_table.setHorizontalHeaderLabels(["Модель", "Ответ", "Выбрать"])
        header = self.results_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Interactive)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Fixed)
        header.setMinimumSectionSize(80)
        self.results_table.setColumnWidth(0, 220)
        self.results_table.setColumnWidth(2, 90)
        self.results_table.verticalHeader().setVisible(True)
        self.results_table.verticalHeader().setDefaultSectionSize(120)
        self.results_table.setWordWrap(True)
        self.results_table.setAlternatingRowColors(True)
        self.results_table.itemChanged.connect(self.on_result_item_changed)
        header.sectionResized.connect(self._update_response_heights)
        layout.addWidget(self.results_table, 1)

        self.refresh_prompts()

    def _create_menu(self) -> None:
        menu_bar = self.menuBar()
        app_menu = menu_bar.addMenu("Приложение")

        models_action = app_menu.addAction("Модели...")
        models_action.triggered.connect(self.open_models)

        settings_action = app_menu.addAction("Настройки...")
        settings_action.triggered.connect(self.open_settings)

        history_action = app_menu.addAction("История...")
        history_action.triggered.connect(self.open_history)

    def open_models(self) -> None:
        ModelsDialog(self.service, self).exec()

    def open_settings(self) -> None:
        SettingsDialog(self.service, self).exec()

    def open_history(self) -> None:
        dialog = HistoryDialog(self.service, self)
        dialog.exec()
        self.refresh_prompts()

    def refresh_prompts(self) -> None:
        self.prompt_combo.blockSignals(True)
        self.prompt_combo.clear()
        self.prompt_combo.addItem("— новый промт —", None)
        for prompt in self.service.load_prompts():
            preview = prompt.text.replace("\n", " ")
            if len(preview) > 80:
                preview = preview[:77] + "..."
            label = f"[{prompt.created_at}] {preview}"
            self.prompt_combo.addItem(label, prompt.id)
        self.prompt_combo.blockSignals(False)

    def on_prompt_selected(self, index: int) -> None:
        if index <= 0:
            self.service.current_prompt_id = None
            self.service.current_prompt_text = ""
            return
        prompt_id = self.prompt_combo.currentData()
        if prompt_id is None:
            return
        prompt = self.service.select_saved_prompt(int(prompt_id))
        if prompt:
            self.prompt_edit.setPlainText(prompt.text)

    def set_loading(self, loading: bool, message: str = "") -> None:
        self._loading = loading
        self.progress.setVisible(loading)
        self.send_button.setEnabled(not loading)
        self.save_button.setEnabled(not loading and bool(self.service.temp_results))
        if message:
            self.status_label.setText(message)

    def on_send(self) -> None:
        if self._loading:
            return

        prompt_text = self.prompt_edit.toPlainText().strip()
        if not prompt_text:
            QMessageBox.warning(self, "ChatList", "Введите текст промта.")
            return

        try:
            self.service.resolve_prompt_id(prompt_text)
        except ValueError as exc:
            QMessageBox.warning(self, "ChatList", str(exc))
            return

        self.service.clear_temp_results()
        self.populate_results_table()
        self.set_loading(True, "Отправка запросов...")

        self.worker = FetchWorker(self.service, prompt_text, self)
        self.worker.finished.connect(self.on_fetch_finished)
        self.worker.failed.connect(self.on_fetch_failed)
        self.worker.start()

    def on_fetch_finished(self, results: list) -> None:
        temp_results = [TempResult(**item) for item in results]
        self.service.set_temp_results(temp_results)
        self.populate_results_table()
        self.set_loading(False, f"Получено ответов: {len(temp_results)}")
        self.save_button.setEnabled(bool(temp_results))

    def on_fetch_failed(self, message: str) -> None:
        self.set_loading(False, message)
        QMessageBox.warning(self, "ChatList", message)

    def _make_response_editor(self, model_name: str, response: str) -> QTextEdit:
        editor = QTextEdit()
        editor.setReadOnly(True)
        editor.setFrameShape(QFrame.Shape.NoFrame)
        editor.setPlainText(f"【{model_name}】\n\n{response}")
        editor.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        editor.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        editor.setLineWrapMode(QTextEdit.LineWrapMode.WidgetWidth)
        return editor

    def _response_editor_height(self, editor: QTextEdit) -> int:
        column_width = self.results_table.columnWidth(1)
        if column_width < 80:
            column_width = (
                self.results_table.viewport().width()
                - self.results_table.columnWidth(0)
                - self.results_table.columnWidth(2)
                - 30
            )
        doc = editor.document()
        doc.setTextWidth(max(column_width - 16, 120))
        height = int(doc.size().height()) + 20
        return max(height, 80)

    def _update_response_heights(self, *_args) -> None:
        for row in range(self.results_table.rowCount()):
            editor = self.results_table.cellWidget(row, 1)
            if isinstance(editor, QTextEdit):
                self.results_table.setRowHeight(row, self._response_editor_height(editor))

    def populate_results_table(self) -> None:
        self.results_table.blockSignals(True)
        self.results_table.setRowCount(0)
        for index, item in enumerate(self.service.temp_results):
            self.results_table.insertRow(index)

            name_item = QTableWidgetItem(item.model_name)
            name_item.setFlags(name_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            name_item.setTextAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
            self.results_table.setItem(index, 0, name_item)

            response_editor = self._make_response_editor(item.model_name, item.response)
            self.results_table.setCellWidget(index, 1, response_editor)

            check_item = QTableWidgetItem()
            check_item.setFlags(
                Qt.ItemFlag.ItemIsUserCheckable | Qt.ItemFlag.ItemIsEnabled,
            )
            check_item.setCheckState(
                Qt.CheckState.Checked if item.selected else Qt.CheckState.Unchecked,
            )
            check_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.results_table.setItem(index, 2, check_item)

            self.results_table.setRowHeight(index, self._response_editor_height(response_editor))

        self.results_table.blockSignals(False)

    def on_result_item_changed(self, item: QTableWidgetItem) -> None:
        if item.column() != 2:
            return
        row = item.row()
        selected = item.checkState() == Qt.CheckState.Checked
        self.service.set_selected(row, selected)

    def on_save(self) -> None:
        for row in range(self.results_table.rowCount()):
            check_item = self.results_table.item(row, 2)
            if check_item is not None:
                selected = check_item.checkState() == Qt.CheckState.Checked
                self.service.set_selected(row, selected)

        try:
            saved_count = self.service.save_selected_results()
        except ValueError as exc:
            QMessageBox.warning(self, "ChatList", str(exc))
            return

        if saved_count == 0:
            QMessageBox.information(self, "ChatList", "Отметьте хотя бы один результат для сохранения.")
            return

        self.populate_results_table()
        self.save_button.setEnabled(False)
        self.status_label.setText(f"Сохранено результатов: {saved_count}")
        self.refresh_prompts()
        QMessageBox.information(self, "ChatList", f"Сохранено результатов: {saved_count}")


def main() -> None:
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
