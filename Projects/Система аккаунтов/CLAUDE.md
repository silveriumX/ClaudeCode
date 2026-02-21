# Система аккаунтов (AccountingBot)

Система обработки финансовых данных: парсинг банковских выписок, категоризация
транзакций, P&L отчёты. Google Sheets как хранилище данных.

## Структура

```
src/
├── import_statement.py   — парсинг выписок (Модульбанк 1C/HTML/Excel)
├── import_bybit.py       — импорт крипто-транзакций (Bybit)
├── import_wb.py          — импорт данных Wildberries
├── import_wb_detail.py   — детальные отчёты WB
├── import_personal.py    — личные транзакции
├── dbz_report.py         — отчёты ДБЗ
├── merge_pnl.py          — агрегация P&L
└── diff_journal.py       — сравнение журналов
```

## Стек

- Python 3.10+ / pandas / openpyxl
- Google Sheets (gspread) — хранилище транзакций
- Форматы выписок: Модульбанк (1C XML, HTML, Excel), Bybit CSV, Wildberries XLSX

## Скиллы проекта

- `/bank-statement-parser` — парсинг выписок → нормализованные транзакции
- `/transaction-categorizer` — категоризация: ИНН-правила → паттерны → GPT
- `/financial-journal-schema` — схема единого журнала транзакций в Google Sheets
- `/bank-import-bot` — Telegram-бот для загрузки выписок → Sheets с AI разметкой
- `/financial-dashboard` — Dashboard: P&L, Cash Flow, категории в Google Sheets

## Связанные скиллы (глобальные)

- `/tabular-schema-evolution` — при изменении схемы колонок в Sheets
- `/google-drive-sheets-auth` — OAuth vs Service Account для Sheets
- `/openai-json-extraction` — извлечение структурированных данных через GPT
