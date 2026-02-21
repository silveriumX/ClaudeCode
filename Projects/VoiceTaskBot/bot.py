"""
VoiceTaskBot — голосовые заметки → задачи → Google Sheets.

Поток:
  Голосовое/текст → Groq Whisper (STT) → Groq LLM (извлечение задач)
  → подтверждение в Telegram → Google Sheets «Задачи»

Управление задачами:
  /tasks — список активных задач с кнопками [✅ Готово] [✏️ Изменить] [🗑 Удалить]
"""
import asyncio
import json
import logging
import os
import tempfile
from pathlib import Path
from typing import Optional

from aiogram import Bot, Dispatcher, F, types
from aiogram.filters import Command
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup
from dotenv import load_dotenv
from groq import Groq

from sheets import STATUS_DONE, STATUS_IN_PROGRESS, STATUS_NEW, TaskSheets

# ── Конфигурация ─────────────────────────────────────────────────────────────

load_dotenv(Path(__file__).parent / ".env")

TELEGRAM_TOKEN = os.environ["TELEGRAM_TOKEN"]
GROQ_API_KEY = os.environ["GROQ_API_KEY"]
SPREADSHEET_ID = os.environ["SPREADSHEET_ID"]
GOOGLE_CREDENTIALS_PATH = str(
    (Path(__file__).parent / os.environ["GOOGLE_CREDENTIALS_PATH"]).resolve()
)

OWNER_IDS: list[int] = [963129618, 8127547204, 7961558091]

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.FileHandler("bot.log", encoding="utf-8")],
)
logger = logging.getLogger(__name__)

# ── Инициализация ─────────────────────────────────────────────────────────────

bot = Bot(token=TELEGRAM_TOKEN)
dp = Dispatcher()
groq_client = Groq(api_key=GROQ_API_KEY)
sheets = TaskSheets(GOOGLE_CREDENTIALS_PATH, SPREADSHEET_ID)

# Подтверждение новых задач: message_id → list[str]
pending: dict[int, list[str]] = {}

# Редактирование задачи при подтверждении: user_id → original_message_id
awaiting_edit: dict[int, int] = {}

# Редактирование существующей задачи в Sheets: user_id → (task_id, chat_id, msg_id)
editing_existing: dict[int, tuple[int, int, int]] = {}


# ── Groq: транскрипция ────────────────────────────────────────────────────────

async def transcribe(audio_path: str) -> str:
    """Транскрибировать аудио через Groq Whisper."""
    with open(audio_path, "rb") as f:
        result = groq_client.audio.transcriptions.create(
            model="whisper-large-v3-turbo",
            file=f,
            language="ru",
        )
    return result.text.strip()


# ── Groq: извлечение задач ────────────────────────────────────────────────────

TASK_EXTRACTION_PROMPT = """Ты помощник, который извлекает задачи из текста.

Из текста ниже извлеки все задачи, поручения, дела — всё что нужно сделать.
Верни ТОЛЬКО JSON массив объектов. Каждый объект:
{"задача": "ПОЛНОЕ описание — сохраняй ВСЕ детали: кому, сколько, что именно"}

ВАЖНО: НЕ СОКРАЩАЙ. "Перевести деньги Александру" — не "перевести деньги".
Если задач нет — верни [].
Только JSON, без пояснений.

Текст:
"""


async def extract_tasks(text: str) -> list[str]:
    """Извлечь задачи из текста, вернуть список строк."""
    try:
        response = groq_client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": TASK_EXTRACTION_PROMPT + text}],
            temperature=0.1,
            max_tokens=1024,
        )
        content = response.choices[0].message.content.strip()

        # Убираем markdown-обёртку если есть
        if content.startswith("```"):
            content = content.split("```")[1]
            if content.startswith("json"):
                content = content[4:]

        raw = json.loads(content)
        if not isinstance(raw, list):
            return []
        return [t["задача"] for t in raw if isinstance(t, dict) and t.get("задача")]

    except Exception as e:
        logger.exception(f"Ошибка извлечения задач: {e}")
        return []


