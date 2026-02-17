Автоматическая настройка нового ПК. Прочитай Documentation/NEW_PC_FULL_SETUP.md как справочник.

Выполни по порядку:

## 1. Проверка предусловий
Проверь что установлены: git, node, python, claude. Если чего-то нет — скажи что установить и останови выполнение.

## 2. Импорт секретов
- Найди файл SECRETS_EXPORT.txt в корне проекта
- Если нет — скажи: "Скачай SECRETS_EXPORT.txt из Google Drive в папку ClaudeCode/ и запусти команду снова"
- Если есть — запусти: `python Scripts/secrets_import.py SECRETS_EXPORT.txt`
- Проверь результат: количество .env файлов и .credentials/*.json

## 3. Установка Python-зависимостей
```bash
pip install python-dotenv paramiko requests gspread google-auth google-api-python-client
```

## 4. VS Code settings.json
Открой файл настроек VS Code (путь зависит от ОС) и убедись что там есть:
- Git Bash как дефолтный терминал
- CLAUDE_CODE_GIT_BASH_PATH указывает на bash.exe
- claudeCode.preferredLocation = "panel"
- claudeCode.selectedModel = "opus"

Если файл пустой или настроек нет — добавь их (блок из NEW_PC_FULL_SETUP.md, ФАЗА 4.1).

## 5. VS Code keybindings.json
Проверь/добавь Shift+Enter биндинг для multiline input в терминале (блок из ФАЗЫ 4.2).

## 6. VS Code расширения
```bash
code --install-extension anthropic.claude-code
code --install-extension eamodio.gitlens
code --install-extension pomdtr.excalidraw-editor
code --install-extension tomoki1207.pdf
```

## 7. Глобальные настройки Claude
Создай ~/.claude/settings.json с содержимым: {"model": "opus"}

## 8. Локальные разрешения проекта
Создай .claude/settings.local.json с полными разрешениями (блок из ФАЗЫ 6.1 в NEW_PC_FULL_SETUP.md).

## 9. Удаление SECRETS_EXPORT.txt
Удали файл — он больше не нужен и не должен оставаться на диске.

## 10. Финальная проверка
Запусти чеклист:
- git --version
- node --version
- python --version
- claude --version
- Количество .env файлов (ожидается ~14)
- Количество .credentials/*.json (ожидается 4)
- Наличие .claude/settings.local.json
- Наличие ~/.claude/settings.json

Покажи результат в виде таблицы: компонент | статус | детали.

В конце напомни: "Выполни `claude login` вручную если ещё не залогинен."
