"""
TGStat Search CLI — поиск по Telegram-каналам через TGStat API.

Использование:
    python scripts/tgstat_search.py "запрос" [опции]

Опции:
    --mode posts|channels     режим поиска (по умолчанию: posts)
    --limit 50                количество результатов
    --days 30                 за последние N дней
    --lang ru|en              язык каналов (для поиска каналов)

Примеры:
    python scripts/tgstat_search.py "Claude Code" --mode posts --days 14
    python scripts/tgstat_search.py "AI coding" --mode channels --lang ru
    python scripts/tgstat_search.py "автоматизация" --mode posts --limit 30
"""

import argparse
import json
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

# Фикс UTF-8 для Windows терминала
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8")
if sys.stderr.encoding and sys.stderr.encoding.lower() != "utf-8":
    sys.stderr.reconfigure(encoding="utf-8")

# Загрузка .env
env_path = Path(__file__).parent.parent / ".env"
if env_path.exists():
    from dotenv import load_dotenv
    load_dotenv(env_path)

try:
    import requests
except ImportError:
    print("ERROR: pip install requests", file=sys.stderr)
    sys.exit(1)

TGSTAT_TOKEN = os.getenv("TGSTAT_TOKEN")
TGSTAT_BASE = "https://api.tgstat.ru"


def search_posts(query: str, limit: int = 50, days: int | None = None) -> dict:
    """Поиск постов по ключевому слову."""
    if not TGSTAT_TOKEN:
        return {"error": "TGSTAT_TOKEN not found in .env — получи на api.tgstat.ru ($25/мес)"}

    params: dict = {
        "token": TGSTAT_TOKEN,
        "q": query,
        "limit": limit,
    }

    if days:
        since = datetime.now(timezone.utc) - timedelta(days=days)
        params["startDate"] = int(since.timestamp())

    try:
        resp = requests.get(f"{TGSTAT_BASE}/posts/search", params=params, timeout=30)
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        return {"error": str(e)}


def search_channels(query: str, limit: int = 20, lang: str | None = None) -> dict:
    """Поиск каналов по теме."""
    if not TGSTAT_TOKEN:
        return {"error": "TGSTAT_TOKEN not found in .env"}

    params: dict = {
        "token": TGSTAT_TOKEN,
        "q": query,
        "limit": limit,
    }
    if lang:
        params["language"] = lang

    try:
        resp = requests.get(f"{TGSTAT_BASE}/channels/search", params=params, timeout=30)
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        return {"error": str(e)}


def format_posts(data: dict) -> str:
    if "error" in data:
        return f"ОШИБКА: {data['error']}"

    response = data.get("response", {})
    items = response.get("items", [])
    if not items:
        return "Постов не найдено."

    lines = [f"Найдено постов: {len(items)}\n"]
    for i, post in enumerate(items, 1):
        channel = post.get("channelName", post.get("channelId", "unknown"))
        date = datetime.fromtimestamp(post.get("date", 0)).strftime("%Y-%m-%d") if post.get("date") else "?"
        views = post.get("viewsCount", 0)
        text = post.get("text", "")[:400]
        post_id = post.get("postId", "")
        channel_id = post.get("channelId", "")

        lines.append(f"### [{i}] @{channel} | {date} | {views:,} просмотров")
        if channel_id and post_id:
            lines.append(f"URL: https://t.me/{channel_id}/{post_id}")
        lines.append(f"Текст: {text}")
        lines.append("")

    return "\n".join(lines)


def format_channels(data: dict) -> str:
    if "error" in data:
        return f"ОШИБКА: {data['error']}"

    response = data.get("response", {})
    items = response.get("items", [])
    if not items:
        return "Каналов не найдено."

    lines = [f"Найдено каналов: {len(items)}\n"]
    for i, ch in enumerate(items, 1):
        name = ch.get("title", "?")
        username = ch.get("username", "?")
        subs = ch.get("participantsCount", 0)
        desc = (ch.get("description") or "")[:200]
        lang = ch.get("language", "?")

        lines.append(f"### [{i}] {name} (@{username})")
        lines.append(f"Подписчики: {subs:,} | Язык: {lang}")
        lines.append(f"URL: https://t.me/{username}")
        if desc:
            lines.append(f"Описание: {desc}")
        lines.append("")

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="TGStat Search для Claude sub-агентов")
    parser.add_argument("query", help="Поисковый запрос")
    parser.add_argument(
        "--mode",
        choices=["posts", "channels"],
        default="posts",
        help="posts — поиск постов, channels — поиск каналов",
    )
    parser.add_argument("--limit", type=int, default=50, help="Количество результатов")
    parser.add_argument("--days", type=int, default=None, help="За последние N дней")
    parser.add_argument("--lang", help="Язык каналов: ru, en (только для --mode channels)")
    parser.add_argument("--json", action="store_true", help="Вернуть сырой JSON")

    args = parser.parse_args()

    if args.mode == "posts":
        data = search_posts(args.query, limit=args.limit, days=args.days)
        output = json.dumps(data, ensure_ascii=False, indent=2) if args.json else format_posts(data)
    else:
        data = search_channels(args.query, limit=args.limit, lang=args.lang)
        output = json.dumps(data, ensure_ascii=False, indent=2) if args.json else format_channels(data)

    print(output)


if __name__ == "__main__":
    main()
