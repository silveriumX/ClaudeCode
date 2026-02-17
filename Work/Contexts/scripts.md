# Контекст: Скрипты (scripts)

**Фокус:** Scripts/, утилиты, ProxyMA, Hub, GoogleSheets, Server, деплой-скрипты.

## Что соблюдать

- **python-standards.mdc** — pathlib, type hints, docstrings, encoding utf-8 для файлов.
- **windows-unicode-fix.mdc** / **unicode-encoding-standards.mdc** — при выводе в консоль (safe_print / ASCII в скриптах для Shell).
- **file-indexing-storage.mdc** — новые скрипты в нужную подпапку, обновлять `Scripts/INDEX.md`.

## Ключевые пути

- `Scripts/` — ProxyMA, Hub, GoogleSheets, Server, WireGuard, ProxiFyre и др.
- `Scripts/INDEX.md` — индекс скриптов.
- `Utils/` — общие утилиты (google_api, proxyma_api, safe_console).

## В этом контексте

- Предлагать класть скрипт в тематическую подпапку (Scripts/ProxyMA, Scripts/Hub и т.д.).
- Для скриптов, запускаемых через Shell, — без эмодзи в print; при необходимости — Utils/safe_console.
- Учитывать PowerShell: не использовать `&&`, использовать `working_directory` или `;`.