# ── UI: задачи ────────────────────────────────────────────────────────────────

def _build_tasks_display(tasks: list[dict]) -> tuple[str, InlineKeyboardMarkup]:
    """Построить сообщение со списком задач и клавиатурой управления."""
    lines = [f"📋 <b>Активных задач: {len(tasks)}</b>\n"]
    buttons: list[list[InlineKeyboardButton]] = []

    for i, task in enumerate(tasks, 1):
        tid = task["ID"]
        status = task.get("Статус", "")
        prefix = "🔄 " if status == STATUS_IN_PROGRESS else ""
        lines.append(f"{i}. {prefix}{task['Задача']}")
        buttons.append([
            InlineKeyboardButton(text=f"✅ {i}", callback_data=f"tk:done:{tid}"),
            InlineKeyboardButton(text=f"✏️ {i}", callback_data=f"tk:edit:{tid}"),
            InlineKeyboardButton(text=f"🗑 {i}", callback_data=f"tk:delete:{tid}"),
        ])

    lines.append("\n<i>✅ выполнено  ✏️ изменить  🗑 удалить</i>")
    return "\n".join(lines), InlineKeyboardMarkup(inline_keyboard=buttons)


async def _refresh_tasks_message(message: types.Message) -> None:
    """Обновить сообщение со списком задач после изменения."""
    tasks = sheets.get_active_tasks()
    try:
        if not tasks:
            await message.edit_text("✅ Нет активных задач", reply_markup=None)
        else:
            text, keyboard = _build_tasks_display(tasks)
            await message.edit_text(text, parse_mode="HTML", reply_markup=keyboard)
    except Exception:
        pass  # сообщение не изменилось — игнорируем


# ── UI: подтверждение новых задач ────────────────────────────────────────────

def format_pending_message(tasks: list[str], transcript: str) -> str:
    lines = [f"🎤 <i>{transcript[:200]}{'...' if len(transcript) > 200 else ''}</i>\n"]
    if not tasks:
        lines.append("Задач не найдено.")
        return "\n".join(lines)
    lines.append(f"<b>Найдено задач: {len(tasks)}</b>\n")
    for i, task in enumerate(tasks, 1):
        lines.append(f"{i}. {task}")
    return "\n".join(lines)


def make_confirm_keyboard(msg_id: int, has_tasks: bool) -> InlineKeyboardMarkup:
    if not has_tasks:
        return InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="❌ Закрыть", callback_data=f"t:cancel:{msg_id}")]
        ])
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="✅ Добавить", callback_data=f"t:confirm:{msg_id}"),
        InlineKeyboardButton(text="✏️ Изменить", callback_data=f"t:edit:{msg_id}"),
        InlineKeyboardButton(text="❌ Отмена", callback_data=f"t:cancel:{msg_id}"),
    ]])


# ── Общая логика обработки ────────────────────────────────────────────────────

async def process_input(message: types.Message, text: str) -> None:
    """Извлечь задачи из текста.

    1 задача  → авто-сохранение с кнопкой [↩️ Отменить].
    2+ задачи → диалог подтверждения.
    0 задач   → сообщить что не найдено.
    """
    tasks = await extract_tasks(text)

    if not tasks:
        transcript_preview = text[:200] + ("..." if len(text) > 200 else "")
        await message.answer(
            f"🎤 <i>{transcript_preview}</i>\n\nЗадач не найдено.",
            parse_mode="HTML",
        )
        return

    if len(tasks) == 1:
        # Авто-сохранение без подтверждения
        created_ids = sheets.append_tasks(tasks)
        task_id = created_ids[0] if created_ids else None
        kb = InlineKeyboardMarkup(inline_keyboard=[[
            InlineKeyboardButton(text="↩️ Отменить", callback_data=f"t:undo:{task_id}"),
        ]]) if task_id is not None else None
        await message.answer(
            f"✅ <b>Сохранено:</b> {tasks[0]}",
            parse_mode="HTML",
            reply_markup=kb,
        )
        return

    # 2+ задач → диалог подтверждения
    reply_text = format_pending_message(tasks, text)
    await message.answer(
        reply_text,
        parse_mode="HTML",
        reply_markup=make_confirm_keyboard(message.message_id, True),
    )
    pending[message.message_id] = tasks


