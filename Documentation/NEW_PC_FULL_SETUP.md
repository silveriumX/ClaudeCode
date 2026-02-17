# Полная настройка нового ноутбука

> Один файл — от нуля до рабочего окружения.
> Предусловия: Windows 10, Git и VS Code уже установлены.

---

## ФАЗА 1: Установка софта

### 1.1. Node.js

1. Скачать с https://nodejs.org/ (LTS или Current)
2. Установить с дефолтными настройками
3. Проверить:
   ```bash
   node --version   # v24.x.x
   npm --version    # 11.x.x
   ```

### 1.2. Python 3.12+

1. Скачать с https://www.python.org/downloads/
2. **ВАЖНО:** при установке поставить галку **"Add Python to PATH"**
3. Проверить:
   ```bash
   python --version   # Python 3.12.x
   pip --version
   ```

### 1.3. Базовые Python-пакеты

```bash
pip install python-dotenv paramiko requests gspread google-auth google-api-python-client
```

---

## ФАЗА 2: Клонирование проекта и импорт секретов

### 2.1. Клонировать репозиторий

```bash
cd "C:\Users\<USER>\Documents"
git clone https://github.com/silveriumX/ClaudeCode.git
cd ClaudeCode
```

> Замени `<USER>` на своё имя пользователя Windows.

### 2.2. Импорт секретов

1. Скачать `SECRETS_EXPORT.txt` из Google Drive
2. Положить в корень `ClaudeCode/`
3. Запустить:

```bash
python Scripts/secrets_import.py SECRETS_EXPORT.txt
```

Скрипт создаст:
- 14 файлов `.env` в каждом проекте
- `.credentials/` с 4 JSON-файлами (Google Service Account, OAuth)
- `.claude/mcp.json` с конфигурацией MCP-серверов

4. **УДАЛИТЬ** `SECRETS_EXPORT.txt`:
```bash
del SECRETS_EXPORT.txt
```
И удалить из Google Drive + Корзины.

### 2.3. Проверить что секреты на месте

```bash
# Должен показать ~14 файлов
python -c "from pathlib import Path; print(len(list(Path('.').rglob('.env'))))"

# Должен показать 4 файла
python -c "from pathlib import Path; print(list(Path('.credentials').glob('*.json')))"
```

---

## ФАЗА 3: Claude Code

### 3.1. Установка CLI

```bash
npm install -g @anthropic-ai/claude-code
```

Проверить:
```bash
claude --version   # Claude Code v2.x.x
```

Если `claude: command not found`:
- Добавить `C:\Users\<USER>\.local\bin` в PATH
- Win+R -> `sysdm.cpl` -> Дополнительно -> Переменные среды -> Path -> Добавить
- Перезапустить терминал

### 3.2. VS Code Extension

```bash
code --install-extension anthropic.claude-code
```

### 3.3. Другие полезные расширения

```bash
code --install-extension eamodio.gitlens
code --install-extension pomdtr.excalidraw-editor
code --install-extension tomoki1207.pdf
```

---

## ФАЗА 4: Настройка VS Code

### 4.1. settings.json

Открыть: `Ctrl+Shift+P` -> "Preferences: Open User Settings (JSON)"

Вставить **весь блок**:

```json
{
    "terminal.integrated.profiles.windows": {
        "Git Bash": {
            "source": "Git Bash"
        }
    },
    "terminal.integrated.defaultProfile.windows": "Git Bash",
    "terminal.integrated.enableMultiLinePasteWarning": "never",
    "git.enableSmartCommit": true,
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

> **Критично:** Claude Code на Windows работает ТОЛЬКО через Git Bash.
> Если Git установлен не в `C:\Program Files\Git\`, найди реальный путь: `where bash`

### 4.2. keybindings.json

Открыть: `Ctrl+Shift+P` -> "Preferences: Open Keyboard Shortcuts (JSON)"

Добавить:

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

> Shift+Enter = новая строка в промпте (без отправки). Без этого не получится писать многострочные запросы.

---

## ФАЗА 5: Авторизация и глобальные настройки

### 5.1. Логин в Claude

Перезапустить VS Code, открыть терминал (должен быть Git Bash!) и:

```bash
claude login
```

Выбрать **"Claude.ai (OAuth)"** -> откроется браузер -> войти -> подтвердить.

### 5.2. Глобальная модель

Создать файл `C:\Users\<USER>\.claude\settings.json`:

```json
{
    "model": "opus"
}
```

### 5.3. Проверка

```bash
claude --version
# Внутри Claude Code:
/status
```

---

## ФАЗА 6: Локальные настройки проекта

### 6.1. settings.local.json (разрешения)

Этот файл НЕ коммитится в git — его нужно создать вручную.

Создать файл `ClaudeCode/.claude/settings.local.json`:

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
            "mcp__*",
            "mcp__claude_ai_Excalidraw__create_view",
            "mcp__claude_ai_Excalidraw__export_to_excalidraw",
            "mcp__claude_ai_Excalidraw__read_me",
            "mcp__claude_ai_Excalidraw__read_checkpoint"
        ]
    },
    "enabledMcpjsonServers": ["excalidraw-render"],
    "enableAllProjectMcpServers": true
}
```

