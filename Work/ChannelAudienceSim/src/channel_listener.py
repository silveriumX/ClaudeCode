"""
Слушатель группы обсуждений: новые посты и ответы в тредах.
Комментарии — только через LLM, от разных юзерботов (разные персоны).
Время появления — в разное (delay_range + случайный джиттер), не пачкой.
"""
import asyncio
import random
from pathlib import Path

from personas import load_personas, should_comment, get_persona_by_id
from generator import generate_comment, generate_reply
from poster import PosterBase

OUR_MESSAGES: dict[int, str] = {}
JITTER_MAX_SEC = 45


class ChannelListener:
    def __init__(self, group_id: str, poster: PosterBase):
        self.group_id = group_id
        self.poster = poster
        root = Path(__file__).resolve().parent.parent
        self.personas = load_personas(root / "config" / "personas.yaml")

    def _delay_with_jitter(self, persona: dict) -> int:
        """Задержка из delay_range + случайный джиттер, чтобы не пачкой."""
        lo, hi = persona.get("delay_range", [60, 300])
        base = random.randint(lo, hi)
        jitter = random.randint(0, min(JITTER_MAX_SEC, (hi - lo) // 2))
        return base + jitter

    async def on_new_post(self, message_id: int, post_text: str):
        """Новый пост в группе. Для каждой персоны — своя задержка, потом LLM и отправка от её аккаунта."""
        for persona in self.personas:
            if not should_comment(persona):
                continue
            delay = self._delay_with_jitter(persona)
            asyncio.create_task(
                self._comment_after_delay(message_id, post_text, persona, delay)
            )

    async def _comment_after_delay(
        self, message_id: int, post_text: str, persona: dict, delay: int
    ):
        await asyncio.sleep(delay)
        text = await generate_comment(persona, post_text)
        if not text:
            return
        sent_id = await self.poster.send_message(
            self.group_id,
            text,
            reply_to=message_id,
            persona_id=persona["id"],
        )
        if sent_id is not None:
            OUR_MESSAGES[sent_id] = persona["id"]

    async def on_reply(self, parent_message_id: int, reply_text: str, new_message_id: int):
        """Кто-то ответил в треде. Если это ответ нашему агенту — генерируем ответ от той же персоны через LLM."""
        persona_id = OUR_MESSAGES.get(parent_message_id)
        if not persona_id:
            return
        persona = get_persona_by_id(self.personas, persona_id)
        if not persona:
            return
        reply_prob = persona.get("reply_probability", 0.5)
        if random.random() > reply_prob:
            return
        reply = await generate_reply(persona, reply_text, thread_context="")
        if not reply:
            return
        sent_id = await self.poster.send_message(
            self.group_id,
            reply,
            reply_to=new_message_id,
            persona_id=persona["id"],
        )
        if sent_id is not None:
            OUR_MESSAGES[sent_id] = persona["id"]

    async def run(self):
        await self.poster.start_listening(
            self.group_id, self.on_new_post, self.on_reply
        )
