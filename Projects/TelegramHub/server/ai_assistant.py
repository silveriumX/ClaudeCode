"""
TelegramHub AI Assistant Module
Provides AI-powered chat analysis, reply suggestions, and summarization.
Supports OpenAI and Anthropic Claude APIs.
"""
import json
import logging
from datetime import datetime
from typing import Optional
from pathlib import Path

try:
    import openai
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False

try:
    import anthropic
    ANTHROPIC_AVAILABLE = True
except ImportError:
    ANTHROPIC_AVAILABLE = False

from config import (
    AI_PROVIDER,
    AI_API_KEY,
    AI_MODEL,
    AI_CUSTOM_INSTRUCTIONS,
    DRAFTS_DIR
)

logger = logging.getLogger("TelegramHub.AI")


class AIAssistant:
    """AI-powered assistant for chat analysis and reply generation"""

    def __init__(self):
        self.provider = AI_PROVIDER
        self.model = AI_MODEL
        self.client = None

        self._init_client()

    def _init_client(self):
        """Initialize the AI client based on provider"""
        if not AI_API_KEY:
            logger.warning("AI_API_KEY not set. AI features will be disabled.")
            return

        if self.provider == "openai" and OPENAI_AVAILABLE:
            self.client = openai.OpenAI(api_key=AI_API_KEY, timeout=60.0)
            logger.info(f"OpenAI client initialized with model: {self.model}")
        elif self.provider == "anthropic" and ANTHROPIC_AVAILABLE:
            self.client = anthropic.Anthropic(api_key=AI_API_KEY, timeout=60.0)
            logger.info(f"Anthropic client initialized with model: {self.model}")
        else:
            logger.warning(f"Provider {self.provider} not available or not supported")

    @property
    def is_available(self) -> bool:
        """Check if AI is configured and available"""
        return self.client is not None

    def _format_messages_for_context(self, messages: list[dict]) -> str:
        """Format chat messages into a readable context string"""
        formatted = []
        for msg in messages[-50:]:  # Last 50 messages max
            date = msg.get("date", "")[:16].replace("T", " ")
            sender = "Я" if msg.get("is_outgoing") else "Собеседник"
            text = msg.get("text", "[медиа/файл]") or "[медиа/файл]"
            formatted.append(f"[{date}] {sender}: {text}")
        return "\n".join(formatted)

    async def _call_openai(self, system_prompt: str, user_prompt: str) -> str:
        """Make a call to OpenAI API"""
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.7,
                max_tokens=2000
            )
            return response.choices[0].message.content
        except Exception as e:
            logger.error(f"OpenAI API error: {e}")
            raise

    async def _call_anthropic(self, system_prompt: str, user_prompt: str) -> str:
        """Make a call to Anthropic Claude API"""
        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=2000,
                system=system_prompt,
                messages=[
                    {"role": "user", "content": user_prompt}
                ]
            )
            return response.content[0].text
        except Exception as e:
            logger.error(f"Anthropic API error: {e}")
            raise

    async def _call_ai(self, system_prompt: str, user_prompt: str) -> str:
        """Universal AI call method"""
        if not self.is_available:
            raise ValueError("AI is not configured")

        if self.provider == "openai":
            return await self._call_openai(system_prompt, user_prompt)
        elif self.provider == "anthropic":
            return await self._call_anthropic(system_prompt, user_prompt)
        else:
            raise ValueError(f"Unknown provider: {self.provider}")

    async def analyze_chat(self, messages: list[dict], chat_info: dict = None) -> dict:
        """
        Analyze a chat conversation and provide insights.

        Returns:
        {
            "summary": "Brief summary of the conversation",
            "topics": ["topic1", "topic2"],
            "sentiment": "positive/neutral/negative",
            "action_items": ["action1", "action2"],
            "urgency": "high/medium/low",
            "needs_reply": true/false
        }
        """
        if not self.is_available:
            return {"error": "AI not configured", "needs_reply": False}

        context = self._format_messages_for_context(messages)
        chat_name = chat_info.get("name", "Unknown") if chat_info else "Unknown"
        chat_type = chat_info.get("type", "chat") if chat_info else "chat"

        system_prompt = """Ты помощник для анализа переписок в Telegram.
Анализируй диалоги и предоставляй структурированную информацию.
Отвечай ТОЛЬКО валидным JSON без markdown форматирования."""

        user_prompt = f"""Проанализируй этот диалог с "{chat_name}" (тип: {chat_type}):

{context}

Верни JSON в формате:
{{
    "summary": "Краткое описание диалога (1-2 предложения)",
    "topics": ["список основных тем"],
    "sentiment": "positive/neutral/negative",
    "action_items": ["что нужно сделать"],
    "urgency": "high/medium/low",
    "needs_reply": true/false,
    "last_question": "последний вопрос собеседника, если есть, иначе null"
}}"""

        try:
            response = await self._call_ai(system_prompt, user_prompt)
            # Clean response if it has markdown
            response = response.strip()
            if response.startswith("```"):
                response = response.split("\n", 1)[1]
                response = response.rsplit("```", 1)[0]

            result = json.loads(response)
            return result
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse AI response as JSON: {e}")
            return {
                "summary": "Не удалось проанализировать",
                "topics": [],
                "sentiment": "neutral",
                "action_items": [],
                "urgency": "low",
                "needs_reply": False,
                "error": str(e)
            }
        except Exception as e:
            logger.error(f"AI analysis failed: {e}")
            return {"error": str(e), "needs_reply": False}

    async def suggest_replies(
        self,
        messages: list[dict],
        chat_info: dict = None,
        context: str = None,
        num_suggestions: int = 3
    ) -> list[dict]:
        """
        Generate reply suggestions based on conversation context.

        Returns list of suggestions:
        [
            {"text": "Suggested reply 1", "tone": "formal"},
            {"text": "Suggested reply 2", "tone": "casual"},
            {"text": "Suggested reply 3", "tone": "brief"}
        ]
        """
        if not self.is_available:
            return [{"text": "AI не настроен", "tone": "error"}]

        msg_context = self._format_messages_for_context(messages)
        chat_name = chat_info.get("name", "Unknown") if chat_info else "Unknown"

        system_prompt = f"""Ты помощник для написания ответов в Telegram.
Генерируй естественные, уместные ответы на основе контекста переписки.
Учитывай тон и стиль предыдущих сообщений.

ВАЖНЫЕ ПРАВИЛА:
{AI_CUSTOM_INSTRUCTIONS}

Отвечай ТОЛЬКО валидным JSON без markdown форматирования."""

        additional_context = f"\nДополнительный контекст: {context}" if context else ""

        user_prompt = f"""Переписка с "{chat_name}":

{msg_context}
{additional_context}

Предложи {num_suggestions} варианта ответа с разным тоном (формальный, дружеский, краткий).
Верни JSON массив:
[
    {{"text": "текст ответа 1", "tone": "formal"}},
    {{"text": "текст ответа 2", "tone": "casual"}},
    {{"text": "текст ответа 3", "tone": "brief"}}
]

Если контекст не требует ответа, верни пустой массив []."""

        try:
            response = await self._call_ai(system_prompt, user_prompt)
            response = response.strip()
            if response.startswith("```"):
                response = response.split("\n", 1)[1]
                response = response.rsplit("```", 1)[0]

            suggestions = json.loads(response)
            return suggestions if isinstance(suggestions, list) else []
        except Exception as e:
            logger.error(f"AI suggestion failed: {e}")
            return [{"text": f"Ошибка: {e}", "tone": "error"}]

    async def summarize_conversation(self, messages: list[dict], chat_info: dict = None) -> str:
        """
        Create a brief summary of the conversation.
        """
        if not self.is_available:
            return "AI не настроен"

        context = self._format_messages_for_context(messages)
        chat_name = chat_info.get("name", "Unknown") if chat_info else "Unknown"

        system_prompt = """Ты помощник для анализа переписок.
Создавай краткие, информативные саммари диалогов на русском языке."""

        user_prompt = f"""Создай краткое саммари (2-3 предложения) этого диалога с "{chat_name}":

{context}

Саммари должно отвечать на вопросы:
1. О чём диалог?
2. Какой текущий статус?
3. Нужны ли действия?"""

        try:
            return await self._call_ai(system_prompt, user_prompt)
        except Exception as e:
            logger.error(f"AI summarization failed: {e}")
            return f"Не удалось создать саммари: {e}"

    async def generate_quick_reply(self, last_message: str, tone: str = "casual") -> str:
        """
        Generate a quick single reply to the last message.
        """
        if not self.is_available:
            return ""

        tone_instructions = {
            "formal": "формальный, деловой тон",
            "casual": "дружеский, неформальный тон",
            "brief": "максимально краткий ответ",
            "detailed": "подробный, развёрнутый ответ"
        }

        system_prompt = f"""Ты помощник для быстрых ответов в мессенджере.
Используй {tone_instructions.get(tone, 'нейтральный тон')}.
Отвечай коротко и по делу.

ВАЖНЫЕ ПРАВИЛА СТИЛЯ:
{AI_CUSTOM_INSTRUCTIONS}"""

        user_prompt = f"""Напиши ответ на это сообщение:
"{last_message}"

Только текст ответа, без пояснений."""

        try:
            return await self._call_ai(system_prompt, user_prompt)
        except Exception as e:
            logger.error(f"AI quick reply failed: {e}")
            return ""


