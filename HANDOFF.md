# HANDOFF — 2026-02-20

## Цель сессии
Ресёрч инструментов мониторинга соцсетей + создание скиллов и скриптов для Claude Code.

## Сделано
- [x] Ресёрч: Telegram, Twitter/X, Reddit, LLM-пайплайны (3 параллельных агента)
- [x] Создан `scripts/exa_search.py` — CLI обёртка Exa API для sub-агентов (протестирован, работает)
- [x] Создан `scripts/tgstat_search.py` — CLI для TGStat API (ждёт ключ в .env)
- [x] Новые скиллы: `/social-research`, `/reddit-search`, `/hn-search`, `/twitter-search`, `/telegram-search`, `/monitor-pipeline`
- [x] Обновлён `research-guide.md` — Exa MCP приоритет над WebSearch + преамбула для sub-агентов с Bash-командами
- [x] Проверено: `exa_search.py --domains reddit.com` возвращает реальные треды

## Текущее состояние
- Незакоммичено: см. `git status` — research-guide.md, social-research.md, 4 скилла, 2 скрипта, settings.local.json
- Exa MCP установлен и работает (ключ уже в системе)
- TGStat: скрипт готов, нужно добавить `TGSTAT_TOKEN=...` в `.env` когда получишь ключ

## Что решили и почему
- Sub-агенты + Bash → scripts/ — потому что MCP не передаётся в Task sub-агенты
- TGStat/Telethon отложили — TGStat ограничивает поиск по всем постам, Telethon требует отдельный аккаунт
- Twitter отложили — SociaVault/Xpoz не нужны прямо сейчас

## Что НЕ пробовать
- MCP инструменты внутри Task sub-агентов — не работает, только главная сессия
- TGStat free tier для поиска по всем постам — разрешает только мониторинг добавленных каналов

## Следующие шаги
1. Добавить `TGSTAT_TOKEN=...` в `.env` когда получишь ключ на api.tgstat.ru
2. Попробовать `/social-research topic="нужная тема"` — всё уже готово
3. Если нужен Telegram глубже — рассмотреть Telethon (бесплатно, отдельный аккаунт)

## Важные файлы
- `scripts/exa_search.py` — поиск для sub-агентов (Reddit, HN, Twitter, web)
- `scripts/tgstat_search.py` — Telegram поиск (нужен TGSTAT_TOKEN)
- `.claude/rules/research-guide.md` — обновлён: Exa приоритет + Bash-команды для sub-агентов
- `.claude/skills/` — 6 новых скиллов по мониторингу соцсетей

## Справка
- Последний коммит: 629dd1d (feat: python-project-init, contract-first, handoff skills)
- Тесты: n/a
