import os
import asyncio
from datetime import datetime
from pathlib import Path

from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.enums import ChatType
from openai import OpenAI

# === НАСТРОЙКИ ===
from dotenv import load_dotenv
load_dotenv()
TELEGRAM_TOKEN = os.environ["TELEGRAM_TOKEN"]
OPENAI_API_KEY = os.environ["OPENAI_API_KEY"]
MY_USER_IDS = [963129618, 8127547204]  # Твои ID - для определения твоей папки

# Корневая папка для сохранения транскрибаций (на сервере)
BASE_DIR = Path.home() / "transcriptions"
BASE_DIR.mkdir(exist_ok=True)

# === ИНИЦИАЛИЗАЦИЯ ===
bot = Bot(token=TELEGRAM_TOKEN)
dp = Dispatcher()
openai_client = OpenAI(api_key=OPENAI_API_KEY)


def get_user_directory(user_id: int, username: str = None, chat_title: str = None, chat_type: str = "private", chat_id: int = None) -> Path:
    """Определяет папку для сохранения в зависимости от источника сообщения"""
    if hasattr(chat_type, "value"):
        chat_type = chat_type.value
    if chat_type in ["group", "supergroup"]:
        # Групповой чат - папка по названию чата
        safe_chat_name = "".join(c if c.isalnum() or c in (' ', '-', '_') else '_' for c in (chat_title or f"chat_{user_id}"))
        user_dir = BASE_DIR / "Чаты" / safe_chat_name
    elif chat_type == "channel":
        # Канал - папка по названию канала
        safe_chat_name = "".join(c if c.isalnum() or c in (' ', '-', '_') else '_' for c in (chat_title or f"channel_{chat_id or 0}"))
        user_dir = BASE_DIR / "Каналы" / safe_chat_name
    elif user_id in MY_USER_IDS:
        # Мои личные сообщения (все мои аккаунты)
        user_dir = BASE_DIR / "Мои"
    else:
        # Чужие личные сообщения - папка по username или ID
        folder_name = username if username else f"user_{user_id}"
        user_dir = BASE_DIR / "Другие" / folder_name

    user_dir.mkdir(parents=True, exist_ok=True)
    return user_dir


def get_today_file(user_dir: Path) -> Path:
    """Возвращает путь к файлу транскрибаций за сегодня"""
    today = datetime.now().strftime("%Y-%m-%d")
    return user_dir / f"{today}.md"


def append_transcription(user_dir: Path, text: str, username: str = None):
    """Добавляет транскрибацию в файл дня"""
    file_path = get_today_file(user_dir)
    time_now = datetime.now().strftime("%H:%M")

    # Создаём файл с заголовком если не существует
    if not file_path.exists():
        today = datetime.now().strftime("%d.%m.%Y")
        header = f"# Транскрибации за {today}\n\n"
        file_path.write_text(header, encoding="utf-8")

    # Добавляем транскрибацию с временной меткой
    with open(file_path, "a", encoding="utf-8") as f:
        if username:
            f.write(f"### {time_now} — @{username}\n{text}\n\n")
        else:
            f.write(f"### {time_now}\n{text}\n\n")


async def transcribe_voice(file_path: str) -> str:
    """Транскрибирует голосовое через Whisper"""
    with open(file_path, "rb") as audio_file:
        transcript = openai_client.audio.transcriptions.create(
            model="whisper-1",
            file=audio_file,
            language="ru"
        )
    return transcript.text


@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    # В группах не отвечаем на команды
    if message.chat.type in [ChatType.GROUP, ChatType.SUPERGROUP]:
        return

    await message.answer(
        "Привет! Я транскрибирую голосовые и видеокружки.\n\n"
        "📌 В личке:\n"
        "• Голосовое или кружочек (video note) → транскрибация\n"
        "• Текст → сохраняется с пометкой 'Сохранено'\n\n"
        "📌 В группах:\n"
        "• Добавь меня в чат\n"
        "• Я транскрибирую голосовые и кружки\n\n"
        "Команды:\n"
        "/today — показать записи за сегодня\n"
        "/file — получить файл за сегодня"
    )


@dp.message(Command("today"))
async def cmd_today(message: types.Message):
    # В группах не отвечаем на команды
    if message.chat.type in [ChatType.GROUP, ChatType.SUPERGROUP]:
        return

    user_dir = get_user_directory(
        message.from_user.id,
        message.from_user.username,
        message.chat.title,
        message.chat.type
    )
    file_path = get_today_file(user_dir)

    if file_path.exists():
        content = file_path.read_text(encoding="utf-8")
        # Telegram лимит 4096 символов
        if len(content) > 4000:
            content = content[:4000] + "\n\n... (обрезано, используй /file)"
        await message.answer(content)
    else:
        await message.answer("Сегодня пока нет записей.")


