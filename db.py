"""Модуль доступа к SQLite. Все SQL-запросы инкапсулированы здесь."""

from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Generator, Iterable

DEFAULT_DB_PATH = Path(__file__).parent / "chatlist.db"

DEFAULT_SETTINGS: dict[str, str] = {
    "request_timeout": "30",
    "max_tokens": "2048",
    "db_path": "chatlist.db",
    "assistant_model_id": "",
    "assistant_enabled": "1",
    "assistant_system_prompt": "",
    "theme": "light",
    "font_size": "10",
}

_SCHEMA = """
CREATE TABLE IF NOT EXISTS prompts (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    created_at TEXT    NOT NULL DEFAULT (datetime('now')),
    text       TEXT    NOT NULL,
    tags       TEXT    DEFAULT ''
);

CREATE TABLE IF NOT EXISTS models (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    name       TEXT    NOT NULL UNIQUE,
    api_url    TEXT    NOT NULL,
    api_id     TEXT    NOT NULL,
    is_active  INTEGER NOT NULL DEFAULT 1,
    model_type TEXT    DEFAULT 'openai'
);

CREATE TABLE IF NOT EXISTS results (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    prompt_id  INTEGER NOT NULL REFERENCES prompts(id) ON DELETE CASCADE,
    model_id   INTEGER NOT NULL REFERENCES models(id)  ON DELETE RESTRICT,
    response   TEXT    NOT NULL,
    created_at TEXT    NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS settings (
    key   TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_prompts_created_at ON prompts(created_at);
CREATE INDEX IF NOT EXISTS idx_prompts_text ON prompts(text);
CREATE INDEX IF NOT EXISTS idx_models_is_active ON models(is_active);
CREATE INDEX IF NOT EXISTS idx_results_prompt_id ON results(prompt_id);
CREATE INDEX IF NOT EXISTS idx_results_model_id ON results(model_id);
CREATE INDEX IF NOT EXISTS idx_results_created_at ON results(created_at);
"""


def _resolve_db_path(db_path: str | Path | None = None) -> Path:
    if db_path is None:
        return DEFAULT_DB_PATH
    path = Path(db_path)
    if not path.is_absolute():
        path = Path(__file__).parent / path
    return path


