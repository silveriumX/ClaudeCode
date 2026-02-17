# Контекст: FinanceBot (financebot)

**Фокус:** Projects/FinanceBot, VPS 195.177.94.189, деплой, Google Sheets, бот управления финансами.

## Что соблюдать

- **finance-bot-practices.mdc** — кодировка (ASCII в print/logging), SSH через Task/subagent, PowerShell (working_directory, без &&), встроенные зависимости в sheets.py.
- **finance-bot-vps.mdc** и **vps-ssh-deployment.mdc** — при деплое и проверке логов.
- **windows-unicode-fix.mdc** / **unicode-encoding-standards.mdc** — при скриптах на Windows.

## Ключевые пути

- `Projects/FinanceBot/` — бот, handlers, sheets, config.
- Деплой: Task с subagent (не прямой ssh из Shell).
- Логи на VPS: `journalctl -u finance_bot -n N`.

## В этом контексте

- Предлагать проверку логов после деплоя.
- Не использовать эмодзи в коде/скриптах для Shell.
- Использовать `working_directory` в Shell для путей к проекту.
- Проверять `is_user_active()` / роли при доступе к функциям.
