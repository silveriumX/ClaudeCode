# Диагностика MCP серверов (12.02.2026)

## Почему все MCP серверы недоступны

По логам Cursor (`%AppData%\Cursor\logs\...\exthost\anysphere.cursor-mcp\`) выявлены **три основные причины**.

---

## 1. Node.js не в PATH при запуске Cursor

**Ошибка в логах:** `"npx" не является внутренней или внешней командой` → `Client error for command spawn npx ENOENT`

**Затронутые серверы:** fireflies, zoom, exa, google-drive (все, что запускаются через `npx`).

**Причина:** Cursor при старте наследует PATH. Если Node.js установлен, но:
- Cursor запущен не из того терминала, где есть Node в PATH, или
- Node добавлен в PATH пользователя/системы после последнего перезапуска ПК, или
- Cursor запущен с ярлыка/панели без доступа к полному PATH,

то `npx` не находится.

**Что сделать:**
1. Убедиться, что Node.js установлен: в **новом** PowerShell выполнить `node -v` и `npx -v`. Если команды не найдены — установить [Node.js LTS](https://nodejs.org/) (рекомендуется v20+).
2. Добавить путь к Node в **системный** PATH (Параметры → Система → О программе → Дополнительные параметры системы → Переменные среды). Обычно это `C:\Program Files\nodejs\`.
3. **Полностью закрыть Cursor и запустить снова** (чтобы подхватить обновлённый PATH).
4. При запуске Cursor из терминала: сначала в этом же терминале проверить `npx -v`, затем из него запустить Cursor (`cursor .` или через `code`/путь к Cursor), чтобы PATH был тем же.

---

## 2. uvx не найден (Excel MCP)

**Ошибка в логах:** `"uvx" не является внутренней или внешней командой` → `Client error for command spawn uvx ENOENT`

**Затронутый сервер:** excel (`uvx excel-mcp-server stdio`).

**Причина:** [uv](https://github.com/astral-sh/uv) не установлен или не в PATH.

**Варианты решения:**

**Вариант A — установить uv** (если нужен именно uvx):
- Установка: <https://github.com/astral-sh/uv#installation>
- После установки перезапустить Cursor.

**Вариант B — перейти на Python** (как в документации проекта):
- Установить пакет: `pip install excel-mcp-server`
- В `.cursor/mcp.json` заменить блок `excel` на:
```json
"excel": {
  "command": "python",
  "args": ["-m", "excel_mcp_server", "stdio"]
}
```
- Убедиться, что в PATH при запуске Cursor доступен тот же `python`, для которого установлен пакет.

---

## 3. document-processor — нет модуля anthropic

**Ошибка в логах:** `ModuleNotFoundError: No module named 'anthropic'`

**Причина:** Скрипт `Scripts\mcp-document-processor\server.py` запускается тем Python, который видит Cursor, но в этом окружении не установлены зависимости из `requirements.txt`.

**Что сделать:**
1. Открыть терминал и перейти в папку:
   `cd "c:\Users\Admin\Documents\workspaces for ai\Cursor\Scripts\mcp-document-processor"`
2. Создать виртуальное окружение (рекомендуется):
   `python -m venv .venv`
   затем активировать:
   `.venv\Scripts\activate`
3. Установить зависимости:
   `pip install -r requirements.txt`
4. В `mcp.json` для document-processor указать полный путь к этому Python:
   - Либо заменить `"command": "python"` на полный путь к `Scripts\mcp-document-processor\.venv\Scripts\python.exe`,
   - Либо убедиться, что в системном PATH при запуске Cursor первым идёт именно этот Python (после активации venv), если Cursor запускается из того же терминала.

Пример с явным путём к venv (в mcp.json):
```json
"document-processor": {
  "command": "${workspaceFolder}/Scripts/mcp-document-processor/.venv/Scripts/python.exe",
  "args": ["${workspaceFolder}/Scripts/mcp-document-processor/server.py"],
  "env": { "ANTHROPIC_API_KEY": "..." }
}
```
(На Windows в JSON можно использовать прямые слэши `/` или двойные обратные `\\\\`.)

---

## 4. URL-серверы (excalidraw, clickup)

**excalidraw в логах:**
- `Client error for command fetch failed` (streamableHttp),
- затем fallback на SSE: `SSE error: Non-200 status code (405)`.

**Возможные причины:** сеть (файрвол/прокси), блокировка хоста или несовместимость протокола/эндпоинта. Для ClickUp часто требуется OAuth в браузере при первом подключении.

**Что сделать:**
- Проверить доступность в браузере:
  https://excalidraw-mcp-app.vercel.app/mcp
  https://mcp.clickup.com/mcp
- Для ClickUp: в настройках MCP в Cursor при первом использовании пройти OAuth.
- При работе через корпоративный прокси/VPN — настроить их или временно проверить без них.

---

## Краткий чеклист

| Сервер            | Проблема              | Действие                                      |
|-------------------|------------------------|-----------------------------------------------|
| fireflies         | npx ENOENT             | Установить Node.js, добавить в PATH, перезапуск Cursor |
| zoom              | npx ENOENT             | То же                                         |
| exa               | npx ENOENT             | То же                                         |
| google-drive      | npx ENOENT             | То же                                         |
| excel             | uvx ENOENT             | Установить uv ИЛИ перейти на `python -m excel_mcp_server` |
| document-processor | No module 'anthropic'  | venv + `pip install -r requirements.txt`, правильный Python в mcp.json |
| excalidraw        | fetch failed, SSE 405  | Сеть, прокси, доступность URL                  |
| clickup           | (проверить по логам)   | Сеть, OAuth при первом подключении            |

---

## Где смотреть логи

- Папка: `%AppData%\Cursor\logs\<дата_время>\window1\exthost\anysphere.cursor-mcp\`
- Файлы: `MCP project-0-Cursor-<имя_сервера>.log`

После изменений (PATH, uv, pip, mcp.json) **обязательно полностью перезапустить Cursor**.