> Без этого файла Claude будет спрашивать разрешение на каждое действие.

### 6.2. Проверка MCP-серверов

Внутри Claude Code:
```
/mcp
```

Должны быть видны: exa, figma, context7, playwright, github.

---

## ФАЗА 7: Финальная проверка

### Чеклист

```bash
# 1. Git
git --version                    # git version 2.x.x

# 2. Node.js
node --version                   # v24.x.x
npm --version                    # 11.x.x

# 3. Python
python --version                 # Python 3.12.x

# 4. Claude Code
claude --version                 # Claude Code v2.x.x

# 5. Проект
cd "C:\Users\<USER>\Documents\ClaudeCode"
git status                       # On branch main, nothing to commit

# 6. Секреты на месте
cat .env | head -5               # Должны быть ключи (не пустой)

# 7. Запуск Claude Code
claude
/status                          # Модель, подписка, MCP
```

---

## Troubleshooting

### `claude: command not found`
- Добавить `C:\Users\<USER>\.local\bin` в PATH
- Перезапустить VS Code

### Терминал — PowerShell вместо Git Bash
- Проверить settings.json: `"terminal.integrated.defaultProfile.windows": "Git Bash"`
- В терминале нажать `+` -> выбрать Git Bash
- Перезапустить VS Code

### Claude Code не видит Git Bash / ошибки Windows-синтаксиса
- Проверить `CLAUDE_CODE_GIT_BASH_PATH` в settings.json
- Путь должен быть к `bash.exe`, не к `git.exe`

### OAuth не проходит
```bash
rm ~/.claude/.credentials.json
claude login
```

### MCP-серверы не работают
- Проверить что `.env` в корне проекта (EXA_API_KEY, FIGMA_API_TOKEN)
- Для npx-серверов: проверить `node --version`
- Перезапустить Claude Code

### Shift+Enter не работает
- Проверить keybindings.json
- Убедиться что курсор в терминале, не в редакторе
- Перезапустить VS Code

---

## Что где лежит (после настройки)

```
C:\Users\<USER>\
├── .claude\
│   ├── .credentials.json        # OAuth токены (создается при login)
│   └── settings.json            # {"model": "opus"}
│
└── Documents\
    └── ClaudeCode\              # Клонированный репо
        ├── .env                 # Корневые секреты (из импорта)
        ├── .credentials\        # Google JSON ключи (из импорта)
        ├── .claude\
        │   ├── mcp.json         # MCP-серверы (из импорта)
        │   ├── settings.json    # {} (из git)
        │   ├── settings.local.json  # Разрешения (создано вручную!)
        │   ├── commands\        # Slash-команды (из git)
        │   ├── rules\           # Правила (из git)
        │   └── skills\          # Скиллы (из git)
        ├── CLAUDE.md            # Инструкции для Claude (из git)
        ├── Projects\            # Все проекты (из git)
        │   └── */\.env          # Секреты проектов (из импорта)
        ├── Scripts\             # Скрипты (из git)
        └── Documentation\      # Документация (из git)
```

Файлы из git = клонируются автоматически.
Файлы из импорта = создаются `secrets_import.py`.
Файлы вручную = `settings.local.json` + `~/.claude/settings.json`.

---

*Создано: 2026-02-17*
