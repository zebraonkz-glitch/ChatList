# ChatList

Python-приложение для отправки одного промта в несколько нейросетей и сравнения их ответов.

## Возможности

- Отправка промта во все **активные** модели параллельно
- Сравнение ответов в одном окне
- Сохранение выбранных результатов в SQLite
- Управление моделями (OpenAI, DeepSeek, Groq, [OpenRouter](https://openrouter.ai/))
- История промтов и результатов
- Экспорт в Markdown и JSON
- Просмотр ответа в форматированном Markdown
- Логирование запросов в `logs/chatlist.log`

## Требования

- Python 3.11+
- Windows / Linux / macOS

## Установка

```powershell
cd d:\work\ChatList
pip install -r requirements.txt
```

## Настройка `.env`

Скопируйте шаблон и укажите API-ключи:

```powershell
Copy-Item .env.example .env
```

Пример `.env`:

```env
OPENAI_API_KEY=sk-...
DEEPSEEK_API_KEY=sk-...
GROQ_API_KEY=gsk_...
OPENROUTER_API_KEY=sk-or-v1-...
```

Имена переменных должны совпадать с полем **«Переменная .env»** в настройках модели.

## Запуск

```powershell
python main.py
```

### Первый запуск

1. Откройте **Приложение → Модели...**
2. Включите нужные модели (**Вкл/Выкл**) или импортируйте из OpenRouter (**Из OpenRouter...**)
3. Введите промт и нажмите **Отправить**
4. Отметьте нужные ответы и нажмите **Сохранить**

## Сборка `.exe`

```powershell
.\build.ps1
```

Исполняемый файл: `dist\ChatList.exe`

## Тестирование

```powershell
python -m unittest discover -s tests -v
```

Проверяются сценарии:

- ввод промта → выбор ответов → сохранение в БД
- повторное использование сохранённого промта
- обработка отсутствующих ключей и HTTP-ошибок API
- экспорт Markdown / JSON

## Структура проекта

| Файл | Назначение |
|------|------------|
| `main.py` | Главное окно (GUI) |
| `db.py` | Работа с SQLite |
| `models.py` | Бизнес-логика |
| `network.py` | HTTP-запросы к API |
| `dialogs.py` | Диалоги: модели, настройки, история |
| `export_utils.py` | Экспорт MD / JSON |
| `app_log.py` | Логирование |
| `chatlist.db` | База данных (создаётся автоматически) |
| `logs/chatlist.log` | Журнал запросов |

## Документация

- [PROJECT.md](PROJECT.md) — спецификация
- [PLAN.md](PLAN.md) — план реализации
- [DATABASE.md](DATABASE.md) — схема БД
