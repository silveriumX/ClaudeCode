"""
User Profile — persistent per-user storage with detailed tracking.

Each user gets:
  user_data/{user_id}.json        — profile, settings, plan, recent history
  user_data/{user_id}_sessions.json — completed session logs
  user_data/{user_id}_archive.json  — full conversation archive
"""
import json
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from datetime import datetime, date

USER_DATA_DIR = Path("user_data")
USER_DATA_DIR.mkdir(exist_ok=True)

SUPPORTED_LANGS = ("en", "jp", "es")

# ---------------------------------------------------------------------------
# Default structures
# ---------------------------------------------------------------------------


def _empty_lang_slice(now: str = None) -> dict:
    """One language's data: history, stats, plan, mistakes, skills — independent per lang."""
    now = now or datetime.now().isoformat()
    return {
        "learning_plan": {
            "global_goal": "",
            "target_level": "",
            "current_focus": "",
            "focus_areas": [],
            "ai_recommendations": [],
            "weekly_plan": None,
            "created_at": now,
            "updated_at": now,
        },
        "stats": {
            "level": "beginner",
            "total_messages": 0,
            "total_sessions": 0,
            "streak_days": 0,
            "last_practice_date": None,
            "messages_since_last_review": 0,
        },
        "detailed_mistakes": [],
        "skills": {},
        "progress_snapshots": [],
        "custom_instructions": [],
        "bot_observations": [],
        "conversation_history": [],
    }


def _empty_profile(user_id: int) -> dict:
    """Create a blank profile for a new user. Progress and dialogue are per-language."""
    now = datetime.now().isoformat()
    return {
        "user_id": user_id,
        "display_name": "",
        "native_language": "ru",
        "created_at": now,
        "settings": {
            "current_lang": "en",
            "session_mode": "tutor",
            "response_format": "auto",
            "default_session_minutes": 5,
            "tts_voice": "nova",
        },
        "profiles_by_lang": {
            lang: _empty_lang_slice(now) for lang in SUPPORTED_LANGS
        },
    }


# ---------------------------------------------------------------------------
# Main class
# ---------------------------------------------------------------------------

