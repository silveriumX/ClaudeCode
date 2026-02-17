# Scripts — индекс скриптов

> Рабочие скрипты по категориям. Добавляй сюда новые скрипты при создании.

## Категории

### ProxyMA
- **Единый модуль:** `Utils/proxyma_api.py` (использовать в новых скриптах)
- `proxyma_api.py`, `proxyma_api_working.py`, `proxyma_api_correct.py` — локальные версии, миграция: см. `Scripts/ProxyMA/MIGRATION_UTILS.md`
- `get_proxyma_data_api.py`, `proxyma_collector.py` — сбор данных
- `proxyma_enable_autorenewal.py`, `proxyma_login_flow.py` — автопродление, логин
- Тесты: `test_proxyma*.ps1`, `test_proxyma_correct.ps1`

### Hub
- `check_hub_traffic.ps1`, `check_hub_usage.py` — проверка трафика
- `find_hub_rdp.py`, `get_hub_detailed.ps1`, `renew_hub_package.ps1`

### Traffic
- `find_traffic_data.py`, `find_traffic_stats_api.ps1`
- `get_traffic_reseller_api.ps1`, `test_traffic_api_python.py`

### Google Sheets
- `GoogleSheets/google_sheets_reader.py` — чтение таблиц

### Server / SSH
- `Server/server_helper.py`, `session_monitor.py`, `get_login.py`
- `ssh_helper.py`, `ssh_execute.ps1`
- `update_via_vps.py`

### PDF и документы
- `compress_pdf.py`, `compress_pdf_images.py` — сжатие PDF
- `process_pdf_pages.py`, `split_pdf_and_process.py` — разбивка и обработка
- `extract_pdf_text.py`, `pdf_to_text_ocr.py`
- `InstructionTools/` — извлечение изображений, подготовка документов
- `mcp-document-processor/` — MCP-сервер обработки документов

### Прочее
- `get_zoom_personal_meeting.py` — Zoom, сохранение в `Data/`
- `trace_and_remove_process.ps1` — поиск процесса по PID/имени, родитель, путь, рекомендации по удалению (требует прав администратора)
- `CLINT_REMOVAL_GUIDE.md` — пошаговая инструкция: найти clint/Runtime Brocker, заблокировать трафик, удалить автозагрузку и папку (все рабочие команды в одном файле)

## Где что хранить

- **Новый скрипт под существующую тему** → в подпапку (ProxyMA, Hub, Traffic, Server, GoogleSheets)
- **Новый тип задач** → новая подпапка в `Scripts/` с `README.md`
- **Общие утилиты** → `Utils/` (например, `Utils/google_api.py`)
- **Данные скриптов** → `Data/` (JSON, CSV — не коммитить секреты)

## Связанные файлы

- **NAVIGATION.md** — общая навигация
- **Documentation/API/** — PROXYMA, Google Sheets
- **Data/** — входные/выходные данные скриптов
