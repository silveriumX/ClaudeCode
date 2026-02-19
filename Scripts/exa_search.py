"""
Exa Search CLI — обёртка над Exa API для использования sub-агентами.

Использование:
    python scripts/exa_search.py "запрос" [опции]

Опции:
    --domains reddit.com,news.ycombinator.com   фильтр по доменам
    --days 30                                   за последние N дней
    --num 20                                    количество результатов
    --livecrawl                                 принудительно живой краулинг
    --highlights                                вернуть только highlights (экономит токены)
    --type auto|keyword                         тип поиска (auto = семантический)

Примеры:
    python scripts/exa_search.py "Claude Code vs Cursor" --domains reddit.com --days 30
    python scripts/exa_search.py "Rust async" --domains news.ycombinator.com --num 15
    python scripts/exa_search.py "AI coding tools" --domains reddit.com,twitter.com --days 7 --highlights
    python scripts/exa_search.py "telegram monitoring" --domains t.me
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

EXA_API_KEY = os.getenv("EXA_API_KEY")
EXA_BASE_URL = "https://api.exa.ai"


def search(
    query: str,
    domains: list[str] | None = None,
    days: int | None = None,
    num_results: int = 20,
    livecrawl: bool = False,
    highlights: bool = True,
    search_type: str = "auto",
) -> dict:
    if not EXA_API_KEY:
        return {"error": "EXA_API_KEY not found in .env"}

    headers = {
        "x-api-key": EXA_API_KEY,
        "Content-Type": "application/json",
    }

    payload: dict = {
        "query": query,
        "numResults": num_results,
        "type": search_type,
    }

    if domains:
        payload["includeDomains"] = domains

    if days:
        since = datetime.now(timezone.utc) - timedelta(days=days)
        payload["startPublishedDate"] = since.strftime("%Y-%m-%dT%H:%M:%SZ")

    if livecrawl:
        payload["livecrawl"] = "preferred"

    # Запрашиваем контент
    contents: dict = {}
    if highlights:
        contents["highlights"] = {"numSentences": 3, "highlightsPerUrl": 2}
    else:
        contents["text"] = {"maxCharacters": 1000}
    payload["contents"] = contents

    try:
        resp = requests.post(
            f"{EXA_BASE_URL}/search",
            headers=headers,
            json=payload,
            timeout=30,
        )
        resp.raise_for_status()
        return resp.json()
    except requests.exceptions.HTTPError as e:
        return {"error": f"HTTP {e.response.status_code}: {e.response.text[:300]}"}
    except Exception as e:
        return {"error": str(e)}


def format_results(data: dict, highlights: bool = True) -> str:
    """Форматирует результаты для читаемого вывода агентом."""
    if "error" in data:
        return f"ОШИБКА: {data['error']}"

    results = data.get("results", [])
    if not results:
        return "Результатов не найдено."

    lines = [f"Найдено результатов: {len(results)}\n"]

    for i, r in enumerate(results, 1):
        lines.append(f"### [{i}] {r.get('title', 'Без заголовка')}")
        lines.append(f"URL: {r.get('url', '')}")

        if r.get("publishedDate"):
            lines.append(f"Дата: {r['publishedDate'][:10]}")

        if highlights and r.get("highlights"):
            lines.append("Ключевые фрагменты:")
            for h in r["highlights"]:
                lines.append(f"  > {h.strip()}")
        elif r.get("text"):
            lines.append(f"Текст: {r['text'][:500]}...")

        lines.append("")  # пустая строка между результатами

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(
        description="Exa Search — поиск для Claude sub-агентов"
    )
    parser.add_argument("query", help="Поисковый запрос")
    parser.add_argument(
        "--domains",
        help="Домены через запятую: reddit.com,news.ycombinator.com",
        default=None,
    )
    parser.add_argument("--days", type=int, help="За последние N дней", default=None)
    parser.add_argument("--num", type=int, help="Количество результатов", default=20)
    parser.add_argument(
        "--livecrawl",
        action="store_true",
        help="Принудительный живой краулинг (для свежего контента)",
    )
    parser.add_argument(
        "--highlights",
        action="store_true",
        default=True,
        help="Вернуть highlights вместо полного текста (по умолчанию)",
    )
    parser.add_argument(
        "--full-text",
        action="store_true",
        help="Вернуть полный текст вместо highlights",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Вернуть сырой JSON вместо форматированного текста",
    )
    parser.add_argument(
        "--type",
        choices=["auto", "keyword"],
        default="auto",
        help="Тип поиска: auto (семантический) или keyword (точный)",
    )

    args = parser.parse_args()

    domains = [d.strip() for d in args.domains.split(",")] if args.domains else None
    use_highlights = not args.full_text

    data = search(
        query=args.query,
        domains=domains,
        days=args.days,
        num_results=args.num,
        livecrawl=args.livecrawl,
        highlights=use_highlights,
        search_type=args.type,
    )

    if args.json:
        print(json.dumps(data, ensure_ascii=False, indent=2))
    else:
        print(format_results(data, highlights=use_highlights))


if __name__ == "__main__":
    main()
