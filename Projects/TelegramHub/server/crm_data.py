"""
CRM Data Manager - управление тегами, заметками, статусами чатов
"""
import json
from pathlib import Path
from datetime import datetime

DATA_DIR = Path(__file__).parent.parent / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)

CRM_FILE = DATA_DIR / "crm_chats.json"
TEMPLATES_FILE = DATA_DIR / "templates.json"

# Default tags
DEFAULT_TAGS = [
    {"id": "important", "name": "Important", "color": "#f44336"},
    {"id": "client", "name": "Client", "color": "#4caf50"},
    {"id": "supplier", "name": "Supplier", "color": "#2196f3"},
    {"id": "partner", "name": "Partner", "color": "#9c27b0"},
    {"id": "spam", "name": "Spam", "color": "#757575"},
    {"id": "todo", "name": "To Do", "color": "#ff9800"},
]

# Default templates
DEFAULT_TEMPLATES = [
    {"id": "1", "name": "Hello", "text": "Hello! How can I help you?"},
    {"id": "2", "name": "Thanks", "text": "Thank you for reaching out!"},
    {"id": "3", "name": "Wait", "text": "Please wait, I'll check and get back to you."},
    {"id": "4", "name": "Done", "text": "Done! Let me know if you need anything else."},
]


class CRMData:
    def __init__(self):
        self.chats = {}  # "account:chat_id" -> {tags, notes, status, pinned}
        self.tags = DEFAULT_TAGS.copy()
        self.templates = DEFAULT_TEMPLATES.copy()
        self.load()

    def load(self):
        """Load CRM data from file"""
        if CRM_FILE.exists():
            try:
                with open(CRM_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.chats = data.get("chats", {})
                    self.tags = data.get("tags", DEFAULT_TAGS)
            except:
                pass

        if TEMPLATES_FILE.exists():
            try:
                with open(TEMPLATES_FILE, "r", encoding="utf-8") as f:
                    self.templates = json.load(f)
            except:
                pass

    def save(self):
        """Save CRM data to file"""
        with open(CRM_FILE, "w", encoding="utf-8") as f:
            json.dump({
                "chats": self.chats,
                "tags": self.tags
            }, f, ensure_ascii=False, indent=2)

        with open(TEMPLATES_FILE, "w", encoding="utf-8") as f:
            json.dump(self.templates, f, ensure_ascii=False, indent=2)

    def get_chat_key(self, account: str, chat_id: int) -> str:
        return f"{account}:{chat_id}"

    def get_chat_data(self, account: str, chat_id: int) -> dict:
        """Get CRM data for a chat"""
        key = self.get_chat_key(account, chat_id)
        return self.chats.get(key, {
            "tags": [],
            "notes": "",
            "status": "new",
            "pinned": False
        })

    def set_chat_tags(self, account: str, chat_id: int, tags: list):
        """Set tags for a chat"""
        key = self.get_chat_key(account, chat_id)
        if key not in self.chats:
            self.chats[key] = {"tags": [], "notes": "", "status": "new", "pinned": False}
        self.chats[key]["tags"] = tags
        self.save()

    def add_chat_tag(self, account: str, chat_id: int, tag_id: str):
        """Add a tag to a chat"""
        key = self.get_chat_key(account, chat_id)
        if key not in self.chats:
            self.chats[key] = {"tags": [], "notes": "", "status": "new", "pinned": False}
        if tag_id not in self.chats[key]["tags"]:
            self.chats[key]["tags"].append(tag_id)
        self.save()

    def remove_chat_tag(self, account: str, chat_id: int, tag_id: str):
        """Remove a tag from a chat"""
        key = self.get_chat_key(account, chat_id)
        if key in self.chats and tag_id in self.chats[key]["tags"]:
            self.chats[key]["tags"].remove(tag_id)
            self.save()

    def set_chat_notes(self, account: str, chat_id: int, notes: str):
        """Set notes for a chat"""
        key = self.get_chat_key(account, chat_id)
        if key not in self.chats:
            self.chats[key] = {"tags": [], "notes": "", "status": "new", "pinned": False}
        self.chats[key]["notes"] = notes
        self.save()

    def set_chat_status(self, account: str, chat_id: int, status: str):
        """Set status for a chat (new, active, pending, closed)"""
        key = self.get_chat_key(account, chat_id)
        if key not in self.chats:
            self.chats[key] = {"tags": [], "notes": "", "status": "new", "pinned": False}
        self.chats[key]["status"] = status
        self.save()

    def toggle_chat_pinned(self, account: str, chat_id: int) -> bool:
        """Toggle pinned status for a chat"""
        key = self.get_chat_key(account, chat_id)
        if key not in self.chats:
            self.chats[key] = {"tags": [], "notes": "", "status": "new", "pinned": False}
        self.chats[key]["pinned"] = not self.chats[key]["pinned"]
        self.save()
        return self.chats[key]["pinned"]

    # Tags management
    def get_tags(self) -> list:
        return self.tags

    def add_tag(self, tag_id: str, name: str, color: str = "#888888"):
        """Add a new tag"""
        if not any(t["id"] == tag_id for t in self.tags):
            self.tags.append({"id": tag_id, "name": name, "color": color})
            self.save()

    def remove_tag(self, tag_id: str):
        """Remove a tag"""
        self.tags = [t for t in self.tags if t["id"] != tag_id]
        # Remove from all chats
        for chat_data in self.chats.values():
            if tag_id in chat_data.get("tags", []):
                chat_data["tags"].remove(tag_id)
        self.save()

    # Templates management
    def get_templates(self) -> list:
        return self.templates

    def add_template(self, name: str, text: str) -> str:
        """Add a new template"""
        template_id = str(len(self.templates) + 1)
        self.templates.append({"id": template_id, "name": name, "text": text})
        self.save()
        return template_id

    def update_template(self, template_id: str, name: str, text: str):
        """Update a template"""
        for t in self.templates:
            if t["id"] == template_id:
                t["name"] = name
                t["text"] = text
                self.save()
                break

    def remove_template(self, template_id: str):
        """Remove a template"""
        self.templates = [t for t in self.templates if t["id"] != template_id]
        self.save()

    def enrich_dialogs(self, dialogs: list) -> list:
        """Add CRM data to dialogs list"""
        for d in dialogs:
            crm = self.get_chat_data(d["account"], d["id"])
            d["crm"] = crm

        # Sort: pinned first, then by date
        dialogs.sort(key=lambda x: (
            not x.get("crm", {}).get("pinned", False),
            x.get("last_message_date", "") or ""
        ), reverse=False)

        # Re-sort pinned to top, rest by date desc
        pinned = [d for d in dialogs if d.get("crm", {}).get("pinned")]
        unpinned = [d for d in dialogs if not d.get("crm", {}).get("pinned")]
        unpinned.sort(key=lambda x: x.get("last_message_date", "") or "", reverse=True)

        return pinned + unpinned


# Global instance
crm = CRMData()
