# Projects — индекс проектов

> Навигация по готовым проектам. Обновляй этот файл при добавлении нового проекта.

## Активные (2026)

| Проект | Назначение | Точка входа |
|--------|------------|-------------|
| **OpenClaw** | Инструменты развертывания OpenClaw AI-агента на VPS | `vps_connect.py` |
| **ChatManager** | AI-first управление чатами (UserBot + Control Bot), Google Sheets | `bot.py`, `userbot.py` |
| **FinanceBot** | Telegram-бот для заявок и выплат, Google Sheets | `bot.py`, `sheets.py` |
| **VoiceBot** | Голосовые заметки, синхронизация с VPS | `bot.py`, `sync_thoughts.ps1` |
| **ServerManager** | Мониторинг Windows-серверов (SSH), отчёты в Telegram | `server-monitor-package/server_monitor_ssh.py` |
| **TelegramHub** | Универсальный бот, AI overlay, деплой | `server/main.py`, `START_TELEGRAMHUB.bat` |
| **ResearchSystem** | Исследования, EXA, отчёты | `data/reports/`, skills |
| **DocChat** | Обработка документов (Streamlit) | `app.py` |
| **FinanceSystem** | Google Sheets, Apps Script, TypeScript | `src/`, `*.gs` |
| **AIOverlay** | Оверлей для подсказок в приложениях | `ai_overlay.py`, `START.bat` |
| **BitcoinWalletTest** | Создание и тестирование Bitcoin Core wallet v60000 | `step_by_step.ps1`, `SIMPLE_GUIDE.md` |
| **EnglishTutorBot** | AI репетитор английского (голосовая практика) | `bot.py`, `README.md` |
| **MedicalDocBot** | Медицинские документы: загрузка в Drive + таблица | `bot.py`, `README.md` |
| **CardDesigner** | Обработка фото через Replicate API + Claude | `main.py` |
| **MediaDownloaderBot** | Скачивание медиа через yt-dlp | `bot.py` |
| **SMS_Journals** | Google Apps Script для SMS через MTT/FlowSMS | `*.gs` |
| **Финансовая система** | Документация/планирование финансов (Excel) | `*.xlsx` |

## По категориям

- **Боты (Telegram):** ChatManager, FinanceBot, VoiceBot, TelegramHub, EnglishTutorBot, MedicalDocBot, MediaDownloaderBot
- **AI Агенты:** OpenClaw
- **Инфраструктура:** ServerManager
- **Данные/таблицы:** ChatManager, FinanceBot, FinanceSystem, SMS_Journals
- **Инструменты:** ResearchSystem, DocChat, CardDesigner, AIOverlay
- **Документация:** Финансовая система, BitcoinWalletTest

## Соглашения

- В каждом проекте: `README.md` (описание), при необходимости `requirements.txt`, `.env.example`
- Деплой-скрипты и инструкции — в папке проекта или в `Documentation/`
- Общие утилиты (Google API, ProxyMA) — в `Utils/` и `Scripts/`

## Связанные файлы

- **NAVIGATION.md** (корень) — общая карта репозитория
- **Documentation/** — API, Cursor, GitHub, Team
