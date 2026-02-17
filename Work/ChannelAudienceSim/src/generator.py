"""
Генерация комментариев и ответов в тредах — только через LLM.
У каждой персоны своя инструкция (личность, психология, история).
"""
import os
from typing import Any

from openai import AsyncOpenAI


def _get_client() -> AsyncOpenAI:
    key = os.getenv("OPENAI_API_KEY", "").strip()
    if not key:
        raise RuntimeError("OPENAI_API_KEY не задан. Заполни .env")
    return AsyncOpenAI(api_key=key)


def _model() -> str:
    return os.getenv("OPENAI_MODEL", "gpt-4o-mini").strip()


async def generate_comment(persona: dict[str, Any], post_text: str) -> str:
    """
    Генерирует один комментарий к посту от лица персоны.
    Системный промпт = instruction персоны (личность, психология).
    """
    instruction = (persona.get("instruction") or "").strip()
    if not instruction:
        return ""
    name = persona.get("name", "Агент")
    system = (
        f"{instruction}\n\n"
        "Ты комментируешь пост в обсуждении канала. Пиши только текст комментария от своего имени: "
        "без кавычек, без подписи имени, без «я думаю» в третьем лице. Один короткий комментарий (1–3 предложения)."
    )
    user = f"Пост из канала:\n\n{post_text[:4000]}\n\nНапиши свой комментарий."
    client = _get_client()
    try:
        r = await client.chat.completions.create(
            model=_model(),
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            max_tokens=300,
            temperature=0.8,
        )
        text = (r.choices[0].message.content or "").strip()
        return text if text else ""
    except Exception:
        return ""


async def generate_reply(
    persona: dict[str, Any],
    reply_text: str,
    thread_context: str = "",
) -> str:
    """
    Генерирует ответ в треде на сообщение reply_text.
    thread_context — необязательный контекст ветки (пост + предыдущие реплики).
    """
    instruction = (persona.get("instruction") or "").strip()
    if not instruction:
        return ""
    system = (
        f"{instruction}\n\n"
        "Ты отвечаешь на сообщение в обсуждении поста. Пиши только текст ответа от своего имени: "
        "без кавычек, без подписи. Коротко (1–2 предложения)."
    )
    parts = [f"Сообщение, на которое отвечаешь:\n{reply_text[:2000]}"]
    if thread_context:
        parts.append(f"Контекст ветки:\n{thread_context[:1500]}")
    user = "\n\n".join(parts) + "\n\nНапиши ответ."
    client = _get_client()
    try:
        r = await client.chat.completions.create(
            model=_model(),
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            max_tokens=200,
            temperature=0.7,
        )
        text = (r.choices[0].message.content or "").strip()
        return text if text else ""
    except Exception:
        return ""
