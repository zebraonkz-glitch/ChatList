import sys

from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QScrollArea,
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


RESULT_ROW_HEIGHT = 150


class ResultRowWidget(QFrame):
    def __init__(
        self,
        index: int,
        model_name: str,
        response: str,
        selected: bool,
        on_toggle,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.index = index
        self.setFrameShape(QFrame.Shape.StyledPanel)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)

        model_box = QVBoxLayout()
        model_box.addWidget(QLabel("Модель"))
        model_label = QLabel(model_name)
        model_label.setWordWrap(True)
        model_label.setMinimumWidth(180)
        model_label.setMaximumWidth(220)
        model_label.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        model_box.addWidget(model_label)
        model_box.addStretch()
        layout.addLayout(model_box)

        response_box = QVBoxLayout()
        response_box.addWidget(QLabel("Ответ"))
        editor = QTextEdit()
        editor.setReadOnly(True)
        editor.setPlainText(response)
        editor.setFixedHeight(RESULT_ROW_HEIGHT)
        editor.setLineWrapMode(QTextEdit.LineWrapMode.WidgetWidth)
        response_box.addWidget(editor)
        layout.addLayout(response_box, 1)

        select_box = QVBoxLayout()
        select_box.addWidget(QLabel("Выбрать"))
        self.checkbox = QCheckBox()
        self.checkbox.setChecked(selected)
        self.checkbox.toggled.connect(lambda checked: on_toggle(index, checked))
        select_box.addWidget(self.checkbox, alignment=Qt.AlignmentFlag.AlignHCenter)
        select_box.addStretch()
        select_box.setContentsMargins(8, 0, 8, 0)
        layout.addLayout(select_box)


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

        self.results_scroll = QScrollArea()
        self.results_scroll.setWidgetResizable(True)
        self.results_scroll.setFrameShape(QFrame.Shape.StyledPanel)
        self.results_container = QWidget()
        self.results_layout = QVBoxLayout(self.results_container)
        self.results_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.results_layout.setSpacing(8)
        self.results_scroll.setWidget(self.results_container)
        layout.addWidget(self.results_scroll, 1)

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
        self.populate_results()
        self.set_loading(True, "Отправка запросов...")

        self.worker = FetchWorker(self.service, prompt_text, self)
        self.worker.finished.connect(self.on_fetch_finished)
        self.worker.failed.connect(self.on_fetch_failed)
        self.worker.start()

    def on_fetch_finished(self, results: list) -> None:
        temp_results = [TempResult(**item) for item in results]
        self.service.set_temp_results(temp_results)
        self.populate_results()
        self.set_loading(False, f"Получено ответов: {len(temp_results)}")
        self.save_button.setEnabled(bool(temp_results))

    def on_fetch_failed(self, message: str) -> None:
        self.set_loading(False, message)
        QMessageBox.warning(self, "ChatList", message)

    def on_result_toggled(self, index: int, selected: bool) -> None:
        self.service.set_selected(index, selected)

    def _clear_results_layout(self) -> None:
        while self.results_layout.count():
            item = self.results_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()

    def populate_results(self) -> None:
        self._clear_results_layout()
        if not self.service.temp_results:
            placeholder = QLabel("Нет результатов")
            placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.results_layout.addWidget(placeholder)
            return

        for index, item in enumerate(self.service.temp_results):
            row = ResultRowWidget(
                index,
                item.model_name,
                item.response,
                item.selected,
                self.on_result_toggled,
                self.results_container,
            )
            self.results_layout.addWidget(row)

    def on_save(self) -> None:
        try:
            saved_count = self.service.save_selected_results()
        except ValueError as exc:
            QMessageBox.warning(self, "ChatList", str(exc))
            return

        if saved_count == 0:
            QMessageBox.information(self, "ChatList", "Отметьте хотя бы один результат для сохранения.")
            return

        self.populate_results()
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