@dp.message(Command("file"))
async def cmd_file(message: types.Message):
    """Отправляет файл за сегодня"""
    # В группах не отвечаем на команды
    if message.chat.type in [ChatType.GROUP, ChatType.SUPERGROUP]:
        return

    user_dir = get_user_directory(
        message.from_user.id,
        message.from_user.username,
        message.chat.title,
        message.chat.type
    )
    file_path = get_today_file(user_dir)

    if file_path.exists():
        await message.answer_document(
            types.FSInputFile(file_path),
            caption="Записи за сегодня"
        )
    else:
        await message.answer("Сегодня пока нет записей.")


async def _process_voice_message(message: types.Message, temp_path: str):
    """Общая логика: транскрибировать, сохранить, ответить. temp_path уже скачан."""
    user_id = message.from_user.id if message.from_user else 0
    username = message.from_user.username if message.from_user else None
    user_dir = get_user_directory(
        user_id,
        username,
        message.chat.title,
        message.chat.type,
        chat_id=message.chat.id,
    )
    text = await transcribe_voice(temp_path)
    append_transcription(user_dir, text, username or (getattr(message, "author_signature", None)))
    await message.reply(text)


@dp.message(lambda m: m.voice is not None)
async def handle_voice(message: types.Message):
    """Обрабатывает голосовые сообщения везде (личка + группы)."""
    if message.chat.type == ChatType.PRIVATE:
        status_msg = await message.answer("🎤 Транскрибирую...")
    file = await bot.get_file(message.voice.file_id)
    temp_path = f"/tmp/voice_{message.message_id}.ogg"
    await bot.download_file(file.file_path, temp_path)
    try:
        await _process_voice_message(message, temp_path)
        if message.chat.type == ChatType.PRIVATE:
            await status_msg.delete()
    except Exception as e:
        error_text = f"❌ Ошибка: {e}"
        if message.chat.type == ChatType.PRIVATE:
            await status_msg.edit_text(error_text)
        else:
            await message.reply(error_text)
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)


@dp.channel_post(lambda m: m.voice is not None)
async def handle_channel_voice(message: types.Message):
    """Обрабатывает голосовые в постах канала (бот должен быть админом канала)."""
    file = await bot.get_file(message.voice.file_id)
    temp_path = f"/tmp/voice_ch_{message.message_id}.ogg"
    await bot.download_file(file.file_path, temp_path)
    try:
        await _process_voice_message(message, temp_path)
    except Exception as e:
        await message.reply(f"❌ Ошибка: {e}")
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)


@dp.message(lambda m: m.video_note is not None)
async def handle_video_note(message: types.Message):
    """Обрабатывает видеокружки (кружочек) — транскрибирует звук через Whisper."""
    if message.chat.type == ChatType.PRIVATE:
        status_msg = await message.answer("🎬 Транскрибирую кружочек...")
    file = await bot.get_file(message.video_note.file_id)
    temp_path = f"/tmp/vn_{message.message_id}.mp4"
    await bot.download_file(file.file_path, temp_path)
    try:
        await _process_voice_message(message, temp_path)
        if message.chat.type == ChatType.PRIVATE:
            await status_msg.delete()
    except Exception as e:
        error_text = f"❌ Ошибка: {e}"
        if message.chat.type == ChatType.PRIVATE:
            await status_msg.edit_text(error_text)
        else:
            await message.reply(error_text)
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)


@dp.channel_post(lambda m: m.video_note is not None)
async def handle_channel_video_note(message: types.Message):
    """Обрабатывает видеокружки в постах канала."""
    file = await bot.get_file(message.video_note.file_id)
    temp_path = f"/tmp/vn_ch_{message.message_id}.mp4"
    await bot.download_file(file.file_path, temp_path)
    try:
        await _process_voice_message(message, temp_path)
    except Exception as e:
        await message.reply(f"❌ Ошибка: {e}")
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)


@dp.message(lambda m: m.text and not m.text.startswith("/"))
async def handle_text(message: types.Message):
    """Обрабатывает текстовые сообщения ТОЛЬКО в личке"""

    # В группах игнорируем текст
    if message.chat.type in [ChatType.GROUP, ChatType.SUPERGROUP]:
        return

    # Определяем директорию пользователя
    user_dir = get_user_directory(
        message.from_user.id,
        message.from_user.username,
        message.chat.title,
        message.chat.type
    )

    # Сохраняем текстовое сообщение
    append_transcription(user_dir, message.text, message.from_user.username)

    # Отвечаем просто "Сохранено"
    await message.answer("Сохранено")


async def main():
    print("Бот запущен на сервере...")
    print(f"Файлы сохраняются в: {BASE_DIR}")
    print("Структура:")
    print("  - Мои/ (твои личные сообщения)")
    print("  - Другие/ (личные сообщения других пользователей)")
    print("  - Чаты/ (групповые чаты)")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
