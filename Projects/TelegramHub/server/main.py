"""
TelegramHub CRM v2.0
Full-featured Telegram multi-account management system
"""
import asyncio
import json
import csv
import io
import base64
from datetime import datetime
from pathlib import Path
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request, UploadFile, File
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse
from pydantic import BaseModel
import uvicorn

from config import HOST, PORT, CONTEXT_DIR, DRAFTS_DIR, AI_ENABLED, REVIEW_MIN_UNREAD, REVIEW_MAX_CHATS, REVIEW_SKIP_GROUPS
from telegram_manager import manager, logger
from crm_data import crm
from ai_assistant import ai_assistant, drafts_manager


# ============================================================
# Data Models
# ============================================================

class SendMessageRequest(BaseModel):
    account: str
    chat_id: int
    text: str
    reply_to: int | None = None


class TagRequest(BaseModel):
    account: str
    chat_id: int
    tag_id: str


class NotesRequest(BaseModel):
    account: str
    chat_id: int
    notes: str


class StatusRequest(BaseModel):
    account: str
    chat_id: int
    status: str


class PinRequest(BaseModel):
    account: str
    chat_id: int


class TemplateRequest(BaseModel):
    name: str
    text: str


class NewTagRequest(BaseModel):
    tag_id: str
    name: str
    color: str = "#888888"


class BroadcastRequest(BaseModel):
    targets: list[dict]  # [{"account": "acc1", "chat_id": 123}, ...]
    text: str
    delay: float = 3.0


class ExportRequest(BaseModel):
    account: str
    chat_id: int
    limit: int = 200
    format: str = "markdown"


class MultiExportRequest(BaseModel):
    chats: list[dict]
    limit_per_chat: int = 100


class TagExportRequest(BaseModel):
    tag_id: str
    limit_per_chat: int = 50


# AI Request Models
class AIAnalyzeRequest(BaseModel):
    account: str
    chat_id: int
    limit: int = 50


class AISuggestRequest(BaseModel):
    account: str
    chat_id: int
    context: str | None = None
    num_suggestions: int = 3


class AISummarizeRequest(BaseModel):
    account: str
    chat_id: int
    limit: int = 50


class AIQuickReplyRequest(BaseModel):
    last_message: str
    tone: str = "casual"


class AICustomRequest(BaseModel):
    account: str
    chat_id: int
    custom_prompt: str
    num_suggestions: int = 3


class DraftCreateRequest(BaseModel):
    account: str
    chat_id: int
    chat_name: str
    text: str
    suggested_by: str = "user"


class DraftUpdateRequest(BaseModel):
    text: str | None = None
    status: str | None = None


class ReviewActionRequest(BaseModel):
    action: str  # "send", "draft", "skip", "later"
    text: str | None = None
    draft_id: str | None = None


# Drafts storage
drafts = {}


def load_drafts():
    global drafts
    drafts_file = DRAFTS_DIR / "outbox.json"
    if drafts_file.exists():
        with open(drafts_file, "r", encoding="utf-8") as f:
            data = json.load(f)
            drafts = {d["id"]: d for d in data}


def save_drafts():
    drafts_file = DRAFTS_DIR / "outbox.json"
    with open(drafts_file, "w", encoding="utf-8") as f:
        json.dump(list(drafts.values()), f, ensure_ascii=False, indent=2)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting TelegramHub CRM v2.0...")
    load_drafts()
    loaded = await manager.load_accounts()
    logger.info(f"Accounts loaded: {loaded}")
    if loaded > 0:
        await manager.sync_to_files()
    yield
    logger.info("Stopping TelegramHub CRM...")
    await manager.disconnect_all()


app = FastAPI(title="TelegramHub CRM", version="2.0.0", lifespan=lifespan)


# ============================================================
# API Endpoints
# ============================================================

@app.get("/api/accounts")
async def get_accounts():
    return manager.get_accounts_status()


@app.get("/api/statistics")
async def get_statistics():
    return manager.get_statistics()


@app.get("/api/dialogs")
async def get_dialogs():
    dialogs = await manager.get_all_dialogs()
    # Enrich with CRM data
    for d in dialogs:
        crm_data = crm.get_chat_data(d["account"], d["id"])
        d["crm"] = crm_data
    return dialogs


@app.get("/api/messages/{account}/{chat_id}")
async def get_messages(account: str, chat_id: int, limit: int = 50):
    acc = manager.get_account(account)
    if not acc:
        raise HTTPException(404, "Account not found")
    messages = await acc.get_messages(chat_id, limit)
    return messages


@app.post("/api/send")
async def send_message(req: SendMessageRequest):
    acc = manager.get_account(req.account)
    if not acc:
        raise HTTPException(404, "Account not found")
    result = await acc.send_message(req.chat_id, req.text, req.reply_to)
    return result


@app.post("/api/send-file")
async def send_file(
    account: str,
    chat_id: int,
    file: UploadFile = File(...),
    caption: str = None
):
    acc = manager.get_account(account)
    if not acc:
        raise HTTPException(404, "Account not found")

    file_data = await file.read()
    result = await acc.send_file(chat_id, file_data, file.filename, caption)
    return result


@app.get("/api/media/{account}/{chat_id}/{message_id}")
async def get_media(account: str, chat_id: int, message_id: int):
    acc = manager.get_account(account)
    if not acc:
        raise HTTPException(404, "Account not found")

    media = await acc.download_media(chat_id, message_id)
    if not media:
        raise HTTPException(404, "Media not found")

    return media


# CRM Endpoints
@app.post("/api/crm/tag/add")
async def add_tag(req: TagRequest):
    crm.add_tag_to_chat(req.account, req.chat_id, req.tag_id)
    return {"status": "ok"}


@app.post("/api/crm/tag/remove")
async def remove_tag(req: TagRequest):
    crm.remove_tag_from_chat(req.account, req.chat_id, req.tag_id)
    return {"status": "ok"}


@app.post("/api/crm/notes")
async def set_notes(req: NotesRequest):
    crm.set_notes(req.account, req.chat_id, req.notes)
    return {"status": "ok"}


@app.post("/api/crm/status")
async def set_status(req: StatusRequest):
    crm.set_status(req.account, req.chat_id, req.status)
    return {"status": "ok"}


@app.post("/api/crm/pin")
async def toggle_pin(req: PinRequest):
    pinned = crm.toggle_pin(req.account, req.chat_id)
    return {"pinned": pinned}


# Tags Management
@app.get("/api/tags")
async def get_tags():
    return crm.tags


@app.post("/api/tags")
async def create_tag(req: NewTagRequest):
    crm.tags.append({
        "id": req.tag_id,
        "name": req.name,
        "color": req.color
    })
    crm.save()
    return {"status": "ok"}


@app.put("/api/tags/{tag_id}")
async def update_tag(tag_id: str, req: NewTagRequest):
    for tag in crm.tags:
        if tag["id"] == tag_id:
            tag["name"] = req.name
            tag["color"] = req.color
            crm.save()
            return {"status": "ok"}
    raise HTTPException(404, "Tag not found")


@app.delete("/api/tags/{tag_id}")
async def delete_tag(tag_id: str):
    crm.tags = [t for t in crm.tags if t["id"] != tag_id]
    # Remove tag from all chats
    for chat_key, chat_data in crm.chats.items():
        if tag_id in chat_data.get("tags", []):
            chat_data["tags"].remove(tag_id)
    crm.save()
    return {"status": "ok"}


# Templates Management
@app.get("/api/templates")
async def get_templates():
    return crm.templates


@app.post("/api/templates")
async def add_template(req: TemplateRequest):
    template_id = crm.add_template(req.name, req.text)
    return {"id": template_id}


@app.put("/api/templates/{template_id}")
async def update_template(template_id: str, req: TemplateRequest):
    for t in crm.templates:
        if t["id"] == template_id:
            t["name"] = req.name
            t["text"] = req.text
            crm.save()
            return {"status": "ok"}
    raise HTTPException(404, "Template not found")


@app.delete("/api/templates/{template_id}")
async def delete_template(template_id: str):
    crm.remove_template(template_id)
    return {"status": "ok"}


# Broadcast
@app.post("/api/broadcast")
async def broadcast_message(req: BroadcastRequest):
    result = await manager.broadcast_message(req.targets, req.text, req.delay)
    return result


@app.post("/api/broadcast/cancel")
async def cancel_broadcast():
    manager.cancel_broadcast()
    return {"status": "cancelled"}


# Export Endpoints
@app.post("/api/export/chat")
async def export_chat(req: ExportRequest):
    from cursor_integration import init_exporter
    exp = init_exporter(manager)

    if req.format == "json":
        filepath = await exp.export_chat_structured(req.account, req.chat_id, req.limit)
    else:
        filepath = await exp.export_chat_full(req.account, req.chat_id, req.limit)

    if not filepath:
        raise HTTPException(404, "Chat not found or account not connected")

    return {"status": "exported", "filepath": filepath}


@app.post("/api/export/multiple")
async def export_multiple_chats(req: MultiExportRequest):
    from cursor_integration import init_exporter
    exp = init_exporter(manager)
    filepath = await exp.export_multiple_chats(req.chats, req.limit_per_chat)
    if not filepath:
        raise HTTPException(500, "Export failed")
    return {"status": "exported", "filepath": filepath}


@app.post("/api/export/by-tag")
async def export_by_tag(req: TagExportRequest):
    from cursor_integration import init_exporter
    exp = init_exporter(manager)
    filepath = await exp.export_by_tag(req.tag_id, req.limit_per_chat)
    if not filepath:
        raise HTTPException(404, "No chats found with this tag")
    return {"status": "exported", "filepath": filepath}


@app.get("/api/export/list")
async def list_exports():
    exports_dir = CONTEXT_DIR / "exports"
    exports_dir.mkdir(parents=True, exist_ok=True)

    files = []
    for f in sorted(exports_dir.glob("*.*"), key=lambda x: x.stat().st_mtime, reverse=True):
        files.append({
            "name": f.name,
            "path": str(f),
            "size": f.stat().st_size,
            "modified": datetime.fromtimestamp(f.stat().st_mtime).isoformat()
        })

    return {"exports": files[:50]}


@app.get("/api/export/csv")
async def export_csv():
    """Export all chats to CSV"""
    dialogs = await manager.get_all_dialogs()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Account", "Chat Name", "Type", "Unread", "Last Message", "Tags", "Status", "Notes"])

    for d in dialogs:
        crm_data = crm.get_chat_data(d["account"], d["id"])
        tags = ", ".join(crm_data.get("tags", []))
        writer.writerow([
            d["account"],
            d.get("name", "Unknown"),
            d["type"],
            d.get("unread_count", 0),
            d.get("last_message", {}).get("text", "")[:100],
            tags,
            crm_data.get("status", ""),
            crm_data.get("notes", "")[:200]
        ])

    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=telegramhub_export_{datetime.now().strftime('%Y%m%d')}.csv"}
    )


@app.post("/api/sync")
async def sync_context():
    await manager.sync_to_files()
    return {"status": "synced", "timestamp": datetime.now().isoformat()}


# ============================================================
# AI Endpoints
# ============================================================

@app.get("/api/ai/status")
async def ai_status():
    """Check if AI is available and configured"""
    return {
        "available": ai_assistant.is_available,
        "enabled": AI_ENABLED,
        "provider": ai_assistant.provider if ai_assistant.is_available else None,
        "model": ai_assistant.model if ai_assistant.is_available else None
    }


@app.post("/api/ai/analyze")
async def ai_analyze_chat(req: AIAnalyzeRequest):
    """Analyze a chat conversation with AI"""
    if not ai_assistant.is_available:
        raise HTTPException(503, "AI is not configured. Set AI_API_KEY environment variable.")

    acc = manager.get_account(req.account)
    if not acc:
        raise HTTPException(404, "Account not found")

    messages = await acc.get_messages(req.chat_id, req.limit)
    dialogs = await acc.get_dialogs(limit=200)
    chat_info = next((d for d in dialogs if d["id"] == req.chat_id), {})

    analysis = await ai_assistant.analyze_chat(messages, chat_info)
    return analysis


