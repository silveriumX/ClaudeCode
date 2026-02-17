"""
TelegramHub Manager v2
Multi-account management with auto-reconnect, media support, and rate limiting
"""
import asyncio
import json
import logging
import base64
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional
from telethon import TelegramClient
from telethon.tl.types import User, Chat, Channel, Message, MessageMediaPhoto, MessageMediaDocument
from telethon.errors import FloodWaitError, SessionPasswordNeededError
from config import (
    SESSIONS_DIR,
    CONTEXT_DIR,
    DRAFTS_DIR,
    API_ID,
    API_HASH,
    MAX_MESSAGES_PER_CHAT
)


# Setup logging
LOG_DIR = Path(__file__).parent.parent / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler(LOG_DIR / "telegramhub.log", encoding="utf-8"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("TelegramHub")


# Rate limiting
class RateLimiter:
    """Prevents flood by limiting request rate"""

    def __init__(self, min_delay: float = 1.0):
        self.min_delay = min_delay
        self.last_request: dict[str, datetime] = {}

    async def wait(self, key: str = "default"):
        """Wait if needed to respect rate limit"""
        now = datetime.now()
        if key in self.last_request:
            elapsed = (now - self.last_request[key]).total_seconds()
            if elapsed < self.min_delay:
                await asyncio.sleep(self.min_delay - elapsed)
        self.last_request[key] = datetime.now()


rate_limiter = RateLimiter(min_delay=2.0)


class TelegramAccount:
    """Represents single Telegram account with auto-reconnect"""

    def __init__(self, session_path: Path):
        self.session_path = session_path
        self.name = session_path.stem
        self.client: Optional[TelegramClient] = None
        self.user_info: dict = {}
        self.connected = False
        self._reconnect_task: Optional[asyncio.Task] = None
        self._health_check_task: Optional[asyncio.Task] = None
        self._should_run = True
        self.last_error: Optional[str] = None
        self.stats = {
            "messages_sent": 0,
            "messages_received": 0,
            "reconnects": 0,
            "flood_waits": 0,
            "last_activity": None
        }

    async def connect(self) -> bool:
        """Connect to account"""
        try:
            self.client = TelegramClient(
                str(self.session_path.with_suffix("")),
                API_ID,
                API_HASH,
                device_model="TelegramHub CRM",
                system_version="Windows 10",
                app_version="2.0",
                lang_code="en",
                system_lang_code="en"
            )
            await self.client.connect()

            if await self.client.is_user_authorized():
                me = await self.client.get_me()
                self.user_info = {
                    "id": me.id,
                    "username": me.username,
                    "first_name": me.first_name,
                    "last_name": me.last_name,
                    "phone": me.phone
                }
                self.connected = True
                self.last_error = None
                logger.info(f"{self.name}: Connected as {me.first_name}")

                # Start health check
                self._should_run = True
                self._health_check_task = asyncio.create_task(self._health_check_loop())

                return True
            else:
                logger.warning(f"{self.name}: Not authorized")
                return False

        except Exception as e:
            self.last_error = str(e)
            logger.error(f"{self.name}: Connection error - {e}")
            return False

    async def disconnect(self):
        """Disconnect from account"""
        self._should_run = False
        if self._health_check_task:
            self._health_check_task.cancel()
        if self.client:
            await self.client.disconnect()
            self.connected = False
            logger.info(f"{self.name}: Disconnected")

    async def _health_check_loop(self):
        """Background task to check connection health"""
        while self._should_run:
            try:
                await asyncio.sleep(60)  # Check every 60 seconds
                if self.client and self.connected:
                    try:
                        await self.client.get_me()
                    except Exception as e:
                        logger.warning(f"{self.name}: Health check failed - {e}")
                        await self._try_reconnect()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"{self.name}: Health check error - {e}")

    async def _try_reconnect(self):
        """Attempt to reconnect"""
        if not self._should_run:
            return

        logger.info(f"{self.name}: Attempting reconnect...")
        self.connected = False
        self.stats["reconnects"] += 1

        for attempt in range(3):
            try:
                await asyncio.sleep(5 * (attempt + 1))  # Backoff
                if self.client:
                    await self.client.disconnect()
                if await self.connect():
                    logger.info(f"{self.name}: Reconnected successfully")
                    return
            except Exception as e:
                logger.error(f"{self.name}: Reconnect attempt {attempt + 1} failed - {e}")

        logger.error(f"{self.name}: All reconnect attempts failed")

    async def _handle_flood_wait(self, e: FloodWaitError):
        """Handle Telegram flood wait error"""
        wait_time = e.seconds
        self.stats["flood_waits"] += 1
        logger.warning(f"{self.name}: Flood wait for {wait_time} seconds")
        await asyncio.sleep(wait_time)

    async def get_dialogs(self, limit: int = 100) -> list[dict]:
        """Get dialogs list"""
        if not self.connected:
            return []

        dialogs = []
        try:
            async for dialog in self.client.iter_dialogs(limit=limit):
                entity = dialog.entity

                dialog_info = {
                    "id": dialog.id,
                    "name": dialog.name or "Unknown",
                    "unread_count": dialog.unread_count,
                    "last_message_date": dialog.date.isoformat() if dialog.date else None,
                    "type": self._get_entity_type(entity),
                    "account": self.name
                }

                if dialog.message:
                    has_media = dialog.message.media is not None
                    dialog_info["last_message"] = {
                        "text": dialog.message.text or ("[Media]" if has_media else ""),
                        "from_id": self._extract_peer_id(dialog.message.from_id),
                        "date": dialog.message.date.isoformat(),
                        "has_media": has_media
                    }

                dialogs.append(dialog_info)

        except FloodWaitError as e:
            await self._handle_flood_wait(e)
            return await self.get_dialogs(limit)
        except Exception as e:
            logger.error(f"{self.name}: Error getting dialogs - {e}")
            self.last_error = str(e)

        return dialogs

    async def get_messages(self, chat_id: int, limit: int = MAX_MESSAGES_PER_CHAT) -> list[dict]:
        """Get messages from chat with media info"""
        if not self.connected:
            return []

        messages = []
        try:
            async for msg in self.client.iter_messages(chat_id, limit=limit):
                media_info = self._get_media_info(msg)

                messages.append({
                    "id": msg.id,
                    "text": msg.text,
                    "date": msg.date.isoformat(),
                    "from_id": self._extract_peer_id(msg.from_id),
                    "reply_to": msg.reply_to_msg_id if msg.reply_to else None,
                    "is_outgoing": msg.out,
                    "has_media": media_info is not None,
                    "media": media_info
                })

            self.stats["last_activity"] = datetime.now().isoformat()

        except FloodWaitError as e:
            await self._handle_flood_wait(e)
            return await self.get_messages(chat_id, limit)
        except Exception as e:
            logger.error(f"{self.name}: Error getting messages - {e}")

        return messages

    def _get_media_info(self, msg: Message) -> Optional[dict]:
        """Extract media information from message"""
        if not msg.media:
            return None

        if isinstance(msg.media, MessageMediaPhoto):
            return {
                "type": "photo",
                "id": msg.media.photo.id if msg.media.photo else None
            }
        elif isinstance(msg.media, MessageMediaDocument):
            doc = msg.media.document
            if doc:
                attrs = {type(a).__name__: a for a in doc.attributes} if doc.attributes else {}
                filename = None
                if "DocumentAttributeFilename" in attrs:
                    filename = attrs["DocumentAttributeFilename"].file_name

                # Determine type
                mime = doc.mime_type or ""
                if "DocumentAttributeVideo" in attrs:
                    media_type = "video"
                elif "DocumentAttributeAudio" in attrs:
                    if attrs["DocumentAttributeAudio"].voice:
                        media_type = "voice"
                    else:
                        media_type = "audio"
                elif "DocumentAttributeSticker" in attrs:
                    media_type = "sticker"
                elif "DocumentAttributeAnimated" in attrs:
                    media_type = "gif"
                elif mime.startswith("image/"):
                    media_type = "image"
                else:
                    media_type = "document"

                return {
                    "type": media_type,
                    "id": doc.id,
                    "filename": filename,
                    "size": doc.size,
                    "mime_type": mime
                }

        return {"type": "other"}

    async def download_media(self, chat_id: int, message_id: int) -> Optional[dict]:
        """Download media from message and return as base64"""
        if not self.connected:
            return None

        try:
            msg = await self.client.get_messages(chat_id, ids=message_id)
            if not msg or not msg.media:
                return None

            # Download to bytes
            data = await self.client.download_media(msg, file=bytes)
            if data:
                return {
                    "data": base64.b64encode(data).decode("utf-8"),
                    "media_info": self._get_media_info(msg)
                }
        except Exception as e:
            logger.error(f"{self.name}: Error downloading media - {e}")

        return None

    async def send_message(self, chat_id: int, text: str, reply_to: int = None) -> dict:
        """Send text message with rate limiting"""
        if not self.connected:
            return {"success": False, "error": "Not connected"}

        await rate_limiter.wait(f"send_{self.name}")

        try:
            msg = await self.client.send_message(
                chat_id,
                text,
                reply_to=reply_to
            )
            self.stats["messages_sent"] += 1
            self.stats["last_activity"] = datetime.now().isoformat()
            logger.info(f"{self.name}: Message sent to {chat_id}")

            return {
                "success": True,
                "message_id": msg.id,
                "date": msg.date.isoformat()
            }
        except FloodWaitError as e:
            await self._handle_flood_wait(e)
            return await self.send_message(chat_id, text, reply_to)
        except Exception as e:
            logger.error(f"{self.name}: Error sending message - {e}")
            return {"success": False, "error": str(e)}

    async def send_file(self, chat_id: int, file_data: bytes, filename: str, caption: str = None) -> dict:
        """Send file/media with rate limiting"""
        if not self.connected:
            return {"success": False, "error": "Not connected"}

        await rate_limiter.wait(f"send_{self.name}")

        try:
            # Save temp file
            import tempfile
            import os

            ext = Path(filename).suffix
            with tempfile.NamedTemporaryFile(delete=False, suffix=ext) as f:
                f.write(file_data)
                temp_path = f.name

            try:
                msg = await self.client.send_file(
                    chat_id,
                    temp_path,
                    caption=caption,
                    force_document=not filename.lower().endswith(('.jpg', '.jpeg', '.png', '.gif'))
                )
                self.stats["messages_sent"] += 1
                logger.info(f"{self.name}: File sent to {chat_id}")

                return {
                    "success": True,
                    "message_id": msg.id,
                    "date": msg.date.isoformat()
                }
            finally:
                os.unlink(temp_path)

        except FloodWaitError as e:
            await self._handle_flood_wait(e)
            return await self.send_file(chat_id, file_data, filename, caption)
        except Exception as e:
            logger.error(f"{self.name}: Error sending file - {e}")
            return {"success": False, "error": str(e)}

    def _get_entity_type(self, entity) -> str:
        if isinstance(entity, User):
            return "user"
        elif isinstance(entity, Chat):
            return "chat"
        elif isinstance(entity, Channel):
            return "channel" if entity.broadcast else "supergroup"
        return "unknown"

    def _extract_peer_id(self, peer) -> int | None:
        """Extract ID from Peer objects"""
        if peer is None:
            return None
        if hasattr(peer, "user_id"):
            return peer.user_id
        if hasattr(peer, "channel_id"):
            return peer.channel_id
        if hasattr(peer, "chat_id"):
            return peer.chat_id
        return None


