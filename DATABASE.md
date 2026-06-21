# Схема базы данных ChatList

База данных: **SQLite**, файл `chatlist.db`.  
Доступ только через модуль `db.py`.

API-ключи **не хранятся** в БД — в таблице `models` указывается имя переменной окружения, значение берётся из файла `.env`.

---

## ER-диаграмма

```
┌─────────────┐       ┌─────────────┐
│   prompts   │       │   models    │
├─────────────┤       ├─────────────┤
│ id (PK)     │       │ id (PK)     │
│ created_at  │       │ name        │
│ text        │       │ api_url     │
│ tags        │       │ api_id      │
└──────┬──────┘       │ is_active   │
       │              │ model_type  │
       │              └──────┬──────┘
       │                     │
       └──────────┬──────────┘
                  │
           ┌──────▼──────┐
           │   results   │
           ├─────────────┤
           │ id (PK)     │
           │ prompt_id   │── FK → prompts.id
           │ model_id    │── FK → models.id
           │ response    │
           │ created_at  │
           └─────────────┘

┌─────────────┐
│  settings   │
├─────────────┤
│ key (PK)    │
│ value       │
└─────────────┘
```

---

## Таблица `prompts`

Хранение запросов пользователя.

| Поле         | Тип          | Ограничения              | Описание                          |
|--------------|--------------|--------------------------|-----------------------------------|
| `id`         | INTEGER      | PRIMARY KEY AUTOINCREMENT| Уникальный идентификатор          |
| `created_at` | TEXT         | NOT NULL                 | Дата и время создания (ISO 8601)  |
| `text`       | TEXT         | NOT NULL                 | Текст промта                      |
| `tags`       | TEXT         |                          | Теги через запятую, напр. `code,test` |

**Индексы:** `idx_prompts_created_at`, `idx_prompts_text` (для поиска).

```sql
CREATE TABLE prompts (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    created_at TEXT    NOT NULL DEFAULT (datetime('now')),
    text       TEXT    NOT NULL,
    tags       TEXT    DEFAULT ''
);
```

---

## Таблица `models`

Список нейросетей и параметры подключения.

| Поле         | Тип          | Ограничения              | Описание                                      |
|--------------|--------------|--------------------------|-----------------------------------------------|
| `id`         | INTEGER      | PRIMARY KEY AUTOINCREMENT| Уникальный идентификатор                      |
| `name`       | TEXT         | NOT NULL UNIQUE          | Отображаемое имя модели                       |
| `api_url`    | TEXT         | NOT NULL                 | URL endpoint API                              |
| `api_id`     | TEXT         | NOT NULL                 | Имя переменной в `.env`, напр. `OPENAI_API_KEY` |
| `is_active`  | INTEGER      | NOT NULL DEFAULT 1       | `1` — активна, `0` — отключена                |
| `model_type` | TEXT         | DEFAULT 'openai'         | Тип API: `openai`, `deepseek`, `groq` и т.д.  |

**Индексы:** `idx_models_is_active`.

```sql
CREATE TABLE models (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    name       TEXT    NOT NULL UNIQUE,
    api_url    TEXT    NOT NULL,
    api_id     TEXT    NOT NULL,
    is_active  INTEGER NOT NULL DEFAULT 1,
    model_type TEXT    DEFAULT 'openai'
);
```

**Пример `.env`:**

```env
OPENAI_API_KEY=sk-...
DEEPSEEK_API_KEY=sk-...
GROQ_API_KEY=gsk_...
```

**Пример записи в `models`:**

| name       | api_url                                      | api_id           | is_active |
|------------|----------------------------------------------|------------------|-----------|
| GPT-4o     | https://api.openai.com/v1/chat/completions   | OPENAI_API_KEY   | 1         |
| DeepSeek   | https://api.deepseek.com/v1/chat/completions | DEEPSEEK_API_KEY | 1         |

---

## Таблица `results`

Постоянное хранение отмеченных пользователем ответов.

| Поле         | Тип          | Ограничения              | Описание                          |
|--------------|--------------|--------------------------|-----------------------------------|
| `id`         | INTEGER      | PRIMARY KEY AUTOINCREMENT| Уникальный идентификатор          |
| `prompt_id`  | INTEGER      | NOT NULL, FK → prompts   | Связь с промтом                   |
| `model_id`   | INTEGER      | NOT NULL, FK → models    | Связь с моделью                   |
| `response`   | TEXT         | NOT NULL                 | Текст ответа нейросети            |
| `created_at` | TEXT         | NOT NULL                 | Дата и время сохранения (ISO 8601)|

**Индексы:** `idx_results_prompt_id`, `idx_results_model_id`, `idx_results_created_at`.

```sql
CREATE TABLE results (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    prompt_id  INTEGER NOT NULL REFERENCES prompts(id) ON DELETE CASCADE,
    model_id   INTEGER NOT NULL REFERENCES models(id)  ON DELETE RESTRICT,
    response   TEXT    NOT NULL,
    created_at TEXT    NOT NULL DEFAULT (datetime('now'))
);
```

---

## Таблица `settings`

Настройки программы в формате ключ–значение.

| Поле    | Тип  | Ограничения | Описание              |
|---------|------|-------------|-----------------------|
| `key`   | TEXT | PRIMARY KEY | Имя настройки         |
| `value` | TEXT | NOT NULL    | Значение настройки    |

```sql
CREATE TABLE settings (
    key   TEXT PRIMARY KEY,
    value TEXT NOT NULL
);
```

**Примеры настроек:**

| key              | value  | Описание                        |
|------------------|--------|---------------------------------|
| `request_timeout`| `30`   | Таймаут HTTP-запроса (секунды)  |
| `max_tokens`     | `2048` | Лимит токенов в ответе          |
| `db_path`        | `chatlist.db` | Путь к файлу БД          |

---

## Временная таблица результатов (не в SQLite)

При отправке промта программа формирует таблицу **в памяти** (Python-структура, не таблица БД):

| Поле          | Тип     | Описание                              |
|---------------|---------|---------------------------------------|
| `model_name`  | str     | Название модели                       |
| `model_id`    | int     | ID модели (для сохранения в `results`)|
| `response`    | str     | Текст ответа                          |
| `selected`    | bool    | Отмечен ли пользователем для сохранения|

Жизненный цикл:

1. Создаётся после отправки промта и получения ответов.
2. Очищается при нажатии «Сохранить» или при новом запросе.
3. Строки с `selected = True` переносятся в таблицу `results`.

---

## Инициализация БД

При первом запуске `db.py` выполняет:

1. Создание файла `chatlist.db`, если его нет.
2. Выполнение DDL для всех таблиц.
3. Заполнение `settings` значениями по умолчанию.
4. *(Опционально)* Добавление тестовых записей в `models`.