class DraftsManager:
    """Manages draft messages for later sending"""

    def __init__(self):
        self.drafts_file = DRAFTS_DIR / "outbox.json"
        self.drafts: dict[str, dict] = {}
        self._load_drafts()

    def _load_drafts(self):
        """Load drafts from file"""
        if self.drafts_file.exists():
            try:
                with open(self.drafts_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if isinstance(data, list):
                        self.drafts = {d["id"]: d for d in data if "id" in d}
                    else:
                        self.drafts = data
            except Exception as e:
                logger.error(f"Failed to load drafts: {e}")
                self.drafts = {}

    def _save_drafts(self):
        """Save drafts to file"""
        try:
            with open(self.drafts_file, "w", encoding="utf-8") as f:
                json.dump(list(self.drafts.values()), f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"Failed to save drafts: {e}")

    def create_draft(
        self,
        account: str,
        chat_id: int,
        chat_name: str,
        text: str,
        suggested_by: str = "user"
    ) -> dict:
        """Create a new draft message"""
        draft_id = f"draft_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{chat_id}"

        draft = {
            "id": draft_id,
            "account": account,
            "chat_id": chat_id,
            "chat_name": chat_name,
            "text": text,
            "suggested_by": suggested_by,
            "created_at": datetime.now().isoformat(),
            "status": "pending"
        }

        self.drafts[draft_id] = draft
        self._save_drafts()
        logger.info(f"Draft created: {draft_id}")
        return draft

    def get_draft(self, draft_id: str) -> Optional[dict]:
        """Get a draft by ID"""
        return self.drafts.get(draft_id)

    def get_all_drafts(self, status: str = None) -> list[dict]:
        """Get all drafts, optionally filtered by status"""
        drafts = list(self.drafts.values())
        if status:
            drafts = [d for d in drafts if d.get("status") == status]
        return sorted(drafts, key=lambda x: x.get("created_at", ""), reverse=True)

    def get_drafts_for_chat(self, account: str, chat_id: int) -> list[dict]:
        """Get all drafts for a specific chat"""
        return [
            d for d in self.drafts.values()
            if d.get("account") == account and d.get("chat_id") == chat_id
        ]

    def update_draft(self, draft_id: str, text: str = None, status: str = None) -> Optional[dict]:
        """Update a draft"""
        if draft_id not in self.drafts:
            return None

        if text is not None:
            self.drafts[draft_id]["text"] = text
        if status is not None:
            self.drafts[draft_id]["status"] = status

        self.drafts[draft_id]["updated_at"] = datetime.now().isoformat()
        self._save_drafts()
        return self.drafts[draft_id]

    def delete_draft(self, draft_id: str) -> bool:
        """Delete a draft"""
        if draft_id in self.drafts:
            del self.drafts[draft_id]
            self._save_drafts()
            logger.info(f"Draft deleted: {draft_id}")
            return True
        return False

    def mark_sent(self, draft_id: str) -> Optional[dict]:
        """Mark a draft as sent"""
        return self.update_draft(draft_id, status="sent")


# Global instances
ai_assistant = AIAssistant()
drafts_manager = DraftsManager()