@app.post("/api/ai/suggest")
async def ai_suggest_replies(req: AISuggestRequest):
    """Get AI-generated reply suggestions for a chat"""
    if not ai_assistant.is_available:
        raise HTTPException(503, "AI is not configured. Set AI_API_KEY environment variable.")

    acc = manager.get_account(req.account)
    if not acc:
        raise HTTPException(404, "Account not found")

    messages = await acc.get_messages(req.chat_id, 30)  # Last 30 messages for context
    dialogs = await acc.get_dialogs(limit=200)
    chat_info = next((d for d in dialogs if d["id"] == req.chat_id), {})

    suggestions = await ai_assistant.suggest_replies(
        messages,
        chat_info,
        req.context,
        req.num_suggestions
    )
    return {"suggestions": suggestions}


@app.post("/api/ai/summarize")
async def ai_summarize_chat(req: AISummarizeRequest):
    """Get AI-generated summary of a chat"""
    if not ai_assistant.is_available:
        raise HTTPException(503, "AI is not configured. Set AI_API_KEY environment variable.")

    acc = manager.get_account(req.account)
    if not acc:
        raise HTTPException(404, "Account not found")

    messages = await acc.get_messages(req.chat_id, req.limit)
    dialogs = await acc.get_dialogs(limit=200)
    chat_info = next((d for d in dialogs if d["id"] == req.chat_id), {})

    summary = await ai_assistant.summarize_conversation(messages, chat_info)
    return {"summary": summary}


@app.post("/api/ai/quick-reply")
async def ai_quick_reply(req: AIQuickReplyRequest):
    """Generate a quick reply to a single message"""
    if not ai_assistant.is_available:
        raise HTTPException(503, "AI is not configured. Set AI_API_KEY environment variable.")

    reply = await ai_assistant.generate_quick_reply(req.last_message, req.tone)
    return {"reply": reply}


@app.post("/api/ai/custom")
async def ai_custom_request(req: AICustomRequest):
    """Generate AI suggestions based on custom user prompt"""
    if not ai_assistant.is_available:
        raise HTTPException(503, "AI is not configured. Set AI_API_KEY environment variable.")

    acc = manager.accounts.get(req.account)
    if not acc:
        raise HTTPException(404, f"Account {req.account} not found")

    # Get messages
    messages = await acc.get_messages(req.chat_id, limit=50)

    # Get chat info
    dialogs = await acc.get_dialogs(limit=200)
    chat_info = next((d for d in dialogs if d["id"] == req.chat_id), {})

    # Generate suggestions with custom context
    suggestions = await ai_assistant.suggest_replies(
        messages,
        chat_info,
        context=req.custom_prompt,
        num_suggestions=req.num_suggestions
    )

    return {"suggestions": suggestions}


# ============================================================
# Drafts Endpoints
# ============================================================

@app.get("/api/drafts")
async def get_drafts(status: str = None):
    """Get all drafts, optionally filtered by status"""
    return {"drafts": drafts_manager.get_all_drafts(status)}


@app.get("/api/drafts/{draft_id}")
async def get_draft(draft_id: str):
    """Get a specific draft"""
    draft = drafts_manager.get_draft(draft_id)
    if not draft:
        raise HTTPException(404, "Draft not found")
    return draft


@app.post("/api/drafts")
async def create_draft(req: DraftCreateRequest):
    """Create a new draft"""
    draft = drafts_manager.create_draft(
        req.account,
        req.chat_id,
        req.chat_name,
        req.text,
        req.suggested_by
    )
    return draft


@app.put("/api/drafts/{draft_id}")
async def update_draft(draft_id: str, req: DraftUpdateRequest):
    """Update a draft"""
    draft = drafts_manager.update_draft(draft_id, req.text, req.status)
    if not draft:
        raise HTTPException(404, "Draft not found")
    return draft


@app.delete("/api/drafts/{draft_id}")
async def delete_draft(draft_id: str):
    """Delete a draft"""
    if not drafts_manager.delete_draft(draft_id):
        raise HTTPException(404, "Draft not found")
    return {"status": "deleted"}


@app.post("/api/drafts/{draft_id}/send")
async def send_draft(draft_id: str):
    """Send a draft message"""
    draft = drafts_manager.get_draft(draft_id)
    if not draft:
        raise HTTPException(404, "Draft not found")

    acc = manager.get_account(draft["account"])
    if not acc:
        raise HTTPException(404, "Account not found")

    result = await acc.send_message(draft["chat_id"], draft["text"])

    if result.get("success"):
        drafts_manager.mark_sent(draft_id)
        return {"status": "sent", "message_id": result.get("message_id")}
    else:
        raise HTTPException(500, f"Failed to send: {result.get('error')}")


# ============================================================
# Review Mode Endpoints
# ============================================================

@app.get("/api/review/queue")
async def get_review_queue():
    """Get list of chats that need review (have unread messages)"""
    all_dialogs = await manager.get_all_dialogs()

    # Filter chats that need review
    review_queue = []
    for dialog in all_dialogs:
        unread = dialog.get("unread_count", 0)
        chat_type = dialog.get("type", "")

        # Skip based on settings
        if unread < REVIEW_MIN_UNREAD:
            continue
        if REVIEW_SKIP_GROUPS and chat_type in ["supergroup", "channel", "chat"]:
            continue

        # Add CRM data
        crm_data = crm.get_chat_data(dialog["account"], dialog["id"])
        dialog["crm"] = crm_data

        # Skip if marked as "later"
        if crm_data.get("status") == "later":
            continue

        review_queue.append(dialog)

    # Sort by unread count (most unread first)
    review_queue.sort(key=lambda x: x.get("unread_count", 0), reverse=True)

    return {
        "queue": review_queue[:REVIEW_MAX_CHATS],
        "total": len(review_queue),
        "ai_available": ai_assistant.is_available
    }


@app.get("/api/review/chat/{account}/{chat_id}")
async def get_review_chat_details(account: str, chat_id: int):
    """Get detailed info for reviewing a specific chat"""
    acc = manager.get_account(account)
    if not acc:
        raise HTTPException(404, "Account not found")

    # Get messages
    messages = await acc.get_messages(chat_id, 30)

    # Get chat info
    dialogs = await acc.get_dialogs(limit=200)
    chat_info = next((d for d in dialogs if d["id"] == chat_id), {})

    # Get CRM data
    crm_data = crm.get_chat_data(account, chat_id)

    # Get drafts for this chat
    chat_drafts = drafts_manager.get_drafts_for_chat(account, chat_id)

    result = {
        "chat": chat_info,
        "messages": messages,
        "crm": crm_data,
        "drafts": chat_drafts,
        "ai_available": ai_assistant.is_available
    }

    # Add AI analysis if available
    if ai_assistant.is_available:
        try:
            analysis = await ai_assistant.analyze_chat(messages, chat_info)
            suggestions = await ai_assistant.suggest_replies(messages, chat_info)
            result["ai_analysis"] = analysis
            result["ai_suggestions"] = suggestions
        except Exception as e:
            logger.error(f"AI analysis failed: {e}")
            result["ai_error"] = str(e)

    return result


@app.post("/api/review/action")
async def review_action(req: ReviewActionRequest):
    """Perform an action on a review item"""
    if req.action == "send" and req.text:
        # Send message directly
        # Need account and chat_id from request
        return {"status": "error", "message": "Use /api/send endpoint for direct sending"}

    elif req.action == "draft" and req.draft_id:
        # Update or create draft
        if req.text:
            draft = drafts_manager.update_draft(req.draft_id, text=req.text)
            return {"status": "drafted", "draft": draft}

    elif req.action == "skip":
        # Just mark as skipped (no action needed)
        return {"status": "skipped"}

    elif req.action == "later":
        # Mark chat status as "later" in CRM
        # Need account and chat_id
        return {"status": "error", "message": "Use /api/crm/status endpoint"}

    return {"status": "unknown_action"}


# ============================================================
# Web Dashboard
# ============================================================