class TelegramManager:
    """Manages all Telegram accounts"""

    def __init__(self):
        self.accounts: dict[str, TelegramAccount] = {}
        self._broadcast_in_progress = False
        self._broadcast_cancel = False

    async def load_accounts(self) -> int:
        """Load all accounts from sessions folder"""
        loaded = 0

        for session_file in SESSIONS_DIR.glob("*.session"):
            account = TelegramAccount(session_file)
            if await account.connect():
                self.accounts[account.name] = account
                loaded += 1
            else:
                logger.warning(f"{account.name}: Failed to connect")

        return loaded

    async def disconnect_all(self):
        """Disconnect all accounts"""
        for account in self.accounts.values():
            await account.disconnect()

    def get_account(self, name: str) -> Optional[TelegramAccount]:
        """Get account by name"""
        return self.accounts.get(name)

    def get_accounts_status(self) -> list[dict]:
        """Get status of all accounts"""
        return [
            {
                "name": acc.name,
                "connected": acc.connected,
                "user_info": acc.user_info,
                "last_error": acc.last_error,
                "stats": acc.stats
            }
            for acc in self.accounts.values()
        ]

    async def get_all_dialogs(self) -> list[dict]:
        """Get dialogs from all accounts"""
        all_dialogs = []

        for account in self.accounts.values():
            if account.connected:
                dialogs = await account.get_dialogs()
                all_dialogs.extend(dialogs)

        # Sort by last message date
        all_dialogs.sort(
            key=lambda x: x.get("last_message_date", "") or "",
            reverse=True
        )

        return all_dialogs

    async def broadcast_message(
        self,
        targets: list[dict],
        text: str,
        delay: float = 3.0,
        progress_callback=None
    ) -> dict:
        """
        Send message to multiple chats with delay.
        targets: [{"account": "acc1", "chat_id": 123}, ...]
        """
        if self._broadcast_in_progress:
            return {"success": False, "error": "Broadcast already in progress"}

        self._broadcast_in_progress = True
        self._broadcast_cancel = False

        results = {
            "total": len(targets),
            "sent": 0,
            "failed": 0,
            "errors": []
        }

        try:
            for i, target in enumerate(targets):
                if self._broadcast_cancel:
                    results["cancelled"] = True
                    break

                account = self.get_account(target["account"])
                if not account or not account.connected:
                    results["failed"] += 1
                    results["errors"].append({
                        "target": target,
                        "error": "Account not connected"
                    })
                    continue

                result = await account.send_message(target["chat_id"], text)

                if result["success"]:
                    results["sent"] += 1
                else:
                    results["failed"] += 1
                    results["errors"].append({
                        "target": target,
                        "error": result.get("error")
                    })

                if progress_callback:
                    await progress_callback(i + 1, len(targets), result)

                # Delay between messages
                if i < len(targets) - 1:
                    await asyncio.sleep(delay)

        finally:
            self._broadcast_in_progress = False

        logger.info(f"Broadcast completed: {results['sent']}/{results['total']} sent")
        return results

    def cancel_broadcast(self):
        """Cancel ongoing broadcast"""
        self._broadcast_cancel = True

    def get_statistics(self) -> dict:
        """Get aggregated statistics"""
        total_sent = sum(acc.stats["messages_sent"] for acc in self.accounts.values())
        total_reconnects = sum(acc.stats["reconnects"] for acc in self.accounts.values())
        total_flood_waits = sum(acc.stats["flood_waits"] for acc in self.accounts.values())

        return {
            "accounts_total": len(self.accounts),
            "accounts_connected": sum(1 for acc in self.accounts.values() if acc.connected),
            "messages_sent_total": total_sent,
            "reconnects_total": total_reconnects,
            "flood_waits_total": total_flood_waits,
            "accounts": self.get_accounts_status()
        }

    async def sync_to_files(self):
        """Sync data to files for Cursor"""
        logger.info("Syncing context...")

        all_dialogs = await self.get_all_dialogs()

        # Save active chats
        active_chats_path = CONTEXT_DIR / "active_chats" / "all_chats.json"
        with open(active_chats_path, "w", encoding="utf-8") as f:
            json.dump(all_dialogs, f, ensure_ascii=False, indent=2)

        # Create markdown summary
        summary_path = CONTEXT_DIR / "summaries" / "dialogs_summary.md"
        await self._create_summary(all_dialogs, summary_path)

        # Pending replies
        pending = [d for d in all_dialogs if d.get("unread_count", 0) > 0]
        pending_path = CONTEXT_DIR / "pending_replies" / "unread.json"
        with open(pending_path, "w", encoding="utf-8") as f:
            json.dump(pending, f, ensure_ascii=False, indent=2)

        pending_md_path = CONTEXT_DIR / "pending_replies" / "unread.md"
        await self._create_pending_md(pending, pending_md_path)

        logger.info(f"Synced {len(all_dialogs)} dialogs, {len(pending)} pending")

    async def _create_summary(self, dialogs: list[dict], path: Path):
        """Create markdown summary"""
        content = f"""# Telegram Dialogs Overview

**Updated:** {datetime.now().strftime("%Y-%m-%d %H:%M")}
**Accounts:** {len(self.accounts)}
**Dialogs:** {len(dialogs)}

## Recent Dialogs

| # | Account | Chat | Type | Unread | Last Message |
|---|---------|------|------|--------|--------------|
"""
        for i, d in enumerate(dialogs[:50], 1):
            last_msg = d.get("last_message", {}).get("text", "-")[:40]
            if len(d.get("last_message", {}).get("text", "")) > 40:
                last_msg += "..."
            last_msg = last_msg.replace("|", "/").replace("\n", " ")
            name = (d.get("name") or "Unknown")[:25]

            content += f"| {i} | {d['account']} | {name} | {d['type']} | {d.get('unread_count', 0)} | {last_msg} |\n"

        with open(path, "w", encoding="utf-8") as f:
            f.write(content)

    async def _create_pending_md(self, pending: list[dict], path: Path):
        """Create markdown for pending replies"""
        content = f"""# Pending Replies

**Updated:** {datetime.now().strftime("%Y-%m-%d %H:%M")}
**Unread Chats:** {len(pending)}

## List

"""
        for d in pending:
            msg_text = d.get('last_message', {}).get('text', '-')[:100]
            content += f"""### {d.get('name', 'Unknown')} ({d['account']})
- **Type:** {d['type']}
- **Unread:** {d['unread_count']} messages
- **Last:** {msg_text}

"""

        with open(path, "w", encoding="utf-8") as f:
            f.write(content)


# Global manager instance
manager = TelegramManager()


async def main():
    """Test run"""
    logger.info("=== TelegramHub Manager Test ===")

    loaded = await manager.load_accounts()
    logger.info(f"Accounts loaded: {loaded}")

    if loaded > 0:
        await manager.sync_to_files()
        stats = manager.get_statistics()
        logger.info(f"Stats: {stats}")

    await manager.disconnect_all()


if __name__ == "__main__":
    asyncio.run(main())