# ── Хэндлеры ─────────────────────────────────────────────────────────────────

def is_owner(user_id: int) -> bool:
    return user_id in OWNER_IDS


@dp.message(Command("whoami"))
async def cmd_whoami(message: types.Message) -> None:
    await message.answer(f"Твой Telegram ID: <code>{message.from_user.id}</code>", parse_mode="HTML")


@dp.message(Command("start"))
async def cmd_start(message: types.Message) -> None:
    if not is_owner(message.from_user.id):
        return
    await message.answer(
        "👋 <b>VoiceTaskBot</b>\n\n"
        "Отправь голосовое или текст — я найду задачи и добавлю в таблицу.\n\n"
        "Команды:\n"
        "/tasks — активные задачи\n"
        "/pending — только новые задачи",
        parse_mode="HTML",
    )


@dp.message(Command("tasks"))
async def cmd_tasks(message: types.Message) -> None:
    if not is_owner(message.from_user.id):
        return
    tasks = sheets.get_active_tasks()
    if not tasks:
        await message.answer("✅ Нет активных задач")
        return
    text, keyboard = _build_tasks_display(tasks)
    await message.answer(text, parse_mode="HTML", reply_markup=keyboard)


@dp.message(Command("pending"))
async def cmd_pending(message: types.Message) -> None:
    if not is_owner(message.from_user.id):
        return
    tasks = sheets.get_pending_tasks()
    if not tasks:
        await message.answer("Нет новых задач в таблице.")
        return
    lines = [f"<b>Новые задачи ({len(tasks)}):</b>\n"]
    for t in tasks:
        lines.append(f"• {t['Задача']}")
    await message.answer("\n".join(lines), parse_mode="HTML")


@dp.message(F.voice | F.video_note)
async def handle_voice(message: types.Message) -> None:
    if not is_owner(message.from_user.id):
        return

    status = await message.answer("🎤 Транскрибирую...")

    file_obj = message.voice if message.voice else message.video_note
    suffix = ".ogg" if message.voice else ".mp4"
    file_info = await bot.get_file(file_obj.file_id)

    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
        tmp_path = tmp.name

    try:
        await bot.download_file(file_info.file_path, tmp_path)
        transcript = await transcribe(tmp_path)
    except Exception as e:
        await status.edit_text(f"❌ Ошибка транскрипции: {e}")
        return
    finally:
        Path(tmp_path).unlink(missing_ok=True)

    await status.delete()
    await process_input(message, transcript)


@dp.message(F.text & ~F.text.startswith("/"))
async def handle_text(message: types.Message) -> None:
    if not is_owner(message.from_user.id):
        return

    user_id = message.from_user.id

    # Редактирование существующей задачи из /tasks
    if user_id in editing_existing:
        task_id, chat_id, tasks_msg_id = editing_existing.pop(user_id)
        ok = sheets.update_task(task_id, message.text)
        if ok:
            await message.reply("✅ Задача обновлена")
            # Обновляем список задач
            try:
                tasks = sheets.get_active_tasks()
                if tasks:
                    text, keyboard = _build_tasks_display(tasks)
                    await bot.edit_message_text(
                        text, chat_id=chat_id, message_id=tasks_msg_id,
                        parse_mode="HTML", reply_markup=keyboard,
                    )
                else:
                    await bot.edit_message_text(
                        "✅ Нет активных задач", chat_id=chat_id, message_id=tasks_msg_id,
                        reply_markup=None,
                    )
            except Exception:
                pass
        else:
            await message.reply("❌ Задача не найдена")
        return

    # Редактирование текста при подтверждении новых задач
    if user_id in awaiting_edit:
        orig_msg_id = awaiting_edit.pop(user_id)
        pending.pop(orig_msg_id, None)
        await process_input(message, message.text)
        return

    await process_input(message, message.text)


