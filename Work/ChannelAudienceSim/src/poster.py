"""
Отправка сообщений в группу от разных юзерботов: одна сессия = одна персона.
Слушание группы — через один из клиентов (первый).
"""
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Callable, Awaitable, Any

OnNewPost = Callable[[int, str], Awaitable[None]]
OnReply = Callable[[int, str, int], Awaitable[None]]


class PosterBase(ABC):
    @abstractmethod
    async def send_message(
        self,
        chat_id: str,
        text: str,
        reply_to: int | None = None,
        persona_id: str | None = None,
    ) -> int | None:
        """Отправляет сообщение от имени персоны (persona_id). Возвращает message_id или None."""
        pass

    @abstractmethod
    async def start_listening(
        self,
        group_id: str,
        on_new_post: OnNewPost,
        on_reply: OnReply,
    ) -> None:
        pass


class MultiUserPoster(PosterBase):
    """
    Несколько юзерботов: у каждой персоны свой аккаунт (своя сессия).
    Слушаем группу через первый клиент.
    """
    def __init__(
        self,
        api_id: int,
        api_hash: str,
        sessions_dir: Path,
        personas: list[dict[str, Any]],
    ):
        self.api_id = api_id
        self.api_hash = api_hash
        self.sessions_dir = sessions_dir
        self.personas = personas
        self._clients: dict[str, Any] = {}
        self._listener_client: Any = None

    async def connect(self):
        from telethon import TelegramClient
        session_names = {p.get("session") for p in self.personas if p.get("session")}
        for name in session_names:
            path = self.sessions_dir / f"{name}.session"
            if not path.exists():
                raise FileNotFoundError(
                    f"Сессия не найдена: {path}. Создай сессию (например через auth как в TelegramBridge)."
                )
            client = TelegramClient(
                str(path),
                self.api_id,
                self.api_hash,
            )
            await client.connect()
            if not await client.is_user_authorized():
                raise SystemExit(
                    f"Сессия '{name}' не авторизована. Запусти auth как в TelegramBridge."
                )
            self._clients[name] = client
        if not self._clients:
            raise SystemExit("Нет ни одной сессии. Добавь .session файлы в SESSIONS_DIR.")
        self._listener_client = next(iter(self._clients.values()))

    def _client_for_persona(self, persona_id: str) -> Any | None:
        for p in self.personas:
            if p.get("id") == persona_id:
                session = p.get("session")
                return self._clients.get(session) if session else None
        return None

    async def send_message(
        self,
        chat_id: str,
        text: str,
        reply_to: int | None = None,
        persona_id: str | None = None,
    ) -> int | None:
        if not persona_id:
            return None
        client = self._client_for_persona(persona_id)
        if client is None:
            return None
        try:
            entity = int(chat_id) if chat_id.lstrip("-").isdigit() else chat_id
            msg = await client.send_message(entity, text, reply_to=reply_to)
            return msg.id
        except Exception:
            return None

    async def start_listening(
        self,
        group_id: str,
        on_new_post: OnNewPost,
        on_reply: OnReply,
    ) -> None:
        from telethon import events
        group_entity = int(group_id) if group_id.lstrip("-").isdigit() else group_id

        @self._listener_client.on(events.NewMessage(chats=group_entity))
        async def handler(event: events.NewMessage.Event):
            msg = event.message
            if msg.reply_to_msg_id:
                await on_reply(msg.reply_to_msg_id, msg.text or "", msg.id)
            else:
                if getattr(msg, "fwd_from", None):
                    await on_new_post(msg.id, msg.text or "")

        await self._listener_client.run_until_disconnected()