@app.get("/", response_class=HTMLResponse)
async def dashboard():
    return """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>TelegramHub CRM</title>
    <style>
        :root {
            --bg-primary: #0f0f0f;
            --bg-secondary: #1a1a1a;
            --bg-tertiary: #252525;
            --bg-hover: #2d2d2d;
            --text-primary: #ffffff;
            --text-secondary: #a0a0a0;
            --text-muted: #666666;
            --accent: #3b82f6;
            --accent-hover: #2563eb;
            --success: #22c55e;
            --warning: #f59e0b;
            --danger: #ef4444;
            --border: #333333;
            --shadow: rgba(0,0,0,0.3);
        }

        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }

        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, sans-serif;
            background: var(--bg-primary);
            color: var(--text-primary);
            min-height: 100vh;
        }

        /* Header */
        .header {
            background: var(--bg-secondary);
            border-bottom: 1px solid var(--border);
            padding: 12px 24px;
            display: flex;
            align-items: center;
            justify-content: space-between;
            position: sticky;
            top: 0;
            z-index: 100;
        }

        .header h1 {
            font-size: 20px;
            font-weight: 600;
            display: flex;
            align-items: center;
            gap: 10px;
        }

        .header h1 span {
            color: var(--accent);
        }

        .header-stats {
            display: flex;
            gap: 20px;
        }

        .stat-item {
            display: flex;
            flex-direction: column;
            align-items: center;
        }

        .stat-value {
            font-size: 18px;
            font-weight: 600;
        }

        .stat-label {
            font-size: 11px;
            color: var(--text-secondary);
            text-transform: uppercase;
        }

        .header-actions {
            display: flex;
            gap: 8px;
        }

        /* Buttons */
        .btn {
            padding: 8px 16px;
            border-radius: 6px;
            font-size: 13px;
            font-weight: 500;
            border: none;
            cursor: pointer;
            transition: all 0.2s;
            display: inline-flex;
            align-items: center;
            gap: 6px;
        }

        .btn-primary {
            background: var(--accent);
            color: white;
        }

        .btn-primary:hover {
            background: var(--accent-hover);
        }

        .btn-secondary {
            background: var(--bg-tertiary);
            color: var(--text-primary);
            border: 1px solid var(--border);
        }

        .btn-secondary:hover {
            background: var(--bg-hover);
        }

        .btn-danger {
            background: var(--danger);
            color: white;
        }

        .btn-success {
            background: var(--success);
            color: white;
        }

        .btn-sm {
            padding: 4px 8px;
            font-size: 12px;
        }

        /* Main Layout */
        .main-container {
            display: grid;
            grid-template-columns: 320px 1fr 350px;
            height: calc(100vh - 57px);
        }

        /* Sidebar - Chats List */
        .sidebar {
            background: var(--bg-secondary);
            border-right: 1px solid var(--border);
            display: flex;
            flex-direction: column;
            overflow: hidden;
        }

        .sidebar-header {
            padding: 12px;
            border-bottom: 1px solid var(--border);
        }

        .search-box {
            width: 100%;
            padding: 10px 12px;
            background: var(--bg-tertiary);
            border: 1px solid var(--border);
            border-radius: 8px;
            color: var(--text-primary);
            font-size: 13px;
        }

        .search-box:focus {
            outline: none;
            border-color: var(--accent);
        }

        .filters {
            display: flex;
            gap: 6px;
            margin-top: 10px;
            flex-wrap: wrap;
        }

        .filter-chip {
            padding: 4px 10px;
            background: var(--bg-tertiary);
            border: 1px solid var(--border);
            border-radius: 12px;
            font-size: 11px;
            cursor: pointer;
            transition: all 0.2s;
        }

        .filter-chip:hover, .filter-chip.active {
            background: var(--accent);
            border-color: var(--accent);
            color: white;
        }

        .chat-list {
            flex: 1;
            overflow-y: auto;
        }

        .chat-item {
            padding: 12px;
            border-bottom: 1px solid var(--border);
            cursor: pointer;
            transition: background 0.2s;
            display: flex;
            align-items: flex-start;
            gap: 12px;
        }

        .chat-item:hover {
            background: var(--bg-hover);
        }

        .chat-item.active {
            background: var(--bg-tertiary);
            border-left: 3px solid var(--accent);
        }

        .chat-item.pinned {
            background: rgba(59, 130, 246, 0.1);
        }

        .chat-checkbox {
            margin-top: 4px;
        }

        .chat-avatar {
            width: 44px;
            height: 44px;
            border-radius: 50%;
            background: var(--bg-tertiary);
            display: flex;
            align-items: center;
            justify-content: center;
            font-weight: 600;
            font-size: 16px;
            flex-shrink: 0;
        }

        .chat-info {
            flex: 1;
            min-width: 0;
        }

        .chat-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 4px;
        }

        .chat-name {
            font-weight: 500;
            font-size: 14px;
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
        }

        .chat-time {
            font-size: 11px;
            color: var(--text-muted);
        }

        .chat-preview {
            font-size: 13px;
            color: var(--text-secondary);
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
        }

        .chat-meta {
            display: flex;
            gap: 4px;
            margin-top: 6px;
            flex-wrap: wrap;
        }

        .chat-tag {
            padding: 2px 6px;
            border-radius: 4px;
            font-size: 10px;
            font-weight: 500;
        }

        .chat-badge {
            background: var(--accent);
            color: white;
            padding: 2px 6px;
            border-radius: 10px;
            font-size: 11px;
            font-weight: 600;
        }

        .chat-account {
            font-size: 10px;
            color: var(--text-muted);
            background: var(--bg-tertiary);
            padding: 2px 6px;
            border-radius: 4px;
        }

        /* Main Content - Messages */
        .content {
            display: flex;
            flex-direction: column;
            background: var(--bg-primary);
        }

        .content-header {
            padding: 16px 20px;
            border-bottom: 1px solid var(--border);
            display: flex;
            justify-content: space-between;
            align-items: center;
            background: var(--bg-secondary);
        }

        .content-title {
            font-size: 16px;
            font-weight: 600;
        }

        .content-subtitle {
            font-size: 12px;
            color: var(--text-secondary);
        }

        .messages-container {
            flex: 1;
            overflow-y: auto;
            padding: 20px;
            display: flex;
            flex-direction: column;
            gap: 8px;
        }

        .message {
            max-width: 70%;
            padding: 10px 14px;
            border-radius: 12px;
            font-size: 14px;
            line-height: 1.4;
            position: relative;
        }

        .message.incoming {
            background: var(--bg-tertiary);
            align-self: flex-start;
            border-bottom-left-radius: 4px;
        }

        .message.outgoing {
            background: var(--accent);
            align-self: flex-end;
            border-bottom-right-radius: 4px;
        }

        .message-time {
            font-size: 10px;
            color: var(--text-muted);
            margin-top: 4px;
        }

        .message.outgoing .message-time {
            color: rgba(255,255,255,0.7);
        }

        .message-media {
            margin-bottom: 8px;
        }

        .message-media img {
            max-width: 100%;
            max-height: 300px;
            border-radius: 8px;
            cursor: pointer;
        }

        .media-placeholder {
            padding: 12px;
            background: var(--bg-hover);
            border-radius: 8px;
            display: flex;
            align-items: center;
            gap: 8px;
            cursor: pointer;
        }

        .reply-preview {
            padding: 8px;
            background: rgba(0,0,0,0.2);
            border-left: 2px solid var(--accent);
            border-radius: 4px;
            margin-bottom: 8px;
            font-size: 12px;
            color: var(--text-secondary);
        }

        /* Message Input */
        .message-input-container {
            padding: 16px 20px;
            border-top: 1px solid var(--border);
            background: var(--bg-secondary);
        }

        .reply-bar {
            background: var(--bg-tertiary);
            padding: 8px 12px;
            border-radius: 8px;
            margin-bottom: 10px;
            display: none;
            justify-content: space-between;
            align-items: center;
        }

        .reply-bar.active {
            display: flex;
        }

        .message-form {
            display: flex;
            gap: 10px;
        }

        .message-input {
            flex: 1;
            padding: 12px 16px;
            background: var(--bg-tertiary);
            border: 1px solid var(--border);
            border-radius: 24px;
            color: var(--text-primary);
            font-size: 14px;
            resize: none;
            min-height: 44px;
            max-height: 120px;
        }

        .message-input:focus {
            outline: none;
            border-color: var(--accent);
        }

        .send-btn {
            width: 44px;
            height: 44px;
            border-radius: 50%;
            background: var(--accent);
            border: none;
            color: white;
            cursor: pointer;
            display: flex;
            align-items: center;
            justify-content: center;
            transition: background 0.2s;
        }

        .send-btn:hover {
            background: var(--accent-hover);
        }

        .attach-btn {
            width: 44px;
            height: 44px;
            border-radius: 50%;
            background: var(--bg-tertiary);
            border: 1px solid var(--border);
            color: var(--text-secondary);
            cursor: pointer;
            display: flex;
            align-items: center;
            justify-content: center;
        }

        /* Right Panel */
        .right-panel {
            background: var(--bg-secondary);
            border-left: 1px solid var(--border);
            display: flex;
            flex-direction: column;
            overflow: hidden;
        }

        .panel-tabs {
            display: flex;
            border-bottom: 1px solid var(--border);
        }

        .panel-tab {
            flex: 1;
            padding: 12px;
            text-align: center;
            font-size: 13px;
            font-weight: 500;
            cursor: pointer;
            border-bottom: 2px solid transparent;
            transition: all 0.2s;
        }

        .panel-tab:hover {
            background: var(--bg-hover);
        }

        .panel-tab.active {
            border-bottom-color: var(--accent);
            color: var(--accent);
        }

        .panel-content {
            flex: 1;
            overflow-y: auto;
            padding: 16px;
        }

        .panel-section {
            margin-bottom: 24px;
        }

        .panel-section-title {
            font-size: 12px;
            font-weight: 600;
            color: var(--text-secondary);
            text-transform: uppercase;
            margin-bottom: 12px;
        }

        /* CRM Panel */
        .crm-status-select {
            width: 100%;
            padding: 10px 12px;
            background: var(--bg-tertiary);
            border: 1px solid var(--border);
            border-radius: 8px;
            color: var(--text-primary);
            font-size: 13px;
        }

        .crm-notes {
            width: 100%;
            min-height: 80px;
            padding: 10px 12px;
            background: var(--bg-tertiary);
            border: 1px solid var(--border);
            border-radius: 8px;
            color: var(--text-primary);
            font-size: 13px;
            resize: vertical;
        }

        .tag-list {
            display: flex;
            flex-wrap: wrap;
            gap: 6px;
        }

        .tag-item {
            padding: 4px 10px;
            border-radius: 12px;
            font-size: 12px;
            cursor: pointer;
            transition: all 0.2s;
            border: 1px solid transparent;
        }

        .tag-item.selected {
            border-color: white;
        }

        /* Templates */
        .template-item {
            padding: 10px 12px;
            background: var(--bg-tertiary);
            border-radius: 8px;
            margin-bottom: 8px;
            cursor: pointer;
            transition: background 0.2s;
        }

        .template-item:hover {
            background: var(--bg-hover);
        }

        .template-name {
            font-weight: 500;
            font-size: 13px;
            margin-bottom: 4px;
        }

        .template-text {
            font-size: 12px;
            color: var(--text-secondary);
        }

        /* Broadcast Panel */
        .broadcast-panel {
            display: none;
            position: fixed;
            bottom: 20px;
            left: 340px;
            right: 370px;
            background: var(--bg-secondary);
            border: 1px solid var(--border);
            border-radius: 12px;
            padding: 16px;
            box-shadow: 0 4px 20px var(--shadow);
            z-index: 50;
        }

        .broadcast-panel.active {
            display: block;
        }

        .broadcast-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 12px;
        }

        .broadcast-count {
            font-size: 14px;
            color: var(--text-secondary);
        }

        .broadcast-textarea {
            width: 100%;
            min-height: 80px;
            padding: 12px;
            background: var(--bg-tertiary);
            border: 1px solid var(--border);
            border-radius: 8px;
            color: var(--text-primary);
            font-size: 14px;
            resize: vertical;
            margin-bottom: 12px;
        }

        .broadcast-actions {
            display: flex;
            justify-content: flex-end;
            gap: 8px;
        }

        /* Modal */
        .modal-overlay {
            display: none;
            position: fixed;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            background: rgba(0,0,0,0.7);
            z-index: 200;
            justify-content: center;
            align-items: center;
        }

        .modal-overlay.active {
            display: flex;
        }

        .modal {
            background: var(--bg-secondary);
            border-radius: 12px;
            padding: 24px;
            width: 90%;
            max-width: 500px;
            max-height: 80vh;
            overflow-y: auto;
        }

        .modal-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 20px;
        }

        .modal-title {
            font-size: 18px;
            font-weight: 600;
        }

        .modal-close {
            background: none;
            border: none;
            color: var(--text-secondary);
            font-size: 24px;
            cursor: pointer;
        }

        .form-group {
            margin-bottom: 16px;
        }

        .form-label {
            display: block;
            font-size: 13px;
            font-weight: 500;
            margin-bottom: 6px;
        }

        .form-input {
            width: 100%;
            padding: 10px 12px;
            background: var(--bg-tertiary);
            border: 1px solid var(--border);
            border-radius: 8px;
            color: var(--text-primary);
            font-size: 14px;
        }

        .form-input:focus {
            outline: none;
            border-color: var(--accent);
        }

        .color-picker {
            width: 50px;
            height: 36px;
            border: none;
            border-radius: 6px;
            cursor: pointer;
        }

        /* Settings Panel */
        .settings-item {
            padding: 12px;
            background: var(--bg-tertiary);
            border-radius: 8px;
            margin-bottom: 8px;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }

        .settings-item-info {
            flex: 1;
        }

        .settings-item-name {
            font-weight: 500;
            margin-bottom: 2px;
        }

        .settings-item-desc {
            font-size: 12px;
            color: var(--text-secondary);
        }

        /* Dashboard Analytics */
        .analytics-grid {
            display: grid;
            grid-template-columns: repeat(2, 1fr);
            gap: 12px;
            margin-bottom: 20px;
        }

        .analytics-card {
            background: var(--bg-tertiary);
            border-radius: 12px;
            padding: 16px;
        }

        .analytics-value {
            font-size: 28px;
            font-weight: 700;
            margin-bottom: 4px;
        }

        .analytics-label {
            font-size: 12px;
            color: var(--text-secondary);
        }

        /* Empty state */
        .empty-state {
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            height: 100%;
            color: var(--text-secondary);
        }

        .empty-state svg {
            width: 64px;
            height: 64px;
            margin-bottom: 16px;
            opacity: 0.5;
        }

        /* Scrollbar */
        ::-webkit-scrollbar {
            width: 6px;
        }

        ::-webkit-scrollbar-track {
            background: transparent;
        }

        ::-webkit-scrollbar-thumb {
            background: var(--border);
            border-radius: 3px;
        }

        ::-webkit-scrollbar-thumb:hover {
            background: var(--text-muted);
        }

        /* Animations */
        @keyframes fadeIn {
            from { opacity: 0; }
            to { opacity: 1; }
        }

        .fade-in {
            animation: fadeIn 0.2s ease;
        }

        /* Loading */
        .loading {
            display: flex;
            align-items: center;
            justify-content: center;
            padding: 20px;
        }

        .spinner {
            width: 24px;
            height: 24px;
            border: 2px solid var(--border);
            border-top-color: var(--accent);
            border-radius: 50%;
            animation: spin 0.8s linear infinite;
        }

        @keyframes spin {
            to { transform: rotate(360deg); }
        }

        /* Toast notifications */
        .toast-container {
            position: fixed;
            bottom: 20px;
            right: 20px;
            z-index: 300;
        }

        .toast {
            background: var(--bg-tertiary);
            border: 1px solid var(--border);
            border-radius: 8px;
            padding: 12px 16px;
            margin-top: 8px;
            display: flex;
            align-items: center;
            gap: 10px;
            animation: slideIn 0.3s ease;
        }

        @keyframes slideIn {
            from { transform: translateX(100%); opacity: 0; }
            to { transform: translateX(0); opacity: 1; }
        }

        .toast.success { border-left: 3px solid var(--success); }
        .toast.error { border-left: 3px solid var(--danger); }
        .toast.warning { border-left: 3px solid var(--warning); }
    </style>
</head>
<body>
    <!-- Header -->
    <header class="header">
        <h1>
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"></path>
            </svg>
            Telegram<span>Hub</span> CRM
        </h1>
        <div class="header-stats">
            <div class="stat-item">
                <span class="stat-value" id="stat-accounts">-</span>
                <span class="stat-label">Accounts</span>
            </div>
            <div class="stat-item">
                <span class="stat-value" id="stat-chats">-</span>
                <span class="stat-label">Chats</span>
            </div>
            <div class="stat-item">
                <span class="stat-value" id="stat-unread">-</span>
                <span class="stat-label">Unread</span>
            </div>
        </div>
        <div class="header-actions">
            <button class="btn btn-secondary" onclick="showSettings()">
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <circle cx="12" cy="12" r="3"></circle>
                    <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1z"></path>
                </svg>
                Settings
            </button>
            <button class="btn btn-secondary" onclick="exportCSV()">
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path>
                    <polyline points="7 10 12 15 17 10"></polyline>
                    <line x1="12" y1="15" x2="12" y2="3"></line>
                </svg>
                Export
            </button>
            <button class="btn btn-secondary" onclick="showDraftsModal()">
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <path d="M19 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11l5 5v11a2 2 0 0 1-2 2z"></path>
                    <polyline points="17 21 17 13 7 13 7 21"></polyline>
                </svg>
                Drafts <span id="drafts-count" style="background: var(--accent); color: white; padding: 1px 6px; border-radius: 10px; font-size: 11px; margin-left: 4px; display: none;">0</span>
            </button>
            <button class="btn btn-success" onclick="showReviewModal()" style="background: var(--success);">
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <path d="M9 11l3 3L22 4"></path>
                    <path d="M21 12v7a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11"></path>
                </svg>
                Review
            </button>
            <button class="btn btn-primary" onclick="syncData()">
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <polyline points="23 4 23 10 17 10"></polyline>
                    <path d="M20.49 15a9 9 0 1 1-2.12-9.36L23 10"></path>
                </svg>
                Sync
            </button>
        </div>
    </header>

    <!-- Main Container -->
    <div class="main-container">
        <!-- Sidebar - Chats -->
        <aside class="sidebar">
            <div class="sidebar-header">
                <input type="text" class="search-box" placeholder="Search chats..." id="search-input" oninput="filterChats()">
                <div class="filters">
                    <span class="filter-chip active" data-filter="all" onclick="setFilter('all')">All</span>
                    <span class="filter-chip" data-filter="unread" onclick="setFilter('unread')">Unread</span>
                    <span class="filter-chip" data-filter="pinned" onclick="setFilter('pinned')">Pinned</span>
                    <select id="account-filter" class="filter-chip" style="background: var(--bg-tertiary);" onchange="filterChats()">
                        <option value="all">All Accounts</option>
                    </select>
                </div>
                <div class="filters" id="tag-filters"></div>
            </div>
            <div class="chat-list" id="chat-list">
                <div class="loading"><div class="spinner"></div></div>
            </div>
            <div style="padding: 10px; border-top: 1px solid var(--border);">
                <button class="btn btn-primary" style="width: 100%;" onclick="toggleBroadcast()">
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <polygon points="11 5 6 9 2 9 2 15 6 15 11 19 11 5"></polygon>
                        <path d="M19.07 4.93a10 10 0 0 1 0 14.14M15.54 8.46a5 5 0 0 1 0 7.07"></path>
                    </svg>
                    Broadcast Message
                </button>
            </div>
        </aside>

        <!-- Main Content - Messages -->
        <main class="content">
            <div class="empty-state" id="empty-state">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"></path>
                </svg>
                <p>Select a chat to start messaging</p>
            </div>
            <div id="chat-view" style="display: none; flex: 1; display: flex; flex-direction: column;">
                <div class="content-header">
                    <div>
                        <div class="content-title" id="current-chat-name">Chat Name</div>
                        <div class="content-subtitle" id="current-chat-info">user | account_1</div>
                    </div>
                    <div>
                        <button class="btn btn-sm btn-secondary" onclick="exportCurrentChat('markdown')">Export MD</button>
                        <button class="btn btn-sm btn-secondary" onclick="exportCurrentChat('json')">Export JSON</button>
                    </div>
                </div>
                <div class="messages-container" id="messages-container"></div>
                <div class="message-input-container">
                    <div class="reply-bar" id="reply-bar">
                        <span id="reply-preview">Replying to message</span>
                        <button class="btn btn-sm" onclick="cancelReply()">Cancel</button>
                    </div>
                    <!-- AI Suggestions Bar -->
                    <div id="ai-suggestions-bar" style="display: none; margin-bottom: 10px;">
                        <div style="font-size: 11px; color: var(--accent); margin-bottom: 6px; display: flex; justify-content: space-between; align-items: center;">
                            <span>AI Suggestions</span>
                            <button class="btn btn-sm" onclick="hideAISuggestions()" style="padding: 2px 6px;">Close</button>
                        </div>

                        <!-- Custom AI Prompt -->
                        <div style="margin-bottom: 8px; display: flex; gap: 6px;">
                            <input
                                type="text"
                                id="ai-custom-prompt"
                                placeholder="Добавь уточнение для AI (например: 'ответь формально', 'предложи встречу')"
                                style="flex: 1; padding: 6px 10px; border: 1px solid var(--border); background: var(--bg-secondary); color: var(--text-primary); border-radius: 6px; font-size: 12px;"
                            >
                            <button class="btn btn-sm btn-primary" onclick="getAISuggestionsWithPrompt()" style="padding: 6px 12px; font-size: 12px;">
                                Генерировать
                            </button>
                        </div>

                        <div id="ai-suggestions-content" style="display: flex; flex-direction: column; gap: 4px;"></div>
                    </div>
                    <div class="message-form">
                        <input type="file" id="file-input" style="display: none;" onchange="sendFile(event)">
                        <button class="attach-btn" onclick="document.getElementById('file-input').click()">
                            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                                <path d="M21.44 11.05l-9.19 9.19a6 6 0 0 1-8.49-8.49l9.19-9.19a4 4 0 0 1 5.66 5.66l-9.2 9.19a2 2 0 0 1-2.83-2.83l8.49-8.48"></path>
                            </svg>
                        </button>
                        <button class="attach-btn" id="ai-suggest-btn" onclick="getAISuggestions()" title="Get AI Suggestions" style="background: var(--accent); border-color: var(--accent); color: white;">
                            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                                <path d="M12 2a2 2 0 0 1 2 2c0 .74-.4 1.39-1 1.73V7h1a7 7 0 0 1 7 7h1a1 1 0 0 1 1 1v3a1 1 0 0 1-1 1h-1v1a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-1H2a1 1 0 0 1-1-1v-3a1 1 0 0 1 1-1h1a7 7 0 0 1 7-7h1V5.73c-.6-.34-1-.99-1-1.73a2 2 0 0 1 2-2M7.5 13A1.5 1.5 0 0 0 6 14.5A1.5 1.5 0 0 0 7.5 16A1.5 1.5 0 0 0 9 14.5A1.5 1.5 0 0 0 7.5 13m9 0a1.5 1.5 0 0 0-1.5 1.5a1.5 1.5 0 0 0 1.5 1.5a1.5 1.5 0 0 0 1.5-1.5a1.5 1.5 0 0 0-1.5-1.5"></path>
                            </svg>
                        </button>
                        <textarea class="message-input" id="message-input" placeholder="Type a message..." rows="1" onkeydown="handleKeyDown(event)"></textarea>
                        <button class="send-btn" onclick="sendMessage()">
                            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                                <line x1="22" y1="2" x2="11" y2="13"></line>
                                <polygon points="22 2 15 22 11 13 2 9 22 2"></polygon>
                            </svg>
                        </button>
                    </div>
                </div>
            </div>
        </main>

        <!-- Right Panel -->
        <aside class="right-panel">
            <div class="panel-tabs">
                <div class="panel-tab active" onclick="switchTab('crm')">CRM</div>
                <div class="panel-tab" onclick="switchTab('templates')">Templates</div>
                <div class="panel-tab" onclick="switchTab('analytics')">Analytics</div>
            </div>
            <div class="panel-content" id="panel-crm">
                <div id="crm-content">
                    <div class="empty-state" style="height: auto; padding: 40px 0;">
                        <p>Select a chat to view CRM data</p>
                    </div>
                </div>
            </div>
            <div class="panel-content" id="panel-templates" style="display: none;">
                <div class="panel-section">
                    <div class="panel-section-title">Quick Replies</div>
                    <div id="templates-list"></div>
                    <button class="btn btn-secondary" style="width: 100%; margin-top: 10px;" onclick="showAddTemplate()">+ Add Template</button>
                </div>
            </div>
            <div class="panel-content" id="panel-analytics" style="display: none;">
                <div class="analytics-grid" id="analytics-grid"></div>
                <div class="panel-section">
                    <div class="panel-section-title">Account Status</div>
                    <div id="accounts-status"></div>
                </div>
            </div>
        </aside>
    </div>

    <!-- Broadcast Panel -->
    <div class="broadcast-panel" id="broadcast-panel">
        <div class="broadcast-header">
            <strong>Broadcast Message</strong>
            <span class="broadcast-count"><span id="selected-count">0</span> chats selected</span>
        </div>
        <textarea class="broadcast-textarea" id="broadcast-text" placeholder="Enter message to broadcast..."></textarea>
        <div class="broadcast-actions">
            <button class="btn btn-secondary" onclick="toggleBroadcast()">Cancel</button>
            <button class="btn btn-primary" onclick="sendBroadcast()">Send Broadcast</button>
        </div>
    </div>

    <!-- Settings Modal -->
    <div class="modal-overlay" id="settings-modal">
        <div class="modal">
            <div class="modal-header">
                <h3 class="modal-title">Settings</h3>
                <button class="modal-close" onclick="hideSettings()">&times;</button>
            </div>
            <div class="panel-section">
                <div class="panel-section-title">Tags</div>
                <div id="tags-settings"></div>
                <button class="btn btn-secondary" style="width: 100%; margin-top: 10px;" onclick="showAddTag()">+ Add Tag</button>
            </div>
            <div class="panel-section">
                <div class="panel-section-title">Templates</div>
                <div id="templates-settings"></div>
            </div>
            <div class="panel-section">
                <div class="panel-section-title">Export</div>
                <button class="btn btn-secondary" style="width: 100%;" onclick="exportCSV()">Export All Chats to CSV</button>
            </div>
        </div>
    </div>

    <!-- Add Tag Modal -->
    <div class="modal-overlay" id="tag-modal">
        <div class="modal" style="max-width: 400px;">
            <div class="modal-header">
                <h3 class="modal-title" id="tag-modal-title">Add Tag</h3>
                <button class="modal-close" onclick="hideTagModal()">&times;</button>
            </div>
            <div class="form-group">
                <label class="form-label">Tag ID</label>
                <input type="text" class="form-input" id="tag-id" placeholder="e.g. client">
            </div>
            <div class="form-group">
                <label class="form-label">Tag Name</label>
                <input type="text" class="form-input" id="tag-name" placeholder="e.g. Client">
            </div>
            <div class="form-group">
                <label class="form-label">Color</label>
                <input type="color" class="color-picker" id="tag-color" value="#3b82f6">
            </div>
            <button class="btn btn-primary" style="width: 100%;" onclick="saveTag()">Save Tag</button>
        </div>
    </div>

    <!-- Add Template Modal -->
    <div class="modal-overlay" id="template-modal">
        <div class="modal" style="max-width: 400px;">
            <div class="modal-header">
                <h3 class="modal-title" id="template-modal-title">Add Template</h3>
                <button class="modal-close" onclick="hideTemplateModal()">&times;</button>
            </div>
            <div class="form-group">
                <label class="form-label">Template Name</label>
                <input type="text" class="form-input" id="template-name" placeholder="e.g. Greeting">
            </div>
            <div class="form-group">
                <label class="form-label">Template Text</label>
                <textarea class="form-input" id="template-text" rows="4" placeholder="Enter template text..."></textarea>
            </div>
            <button class="btn btn-primary" style="width: 100%;" onclick="saveTemplate()">Save Template</button>
        </div>
    </div>

    <!-- Review Mode Modal -->
    <div class="modal-overlay" id="review-modal">
        <div class="modal" style="max-width: 900px; max-height: 90vh; display: flex; flex-direction: column;">
            <div class="modal-header">
                <h3 class="modal-title">
                    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="margin-right: 8px;">
                        <path d="M9 11l3 3L22 4"></path>
                        <path d="M21 12v7a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11"></path>
                    </svg>
                    Review Mode
                    <span id="review-progress" style="font-size: 14px; color: var(--text-secondary); margin-left: 12px;">0/0</span>
                </h3>
                <button class="modal-close" onclick="hideReviewModal()">&times;</button>
            </div>

            <div id="review-loading" class="loading" style="padding: 40px;">
                <div class="spinner"></div>
            </div>

            <div id="review-empty" style="display: none; text-align: center; padding: 40px; color: var(--text-secondary);">
                <svg width="64" height="64" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="margin-bottom: 16px; opacity: 0.5;">
                    <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"></path>
                    <polyline points="22 4 12 14.01 9 11.01"></polyline>
                </svg>
                <p>All caught up! No chats need review.</p>
            </div>

            <div id="review-content" style="display: none; flex: 1; overflow: hidden; display: flex; flex-direction: column;">
                <!-- Chat Header -->
                <div style="padding: 16px; border-bottom: 1px solid var(--border); background: var(--bg-tertiary);">
                    <div style="display: flex; justify-content: space-between; align-items: center;">
                        <div>
                            <div style="font-size: 16px; font-weight: 600;" id="review-chat-name">Chat Name</div>
                            <div style="font-size: 12px; color: var(--text-secondary);" id="review-chat-info">account | type | 5 unread</div>
                        </div>
                        <div style="display: flex; gap: 8px;">
                            <button class="btn btn-sm btn-secondary" onclick="reviewSkip()">Skip</button>
                            <button class="btn btn-sm btn-secondary" onclick="reviewLater()">Later</button>
                        </div>
                    </div>

                    <!-- AI Analysis -->
                    <div id="review-ai-analysis" style="margin-top: 12px; padding: 12px; background: var(--bg-secondary); border-radius: 8px; display: none;">
                        <div style="font-size: 11px; text-transform: uppercase; color: var(--accent); margin-bottom: 8px; font-weight: 600;">
                            AI Analysis
                        </div>
                        <div id="review-ai-summary" style="font-size: 13px; margin-bottom: 8px;"></div>
                        <div style="display: flex; gap: 8px; flex-wrap: wrap;">
                            <span id="review-ai-urgency" class="chat-tag" style="font-size: 11px;"></span>
                            <span id="review-ai-sentiment" class="chat-tag" style="font-size: 11px;"></span>
                        </div>
                    </div>
                </div>

                <!-- Messages -->
                <div id="review-messages" style="flex: 1; overflow-y: auto; padding: 16px; max-height: 300px;">
                </div>

                <!-- AI Suggestions -->
                <div id="review-suggestions" style="padding: 12px 16px; border-top: 1px solid var(--border); background: var(--bg-secondary);">
                    <div style="font-size: 11px; text-transform: uppercase; color: var(--text-secondary); margin-bottom: 8px;">
                        AI Suggestions (click to use)
                    </div>
                    <div id="review-suggestions-list" style="display: flex; flex-direction: column; gap: 6px;">
                    </div>
                </div>

                <!-- Reply Input -->
                <div style="padding: 16px; border-top: 1px solid var(--border);">
                    <textarea id="review-reply-input" class="form-input" rows="3" placeholder="Type your reply..." style="margin-bottom: 12px;"></textarea>
                    <div style="display: flex; gap: 8px; justify-content: flex-end;">
                        <button class="btn btn-secondary" onclick="reviewSaveDraft()">
                            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                                <path d="M19 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11l5 5v11a2 2 0 0 1-2 2z"></path>
                                <polyline points="17 21 17 13 7 13 7 21"></polyline>
                                <polyline points="7 3 7 8 15 8"></polyline>
                            </svg>
                            Save Draft
                        </button>
                        <button class="btn btn-primary" onclick="reviewSendAndNext()">
                            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                                <line x1="22" y1="2" x2="11" y2="13"></line>
                                <polygon points="22 2 15 22 11 13 2 9 22 2"></polygon>
                            </svg>
                            Send & Next
                        </button>
                    </div>
                </div>
            </div>
        </div>
    </div>

    <!-- Drafts Panel Modal -->
    <div class="modal-overlay" id="drafts-modal">
        <div class="modal" style="max-width: 600px;">
            <div class="modal-header">
                <h3 class="modal-title">Drafts</h3>
                <button class="modal-close" onclick="hideDraftsModal()">&times;</button>
            </div>
            <div id="drafts-list" style="max-height: 400px; overflow-y: auto;">
                <div class="loading"><div class="spinner"></div></div>
            </div>
        </div>
    </div>

    <!-- Toast Container -->
    <div class="toast-container" id="toast-container"></div>

    <script>
        // State
        let dialogs = [];
        let reviewQueue = [];
        let reviewIndex = 0;
        let currentReviewChat = null;
        let aiAvailable = false;
        let tags = [];
        let templates = [];
        let currentChat = null;
        let currentFilter = 'all';
        let replyToMessage = null;
        let broadcastMode = false;
        let selectedChats = new Set();
        let editingTagId = null;
        let editingTemplateId = null;

        // Initialize
        document.addEventListener('DOMContentLoaded', () => {
            loadData();
            setInterval(loadData, 30000); // Refresh every 30s
        });

        async function loadData() {
            try {
                const [dialogsRes, tagsRes, templatesRes, statsRes] = await Promise.all([
                    fetch('/api/dialogs').then(r => r.json()),
                    fetch('/api/tags').then(r => r.json()),
                    fetch('/api/templates').then(r => r.json()),
                    fetch('/api/statistics').then(r => r.json())
                ]);

                dialogs = dialogsRes;
                tags = tagsRes;
                templates = templatesRes;

                updateStats(statsRes);
                renderChatList();
                renderTagFilters();
                renderTemplates();
                renderAnalytics(statsRes);
                updateAccountFilter();

            } catch (e) {
                console.error('Error loading data:', e);
                showToast('Failed to load data', 'error');
            }
        }

        function updateStats(stats) {
            document.getElementById('stat-accounts').textContent = stats.accounts_connected;
            document.getElementById('stat-chats').textContent = dialogs.length;
            document.getElementById('stat-unread').textContent = dialogs.filter(d => d.unread_count > 0).length;
        }

        function updateAccountFilter() {
            const select = document.getElementById('account-filter');
            const accounts = [...new Set(dialogs.map(d => d.account))];
            select.innerHTML = '<option value="all">All Accounts</option>';
            accounts.forEach(acc => {
                select.innerHTML += `<option value="${acc}">${acc}</option>`;
            });
        }

        function renderChatList() {
            const container = document.getElementById('chat-list');
            const search = document.getElementById('search-input').value.toLowerCase();
            const accountFilter = document.getElementById('account-filter').value;

            let filtered = dialogs.filter(d => {
                if (search && !d.name.toLowerCase().includes(search)) return false;
                if (accountFilter !== 'all' && d.account !== accountFilter) return false;
                if (currentFilter === 'unread' && d.unread_count === 0) return false;
                if (currentFilter === 'pinned' && !d.crm?.pinned) return false;
                if (currentFilter.startsWith('tag:')) {
                    const tagId = currentFilter.split(':')[1];
                    if (!d.crm?.tags?.includes(tagId)) return false;
                }
                return true;
            });

            // Sort: pinned first, then by date
            filtered.sort((a, b) => {
                if (a.crm?.pinned && !b.crm?.pinned) return -1;
                if (!a.crm?.pinned && b.crm?.pinned) return 1;
                return (b.last_message_date || '').localeCompare(a.last_message_date || '');
            });

            container.innerHTML = filtered.map(d => {
                const initial = (d.name || '?')[0].toUpperCase();
                const lastMsg = d.last_message?.text || '';
                const time = d.last_message_date ? formatTime(d.last_message_date) : '';
                const chatTags = (d.crm?.tags || []).map(tid => {
                    const tag = tags.find(t => t.id === tid);
                    return tag ? `<span class="chat-tag" style="background: ${tag.color}">${tag.name}</span>` : '';
                }).join('');

                const isActive = currentChat && currentChat.id === d.id && currentChat.account === d.account;
                const isPinned = d.crm?.pinned;

                return `
                    <div class="chat-item ${isActive ? 'active' : ''} ${isPinned ? 'pinned' : ''}"
                         onclick="selectChat('${d.account}', ${d.id})"
                         data-account="${d.account}" data-id="${d.id}">
                        ${broadcastMode ? `<input type="checkbox" class="chat-checkbox"
                            ${selectedChats.has(d.account + ':' + d.id) ? 'checked' : ''}
                            onclick="toggleChatSelection(event, '${d.account}', ${d.id})">` : ''}
                        <div class="chat-avatar" style="background: hsl(${d.id % 360}, 50%, 30%)">${initial}</div>
                        <div class="chat-info">
                            <div class="chat-header">
                                <span class="chat-name">${escapeHtml(d.name)}</span>
                                <span class="chat-time">${time}</span>
                            </div>
                            <div class="chat-preview">${escapeHtml(lastMsg.substring(0, 50))}</div>
                            <div class="chat-meta">
                                <span class="chat-account">${d.account}</span>
                                ${d.unread_count > 0 ? `<span class="chat-badge">${d.unread_count}</span>` : ''}
                                ${chatTags}
                            </div>
                        </div>
                    </div>
                `;
            }).join('');
        }

        function renderTagFilters() {
            const container = document.getElementById('tag-filters');
            container.innerHTML = tags.map(t => `
                <span class="filter-chip ${currentFilter === 'tag:' + t.id ? 'active' : ''}"
                      style="background: ${t.color}20; border-color: ${t.color}"
                      onclick="setFilter('tag:${t.id}')">${t.name}</span>
            `).join('');
        }

        function setFilter(filter) {
            currentFilter = filter;
            document.querySelectorAll('.filter-chip').forEach(c => c.classList.remove('active'));
            document.querySelector(`.filter-chip[data-filter="${filter}"]`)?.classList.add('active');
            if (filter.startsWith('tag:')) {
                document.querySelector(`.filter-chip[onclick="setFilter('${filter}')"]`)?.classList.add('active');
            }
            renderChatList();
        }

        function filterChats() {
            renderChatList();
        }

        async function selectChat(account, chatId) {
            currentChat = { account, id: chatId };

            document.getElementById('empty-state').style.display = 'none';
            document.getElementById('chat-view').style.display = 'flex';

            const chat = dialogs.find(d => d.account === account && d.id === chatId);
            document.getElementById('current-chat-name').textContent = chat?.name || 'Unknown';
            document.getElementById('current-chat-info').textContent = `${chat?.type || 'chat'} | ${account}`;

            renderChatList();
            renderCRMPanel(chat);

            // Load messages
            try {
                const messages = await fetch(`/api/messages/${account}/${chatId}?limit=50`).then(r => r.json());
                renderMessages(messages);
            } catch (e) {
                console.error('Error loading messages:', e);
            }
        }

        function renderMessages(messages) {
            const container = document.getElementById('messages-container');
            container.innerHTML = messages.reverse().map(m => {
                const time = formatTime(m.date);
                const mediaHtml = m.has_media ? renderMediaPreview(m) : '';

                return `
                    <div class="message ${m.is_outgoing ? 'outgoing' : 'incoming'}" onclick="setReply(${m.id}, '${escapeHtml(m.text?.substring(0, 30) || '')}')">
                        ${mediaHtml}
                        ${m.text ? `<div>${escapeHtml(m.text)}</div>` : ''}
                        <div class="message-time">${time}</div>
                    </div>
                `;
            }).join('');

            container.scrollTop = container.scrollHeight;
        }

        function renderMediaPreview(msg) {
            if (!msg.media) return '';

            const type = msg.media.type;
            if (type === 'photo' || type === 'image') {
                return `
                    <div class="message-media">
                        <div class="media-placeholder" onclick="loadMedia(${msg.id})">
                            <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                                <rect x="3" y="3" width="18" height="18" rx="2" ry="2"></rect>
                                <circle cx="8.5" cy="8.5" r="1.5"></circle>
                                <polyline points="21 15 16 10 5 21"></polyline>
                            </svg>
                            <span>Click to load image</span>
                        </div>
                    </div>
                `;
            } else if (type === 'video') {
                return `<div class="media-placeholder"><span>Video: ${msg.media.filename || 'video'}</span></div>`;
            } else if (type === 'document') {
                return `<div class="media-placeholder"><span>File: ${msg.media.filename || 'document'}</span></div>`;
            } else if (type === 'voice') {
                return `<div class="media-placeholder"><span>Voice message</span></div>`;
            }

            return `<div class="media-placeholder"><span>${type}</span></div>`;
        }

        async function loadMedia(messageId) {
            if (!currentChat) return;

            try {
                const media = await fetch(`/api/media/${currentChat.account}/${currentChat.id}/${messageId}`).then(r => r.json());
                if (media.data) {
                    const img = document.createElement('img');
                    img.src = `data:image/jpeg;base64,${media.data}`;
                    img.style.maxWidth = '100%';
                    img.style.borderRadius = '8px';

                    // Find and replace placeholder
                    const placeholder = document.querySelector(`.message-media .media-placeholder[onclick="loadMedia(${messageId})"]`);
                    if (placeholder) {
                        placeholder.parentElement.innerHTML = '';
                        placeholder.parentElement.appendChild(img);
                    }
                }
            } catch (e) {
                console.error('Error loading media:', e);
            }
        }

        function renderCRMPanel(chat) {
            if (!chat) {
                document.getElementById('crm-content').innerHTML = '<div class="empty-state"><p>Select a chat</p></div>';
                return;
            }

            const crm = chat.crm || {};
            const chatTags = crm.tags || [];

            document.getElementById('crm-content').innerHTML = `
                <div class="panel-section">
                    <div class="panel-section-title">Status</div>
                    <select class="crm-status-select" onchange="updateStatus(this.value)">
                        <option value="" ${!crm.status ? 'selected' : ''}>No status</option>
                        <option value="new" ${crm.status === 'new' ? 'selected' : ''}>New</option>
                        <option value="active" ${crm.status === 'active' ? 'selected' : ''}>Active</option>
                        <option value="waiting" ${crm.status === 'waiting' ? 'selected' : ''}>Waiting</option>
                        <option value="resolved" ${crm.status === 'resolved' ? 'selected' : ''}>Resolved</option>
                        <option value="closed" ${crm.status === 'closed' ? 'selected' : ''}>Closed</option>
                    </select>
                </div>

                <div class="panel-section">
                    <div class="panel-section-title">Tags</div>
                    <div class="tag-list">
                        ${tags.map(t => `
                            <span class="tag-item ${chatTags.includes(t.id) ? 'selected' : ''}"
                                  style="background: ${t.color}${chatTags.includes(t.id) ? '' : '40'}"
                                  onclick="toggleTag('${t.id}')">${t.name}</span>
                        `).join('')}
                    </div>
                </div>

                <div class="panel-section">
                    <div class="panel-section-title">Notes</div>
                    <textarea class="crm-notes" placeholder="Add notes..." onblur="updateNotes(this.value)">${crm.notes || ''}</textarea>
                </div>

                <div class="panel-section">
                    <button class="btn ${crm.pinned ? 'btn-primary' : 'btn-secondary'}" style="width: 100%;" onclick="togglePin()">
                        ${crm.pinned ? 'Unpin Chat' : 'Pin Chat'}
                    </button>
                </div>
            `;
        }

        function renderTemplates() {
            const list = document.getElementById('templates-list');
            list.innerHTML = templates.map(t => `
                <div class="template-item" onclick="useTemplate('${escapeHtml(t.text)}')">
                    <div class="template-name">${escapeHtml(t.name)}</div>
                    <div class="template-text">${escapeHtml(t.text.substring(0, 50))}${t.text.length > 50 ? '...' : ''}</div>
                </div>
            `).join('');
        }

        function renderAnalytics(stats) {
            const grid = document.getElementById('analytics-grid');
            grid.innerHTML = `
                <div class="analytics-card">
                    <div class="analytics-value">${stats.accounts_connected}/${stats.accounts_total}</div>
                    <div class="analytics-label">Accounts Connected</div>
                </div>
                <div class="analytics-card">
                    <div class="analytics-value">${stats.messages_sent_total}</div>
                    <div class="analytics-label">Messages Sent</div>
                </div>
                <div class="analytics-card">
                    <div class="analytics-value">${stats.reconnects_total}</div>
                    <div class="analytics-label">Reconnections</div>
                </div>
                <div class="analytics-card">
                    <div class="analytics-value">${stats.flood_waits_total}</div>
                    <div class="analytics-label">Flood Waits</div>
                </div>
            `;

            const accountsStatus = document.getElementById('accounts-status');
            accountsStatus.innerHTML = stats.accounts.map(acc => `
                <div class="settings-item">
                    <div class="settings-item-info">
                        <div class="settings-item-name">${acc.name}</div>
                        <div class="settings-item-desc">${acc.user_info?.first_name || 'Unknown'} ${acc.user_info?.last_name || ''}</div>
                    </div>
                    <span style="color: ${acc.connected ? 'var(--success)' : 'var(--danger)'}">
                        ${acc.connected ? 'Connected' : 'Disconnected'}
                    </span>
                </div>
            `).join('');
        }

        // Actions
        async function sendMessage() {
            if (!currentChat) return;

            const input = document.getElementById('message-input');
            const text = input.value.trim();
            if (!text) return;

            try {
                const result = await fetch('/api/send', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        account: currentChat.account,
                        chat_id: currentChat.id,
                        text: text,
                        reply_to: replyToMessage
                    })
                }).then(r => r.json());

                if (result.success) {
                    input.value = '';
                    cancelReply();
                    selectChat(currentChat.account, currentChat.id);
                    showToast('Message sent', 'success');
                } else {
                    showToast('Failed: ' + result.error, 'error');
                }
            } catch (e) {
                showToast('Error sending message', 'error');
            }
        }

        async function sendFile(event) {
            if (!currentChat) return;

            const file = event.target.files[0];
            if (!file) return;

            const formData = new FormData();
            formData.append('file', file);

            try {
                const result = await fetch(`/api/send-file?account=${currentChat.account}&chat_id=${currentChat.id}`, {
                    method: 'POST',
                    body: formData
                }).then(r => r.json());

                if (result.success) {
                    selectChat(currentChat.account, currentChat.id);
                    showToast('File sent', 'success');
                } else {
                    showToast('Failed: ' + result.error, 'error');
                }
            } catch (e) {
                showToast('Error sending file', 'error');
            }

            event.target.value = '';
        }

        function handleKeyDown(event) {
            if (event.key === 'Enter' && !event.shiftKey) {
                event.preventDefault();
                sendMessage();
            }
        }

        function setReply(msgId, preview) {
            replyToMessage = msgId;
            document.getElementById('reply-preview').textContent = 'Replying to: ' + preview;
            document.getElementById('reply-bar').classList.add('active');
        }

        function cancelReply() {
            replyToMessage = null;
            document.getElementById('reply-bar').classList.remove('active');
        }

        async function toggleTag(tagId) {
            if (!currentChat) return;

            const chat = dialogs.find(d => d.account === currentChat.account && d.id === currentChat.id);
            const chatTags = chat?.crm?.tags || [];
            const hasTag = chatTags.includes(tagId);

            await fetch(`/api/crm/tag/${hasTag ? 'remove' : 'add'}`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    account: currentChat.account,
                    chat_id: currentChat.id,
                    tag_id: tagId
                })
            });

            loadData();
        }

        async function updateStatus(status) {
            if (!currentChat) return;

            await fetch('/api/crm/status', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    account: currentChat.account,
                    chat_id: currentChat.id,
                    status: status
                })
            });
        }

        async function updateNotes(notes) {
            if (!currentChat) return;

            await fetch('/api/crm/notes', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    account: currentChat.account,
                    chat_id: currentChat.id,
                    notes: notes
                })
            });
        }

        async function togglePin() {
            if (!currentChat) return;

            await fetch('/api/crm/pin', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    account: currentChat.account,
                    chat_id: currentChat.id
                })
            });

            loadData();
        }

        function useTemplate(text) {
            document.getElementById('message-input').value = text;
            document.getElementById('message-input').focus();
        }

        // Broadcast
        function toggleBroadcast() {
            broadcastMode = !broadcastMode;
            selectedChats.clear();
            document.getElementById('broadcast-panel').classList.toggle('active', broadcastMode);
            document.getElementById('selected-count').textContent = '0';
            renderChatList();
        }

        function toggleChatSelection(event, account, chatId) {
            event.stopPropagation();
            const key = account + ':' + chatId;
            if (selectedChats.has(key)) {
                selectedChats.delete(key);
            } else {
                selectedChats.add(key);
            }
            document.getElementById('selected-count').textContent = selectedChats.size;
        }

        async function sendBroadcast() {
            if (selectedChats.size === 0) {
                showToast('No chats selected', 'warning');
                return;
            }

            const text = document.getElementById('broadcast-text').value.trim();
            if (!text) {
                showToast('Enter message text', 'warning');
                return;
            }

            const targets = Array.from(selectedChats).map(key => {
                const [account, chat_id] = key.split(':');
                return { account, chat_id: parseInt(chat_id) };
            });

            showToast(`Sending to ${targets.length} chats...`, 'warning');

            try {
                const result = await fetch('/api/broadcast', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ targets, text, delay: 3.0 })
                }).then(r => r.json());

                showToast(`Broadcast: ${result.sent}/${result.total} sent`, result.failed > 0 ? 'warning' : 'success');
                toggleBroadcast();
                document.getElementById('broadcast-text').value = '';
            } catch (e) {
                showToast('Broadcast failed', 'error');
            }
        }

        // Export
        async function exportCurrentChat(format) {
            if (!currentChat) return;

            try {
                const result = await fetch('/api/export/chat', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        account: currentChat.account,
                        chat_id: currentChat.id,
                        format: format,
                        limit: 200
                    })
                }).then(r => r.json());

                showToast(`Exported to: ${result.filepath}`, 'success');
            } catch (e) {
                showToast('Export failed', 'error');
            }
        }

        function exportCSV() {
            window.location.href = '/api/export/csv';
        }

        async function syncData() {
            try {
                await fetch('/api/sync', { method: 'POST' });
                showToast('Data synced', 'success');
                loadData();
            } catch (e) {
                showToast('Sync failed', 'error');
            }
        }

        // Settings
        function showSettings() {
            document.getElementById('settings-modal').classList.add('active');
            renderSettingsTags();
            renderSettingsTemplates();
        }

        function hideSettings() {
            document.getElementById('settings-modal').classList.remove('active');
        }

        function renderSettingsTags() {
            const container = document.getElementById('tags-settings');
            container.innerHTML = tags.map(t => `
                <div class="settings-item">
                    <div class="settings-item-info">
                        <div class="settings-item-name" style="color: ${t.color}">${t.name}</div>
                        <div class="settings-item-desc">ID: ${t.id}</div>
                    </div>
                    <div>
                        <button class="btn btn-sm btn-secondary" onclick="editTag('${t.id}')">Edit</button>
                        <button class="btn btn-sm btn-danger" onclick="deleteTag('${t.id}')">Delete</button>
                    </div>
                </div>
            `).join('');
        }

        function renderSettingsTemplates() {
            const container = document.getElementById('templates-settings');
            container.innerHTML = templates.map(t => `
                <div class="settings-item">
                    <div class="settings-item-info">
                        <div class="settings-item-name">${t.name}</div>
                        <div class="settings-item-desc">${t.text.substring(0, 40)}...</div>
                    </div>
                    <div>
                        <button class="btn btn-sm btn-secondary" onclick="editTemplate('${t.id}')">Edit</button>
                        <button class="btn btn-sm btn-danger" onclick="deleteTemplate('${t.id}')">Delete</button>
                    </div>
                </div>
            `).join('');
        }

        function showAddTag() {
            editingTagId = null;
            document.getElementById('tag-modal-title').textContent = 'Add Tag';
            document.getElementById('tag-id').value = '';
            document.getElementById('tag-id').disabled = false;
            document.getElementById('tag-name').value = '';
            document.getElementById('tag-color').value = '#3b82f6';
            document.getElementById('tag-modal').classList.add('active');
        }

        function editTag(tagId) {
            const tag = tags.find(t => t.id === tagId);
            if (!tag) return;

            editingTagId = tagId;
            document.getElementById('tag-modal-title').textContent = 'Edit Tag';
            document.getElementById('tag-id').value = tag.id;
            document.getElementById('tag-id').disabled = true;
            document.getElementById('tag-name').value = tag.name;
            document.getElementById('tag-color').value = tag.color;
            document.getElementById('tag-modal').classList.add('active');
        }

        function hideTagModal() {
            document.getElementById('tag-modal').classList.remove('active');
        }

        async function saveTag() {
            const id = document.getElementById('tag-id').value.trim();
            const name = document.getElementById('tag-name').value.trim();
            const color = document.getElementById('tag-color').value;

            if (!id || !name) {
                showToast('Fill all fields', 'warning');
                return;
            }

            try {
                if (editingTagId) {
                    await fetch(`/api/tags/${editingTagId}`, {
                        method: 'PUT',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ tag_id: id, name, color })
                    });
                } else {
                    await fetch('/api/tags', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ tag_id: id, name, color })
                    });
                }

                hideTagModal();
                loadData();
                renderSettingsTags();
                showToast('Tag saved', 'success');
            } catch (e) {
                showToast('Error saving tag', 'error');
            }
        }

        async function deleteTag(tagId) {
            if (!confirm('Delete this tag?')) return;

            try {
                await fetch(`/api/tags/${tagId}`, { method: 'DELETE' });
                loadData();
                renderSettingsTags();
                showToast('Tag deleted', 'success');
            } catch (e) {
                showToast('Error deleting tag', 'error');
            }
        }

        function showAddTemplate() {
            editingTemplateId = null;
            document.getElementById('template-modal-title').textContent = 'Add Template';
            document.getElementById('template-name').value = '';
            document.getElementById('template-text').value = '';
            document.getElementById('template-modal').classList.add('active');
        }

        function editTemplate(templateId) {
            const template = templates.find(t => t.id === templateId);
            if (!template) return;

            editingTemplateId = templateId;
            document.getElementById('template-modal-title').textContent = 'Edit Template';
            document.getElementById('template-name').value = template.name;
            document.getElementById('template-text').value = template.text;
            document.getElementById('template-modal').classList.add('active');
        }

        function hideTemplateModal() {
            document.getElementById('template-modal').classList.remove('active');
        }

        async function saveTemplate() {
            const name = document.getElementById('template-name').value.trim();
            const text = document.getElementById('template-text').value.trim();

            if (!name || !text) {
                showToast('Fill all fields', 'warning');
                return;
            }

            try {
                if (editingTemplateId) {
                    await fetch(`/api/templates/${editingTemplateId}`, {
                        method: 'PUT',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ name, text })
                    });
                } else {
                    await fetch('/api/templates', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ name, text })
                    });
                }

                hideTemplateModal();
                loadData();
                renderSettingsTemplates();
                showToast('Template saved', 'success');
            } catch (e) {
                showToast('Error saving template', 'error');
            }
        }

        async function deleteTemplate(templateId) {
            if (!confirm('Delete this template?')) return;

            try {
                await fetch(`/api/templates/${templateId}`, { method: 'DELETE' });
                loadData();
                renderSettingsTemplates();
                showToast('Template deleted', 'success');
            } catch (e) {
                showToast('Error deleting template', 'error');
            }
        }

        // Tabs
        function switchTab(tab) {
            document.querySelectorAll('.panel-tab').forEach(t => t.classList.remove('active'));
            document.querySelectorAll('.panel-content').forEach(c => c.style.display = 'none');

            document.querySelector(`.panel-tab[onclick="switchTab('${tab}')"]`).classList.add('active');
            document.getElementById(`panel-${tab}`).style.display = 'block';
        }

        // Utils
        function formatTime(isoDate) {
            const date = new Date(isoDate);
            const now = new Date();
            const diff = now - date;

            if (diff < 86400000 && date.getDate() === now.getDate()) {
                return date.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit', hour12: false });
            } else if (diff < 604800000) {
                return date.toLocaleDateString('en-US', { weekday: 'short' });
            } else {
                return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
            }
        }

        function escapeHtml(text) {
            if (!text) return '';
            return text.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
        }

        function showToast(message, type = 'info') {
            const container = document.getElementById('toast-container');
            const toast = document.createElement('div');
            toast.className = `toast ${type}`;
            toast.textContent = message;
            container.appendChild(toast);

            setTimeout(() => toast.remove(), 3000);
        }

        // ============================================================
        // AI Suggest Functions (for chat view)
        // ============================================================

        async function getAISuggestions() {
            if (!currentChat) {
                showToast('Select a chat first', 'warning');
                return;
            }

            const btn = document.getElementById('ai-suggest-btn');
            const originalContent = btn.innerHTML;
            btn.innerHTML = '<div class="spinner" style="width: 16px; height: 16px;"></div>';
            btn.disabled = true;

            try {
                const result = await fetch('/api/ai/suggest', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        account: currentChat.account,
                        chat_id: currentChat.id,
                        num_suggestions: 3
                    })
                }).then(r => r.json());

                if (result.suggestions && result.suggestions.length > 0) {
                    showAISuggestions(result.suggestions);
                } else if (result.detail) {
                    showToast(result.detail, 'warning');
                } else {
                    showToast('No suggestions available', 'warning');
                }
            } catch (e) {
                showToast('AI suggestions failed', 'error');
            } finally {
                btn.innerHTML = originalContent;
                btn.disabled = false;
            }
        }

        async function getAISuggestionsWithPrompt() {
            if (!currentChat) {
                showToast('Select a chat first', 'warning');
                return;
            }

            const customPrompt = document.getElementById('ai-custom-prompt').value.trim();
            if (!customPrompt) {
                showToast('Enter a custom prompt', 'warning');
                return;
            }

            const content = document.getElementById('ai-suggestions-content');
            content.innerHTML = '<div class="loading"><div class="spinner"></div></div>';

            try {
                const result = await fetch('/api/ai/custom', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        account: currentChat.account,
                        chat_id: currentChat.id,
                        custom_prompt: customPrompt,
                        num_suggestions: 3
                    })
                }).then(r => r.json());

                if (result.suggestions && result.suggestions.length > 0) {
                    displaySuggestions(result.suggestions);
                    showToast('Варианты сгенерированы', 'success');
                } else {
                    content.innerHTML = '<div style="text-align: center; padding: 16px; color: var(--text-secondary);">No suggestions</div>';
                }
            } catch (e) {
                content.innerHTML = '<div style="text-align: center; padding: 16px; color: var(--danger);">Error generating suggestions</div>';
                showToast('AI request failed', 'error');
            }
        }

        function displaySuggestions(suggestions) {
            const content = document.getElementById('ai-suggestions-content');

            content.innerHTML = suggestions.map((s, idx) => `
                <div data-suggestion-idx="${idx}" class="ai-suggestion-item" style="padding: 10px 12px; background: var(--bg-tertiary); border-radius: 8px; cursor: default; font-size: 13px; margin-bottom: 8px; border: 1px solid var(--border);">
                    <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 6px;">
                        <span style="font-size: 10px; color: var(--text-muted); text-transform: uppercase;">${s.tone}</span>
                        <button class="btn btn-sm btn-primary" onclick="saveSuggestionToDraft(${idx})" style="padding: 3px 8px; font-size: 11px;">
                            Сохранить
                        </button>
                    </div>
                    <div class="suggestion-text">${escapeHtml(s.text)}</div>
                </div>
            `).join('');

            // Store suggestions for later use
            window.currentAISuggestions = suggestions;
        }

        async function saveSuggestionToDraft(idx) {
            if (!window.currentAISuggestions || !window.currentAISuggestions[idx]) {
                showToast('Suggestion not found', 'error');
                return;
            }

            const suggestion = window.currentAISuggestions[idx];

            try {
                const result = await fetch('/api/drafts', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        account: currentChat.account,
                        chat_id: currentChat.id,
                        chat_name: currentChat.name,
                        text: suggestion.text,
                        suggested_by: 'ai_custom'
                    })
                }).then(r => r.json());

                showToast('Сохранено в черновики', 'success');
            } catch (e) {
                showToast('Failed to save draft', 'error');
            }
        }

        function showAISuggestions(suggestions) {
            const bar = document.getElementById('ai-suggestions-bar');
            const content = document.getElementById('ai-suggestions-content');

            content.innerHTML = suggestions.map((s, idx) => `
                <div data-suggestion-idx="${idx}" class="ai-suggestion-item"
                     style="padding: 8px 12px; background: var(--bg-tertiary); border-radius: 8px; cursor: pointer; font-size: 13px; transition: background 0.2s;"
                     onmouseover="this.style.background='var(--bg-hover)'"
                     onmouseout="this.style.background='var(--bg-tertiary)'">
                    <span style="font-size: 10px; color: var(--text-muted); display: block; margin-bottom: 2px;">${s.tone}</span>
                    ${escapeHtml(s.text).substring(0, 100)}${s.text.length > 100 ? '...' : ''}
                </div>
            `).join('');

            // Store suggestions globally for safe access
            window.currentAISuggestions = suggestions;

            // Add click handlers
            content.querySelectorAll('.ai-suggestion-item').forEach(el => {
                el.addEventListener('click', () => {
                    const idx = parseInt(el.dataset.suggestionIdx);
                    useAISuggestion(window.currentAISuggestions[idx].text);
                });
            });

            bar.style.display = 'block';
        }

        function hideAISuggestions() {
            document.getElementById('ai-suggestions-bar').style.display = 'none';
        }

        function useAISuggestion(text) {
            document.getElementById('message-input').value = text;
            document.getElementById('message-input').focus();
            hideAISuggestions();
        }

        // ============================================================
        // Review Mode Functions
        // ============================================================

        async function checkAIStatus() {
            try {
                const res = await fetch('/api/ai/status').then(r => r.json());
                aiAvailable = res.available;
                return res;
            } catch (e) {
                aiAvailable = false;
                return { available: false };
            }
        }

        async function showReviewModal() {
            document.getElementById('review-modal').classList.add('active');
            document.getElementById('review-loading').style.display = 'flex';
            document.getElementById('review-empty').style.display = 'none';
            document.getElementById('review-content').style.display = 'none';

            try {
                // Check AI status first
                await checkAIStatus();

                // Load review queue
                const res = await fetch('/api/review/queue').then(r => r.json());
                reviewQueue = res.queue;
                reviewIndex = 0;

                if (reviewQueue.length === 0) {
                    document.getElementById('review-loading').style.display = 'none';
                    document.getElementById('review-empty').style.display = 'block';
                } else {
                    await loadReviewChat(0);
                }
            } catch (e) {
                console.error('Error loading review queue:', e);
                showToast('Failed to load review queue', 'error');
                hideReviewModal();
            }
        }

        function hideReviewModal() {
            document.getElementById('review-modal').classList.remove('active');
            reviewQueue = [];
            reviewIndex = 0;
            currentReviewChat = null;
        }

        async function loadReviewChat(index) {
            if (index >= reviewQueue.length) {
                document.getElementById('review-loading').style.display = 'none';
                document.getElementById('review-content').style.display = 'none';
                document.getElementById('review-empty').style.display = 'block';
                return;
            }

            document.getElementById('review-loading').style.display = 'flex';
            document.getElementById('review-content').style.display = 'none';

            const chat = reviewQueue[index];
            currentReviewChat = chat;
            reviewIndex = index;

            // Update progress
            document.getElementById('review-progress').textContent = `${index + 1}/${reviewQueue.length}`;

            try {
                // Load detailed chat info with AI analysis
                const details = await fetch(`/api/review/chat/${chat.account}/${chat.id}`).then(r => r.json());

                // Update header
                document.getElementById('review-chat-name').textContent = chat.name || 'Unknown';
                document.getElementById('review-chat-info').textContent =
                    `${chat.account} | ${chat.type} | ${chat.unread_count} unread`;

                // Update AI analysis if available
                const aiAnalysis = document.getElementById('review-ai-analysis');
                if (details.ai_analysis && !details.ai_analysis.error) {
                    aiAnalysis.style.display = 'block';
                    document.getElementById('review-ai-summary').textContent = details.ai_analysis.summary || '';

                    const urgency = details.ai_analysis.urgency || 'low';
                    const urgencyEl = document.getElementById('review-ai-urgency');
                    urgencyEl.textContent = `Urgency: ${urgency}`;
                    urgencyEl.style.background = urgency === 'high' ? 'var(--danger)' :
                                                 urgency === 'medium' ? 'var(--warning)' : 'var(--text-muted)';

                    const sentiment = details.ai_analysis.sentiment || 'neutral';
                    const sentimentEl = document.getElementById('review-ai-sentiment');
                    sentimentEl.textContent = `Sentiment: ${sentiment}`;
                    sentimentEl.style.background = sentiment === 'positive' ? 'var(--success)' :
                                                   sentiment === 'negative' ? 'var(--danger)' : 'var(--text-muted)';
                } else {
                    aiAnalysis.style.display = 'none';
                }

                // Render messages
                const messagesContainer = document.getElementById('review-messages');
                const messages = details.messages || [];
                messagesContainer.innerHTML = messages.slice(-20).reverse().map(m => {
                    const time = formatTime(m.date);
                    return `
                        <div class="message ${m.is_outgoing ? 'outgoing' : 'incoming'}" style="max-width: 80%;">
                            ${m.text ? `<div>${escapeHtml(m.text)}</div>` : '<div style="color: var(--text-muted);">[media]</div>'}
                            <div class="message-time">${time}</div>
                        </div>
                    `;
                }).join('');
                messagesContainer.scrollTop = messagesContainer.scrollHeight;

                // Render AI suggestions
                const suggestionsContainer = document.getElementById('review-suggestions');
                const suggestionsList = document.getElementById('review-suggestions-list');

                if (details.ai_suggestions && details.ai_suggestions.length > 0) {
                    suggestionsContainer.style.display = 'block';
                    suggestionsList.innerHTML = details.ai_suggestions.map((s, i) => `
                        <div class="suggestion-item" data-suggestion-idx="${i}">
                            <span class="suggestion-tone" style="font-size: 10px; color: var(--text-muted); margin-right: 8px;">${s.tone}</span>
                            ${escapeHtml(s.text)}
                        </div>
                    `).join('');

                    // Store suggestions for review mode
                    window.currentReviewSuggestions = details.ai_suggestions;

                    // Add click handlers
                    suggestionsList.querySelectorAll('.suggestion-item').forEach(el => {
                        el.addEventListener('click', () => {
                            const idx = parseInt(el.dataset.suggestionIdx);
                            useSuggestion(window.currentReviewSuggestions[idx].text);
                        });
                    });

                    // Add CSS for suggestion items if not already added
                    if (!document.getElementById('suggestion-styles')) {
                        const style = document.createElement('style');
                        style.id = 'suggestion-styles';
                        style.textContent = `
                            .suggestion-item {
                                padding: 10px 12px;
                                background: var(--bg-tertiary);
                                border-radius: 8px;
                                cursor: pointer;
                                font-size: 13px;
                                transition: background 0.2s;
                            }
                            .suggestion-item:hover {
                                background: var(--bg-hover);
                            }
                        `;
                        document.head.appendChild(style);
                    }
                } else {
                    suggestionsContainer.style.display = 'none';
                }

                // Clear reply input
                document.getElementById('review-reply-input').value = '';

                // Show content
                document.getElementById('review-loading').style.display = 'none';
                document.getElementById('review-content').style.display = 'flex';

            } catch (e) {
                console.error('Error loading review chat:', e);
                showToast('Failed to load chat details', 'error');
                reviewSkip(); // Move to next
            }
        }

        function useSuggestion(text) {
            document.getElementById('review-reply-input').value = text;
            document.getElementById('review-reply-input').focus();
        }

        async function reviewSendAndNext() {
            const text = document.getElementById('review-reply-input').value.trim();
            if (!text) {
                showToast('Enter a message', 'warning');
                return;
            }

            if (!currentReviewChat) return;

            try {
                const result = await fetch('/api/send', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        account: currentReviewChat.account,
                        chat_id: currentReviewChat.id,
                        text: text
                    })
                }).then(r => r.json());

                if (result.success) {
                    showToast('Message sent', 'success');
                    reviewIndex++;
                    await loadReviewChat(reviewIndex);
                } else {
                    showToast('Failed: ' + result.error, 'error');
                }
            } catch (e) {
                showToast('Error sending message', 'error');
            }
        }

        async function reviewSaveDraft() {
            const text = document.getElementById('review-reply-input').value.trim();
            if (!text) {
                showToast('Enter a message', 'warning');
                return;
            }

            if (!currentReviewChat) return;

            try {
                await fetch('/api/drafts', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        account: currentReviewChat.account,
                        chat_id: currentReviewChat.id,
                        chat_name: currentReviewChat.name || 'Unknown',
                        text: text,
                        suggested_by: 'review'
                    })
                });

                showToast('Draft saved', 'success');
                updateDraftsCount();
                reviewIndex++;
                await loadReviewChat(reviewIndex);
            } catch (e) {
                showToast('Error saving draft', 'error');
            }
        }

        async function reviewSkip() {
            reviewIndex++;
            await loadReviewChat(reviewIndex);
        }

        async function reviewLater() {
            if (!currentReviewChat) return;

            try {
                await fetch('/api/crm/status', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        account: currentReviewChat.account,
                        chat_id: currentReviewChat.id,
                        status: 'later'
                    })
                });

                showToast('Marked for later', 'success');
                reviewIndex++;
                await loadReviewChat(reviewIndex);
            } catch (e) {
                showToast('Error updating status', 'error');
            }
        }

        // ============================================================
        // Drafts Functions
        // ============================================================

        async function showDraftsModal() {
            document.getElementById('drafts-modal').classList.add('active');
            await loadDraftsList();
        }

        function hideDraftsModal() {
            document.getElementById('drafts-modal').classList.remove('active');
        }

        async function loadDraftsList() {
            const container = document.getElementById('drafts-list');
            container.innerHTML = '<div class="loading"><div class="spinner"></div></div>';

            try {
                const res = await fetch('/api/drafts').then(r => r.json());
                const draftsList = res.drafts || [];

                if (draftsList.length === 0) {
                    container.innerHTML = '<div style="text-align: center; padding: 40px; color: var(--text-secondary);">No drafts</div>';
                    return;
                }

                container.innerHTML = draftsList.map(d => `
                    <div class="draft-item" data-draft-id="${d.id}" style="padding: 12px; border-bottom: 1px solid var(--border);">
                        <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 8px;">
                            <div>
                                <div style="font-weight: 500;">${escapeHtml(d.chat_name)}</div>
                                <div style="font-size: 11px; color: var(--text-secondary);">${d.account} | ${formatTime(d.created_at)}</div>
                            </div>
                            <div style="display: flex; gap: 4px;">
                                <button class="btn btn-sm btn-primary draft-send-btn">Send</button>
                                <button class="btn btn-sm btn-secondary draft-edit-btn">Edit</button>
                                <button class="btn btn-sm btn-danger draft-delete-btn" style="background: var(--danger);">Delete</button>
                            </div>
                        </div>
                        <div style="font-size: 13px; color: var(--text-primary); background: var(--bg-tertiary); padding: 8px; border-radius: 6px;">
                            ${escapeHtml(d.text)}
                        </div>
                    </div>
                `).join('');

                // Store drafts globally
                window.currentDrafts = draftsList;

                // Add event listeners
                container.querySelectorAll('.draft-item').forEach(el => {
                    const draftId = el.dataset.draftId;
                    const draft = draftsList.find(d => d.id === draftId);

                    el.querySelector('.draft-send-btn').addEventListener('click', () => sendDraft(draftId));
                    el.querySelector('.draft-edit-btn').addEventListener('click', () => editDraft(draftId, draft.text));
                    el.querySelector('.draft-delete-btn').addEventListener('click', () => deleteDraft(draftId));
                });

            } catch (e) {
                container.innerHTML = '<div style="text-align: center; padding: 40px; color: var(--danger);">Error loading drafts</div>';
            }
        }

        async function sendDraft(draftId) {
            try {
                const result = await fetch(`/api/drafts/${draftId}/send`, {
                    method: 'POST'
                }).then(r => r.json());

                if (result.status === 'sent') {
                    showToast('Draft sent', 'success');
                    await loadDraftsList();
                    updateDraftsCount();
                } else {
                    showToast('Failed to send draft', 'error');
                }
            } catch (e) {
                showToast('Error sending draft', 'error');
            }
        }

        function editDraft(draftId, text) {
            const newText = prompt('Edit draft:', text);
            if (newText !== null && newText.trim()) {
                fetch(`/api/drafts/${draftId}`, {
                    method: 'PUT',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ text: newText.trim() })
                }).then(() => {
                    showToast('Draft updated', 'success');
                    loadDraftsList();
                }).catch(() => {
                    showToast('Error updating draft', 'error');
                });
            }
        }

        async function deleteDraft(draftId) {
            if (!confirm('Delete this draft?')) return;

            try {
                await fetch(`/api/drafts/${draftId}`, { method: 'DELETE' });
                showToast('Draft deleted', 'success');
                await loadDraftsList();
                updateDraftsCount();
            } catch (e) {
                showToast('Error deleting draft', 'error');
            }
        }

        async function updateDraftsCount() {
            try {
                const res = await fetch('/api/drafts?status=pending').then(r => r.json());
                const count = (res.drafts || []).length;
                const badge = document.getElementById('drafts-count');
                if (count > 0) {
                    badge.textContent = count;
                    badge.style.display = 'inline';
                } else {
                    badge.style.display = 'none';
                }
            } catch (e) {
                // Ignore
            }
        }

        // Load drafts count on page load
        document.addEventListener('DOMContentLoaded', () => {
            updateDraftsCount();
        });
    </script>
</body>
</html>"""


if __name__ == "__main__":
    uvicorn.run(app, host=HOST, port=PORT)