# ── Callback: подтверждение новых задач (prefix "t:") ────────────────────────

@dp.callback_query(F.data.startswith("t:"))
async def handle_confirm_callback(callback: CallbackQuery) -> None:
    parts = callback.data.split(":")
    if len(parts) != 3:
        return

    _, action, msg_id_str = parts
    msg_id = int(msg_id_str)

    if action == "undo":
        # Откат авто-сохранённой одиночной задачи
        task_id = int(msg_id_str)
        ok = sheets.delete_task(task_id)
        if ok:
            await callback.message.edit_text("↩️ Отменено", reply_markup=None)
            await callback.answer("Задача удалена")
        else:
            await callback.answer("❌ Задача не найдена")
        return

    if action == "cancel":
        pending.pop(msg_id, None)
        awaiting_edit.pop(callback.from_user.id, None)
        await callback.message.delete()
        await callback.answer("Отменено")
        return

    if action == "edit":
        if msg_id not in pending:
            await callback.answer("Истекло время. Отправь снова.")
            return
        # Запрашиваем исправленный текст
        tasks = pending[msg_id]
        current = "\n".join(f"{i}. {t}" for i, t in enumerate(tasks, 1))
        awaiting_edit[callback.from_user.id] = msg_id
        await callback.message.reply(
            f"✏️ <b>Введи исправленный текст:</b>\n\n"
            f"<i>Найденные задачи:</i>\n{current}",
            parse_mode="HTML",
        )
        await callback.answer()
        return

    if action == "confirm":
        tasks = pending.pop(msg_id, None)
        if not tasks:
            await callback.answer("Истекло время. Отправь снова.")
            return

        created_ids = sheets.append_tasks(tasks)
        count = len(created_ids)
        if count:
            await callback.message.edit_text(
                f"✅ <b>Добавлено задач: {count}</b>\n\n" + callback.message.text,
                parse_mode="HTML",
                reply_markup=None,
            )
            await callback.answer(f"Добавлено {count} задач")
        else:
            await callback.answer("❌ Ошибка записи в таблицу")


# ── Callback: управление задачами (prefix "tk:") ─────────────────────────────

@dp.callback_query(F.data.startswith("tk:"))
async def handle_task_callback(callback: CallbackQuery) -> None:
    parts = callback.data.split(":")
    if len(parts) != 3:
        return

    _, action, task_id_str = parts
    task_id = int(task_id_str)

    if action == "done":
        ok = sheets.set_status(task_id, STATUS_DONE)
        await callback.answer("✅ Выполнено!" if ok else "❌ Задача не найдена")
        if ok:
            await _refresh_tasks_message(callback.message)

    elif action == "delete":
        ok = sheets.delete_task(task_id)
        await callback.answer("🗑 Удалено" if ok else "❌ Задача не найдена")
        if ok:
            await _refresh_tasks_message(callback.message)

    elif action == "edit":
        tasks = sheets.get_active_tasks()
        task = next((t for t in tasks if str(t["ID"]) == str(task_id)), None)
        if not task:
            await callback.answer("❌ Задача не найдена")
            return
        editing_existing[callback.from_user.id] = (
            task_id,
            callback.message.chat.id,
            callback.message.message_id,
        )
        await callback.message.reply(
            f"✏️ <b>Введи новый текст задачи:</b>\n\n"
            f"<i>Сейчас:</i> {task['Задача']}",
            parse_mode="HTML",
        )
        await callback.answer()


# ── Запуск ────────────────────────────────────────────────────────────────────

async def main() -> None:
    logger.info("VoiceTaskBot запущен")
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
