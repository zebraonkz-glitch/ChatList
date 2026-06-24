# Публикация ChatList на GitHub Release и GitHub Pages

Пошаговая инструкция для первого и последующих релизов.

---

## 0. Подготовка репозитория (один раз)

### 0.1. Создайте репозиторий на GitHub

```powershell
cd d:\work\ChatList
git remote add origin https://github.com/YOUR_USERNAME/ChatList.git
git push -u origin main
```

### 0.2. Укажите свой репозиторий в шаблонах

Замените `YOUR_USERNAME` на ваш логин GitHub в файлах:

| Файл | Что менять |
|------|------------|
| `docs/site.json` | поле `"repo"` |
| `docs/release-notes/TEMPLATE.md` | ссылки на GitHub |
| `installer/ChatList.iss` | `MyAppURL` (опционально) |

Пример `docs/site.json`:

```json
{
  "appName": "ChatList",
  "repo": "nztdesign/ChatList"
}
```

### 0.3. Включите GitHub Pages (обязательно до первого деплоя)

Без этого шага workflow **Deploy GitHub Pages** падает с ошибкой:

```text
Get Pages site failed ... Not Found
```

**Что сделать:**

1. Откройте репозиторий на GitHub.
2. **Settings** → **Pages** (в левом меню).
3. В блоке **Build and deployment** → **Source** выберите **GitHub Actions**.
   - Не выбирайте «Deploy from a branch» — для нашего workflow нужен именно **GitHub Actions**.
4. Если раздел Pages пустой — после выбора источника GitHub создаст сайт автоматически.
5. Запустите деплой вручную: **Actions** → **Deploy GitHub Pages** → **Run workflow**.

Сайт будет доступен по адресу:

```text
https://YOUR_USERNAME.github.io/ChatList/
```

> **Примечание:** автоматическое включение через `enablement: true` в workflow требует Personal Access Token с правами `repo` / Pages — проще один раз включить Pages в настройках вручную.

---

## 1. Версия приложения

Единственный источник номера версии — `version.py`:

```python
__version__ = "1.0.0"
```

Перед релизом обновите только этот файл. Все остальные места (exe, инсталлятор, UI, логи) подхватят версию автоматически.

---

## 2. Локальная подготовка релиза

### 2.1. Запустите скрипт проверки и сборки

```powershell
cd d:\work\ChatList
.\scripts\prepare_release.ps1
```

Скрипт:

- читает версию из `version.py`;
- запускает тесты;
- собирает `dist\ChatList-X.Y.Z.exe` и `dist\ChatList-X.Y.Z-setup.exe`;
- создаёт `dist\SHA256SUMS.txt`.

### 2.2. Подготовьте заметки к релизу

```powershell
Copy-Item docs\release-notes\TEMPLATE.md docs\release-notes\v1.0.0.md
```

Отредактируйте `docs\release-notes\v1.0.0.md`: замените `X.Y.Z`, опишите изменения.

### 2.3. Закоммитьте изменения

```powershell
git add version.py docs/release-notes/v1.0.0.md
git commit -m "Релиз 1.0.0"
git push origin main
```

---

## 3. Публикация GitHub Release

### Вариант A — автоматически (рекомендуется)

1. Создайте аннотированный тег (должен совпадать с `version.py`):

```powershell
git tag -a v1.0.0 -m "ChatList 1.0.0"
git push origin v1.0.0
```

2. Workflow `.github/workflows/release.yml` на Windows:
   - соберёт exe и инсталлятор;
   - создаст Release с тегом `v1.0.0`;
   - прикрепит файлы из `dist\` и `SHA256SUMS.txt`;
   - подставит текст из `docs/release-notes/v1.0.0.md`, если файл существует.

### Вариант B — вручную через веб-интерфейс

1. GitHub → **Releases** → **Draft a new release**
2. **Choose a tag**: `v1.0.0` → **Create new tag**
3. **Release title**: `ChatList 1.0.0`
4. **Description**: вставьте содержимое `docs/release-notes/v1.0.0.md`
5. **Attach binaries** — перетащите из `dist\`:
   - `ChatList-1.0.0-setup.exe` (основной файл для пользователей)
   - `ChatList-1.0.0.exe` (портативная версия)
   - `SHA256SUMS.txt`
6. Нажмите **Publish release**

### Имена файлов в Release

| Файл | Назначение |
|------|------------|
| `ChatList-1.0.0-setup.exe` | Инсталлятор Inno Setup |
| `ChatList-1.0.0.exe` | Портативная сборка |
| `SHA256SUMS.txt` | SHA256 для проверки целостности |

Лендинг на GitHub Pages автоматически найдёт последний релиз и ссылку на `-setup.exe`.

---

## 4. Публикация GitHub Pages (лендинг)

### 4.1. Что уже подготовлено

```text
docs/
  index.html          # лендинг
  site.json           # настройки (repo, слоган)
  assets/favicon.svg  # иконка
  .nojekyll           # отключение Jekyll
```

### 4.2. Деплой

При push в ветку `main` с изменениями в `docs/**` workflow `pages.yml` публикует сайт.

Ручной запуск:

1. GitHub → **Actions** → **Deploy GitHub Pages** → **Run workflow**

### 4.3. Проверка

Откройте `https://YOUR_USERNAME.github.io/ChatList/`:

- кнопка «Скачать» ведёт на последний `-setup.exe`;
- версия подтягивается из GitHub Releases API;
- ссылки на репозиторий и README.

---

## 5. Чеклист перед каждым релизом

- [ ] Обновлён `version.py`
- [ ] Пройдены тесты: `python -m unittest discover -s tests -v`
- [ ] Собраны артефакты: `.\scripts\prepare_release.ps1`
- [ ] Заполнен `docs/release-notes/vX.Y.Z.md`
- [ ] В `docs/site.json` указан правильный `repo`
- [ ] Создан тег `vX.Y.Z` и запушен на GitHub
- [ ] Release содержит setup.exe, portable exe и SHA256SUMS.txt
- [ ] GitHub Pages открывается и кнопка скачивания работает

---

## 6. Проверка контрольной суммы (для пользователей)

```powershell
Get-FileHash .\ChatList-1.0.0-setup.exe -Algorithm SHA256
```

Сравните с записью в `SHA256SUMS.txt` на странице Release.

---

## 7. Частые проблемы

| Проблема | Решение |
|----------|---------|
| Pages не обновляется / `Get Pages site failed` / `Not Found` | **Settings → Pages → Source: GitHub Actions** (см. раздел 0.3). Затем **Actions → Deploy GitHub Pages → Run workflow** |
| Кнопка «Скачать» не находит exe | Убедитесь, что в Release есть файл `*-setup.exe` |
| Workflow release падает | Нужен тег формата `v1.0.0`; версия в теге = `version.py` |
| CORS / API на лендинге | GitHub API для публичных репозиториев работает без токена; для приватных — настройте публичный Release или укажите ссылку вручную в `site.json` |

---

## 8. Полезные команды

```powershell
# Только exe без инсталлятора
.\build.ps1 -SkipInstaller

# Только инсталлятор (exe уже собран)
.\build_installer.ps1 -SkipBuild

# Удалить тег локально и на GitHub (если ошиблись)
git tag -d v1.0.0
git push origin :refs/tags/v1.0.0
```