class UserProfile:
    """Full user profile with settings, plan, skills, and conversation history."""

    HISTORY_CAP = 50            # messages in main profile
    CONTEXT_WINDOW = 7          # messages sent to GPT as context
    REVIEW_INTERVAL = 10        # messages between auto-reviews

    def __init__(self, user_id: int):
        self.user_id = user_id
        self.file_path = USER_DATA_DIR / f"{user_id}.json"
        self.sessions_path = USER_DATA_DIR / f"{user_id}_sessions.json"
        self.archive_path = USER_DATA_DIR / f"{user_id}_archive.json"
        self.data = self._load()

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def _load(self) -> dict:
        if self.file_path.exists():
            try:
                with open(self.file_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                # Migrate old profiles: add missing keys
                return self._migrate(data)
            except json.JSONDecodeError as e:
                # Profile file is corrupted, create backup and start fresh
                import logging
                logger = logging.getLogger(__name__)
                backup_path = self.file_path.with_suffix('.json.backup')
                logger.error(f"Corrupted profile {self.file_path}: {e}. Creating backup at {backup_path}")
                if self.file_path.exists():
                    import shutil
                    shutil.copy(self.file_path, backup_path)
                return _empty_profile(self.user_id)
            except Exception as e:
                # Other file reading errors
                import logging
                logger = logging.getLogger(__name__)
                logger.exception(f"Failed to load profile {self.file_path}: {e}")
                return _empty_profile(self.user_id)
        return _empty_profile(self.user_id)

    def _migrate(self, data: dict) -> dict:
        """Ensure old profiles get new fields. Migrate flat structure -> profiles_by_lang."""
        now = datetime.now().isoformat()
        template = _empty_profile(self.user_id)
        if "profiles_by_lang" not in data:
            data["profiles_by_lang"] = {}
            current = data.get("settings", {}).get("current_lang", "en")
            for lang in SUPPORTED_LANGS:
                data["profiles_by_lang"][lang] = _empty_lang_slice(now)
            for key in ("conversation_history", "stats", "learning_plan", "detailed_mistakes",
                        "skills", "progress_snapshots", "custom_instructions", "bot_observations"):
                if key in data and data[key] is not None:
                    data["profiles_by_lang"][current][key] = data[key]
                if key in data:
                    del data[key]
        for key in ("user_id", "display_name", "native_language", "created_at", "settings"):
            if key not in data and key in template:
                data[key] = template[key]
        for lang in SUPPORTED_LANGS:
            if lang not in data["profiles_by_lang"]:
                data["profiles_by_lang"][lang] = _empty_lang_slice()
            else:
                sl = data["profiles_by_lang"][lang]
                for k, v in _empty_lang_slice(now).items():
                    if k not in sl:
                        sl[k] = v
        return data

    def save(self):
        with open(self.file_path, "w", encoding="utf-8") as f:
            json.dump(self.data, f, ensure_ascii=False, indent=2)

    def _lang_data(self, lang: Optional[str] = None) -> dict:
        """Data for one language (conversation, stats, plan, mistakes — separate per lang)."""
        lang = lang or self.lang
        if lang not in SUPPORTED_LANGS:
            lang = "en"
        by_lang = self.data.setdefault("profiles_by_lang", {})
        if lang not in by_lang:
            by_lang[lang] = _empty_lang_slice()
        return by_lang[lang]

    # ------------------------------------------------------------------
    # Settings helpers
    # ------------------------------------------------------------------

    @property
    def lang(self) -> str:
        return self.data["settings"].get("current_lang", "en")

    @lang.setter
    def lang(self, value: str):
        self.data["settings"]["current_lang"] = value
        self.save()

    @property
    def session_mode(self) -> str:
        return self.data["settings"].get("session_mode", "tutor")

    @session_mode.setter
    def session_mode(self, value: str):
        self.data["settings"]["session_mode"] = value
        self.save()

    @property
    def display_name(self) -> str:
        return self.data.get("display_name", "")

    @display_name.setter
    def display_name(self, value: str):
        self.data["display_name"] = value
        self.save()

    @property
    def level(self) -> str:
        return self._lang_data()["stats"].get("level", "beginner")

    @level.setter
    def level(self, value: str):
        self._lang_data()["stats"]["level"] = value
        self.save()

    @property
    def response_format(self) -> str:
        return self.data["settings"].get("response_format", "auto")

    @response_format.setter
    def response_format(self, value: str):
        self.data["settings"]["response_format"] = value
        self.save()

    # ------------------------------------------------------------------
    # Custom instructions & bot observations
    # ------------------------------------------------------------------

    MAX_INSTRUCTIONS = 20
    MAX_OBSERVATIONS = 10

    def add_instruction(self, text: str, source: str = "user"):
        """Add a custom instruction (user preference or meta-feedback). Per-language."""
        ld = self._lang_data()
        instructions = ld.get("custom_instructions", [])
        for inst in instructions:
            if inst["text"].lower() == text.lower():
                return
        instructions.append({
            "text": text,
            "added": date.today().isoformat(),
            "source": source,
        })
        if len(instructions) > self.MAX_INSTRUCTIONS:
            instructions = instructions[-self.MAX_INSTRUCTIONS:]
        ld["custom_instructions"] = instructions
        self.save()

    def remove_instruction(self, index: int) -> bool:
        """Remove an instruction by index. Returns True if removed. Per-language."""
        ld = self._lang_data()
        instructions = ld.get("custom_instructions", [])
        if 0 <= index < len(instructions):
            instructions.pop(index)
            ld["custom_instructions"] = instructions
            self.save()
            return True
        return False

    def clear_instructions(self):
        """Remove all custom instructions and bot observations for current language."""
        ld = self._lang_data()
        ld["custom_instructions"] = []
        ld["bot_observations"] = []
        self.save()

    def get_instructions(self) -> list:
        return self._lang_data().get("custom_instructions", [])

    def add_observation(self, text: str):
        """Bot adds its own teaching observation. Per-language."""
        ld = self._lang_data()
        observations = ld.get("bot_observations", [])
        for obs in observations:
            if obs["text"].lower() == text.lower():
                return
        observations.append({
            "text": text,
            "added": date.today().isoformat(),
        })
        if len(observations) > self.MAX_OBSERVATIONS:
            observations = observations[-self.MAX_OBSERVATIONS:]
        ld["bot_observations"] = observations
        self.save()

    def get_observations(self) -> list:
        return self._lang_data().get("bot_observations", [])

    # ------------------------------------------------------------------
    # Conversation history
    # ------------------------------------------------------------------

    def add_message(
        self,
        user_message: str,
        bot_response: str,
        corrections: str = "",
        lang: str = "en",
        mode: str = "tutor",
    ):
        ld = self._lang_data(lang)
        entry = {
            "timestamp": datetime.now().isoformat(),
            "user": user_message,
            "bot": bot_response,
            "corrections": corrections,
            "lang": lang,
            "mode": mode,
        }
        ld["conversation_history"].append(entry)

        if len(ld["conversation_history"]) > self.HISTORY_CAP:
            overflow = ld["conversation_history"][:-self.HISTORY_CAP]
            ld["conversation_history"] = ld["conversation_history"][-self.HISTORY_CAP:]
            self._append_archive(overflow, lang)

        ld["stats"]["total_messages"] += 1
        ld["stats"]["messages_since_last_review"] += 1
        self._update_streak(lang)
        self.save()

    def clear_conversation_history(self):
        """Clear conversation history for current language only (stats/plan preserved)."""
        self._lang_data()["conversation_history"] = []
        self.save()

    def get_conversation_context(self, last_n: Optional[int] = None) -> List[Dict]:
        """Return last N exchanges for current language."""
        n = last_n or self.CONTEXT_WINDOW
        history = self._lang_data()["conversation_history"][-n:]
        messages = []
        for msg in history:
            messages.append({"role": "user", "content": msg["user"]})
            # Include corrections in context so GPT sees what was already corrected
            bot_text = msg["bot"]
            corrections = msg.get("corrections", "")
            if corrections:
                bot_text += f"\n[Corrections already given: {corrections}]"
            messages.append({"role": "assistant", "content": bot_text})
        return messages

    def _append_archive(self, entries: list, lang: str):
        for e in entries:
            e["_lang"] = lang
        archive = []
        if self.archive_path.exists():
            with open(self.archive_path, "r", encoding="utf-8") as f:
                archive = json.load(f)
        archive.extend(entries)
        with open(self.archive_path, "w", encoding="utf-8") as f:
            json.dump(archive, f, ensure_ascii=False, indent=2)

    def _update_streak(self, lang: str):
        today = date.today().isoformat()
        ld = self._lang_data(lang)
        last = ld["stats"].get("last_practice_date")
        if last == today:
            return
        yesterday = (date.today().replace(day=date.today().day - 1) if date.today().day > 1 else None)
        if yesterday and last == str(yesterday):
            ld["stats"]["streak_days"] = ld["stats"].get("streak_days", 0) + 1
        elif last != today:
            ld["stats"]["streak_days"] = 1
        ld["stats"]["last_practice_date"] = today

    # ------------------------------------------------------------------
    # Detailed mistake tracking
    # ------------------------------------------------------------------

    def track_detailed_mistake(self, mistake_type: str, specific: str, example: str = ""):
        """Track a specific mistake. Per-language."""
        today = date.today().isoformat()
        ld = self._lang_data()
        mistakes = ld.get("detailed_mistakes", [])

        # Try to find existing
        for m in mistakes:
            if m["type"] == mistake_type and m["specific"].lower() == specific.lower():
                m["times_seen"] += 1
                m["last_seen"] = today
                m["status"] = "recurring" if m["times_seen"] > 2 else m["status"]
                if example:
                    m["example"] = example
                self.save()
                return

        # New mistake
        new_id = f"m_{len(mistakes):03d}"
        mistakes.append({
            "id": new_id,
            "type": mistake_type,
            "specific": specific,
            "example": example,
            "times_seen": 1,
            "first_seen": today,
            "last_seen": today,
            "status": "new",
        })
        ld["detailed_mistakes"] = mistakes
        self.save()

    def track_mistake_legacy(self, mistake_type: str):
        """Backward-compatible: just increment category counter."""
        self.track_detailed_mistake(mistake_type, mistake_type)

    def get_top_mistakes(self, n: int = 5) -> List[dict]:
        """Return top N most frequent detailed mistakes for current language."""
        mistakes = self._lang_data().get("detailed_mistakes", [])
        active = [m for m in mistakes if m["status"] != "resolved"]
        return sorted(active, key=lambda m: m["times_seen"], reverse=True)[:n]

    def get_recurring_mistakes(self) -> List[dict]:
        """Return only mistakes marked as recurring. Per-language."""
        return [m for m in self._lang_data().get("detailed_mistakes", []) if m["status"] == "recurring"]

    # ------------------------------------------------------------------
    # Skills
    # ------------------------------------------------------------------

    def update_skill(self, skill_key: str, score: float, trend: str = ""):
        """Update a skill score (0.0 to 1.0). Per-language."""
        today = date.today().isoformat()
        ld = self._lang_data()
        skills = ld.get("skills", {})
        old = skills.get(skill_key, {})
        old_score = old.get("score", 0.5)

        if not trend:
            if score > old_score + 0.05:
                trend = "improving"
            elif score < old_score - 0.05:
                trend = "declining"
            else:
                trend = "stable"

        skills[skill_key] = {
            "score": round(max(0.0, min(1.0, score)), 2),
            "trend": trend,
            "last_tested": today,
        }
        ld["skills"] = skills
        self.save()

    def get_weak_skills(self, threshold: float = 0.5) -> List[Tuple[str, dict]]:
        """Return skills below threshold for current language."""
        skills = self._lang_data().get("skills", {})
        weak = [(k, v) for k, v in skills.items() if v["score"] < threshold]
        return sorted(weak, key=lambda x: x[1]["score"])

    def get_strong_skills(self, threshold: float = 0.7) -> List[Tuple[str, dict]]:
        """Return skills above threshold for current language."""
        skills = self._lang_data().get("skills", {})
        return [(k, v) for k, v in skills.items() if v["score"] >= threshold]

    # ------------------------------------------------------------------
    # Progress snapshots
    # ------------------------------------------------------------------

    def add_progress_snapshot(
        self,
        level_estimate: str,
        strengths: List[str],
        weaknesses: List[str],
        notes: str = "",
    ):
        ld = self._lang_data()
        ld["progress_snapshots"].append({
            "date": date.today().isoformat(),
            "level_estimate": level_estimate,
            "strengths": strengths,
            "weaknesses": weaknesses,
            "notes": notes,
        })
        ld["stats"]["level"] = level_estimate
        ld["stats"]["messages_since_last_review"] = 0
        self.save()

    def get_last_snapshot(self) -> Optional[dict]:
        snaps = self._lang_data().get("progress_snapshots", [])
        return snaps[-1] if snaps else None

    def needs_review(self) -> bool:
        """True if enough messages passed since last review (current language)."""
        return self._lang_data()["stats"].get("messages_since_last_review", 0) >= self.REVIEW_INTERVAL

    # ------------------------------------------------------------------
    # Learning plan
    # ------------------------------------------------------------------

    def update_plan(self, **kwargs):
        """Update learning plan for current language."""
        ld = self._lang_data()
        plan = ld.get("learning_plan", {})
        for k, v in kwargs.items():
            plan[k] = v
        plan["updated_at"] = datetime.now().isoformat()
        ld["learning_plan"] = plan
        self.save()

    def get_todays_topic(self) -> Optional[str]:
        """If a weekly plan exists for current language, return today's planned topic."""
        plan = self._lang_data().get("learning_plan", {})
        weekly = plan.get("weekly_plan")
        if not weekly or not isinstance(weekly, dict):
            return None
        schedule = weekly.get("schedule", {})
        today_name = date.today().strftime("%A").lower()
        day_plan = schedule.get(today_name)
        if day_plan and not day_plan.get("completed"):
            return day_plan.get("topic")
        return None

    def mark_today_completed(self):
        """Mark today's scheduled topic as done for current language."""
        ld = self._lang_data()
        plan = ld.get("learning_plan", {})
        weekly = plan.get("weekly_plan")
        if not weekly:
            return
        schedule = weekly.get("schedule", {})
        today_name = date.today().strftime("%A").lower()
        if today_name in schedule:
            schedule[today_name]["completed"] = True
            plan["weekly_plan"]["schedule"] = schedule
            ld["learning_plan"] = plan
            self.save()

    # ------------------------------------------------------------------
    # Sessions (stored in separate file; each record has "lang")
    # ------------------------------------------------------------------

    def save_session(self, session_data: dict):
        """Append a completed session record. Increment total_sessions for that lang."""
        sessions = []
        if self.sessions_path.exists():
            with open(self.sessions_path, "r", encoding="utf-8") as f:
                sessions = json.load(f)
        sessions.append(session_data)
        with open(self.sessions_path, "w", encoding="utf-8") as f:
            json.dump(sessions, f, ensure_ascii=False, indent=2)
        lang = session_data.get("lang", self.lang)
        self._lang_data(lang)["stats"]["total_sessions"] += 1
        self.save()

    def get_recent_sessions(self, n: int = 5, lang: Optional[str] = None) -> list:
        """Recent sessions, optionally filtered by language."""
        if not self.sessions_path.exists():
            return []
        with open(self.sessions_path, "r", encoding="utf-8") as f:
            sessions = json.load(f)
        lang = lang or self.lang
        filtered = [s for s in sessions if s.get("lang") == lang]
        return filtered[-n:]

    # ------------------------------------------------------------------
    # Context builder for GPT (the key method)
    # ------------------------------------------------------------------

    def build_teacher_context(self) -> str:
        """Build a compact text block for current language (separate progress per lang)."""
        parts = []
        ld = self._lang_data()
        name = self.display_name or f"User {self.user_id}"
        stats = ld["stats"]
        parts.append(f"STUDENT: {name}")
        parts.append(f"Level: {stats.get('level', 'unknown')} | "
                      f"Messages: {stats.get('total_messages', 0)} | "
                      f"Sessions: {stats.get('total_sessions', 0)} | "
                      f"Streak: {stats.get('streak_days', 0)} days")

        # Top recurring mistakes (for awareness, NOT re-correction)
        top = self.get_top_mistakes(5)
        if top:
            parts.append("\nKNOWN WEAK AREAS (do NOT re-correct unless student repeats the mistake in current message):")
            for m in top:
                parts.append(f"  - [{m['type']}] {m['specific']} "
                              f"(seen {m['times_seen']}x, {m['status']})")

        # Strong / weak skills
        strong = self.get_strong_skills()
        weak = self.get_weak_skills()
        if strong:
            skills_str = ", ".join(f"{k} ({v['score']})" for k, v in strong[:5])
            parts.append(f"\nSTRONG: {skills_str}")
        if weak:
            skills_str = ", ".join(f"{k} ({v['score']})" for k, v in weak[:5])
            parts.append(f"WEAK: {skills_str}")

        # Last progress snapshot
        snap = self.get_last_snapshot()
        if snap:
            parts.append(f"\nLAST ASSESSMENT ({snap['date']}): {snap['level_estimate']}")
            if snap.get("notes"):
                parts.append(f"  Notes: {snap['notes'][:200]}")

        # Learning plan (current language)
        plan = ld.get("learning_plan", {})
        if plan.get("global_goal"):
            parts.append(f"\nGOAL: {plan['global_goal']}")
        if plan.get("current_focus"):
            parts.append(f"CURRENT FOCUS: {plan['current_focus']}")

        today_topic = self.get_todays_topic()
        if today_topic:
            parts.append(f"TODAY'S PLANNED TOPIC: {today_topic}")

        # Last session summary (current language)
        recent = self.get_recent_sessions(1, lang=self.lang)
        if recent:
            last = recent[-1]
            summary = last.get("summary", "")
            if summary:
                parts.append(f"\nLAST SESSION: {summary[:300]}")

        # Custom instructions (user preferences — MUST follow)
        instructions = self.get_instructions()
        if instructions:
            parts.append("\nCUSTOM INSTRUCTIONS (follow these preferences):")
            for inst in instructions:
                parts.append(f"  - {inst['text']}")

        # Bot observations (AI's own notes — use for context)
        observations = self.get_observations()
        if observations:
            parts.append("\nBOT OBSERVATIONS (your own notes about this student):")
            for obs in observations:
                parts.append(f"  - {obs['text']}")

        # Mode
        mode = self.session_mode
        parts.append(f"\nMODE: {mode}")
        if mode == "free_chat":
            parts.append("  -> Conversation only. Do NOT give corrections or analysis.")

        return "\n".join(parts)

    # ------------------------------------------------------------------
    # Stats (backward compatible)
    # ------------------------------------------------------------------

    def get_stats(self) -> dict:
        s = self._lang_data()["stats"]
        return {
            "total_messages": s.get("total_messages", 0),
            "total_sessions": s.get("total_sessions", 0),
            "level": s.get("level", "unknown"),
            "streak_days": s.get("streak_days", 0),
            "last_practice_date": s.get("last_practice_date"),
            "top_mistakes": self.get_top_mistakes(5),
            "weak_skills": self.get_weak_skills(),
            "strong_skills": self.get_strong_skills(),
            "member_since": self.data.get("created_at", "unknown"),
        }
