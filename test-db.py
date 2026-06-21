"""Тестовая программа для просмотра и редактирования SQLite-базы."""

from __future__ import annotations

import sqlite3
import sys
from pathlib import Path

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QApplication,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QListWidget,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

PAGE_SIZE = 50


def quote_ident(name: str) -> str:
    return '"' + name.replace('"', '""') + '"'


class RowEditDialog(QDialog):
    def __init__(
        self,
        columns: list[dict],
        values: dict[str, str | None] | None = None,
        *,
        title: str = "Запись",
        read_only_pk: bool = False,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.columns = columns
        self.setWindowTitle(title)
        self.setMinimumWidth(420)

        layout = QFormLayout(self)
        self.fields: dict[str, QLineEdit] = {}

        for column in columns:
            name = column["name"]
            field = QLineEdit()
            hint = column["type"] or "TEXT"
            if column["pk"]:
                hint += ", PK"
            field.setPlaceholderText(hint)
            if values and values.get(name) is not None:
                field.setText(str(values[name]))
            if read_only_pk and column["pk"]:
                field.setReadOnly(True)
            self.fields[name] = field
            layout.addRow(f"{name}:", field)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel,
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addRow(buttons)

    def get_values(self) -> dict[str, str]:
        return {name: field.text() for name, field in self.fields.items()}


class TableViewWidget(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.conn: sqlite3.Connection | None = None
        self.table_name = ""
        self.columns: list[dict] = []
        self.current_page = 0
        self.total_rows = 0
        self.rowid_column = "rowid"

        layout = QVBoxLayout(self)

        self.title_label = QLabel("Таблица не выбрана")
        self.title_label.setStyleSheet("font-weight: bold; font-size: 12pt;")
        layout.addWidget(self.title_label)

        self.table = QTableWidget(0, 0)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.setAlternatingRowColors(True)
        layout.addWidget(self.table)

        pagination = QHBoxLayout()
        self.prev_btn = QPushButton("← Назад")
        self.prev_btn.clicked.connect(self.prev_page)
        pagination.addWidget(self.prev_btn)

        self.page_label = QLabel("Страница 0 из 0")
        pagination.addWidget(self.page_label)

        self.next_btn = QPushButton("Вперёд →")
        self.next_btn.clicked.connect(self.next_page)
        pagination.addWidget(self.next_btn)

        pagination.addStretch()

        self.page_size_label = QLabel(f"По {PAGE_SIZE} строк")
        pagination.addWidget(self.page_size_label)
        layout.addLayout(pagination)

        crud = QHBoxLayout()
        self.add_btn = QPushButton("Добавить")
        self.add_btn.clicked.connect(self.add_row)
        crud.addWidget(self.add_btn)

        self.edit_btn = QPushButton("Изменить")
        self.edit_btn.clicked.connect(self.edit_row)
        crud.addWidget(self.edit_btn)

        self.delete_btn = QPushButton("Удалить")
        self.delete_btn.clicked.connect(self.delete_row)
        crud.addWidget(self.delete_btn)

        self.refresh_btn = QPushButton("Обновить")
        self.refresh_btn.clicked.connect(self.reload_page)
        crud.addWidget(self.refresh_btn)

        crud.addStretch()
        layout.addLayout(crud)

        self.set_enabled(False)

    def set_enabled(self, enabled: bool) -> None:
        for widget in (
            self.table,
            self.prev_btn,
            self.next_btn,
            self.add_btn,
            self.edit_btn,
            self.delete_btn,
            self.refresh_btn,
        ):
            widget.setEnabled(enabled)

    def open_table(self, conn: sqlite3.Connection, table_name: str) -> None:
        self.conn = conn
        self.table_name = table_name
        self.current_page = 0
        self.columns = self._load_columns()
        self.title_label.setText(f"Таблица: {table_name}")
        self.set_enabled(True)
        self.reload_page()

    def close_table(self) -> None:
        self.conn = None
        self.table_name = ""
        self.columns = []
        self.table.setRowCount(0)
        self.table.setColumnCount(0)
        self.title_label.setText("Таблица не выбрана")
        self.page_label.setText("Страница 0 из 0")
        self.set_enabled(False)

    def _load_columns(self) -> list[dict]:
        assert self.conn and self.table_name
        rows = self.conn.execute(f"PRAGMA table_info({quote_ident(self.table_name)})").fetchall()
        return [
            {
                "cid": row[0],
                "name": row[1],
                "type": row[2] or "",
                "notnull": bool(row[3]),
                "pk": bool(row[5]),
            }
            for row in rows
        ]

    def _total_pages(self) -> int:
        if self.total_rows == 0:
            return 0
        return (self.total_rows - 1) // PAGE_SIZE + 1

    def reload_page(self) -> None:
        if not self.conn or not self.table_name:
            return

        quoted = quote_ident(self.table_name)
        self.total_rows = self.conn.execute(f"SELECT COUNT(*) FROM {quoted}").fetchone()[0]
        total_pages = self._total_pages()
        if total_pages == 0:
            self.current_page = 0
        elif self.current_page >= total_pages:
            self.current_page = max(total_pages - 1, 0)

        offset = self.current_page * PAGE_SIZE
        col_names = [column["name"] for column in self.columns]
        query = (
            f"SELECT {self.rowid_column}, * FROM {quoted} "
            f"LIMIT ? OFFSET ?"
        )
        rows = self.conn.execute(query, (PAGE_SIZE, offset)).fetchall()

        self.table.setColumnCount(len(col_names) + 1)
        headers = ["rowid"] + col_names
        self.table.setHorizontalHeaderLabels(headers)
        self.table.setRowCount(len(rows))

        for row_index, row in enumerate(rows):
            for col_index, value in enumerate(row):
                item = QTableWidgetItem("" if value is None else str(value))
                item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                if col_index == 0:
                    item.setData(Qt.ItemDataRole.UserRole, int(value))
                self.table.setItem(row_index, col_index, item)

        page_num = self.current_page + 1 if total_pages else 0
        self.page_label.setText(
            f"Страница {page_num} из {total_pages} | всего строк: {self.total_rows}",
        )
        self.prev_btn.setEnabled(self.current_page > 0)
        self.next_btn.setEnabled(total_pages > 0 and self.current_page < total_pages - 1)

    def prev_page(self) -> None:
        if self.current_page > 0:
            self.current_page -= 1
            self.reload_page()

    def next_page(self) -> None:
        if self.current_page < self._total_pages() - 1:
            self.current_page += 1
            self.reload_page()

    def _selected_rowid(self) -> int | None:
        rows = self.table.selectionModel().selectedRows()
        if not rows:
            return None
        item = self.table.item(rows[0].row(), 0)
        return int(item.data(Qt.ItemDataRole.UserRole)) if item else None

    def _selected_values(self) -> dict[str, str | None]:
        rows = self.table.selectionModel().selectedRows()
        if not rows:
            return {}
        row = rows[0].row()
        values: dict[str, str | None] = {}
        for index, column in enumerate(self.columns, start=1):
            item = self.table.item(row, index)
            values[column["name"]] = item.text() if item else ""
        return values

    def add_row(self) -> None:
        assert self.conn and self.table_name
        dialog = RowEditDialog(self.columns, title="Добавить запись", parent=self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return

        values = dialog.get_values()
        col_names = [column["name"] for column in self.columns]
        placeholders = ", ".join("?" for _ in col_names)
        columns_sql = ", ".join(quote_ident(name) for name in col_names)
        data = [values.get(name, "") for name in col_names]

        try:
            self.conn.execute(
                f"INSERT INTO {quote_ident(self.table_name)} ({columns_sql}) VALUES ({placeholders})",
                data,
            )
            self.conn.commit()
        except sqlite3.Error as exc:
            QMessageBox.warning(self, "test-db", f"Ошибка добавления:\n{exc}")
            return

        self.reload_page()

    def edit_row(self) -> None:
        assert self.conn and self.table_name
        rowid = self._selected_rowid()
        if rowid is None:
            QMessageBox.information(self, "test-db", "Выберите строку для изменения.")
            return

        current = self._selected_values()
        dialog = RowEditDialog(
            self.columns,
            current,
            title="Изменить запись",
            read_only_pk=True,
            parent=self,
        )
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return

        values = dialog.get_values()
        assignments = ", ".join(
            f"{quote_ident(column['name'])} = ?" for column in self.columns if not column["pk"]
        )
        pk_columns = [column for column in self.columns if column["pk"]]
        if not assignments:
            QMessageBox.information(self, "test-db", "Нет полей для обновления.")
            return

        params = [values[column["name"]] for column in self.columns if not column["pk"]]
        if pk_columns:
            where_sql = " AND ".join(f"{quote_ident(column['name'])} = ?" for column in pk_columns)
            params.extend(values[column["name"]] for column in pk_columns)
        else:
            where_sql = f"{self.rowid_column} = ?"
            params.append(rowid)

        try:
            self.conn.execute(
                f"UPDATE {quote_ident(self.table_name)} SET {assignments} WHERE {where_sql}",
                params,
            )
            self.conn.commit()
        except sqlite3.Error as exc:
            QMessageBox.warning(self, "test-db", f"Ошибка изменения:\n{exc}")
            return

        self.reload_page()

    def delete_row(self) -> None:
        assert self.conn and self.table_name
        rowid = self._selected_rowid()
        if rowid is None:
            QMessageBox.information(self, "test-db", "Выберите строку для удаления.")
            return

        answer = QMessageBox.question(
            self,
            "test-db",
            "Удалить выбранную строку?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if answer != QMessageBox.StandardButton.Yes:
            return

        try:
            self.conn.execute(
                f"DELETE FROM {quote_ident(self.table_name)} WHERE {self.rowid_column} = ?",
                (rowid,),
            )
            self.conn.commit()
        except sqlite3.Error as exc:
            QMessageBox.warning(self, "test-db", f"Ошибка удаления:\n{exc}")
            return

        self.reload_page()


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("test-db — просмотр SQLite")
        self.setMinimumSize(1000, 640)

        self.conn: sqlite3.Connection | None = None
        self.db_path: Path | None = None

        root = QWidget()
        self.setCentralWidget(root)
        layout = QHBoxLayout(root)

        left = QGroupBox("База данных")
        left_layout = QVBoxLayout(left)

        file_row = QHBoxLayout()
        self.path_edit = QLineEdit()
        self.path_edit.setPlaceholderText("Путь к файлу .db...")
        file_row.addWidget(self.path_edit)

        browse_btn = QPushButton("Обзор...")
        browse_btn.clicked.connect(self.browse_db)
        file_row.addWidget(browse_btn)
        left_layout.addLayout(file_row)

        load_btn = QPushButton("Загрузить")
        load_btn.clicked.connect(self.load_database)
        left_layout.addWidget(load_btn)

        left_layout.addWidget(QLabel("Таблицы:"))
        self.tables_list = QListWidget()
        self.tables_list.itemDoubleClicked.connect(self.open_selected_table)
        left_layout.addWidget(self.tables_list)

        self.open_btn = QPushButton("Открыть")
        self.open_btn.clicked.connect(self.open_selected_table)
        self.open_btn.setEnabled(False)
        left_layout.addWidget(self.open_btn)

        layout.addWidget(left, 1)

        self.table_view = TableViewWidget()
        layout.addWidget(self.table_view, 3)

        default_db = Path(__file__).parent / "chatlist.db"
        if default_db.exists():
            self.path_edit.setText(str(default_db))

    def browse_db(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Выберите SQLite базу",
            str(Path(__file__).parent),
            "SQLite (*.db *.sqlite *.sqlite3);;Все файлы (*.*)",
        )
        if path:
            self.path_edit.setText(path)

    def load_database(self) -> None:
        path_text = self.path_edit.text().strip()
        if not path_text:
            QMessageBox.warning(self, "test-db", "Укажите путь к файлу базы данных.")
            return

        path = Path(path_text)
        if not path.exists():
            QMessageBox.warning(self, "test-db", "Файл не найден.")
            return

        self.close_connection()
        try:
            self.conn = sqlite3.connect(path)
            self.conn.row_factory = sqlite3.Row
            self.db_path = path
        except sqlite3.Error as exc:
            QMessageBox.warning(self, "test-db", f"Не удалось открыть базу:\n{exc}")
            return

        tables = self.conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name",
        ).fetchall()

        self.tables_list.clear()
        for row in tables:
            self.tables_list.addItem(str(row[0]))

        self.open_btn.setEnabled(bool(tables))
        self.table_view.close_table()
        self.setWindowTitle(f"test-db — {path.name}")

    def open_selected_table(self) -> None:
        if not self.conn:
            QMessageBox.warning(self, "test-db", "Сначала загрузите базу данных.")
            return
        item = self.tables_list.currentItem()
        if item is None:
            QMessageBox.information(self, "test-db", "Выберите таблицу из списка.")
            return
        self.table_view.open_table(self.conn, item.text())

    def close_connection(self) -> None:
        if self.conn is not None:
            self.conn.close()
            self.conn = None
        self.db_path = None

    def closeEvent(self, event) -> None:
        self.close_connection()
        super().closeEvent(event)


def main() -> None:
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