@contextmanager
def get_connection(db_path: str | Path | None = None) -> Generator[sqlite3.Connection, None, None]:
    path = _resolve_db_path(db_path)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db(db_path: str | Path | None = None) -> None:
    path = _resolve_db_path(db_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with get_connection(path) as conn:
        conn.executescript(_SCHEMA)
        for key, value in DEFAULT_SETTINGS.items():
            conn.execute(
                "INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)",
                (key, value),
            )
        _seed_models_if_empty(conn)
        _seed_assistant_model_default(conn)


def _seed_assistant_model_default(conn: sqlite3.Connection) -> None:
    row = conn.execute(
        "SELECT value FROM settings WHERE key = 'assistant_model_id'",
    ).fetchone()
    if row and str(row["value"]).strip():
        return
    model_row = conn.execute(
        """
        SELECT id FROM models
        WHERE model_type = 'openrouter'
        ORDER BY id
        LIMIT 1
        """,
    ).fetchone()
    if model_row is None:
        return
    conn.execute(
        """
        INSERT INTO settings (key, value) VALUES ('assistant_model_id', ?)
        ON CONFLICT(key) DO UPDATE SET value = excluded.value
        """,
        (str(model_row["id"]),),
    )


def _seed_models_if_empty(conn: sqlite3.Connection) -> None:
    count = conn.execute("SELECT COUNT(*) FROM models").fetchone()[0]
    if count > 0:
        return
    samples = [
        ("gpt-4o-mini", "https://api.openai.com/v1/chat/completions", "OPENAI_API_KEY", 0, "openai"),
        ("deepseek-chat", "https://api.deepseek.com/v1/chat/completions", "DEEPSEEK_API_KEY", 0, "deepseek"),
        ("llama-3.3-70b-versatile", "https://api.groq.com/openai/v1/chat/completions", "GROQ_API_KEY", 0, "groq"),
        ("openai/gpt-4o-mini", "https://openrouter.ai/api/v1/chat/completions", "OPENROUTER_API_KEY", 0, "openrouter"),
        ("anthropic/claude-sonnet-4", "https://openrouter.ai/api/v1/chat/completions", "OPENROUTER_API_KEY", 0, "openrouter"),
    ]
    conn.executemany(
        "INSERT INTO models (name, api_url, api_id, is_active, model_type) VALUES (?, ?, ?, ?, ?)",
        samples,
    )


def _row_to_dict(row: sqlite3.Row) -> dict[str, Any]:
    return dict(row)


# --- prompts ---


def create_prompt(text: str, tags: str = "", db_path: str | Path | None = None) -> int:
    with get_connection(db_path) as conn:
        cursor = conn.execute(
            "INSERT INTO prompts (text, tags) VALUES (?, ?)",
            (text.strip(), tags.strip()),
        )
        return int(cursor.lastrowid)


def get_prompts(
    search: str | None = None,
    db_path: str | Path | None = None,
) -> list[dict[str, Any]]:
    query = "SELECT * FROM prompts"
    params: list[Any] = []
    if search:
        query += " WHERE text LIKE ? OR tags LIKE ?"
        pattern = f"%{search.strip()}%"
        params.extend([pattern, pattern])
    query += " ORDER BY created_at DESC"
    with get_connection(db_path) as conn:
        rows = conn.execute(query, params).fetchall()
    return [_row_to_dict(row) for row in rows]


def get_prompt_by_id(prompt_id: int, db_path: str | Path | None = None) -> dict[str, Any] | None:
    with get_connection(db_path) as conn:
        row = conn.execute("SELECT * FROM prompts WHERE id = ?", (prompt_id,)).fetchone()
    return _row_to_dict(row) if row else None


def delete_prompt(prompt_id: int, db_path: str | Path | None = None) -> None:
    with get_connection(db_path) as conn:
        conn.execute("DELETE FROM prompts WHERE id = ?", (prompt_id,))


# --- models ---


def create_model(
    name: str,
    api_url: str,
    api_id: str,
    is_active: bool = True,
    model_type: str = "openai",
    db_path: str | Path | None = None,
) -> int:
    with get_connection(db_path) as conn:
        cursor = conn.execute(
            """
            INSERT INTO models (name, api_url, api_id, is_active, model_type)
            VALUES (?, ?, ?, ?, ?)
            """,
            (name.strip(), api_url.strip(), api_id.strip(), int(is_active), model_type.strip()),
        )
        return int(cursor.lastrowid)


def update_model(
    model_id: int,
    *,
    name: str | None = None,
    api_url: str | None = None,
    api_id: str | None = None,
    is_active: bool | None = None,
    model_type: str | None = None,
    db_path: str | Path | None = None,
) -> None:
    fields: list[str] = []
    params: list[Any] = []
    if name is not None:
        fields.append("name = ?")
        params.append(name.strip())
    if api_url is not None:
        fields.append("api_url = ?")
        params.append(api_url.strip())
    if api_id is not None:
        fields.append("api_id = ?")
        params.append(api_id.strip())
    if is_active is not None:
        fields.append("is_active = ?")
        params.append(int(is_active))
    if model_type is not None:
        fields.append("model_type = ?")
        params.append(model_type.strip())
    if not fields:
        return
    params.append(model_id)
    with get_connection(db_path) as conn:
        conn.execute(f"UPDATE models SET {', '.join(fields)} WHERE id = ?", params)


def get_model_by_id(model_id: int, db_path: str | Path | None = None) -> dict[str, Any] | None:
    with get_connection(db_path) as conn:
        row = conn.execute("SELECT * FROM models WHERE id = ?", (model_id,)).fetchone()
    return _row_to_dict(row) if row else None


def get_all_models(db_path: str | Path | None = None) -> list[dict[str, Any]]:
    with get_connection(db_path) as conn:
        rows = conn.execute("SELECT * FROM models ORDER BY name").fetchall()
    return [_row_to_dict(row) for row in rows]


def get_active_models(db_path: str | Path | None = None) -> list[dict[str, Any]]:
    with get_connection(db_path) as conn:
        rows = conn.execute(
            "SELECT * FROM models WHERE is_active = 1 ORDER BY name",
        ).fetchall()
    return [_row_to_dict(row) for row in rows]


def delete_model(model_id: int, db_path: str | Path | None = None) -> None:
    with get_connection(db_path) as conn:
        conn.execute("DELETE FROM models WHERE id = ?", (model_id,))


# --- results ---


def save_results(
    prompt_id: int,
    items: Iterable[tuple[int, str]],
    db_path: str | Path | None = None,
) -> int:
    rows = [(prompt_id, model_id, response.strip()) for model_id, response in items if response.strip()]
    if not rows:
        return 0
    with get_connection(db_path) as conn:
        conn.executemany(
            "INSERT INTO results (prompt_id, model_id, response) VALUES (?, ?, ?)",
            rows,
        )
    return len(rows)


def get_results(
    prompt_id: int | None = None,
    db_path: str | Path | None = None,
) -> list[dict[str, Any]]:
    query = "SELECT * FROM results"
    params: list[Any] = []
    if prompt_id is not None:
        query += " WHERE prompt_id = ?"
        params.append(prompt_id)
    query += " ORDER BY created_at DESC"
    with get_connection(db_path) as conn:
        rows = conn.execute(query, params).fetchall()
    return [_row_to_dict(row) for row in rows]


def get_results_detailed(
    prompt_id: int | None = None,
    search: str | None = None,
    db_path: str | Path | None = None,
) -> list[dict[str, Any]]:
    query = """
        SELECT
            r.id,
            r.prompt_id,
            r.model_id,
            r.response,
            r.created_at,
            p.text AS prompt_text,
            m.name AS model_name
        FROM results r
        JOIN prompts p ON p.id = r.prompt_id
        JOIN models m ON m.id = r.model_id
        WHERE 1 = 1
    """
    params: list[Any] = []
    if prompt_id is not None:
        query += " AND r.prompt_id = ?"
        params.append(prompt_id)
    if search:
        pattern = f"%{search.strip()}%"
        query += " AND (p.text LIKE ? OR m.name LIKE ? OR r.response LIKE ?)"
        params.extend([pattern, pattern, pattern])
    query += " ORDER BY r.created_at DESC"
    with get_connection(db_path) as conn:
        rows = conn.execute(query, params).fetchall()
    return [_row_to_dict(row) for row in rows]


# --- settings ---


def get_setting(key: str, default: str | None = None, db_path: str | Path | None = None) -> str | None:
    with get_connection(db_path) as conn:
        row = conn.execute("SELECT value FROM settings WHERE key = ?", (key,)).fetchone()
    if row is None:
        return default
    return str(row["value"])


def set_setting(key: str, value: str, db_path: str | Path | None = None) -> None:
    with get_connection(db_path) as conn:
        conn.execute(
            "INSERT INTO settings (key, value) VALUES (?, ?) ON CONFLICT(key) DO UPDATE SET value = excluded.value",
            (key, value),
        )


def get_all_settings(db_path: str | Path | None = None) -> dict[str, str]:
    with get_connection(db_path) as conn:
        rows = conn.execute("SELECT key, value FROM settings").fetchall()
    return {str(row["key"]): str(row["value"]) for row in rows}
