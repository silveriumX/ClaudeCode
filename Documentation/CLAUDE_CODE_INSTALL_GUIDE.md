# Claude Code — Полная инструкция установки на Windows 10

> Пошаговая инструкция для переноса на новый ПК.
> Предусловия: **Windows 10**, **Git** и **VS Code** уже установлены.

---

## Оглавление

1. [Node.js](#1-nodejs)
2. [Python](#2-python)
3. [Claude Code CLI](#3-claude-code-cli)
4. [VS Code Extension](#4-vs-code-extension)
5. [Настройка VS Code Terminal (Git Bash)](#5-настройка-vs-code-terminal-git-bash)
6. [Авторизация Claude Code](#6-авторизация-claude-code)
7. [Глобальные настройки Claude](#7-глобальные-настройки-claude)
8. [Настройка проекта](#8-настройка-проекта)
9. [MCP-серверы](#9-mcp-серверы)
10. [Keybindings (Shift+Enter для многострочного ввода)](#10-keybindings)
11. [Полезные расширения VS Code](#11-полезные-расширения-vs-code)
12. [Проверка установки](#12-проверка-установки)
13. [Troubleshooting](#13-troubleshooting)

---

## 1. Node.js

Claude Code использует `npx` для запуска некоторых MCP-серверов. Node.js обязателен.

### Установка

1. Скачать **LTS** (или Current) с https://nodejs.org/
   - Текущая версия в рабочей среде: **v24.13.1** (npm 11.8.0)
2. Установить с дефолтными настройками
3. Убедиться что в PATH (обычно автоматически)

### Проверка

```bash
node --version   # v24.x.x
npm --version    # 11.x.x
```

---

## 2. Python

Нужен для скриптов проекта, ботов, автоматизации.

### Установка

1. Скачать **Python 3.12+** с https://www.python.org/downloads/
2. **ВАЖНО:** при установке поставить галку **"Add Python to PATH"**
3. Установить

### Проверка

```bash
python --version   # Python 3.12.x
pip --version      # pip 25.x.x
```

---

## 3. Claude Code CLI

### Вариант A: Автоматическая установка (рекомендуется)

Открыть **Git Bash** (или терминал VS Code с Git Bash) и выполнить:

```bash
# Установка через npm (глобально)
npm install -g @anthropic-ai/claude-code
```

### Вариант B: Standalone binary

Claude Code также ставится как standalone `.exe`:

1. Файл: `claude.exe` (~233 MB)
2. Расположение: `C:\Users\<USER>\.local\bin\claude.exe`
3. Добавить `C:\Users\<USER>\.local\bin` в системный PATH

### Добавление в PATH (если нужно)

1. Win+R → `sysdm.cpl` → вкладка "Дополнительно" → "Переменные среды"
2. В "Переменные среды пользователя" → `Path` → Изменить → Добавить:
   ```
   C:\Users\<USER>\.local\bin
   ```
3. Перезапустить терминал

### Проверка

```bash
claude --version   # Claude Code v2.x.x
```

---

## 4. VS Code Extension

### Установка расширения

1. Открыть VS Code
2. `Ctrl+Shift+X` → поиск: **"Claude Code"**
3. Установить расширение от **Anthropic** (`anthropic.claude-code`)
4. Перезагрузить VS Code

### Альтернатива через командную строку

```bash
code --install-extension anthropic.claude-code
```

---

## 5. Настройка VS Code Terminal (Git Bash)

**Критически важно:** Claude Code на Windows работает через **Git Bash**, не через PowerShell/CMD.

### 5.1. Настройка дефолтного терминала

Открыть `settings.json` в VS Code (`Ctrl+Shift+P` → "Preferences: Open User Settings (JSON)") и добавить:

```json
{
    "terminal.integrated.profiles.windows": {
        "Git Bash": {
            "source": "Git Bash"
        }
    },
    "terminal.integrated.defaultProfile.windows": "Git Bash",
    "terminal.integrated.enableMultiLinePasteWarning": "never"
}
```

### 5.2. Указать путь к Git Bash для Claude Code

В том же `settings.json` добавить:

```json
{
    "claudeCode.environmentVariables": [
        {
            "name": "CLAUDE_CODE_GIT_BASH_PATH",
            "value": "C:\\Program Files\\Git\\bin\\bash.exe"
        }
    ]
}
```

> **Нюанс:** Если Git установлен в нестандартное место, укажите реальный путь к `bash.exe`.
> Проверить путь: в CMD выполнить `where bash` или `where git`.

### 5.3. Расположение панели Claude Code

```json
{
    "claudeCode.preferredLocation": "panel"
}
```

Опции: `"panel"` (внизу, рядом с терминалом) или `"sidebar"` (боковая панель).

### 5.4. Выбор модели по умолчанию

```json
{
    "claudeCode.selectedModel": "opus"
}
```

### Полный settings.json (секция Claude Code)

```json
{
    "terminal.integrated.profiles.windows": {
        "Git Bash": {
            "source": "Git Bash"
        }
    },
    "terminal.integrated.defaultProfile.windows": "Git Bash",
    "terminal.integrated.enableMultiLinePasteWarning": "never",
    "claudeCode.preferredLocation": "panel",
    "claudeCode.selectedModel": "opus",
    "claudeCode.environmentVariables": [
        {
            "name": "CLAUDE_CODE_GIT_BASH_PATH",
            "value": "C:\\Program Files\\Git\\bin\\bash.exe"
        }
    ]
}
```

---

## 6. Авторизация Claude Code

### 6.1. Логин

Открыть терминал VS Code (Git Bash) и выполнить:

```bash
claude login
```

### 6.2. Выбор метода

Появится выбор:
- **Claude.ai (OAuth)** — для подписки Claude Max/Pro (рекомендуется)
- **API Key** — для Anthropic API key

При выборе OAuth:
1. Откроется браузер с страницей авторизации Claude
2. Войти в аккаунт Claude
3. Подтвердить доступ
4. Терминал покажет "Successfully authenticated"

### 6.3. Результат

Credentials сохраняются в:
```
C:\Users\<USER>\.claude\.credentials.json
```

Содержит OAuth токены (accessToken, refreshToken). Файл создается автоматически, не нужно трогать вручную.

### 6.4. Проверка

```bash
claude     # Должен запуститься без ошибок
/status    # Покажет модель и подписку
```

---

## 7. Глобальные настройки Claude

### 7.1. Модель по умолчанию

Создать/отредактировать файл:

```
C:\Users\<USER>\.claude\settings.json
```

Содержимое:

```json
{
    "model": "opus"
}
```

Доступные модели: `opus`, `sonnet`, `haiku`.

### 7.2. Структура ~/.claude/

После первого запуска автоматически создается:

```
~/.claude/
├── .credentials.json    # OAuth токены (создается при login)
├── settings.json        # Глобальные настройки (model)
├── cache/               # Кэш changelog
├── debug/               # Debug-логи
├── ide/                 # VS Code IDE connection
├── plugins/             # Marketplace плагины
├── projects/            # Проектные кэши
├── shell-snapshots/     # Снапшоты shell-окружения
├── telemetry/           # Статистика
└── todos/               # Задачи
```

Большинство папок создаются автоматически. Руками нужно только `settings.json`.

---

## 8. Настройка проекта

### 8.1. Файл CLAUDE.md (корень проекта)

Это главный файл инструкций для Claude Code в проекте. Claude читает его при каждом запуске.

Расположение: `<project-root>/CLAUDE.md`

### 8.2. Директория .claude/ (корень проекта)

```
<project-root>/.claude/
├── settings.json           # Проектные настройки (пустой или {})
├── settings.local.json     # Локальные разрешения (НЕ коммитится)
├── mcp.json                # MCP-серверы проекта
├── commands/               # Пользовательские slash-команды
│   ├── commit.md
│   ├── review.md
│   └── ...
├── rules/                  # Авто-применяемые правила
│   ├── python-standards.md
│   └── ...
└── skills/                 # Скиллы (документированные процедуры)
    ├── README.md
    └── .../
```

### 8.3. settings.local.json (разрешения)

Файл `.claude/settings.local.json` — **локальный**, не коммитится в git. Определяет какие инструменты разрешены без подтверждения.

Создать вручную:

```json
{
    "permissions": {
        "allow": [
            "Bash(*)",
            "Edit(*)",
            "Write(*)",
            "Read(*)",
            "Glob(*)",
            "Grep(*)",
            "WebSearch",
            "WebFetch(*)",
            "mcp__*"
        ]
    },
    "enableAllProjectMcpServers": true
}
```

> **Что это дает:** Claude может выполнять команды, читать/писать файлы, искать в интернете без запроса подтверждения каждый раз.

---

## 9. MCP-серверы

MCP (Model Context Protocol) — внешние инструменты, подключаемые к Claude Code.

### 9.1. Файл `.claude/mcp.json`

```json
{
    "mcpServers": {
        "exa": {
            "type": "http",
            "url": "https://mcp.exa.ai/mcp?exaApiKey=${EXA_API_KEY}"
        },
        "figma": {
            "type": "http",
            "url": "https://mcp.figma.com/mcp",
            "headers": {
                "X-Figma-Token": "${FIGMA_API_TOKEN}"
            }
        },
        "figma-desktop": {
            "type": "http",
            "url": "http://127.0.0.1:3845/mcp"
        },
        "context7": {
            "command": "cmd",
            "args": ["/c", "npx", "-y", "@upstash/context7-mcp"]
        },
        "playwright": {
            "command": "cmd",
            "args": ["/c", "npx", "-y", "@playwright/mcp", "--headless"]
        },
        "github": {
            "type": "http",
            "url": "https://api.githubcopilot.com/mcp/"
        }
    }
}
```

### 9.2. Переменные окружения для MCP

Создать файл `.env` в корне проекта (из `.env.example`):

```env
# EXA (семантический поиск)
EXA_API_KEY=your_exa_api_key_here

# Figma
FIGMA_API_TOKEN=your_figma_token_here

# Google (если используется)
GOOGLE_SERVICE_ACCOUNT_FILE=credentials.json
```

### 9.3. Нюансы MCP на Windows

- Серверы через `npx` используют `cmd /c npx` (не просто `npx`) — это Windows-специфика
- HTTP-серверы (exa, figma, github) работают без дополнительной настройки
- `figma-desktop` требует запущенного Figma Desktop с включенным Dev Mode
- `github` MCP требует GitHub Copilot подписки

---

## 10. Keybindings

### Shift+Enter для многострочного ввода

По умолчанию Enter отправляет сообщение. Для ввода многострочных промптов нужен Shift+Enter.

Открыть `keybindings.json` (`Ctrl+Shift+P` → "Preferences: Open Keyboard Shortcuts (JSON)") и добавить:

```json
[
    {
        "key": "shift+enter",
        "command": "workbench.action.terminal.sendSequence",
        "args": {
            "text": "\u001b\r"
        },
        "when": "terminalFocus"
    }
]
```

> **Что делает:** Shift+Enter в терминале вставляет перенос строки вместо отправки команды. Позволяет набирать многострочные промпты в Claude Code.

---

## 11. Полезные расширения VS Code

Рекомендуемые расширения (опционально):

```bash
# Установить все разом из командной строки:
code --install-extension anthropic.claude-code
code --install-extension eamodio.gitlens
code --install-extension pomdtr.excalidraw-editor
code --install-extension tomoki1207.pdf
```

| Расширение | ID | Зачем |
|-----------|-----|-------|
| Claude Code | `anthropic.claude-code` | Основной AI-ассистент |
| GitLens | `eamodio.gitlens` | Расширенная работа с Git |
| Excalidraw | `pomdtr.excalidraw-editor` | Диаграммы прямо в VS Code |
| PDF Viewer | `tomoki1207.pdf` | Просмотр PDF в VS Code |

---

## 12. Проверка установки

### Чеклист

Открыть терминал VS Code (должен быть Git Bash) и выполнить:

```bash
# 1. Git
git --version
# Ожидается: git version 2.x.x

# 2. Node.js
node --version
# Ожидается: v24.x.x (или LTS)

npm --version
# Ожидается: 11.x.x

# 3. Python
python --version
# Ожидается: Python 3.12.x

# 4. Claude Code
claude --version
# Ожидается: Claude Code v2.x.x

# 5. Запуск Claude Code
claude
# Должен запуститься интерактивный режим

# 6. Внутри Claude Code — проверить статус
/status
# Покажет: модель, подписку, MCP-серверы
```

### Тест MCP-серверов

Внутри Claude Code:

```
/mcp
```

Покажет список подключенных MCP-серверов и их статус.

---

## 13. Troubleshooting

### Claude Code не запускается

**Симптом:** `claude: command not found`

**Решение:**
1. Проверить что `claude.exe` в PATH:
   ```bash
   which claude
   ```
2. Если нет — добавить `C:\Users\<USER>\.local\bin` в PATH (см. шаг 3)
3. Перезапустить VS Code полностью

### Терминал показывает PowerShell вместо Git Bash

**Решение:**
1. Проверить `settings.json` — должен быть `"terminal.integrated.defaultProfile.windows": "Git Bash"`
2. В терминале VS Code нажать `+` → выбрать "Git Bash"
3. Перезапустить VS Code

### Claude Code не видит Git Bash

**Симптом:** Ошибки при выполнении bash-команд, синтаксис Windows

**Решение:**
1. Проверить `CLAUDE_CODE_GIT_BASH_PATH` в settings.json
2. Убедиться что путь `C:\Program Files\Git\bin\bash.exe` существует:
   ```bash
   ls "C:/Program Files/Git/bin/bash.exe"
   ```

### OAuth не проходит

**Симптом:** Браузер не открывается или ошибка авторизации

**Решение:**
1. Попробовать `claude login` снова
2. Убедиться что подписка Claude Max/Pro активна
3. Попробовать в другом браузере
4. Удалить старые credentials:
   ```bash
   rm ~/.claude/.credentials.json
   claude login
   ```

### MCP-серверы не подключаются

**Симптом:** MCP server failed to start

**Решение для npx-серверов:**
1. Проверить Node.js: `node --version`
2. Очистить npx-кэш: `npx clear-npx-cache`
3. Проверить что `cmd` доступен (npx серверы на Windows используют `cmd /c npx`)

**Решение для HTTP-серверов:**
1. Проверить что API-ключи прописаны в `.env`
2. Проверить что `.env` в корне проекта
3. Перезапустить Claude Code

### Shift+Enter не работает

**Решение:**
1. Проверить `keybindings.json` (Ctrl+Shift+P → Open Keyboard Shortcuts JSON)
2. Убедиться что курсор в терминале (не в редакторе)
3. Перезапустить VS Code

---

## Быстрый старт (TL;DR)

```bash
# 1. Установить Node.js (https://nodejs.org/)
# 2. Установить Python 3.12+ (https://python.org/, галка Add to PATH)

# 3. Установить Claude Code
npm install -g @anthropic-ai/claude-code

# 4. Установить VS Code extension
code --install-extension anthropic.claude-code

# 5. Настроить VS Code settings.json (Ctrl+Shift+P → Open User Settings JSON):
#    - defaultProfile: Git Bash
#    - CLAUDE_CODE_GIT_BASH_PATH
#    - claudeCode.preferredLocation: panel

# 6. Настроить keybindings.json:
#    - Shift+Enter → multiline input

# 7. Авторизоваться
claude login

# 8. Клонировать проект и создать .env из .env.example
# 9. Готово!
```

---

## Версии на момент создания инструкции

| Компонент | Версия |
|-----------|--------|
| Windows | 10 (26100) |
| Git | 2.53.0 |
| Node.js | v24.13.1 |
| npm | 11.8.0 |
| Python | 3.12.10 |
| Claude Code CLI | 2.1.44 |
| VS Code Extension | 2.1.44 |
| VS Code | Latest |

---

*Создано: 2026-02-17*
