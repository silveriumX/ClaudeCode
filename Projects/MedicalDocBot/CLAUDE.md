# MedicalDocBot

Бот для загрузки медицинских документов: OCR + AI-извлечение полей + Google Drive + Google Sheets.

## Деплой и управление VPS

Креды VPS: `.env` → VPS_HOST, VPS_PORT, VPS_USER, VPS_PASSWORD
Путь на сервере: `.env` → VPS_REMOTE_DIR
Запуск: nohup python3 bot.py (без systemd)

### Единственный инструмент: `vps_connect.py`

```bash
python vps_connect.py status       # статус бота
python vps_connect.py logs [N]     # логи
python vps_connect.py errors [N]   # ошибки
python vps_connect.py restart      # перезапуск
python vps_connect.py deploy       # загрузить файлы + перезапуск
python vps_connect.py shell <cmd>  # SSH команда
```

**НИКОГДА не создавай новые deploy_*.py, check_*.py, upload_*.py.**

## Структура

```
bot.py              — Telegram хендлеры, оркестрация пайплайна
config.py           — загрузка .env
vision_ocr.py       — Google Cloud Vision OCR (изображения + PDF)
llm_extractor.py    — GPT-4.1-mini извлечение полей в JSON
drive_manager.py    — загрузка файлов в Google Drive (OAuth)
sheets_logger.py    — запись метаданных в Google Sheets (gspread)
vps_connect.py      — управление VPS
```

## Стек

- Python 3.10+ / python-telegram-bot 21.7
- Google Cloud Vision API (OCR)
- OpenAI GPT-4.1-mini (извлечение полей)
- Google Drive (OAuth) + Google Sheets (Service Account)
