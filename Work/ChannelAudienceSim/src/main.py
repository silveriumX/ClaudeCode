"""
Точка входа: агенты-персоны (разные юзерботы) комментируют посты и отвечают в тредах.
Только LLM, без шаблонов. Комментарии в разное время (задержка + джиттер).
"""
import asyncio
import os
from pathlib import Path
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")

DISCUSSION_GROUP_ID = os.getenv("DISCUSSION_GROUP_ID", "").strip()


async def main():
    if not DISCUSSION_GROUP_ID:
        raise SystemExit("DISCUSSION_GROUP_ID не задан. Укажи ID группы обсуждений в .env")
    api_id = os.getenv("API_ID", "").strip()
    api_hash = os.getenv("API_HASH", "").strip()
    sessions_dir = Path(os.getenv("SESSIONS_DIR", str(ROOT / "sessions")))
    if not api_id or not api_hash:
        raise SystemExit("API_ID и API_HASH нужны. Заполни .env")

    from channel_listener import ChannelListener
    from poster import MultiUserPoster
    from personas import load_personas

    personas = load_personas(ROOT / "config" / "personas.yaml")
    if not personas:
        raise SystemExit("Нет персон. Заполни config/personas.yaml")

    poster = MultiUserPoster(
        api_id=int(api_id),
        api_hash=api_hash,
        sessions_dir=sessions_dir,
        personas=personas,
    )
    await poster.connect()
    listener = ChannelListener(group_id=DISCUSSION_GROUP_ID, poster=poster)
    await listener.run()


if __name__ == "__main__":
    asyncio.run(main())
