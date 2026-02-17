"""
Cursor AI Integration Module
Export chat context for AI analysis
"""
import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

CONTEXT_DIR = Path(__file__).parent.parent / "context"
EXPORTS_DIR = CONTEXT_DIR / "exports"
EXPORTS_DIR.mkdir(parents=True, exist_ok=True)


class CursorExporter:
    """Export chat data for Cursor AI analysis"""

    def __init__(self, manager):
        self.manager = manager

    async def export_chat_full(self, account: str, chat_id: int, limit: int = 200) -> str:
        """
        Export full chat history to markdown file.
        Returns path to exported file.
        """
        acc = self.manager.get_account(account)
        if not acc or not acc.connected:
            return None

        # Get messages
        messages = await acc.get_messages(chat_id, limit)
        messages.reverse()  # Oldest first

        # Get chat info
        dialogs = await acc.get_dialogs(limit=200)
        chat_info = next((d for d in dialogs if d["id"] == chat_id), {})
        chat_name = chat_info.get("name", f"chat_{chat_id}")

        # Build markdown
        md = f"""# Chat Export: {chat_name}

**Account:** {account}
**Chat ID:** {chat_id}
**Type:** {chat_info.get('type', 'unknown')}
**Exported:** {datetime.now().strftime('%Y-%m-%d %H:%M')}
**Messages:** {len(messages)}

---

## Conversation

"""
        for msg in messages:
            date = datetime.fromisoformat(msg["date"]).strftime("%Y-%m-%d %H:%M")
            sender = "ME" if msg["is_outgoing"] else "THEM"
            text = msg["text"] or "[media/file]"

            # Escape markdown in text
            text = text.replace("```", "\\`\\`\\`")

            md += f"""### [{date}] {sender}
{text}

"""

        # Save file
        safe_name = "".join(c if c.isalnum() or c in "._- " else "_" for c in chat_name)[:50]
        filename = f"{account}_{safe_name}_{datetime.now().strftime('%Y%m%d_%H%M')}.md"
        filepath = EXPORTS_DIR / filename

        with open(filepath, "w", encoding="utf-8") as f:
            f.write(md)

        return str(filepath)

    async def export_chat_structured(self, account: str, chat_id: int, limit: int = 200) -> str:
        """
        Export chat as structured JSON for detailed analysis.
        Includes metadata for pattern analysis.
        """
        acc = self.manager.get_account(account)
        if not acc or not acc.connected:
            return None

        messages = await acc.get_messages(chat_id, limit)
        messages.reverse()

        dialogs = await acc.get_dialogs(limit=200)
        chat_info = next((d for d in dialogs if d["id"] == chat_id), {})

        # Calculate statistics
        my_messages = [m for m in messages if m["is_outgoing"]]
        their_messages = [m for m in messages if not m["is_outgoing"]]

        # Response times (how long until I reply)
        response_times = []
        for i, msg in enumerate(messages[1:], 1):
            if msg["is_outgoing"] and not messages[i-1]["is_outgoing"]:
                prev_time = datetime.fromisoformat(messages[i-1]["date"])
                curr_time = datetime.fromisoformat(msg["date"])
                delta = (curr_time - prev_time).total_seconds()
                if delta < 86400:  # Within 24 hours
                    response_times.append(delta)

        avg_response = sum(response_times) / len(response_times) if response_times else 0

        # Message length stats
        my_avg_length = sum(len(m["text"] or "") for m in my_messages) / len(my_messages) if my_messages else 0
        their_avg_length = sum(len(m["text"] or "") for m in their_messages) / len(their_messages) if their_messages else 0

        # Activity by hour
        hours = {}
        for msg in messages:
            hour = datetime.fromisoformat(msg["date"]).hour
            hours[hour] = hours.get(hour, 0) + 1

        data = {
            "meta": {
                "account": account,
                "chat_id": chat_id,
                "chat_name": chat_info.get("name", "Unknown"),
                "chat_type": chat_info.get("type", "unknown"),
                "exported_at": datetime.now().isoformat(),
                "message_count": len(messages)
            },
            "statistics": {
                "my_messages": len(my_messages),
                "their_messages": len(their_messages),
                "avg_response_time_seconds": round(avg_response, 1),
                "my_avg_message_length": round(my_avg_length, 1),
                "their_avg_message_length": round(their_avg_length, 1),
                "activity_by_hour": hours
            },
            "messages": [
                {
                    "id": m["id"],
                    "date": m["date"],
                    "is_outgoing": m["is_outgoing"],
                    "text": m["text"],
                    "has_media": m["text"] is None,
                    "reply_to": m.get("reply_to")
                }
                for m in messages
            ]
        }

        safe_name = "".join(c if c.isalnum() or c in "._- " else "_" for c in chat_info.get("name", "chat"))[:50]
        filename = f"{account}_{safe_name}_{datetime.now().strftime('%Y%m%d_%H%M')}.json"
        filepath = EXPORTS_DIR / filename

        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        return str(filepath)

    async def export_multiple_chats(self, chats: list[dict], limit_per_chat: int = 100) -> str:
        """
        Export multiple chats into single analysis file.
        chats: [{"account": "acc1", "chat_id": 123}, ...]
        """
        all_data = {
            "meta": {
                "exported_at": datetime.now().isoformat(),
                "chat_count": len(chats),
                "description": "Multi-chat export for Cursor AI analysis"
            },
            "chats": []
        }

        for chat in chats:
            acc = self.manager.get_account(chat["account"])
            if not acc or not acc.connected:
                continue

            messages = await acc.get_messages(chat["chat_id"], limit_per_chat)
            messages.reverse()

            dialogs = await acc.get_dialogs(limit=200)
            chat_info = next((d for d in dialogs if d["id"] == chat["chat_id"]), {})

            all_data["chats"].append({
                "account": chat["account"],
                "chat_id": chat["chat_id"],
                "chat_name": chat_info.get("name", "Unknown"),
                "type": chat_info.get("type", "unknown"),
                "messages": [
                    {
                        "date": m["date"],
                        "is_outgoing": m["is_outgoing"],
                        "text": m["text"]
                    }
                    for m in messages
                ]
            })

        filename = f"multi_export_{datetime.now().strftime('%Y%m%d_%H%M')}.json"
        filepath = EXPORTS_DIR / filename

        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(all_data, f, ensure_ascii=False, indent=2)

        return str(filepath)

    async def export_by_tag(self, tag_id: str, limit_per_chat: int = 50) -> str:
        """
        Export all chats with specific tag.
        Great for analyzing all client conversations, supplier talks, etc.
        """
        from crm_data import crm

        # Find all chats with this tag
        tagged_chats = []
        for chat_key, chat_data in crm.chats.items():
            if tag_id in chat_data.get("tags", []):
                parts = chat_key.split(":")
                if len(parts) == 2:
                    tagged_chats.append({
                        "account": parts[0],
                        "chat_id": int(parts[1])
                    })

        if not tagged_chats:
            return None

        return await self.export_multiple_chats(tagged_chats, limit_per_chat)

    async def create_analysis_prompt(self, filepath: str) -> str:
        """
        Generate a prompt for Cursor to analyze exported data.
        """
        prompt = f"""# Chat Analysis Task

I have exported Telegram chat data to: `{filepath}`

Please analyze this data and provide insights on:

1. **Communication Patterns**
   - Who initiates conversations more often?
   - What's the typical response time?
   - Are there patterns in message timing?

2. **Content Analysis**
   - What are the main topics discussed?
   - Are there recurring problems or requests?
   - What's the overall tone (formal/informal)?

3. **Action Items**
   - Any unresolved questions?
   - Commitments made but not confirmed?
   - Follow-ups needed?

4. **Recommendations**
   - How to improve communication?
   - Common issues to address proactively?
   - Templates that would be useful?

Please read the file and provide detailed analysis.
"""

        # Save prompt
        prompt_file = EXPORTS_DIR / "analysis_prompt.md"
        with open(prompt_file, "w", encoding="utf-8") as f:
            f.write(prompt)

        return str(prompt_file)


# Singleton instance (initialized when imported with manager)
exporter: Optional[CursorExporter] = None


def init_exporter(manager):
    """Initialize exporter with telegram manager"""
    global exporter
    exporter = CursorExporter(manager)
    return exporter
