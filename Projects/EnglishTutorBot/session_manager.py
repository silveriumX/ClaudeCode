"""
Session Manager — lightweight session tracking for stats.

No timers, no auto-end.  A session starts when the user explicitly asks
("let's practice") and ends when they say "stop" / "enough".
Between sessions the bot works in free-talk mode — no restrictions.
"""
import json
from datetime import datetime
from typing import Dict, Optional

from user_profile import UserProfile


class Session:
    """Single active session for one user (passive tracking only)."""

    def __init__(
        self,
        user_id: int,
        topic: str = "",
        mode: str = "tutor",
        lang: str = "en",
    ):
        self.user_id = user_id
        self.session_id = f"s_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        self.topic = topic
        self.mode = mode
        self.lang = lang
        self.started_at = datetime.now()
        self.messages_count = 0
        self.mistakes: Dict[str, int] = {}

    @property
    def elapsed_seconds(self) -> int:
        return int((datetime.now() - self.started_at).total_seconds())

    def increment_message(self):
        self.messages_count += 1

    def track_mistake(self, mistake_type: str):
        self.mistakes[mistake_type] = self.mistakes.get(mistake_type, 0) + 1

    def to_record(self, summary: str = "") -> dict:
        """Convert to a dict for saving to sessions file."""
        return {
            "session_id": self.session_id,
            "date": self.started_at.date().isoformat(),
            "started_at": self.started_at.isoformat(),
            "topic": self.topic,
            "duration_actual_seconds": self.elapsed_seconds,
            "messages_count": self.messages_count,
            "mode": self.mode,
            "lang": self.lang,
            "mistakes": self.mistakes,
            "summary": summary,
        }


class SessionManager:
    """Manages active sessions for all users."""

    def __init__(self):
        self.active: Dict[int, Session] = {}

    # ------------------------------------------------------------------
    # Session lifecycle
    # ------------------------------------------------------------------

    async def start_session(
        self,
        user_id: int,
        topic: str = "",
        mode: str = "tutor",
        lang: str = "en",
    ) -> Session:
        """Start a new session. Ends existing one if any."""
        if user_id in self.active:
            await self.end_session(user_id, reason="new_session")

        session = Session(
            user_id=user_id,
            topic=topic,
            mode=mode,
            lang=lang,
        )
        self.active[user_id] = session
        return session

    async def end_session(self, user_id: int, reason: str = "manual") -> Optional[dict]:
        """End an active session. Returns session record or None."""
        session = self.active.pop(user_id, None)
        if not session:
            return None

        summary = (
            f"{session.topic or 'General practice'}. "
            f"{session.messages_count} messages in "
            f"{session.elapsed_seconds // 60} min. "
            f"Ended: {reason}."
        )

        record = session.to_record(summary=summary)

        # Save to user profile
        profile = UserProfile(user_id)
        profile.save_session(record)
        if session.topic:
            profile.mark_today_completed()

        return record

    def get_session(self, user_id: int) -> Optional[Session]:
        return self.active.get(user_id)

    def has_active_session(self, user_id: int) -> bool:
        return user_id in self.active

    # ------------------------------------------------------------------
    # Activity tracking
    # ------------------------------------------------------------------

    def on_message(self, user_id: int):
        """Called on every user message to track activity within session."""
        session = self.active.get(user_id)
        if session:
            session.increment_message()


# Global instance
session_manager = SessionManager()
