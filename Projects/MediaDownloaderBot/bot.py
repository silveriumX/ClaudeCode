"""
Сейвер v6.1 - yt-dlp + Pinterest API + Groq Whisper
"""

import asyncio
import json
import logging
import os
import re
import subprocess
from pathlib import Path
from typing import Optional

import aiohttp
from dotenv import load_dotenv
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import FSInputFile, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from aiogram.enums import ParseMode
from groq import Groq

load_dotenv(Path(__file__).parent / ".env")

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
)
logger = logging.getLogger(__name__)

# ═══════════════════════════════════════════════════════════
# КОНФИГУРАЦИЯ
# ═══════════════════════════════════════════════════════════

BOT_TOKEN = os.getenv("BOT_TOKEN")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
ALLOWED_USERS = []
DOWNLOAD_DIR = Path("/tmp/media_downloads")
pending_downloads = {}

# ═══════════════════════════════════════════════════════════
# YT-DLP DOWNLOADER
# ═══════════════════════════════════════════════════════════

async def download_media(
    url: str,
    audio_only: bool = False,
    quality: str = "720",
    for_transcription: bool = False,
) -> tuple[Optional[Path], Optional[str], Optional[str]]:
    """Скачивает медиа через yt-dlp"""

    DOWNLOAD_DIR.mkdir(exist_ok=True)

    output_template = str(DOWNLOAD_DIR / "%(title).40s.%(ext)s")

    cmd = [
        'yt-dlp',
        '--no-playlist',
        '--no-warnings',
        '--no-progress',
        '--js-runtimes', 'node',
        '--remote-components', 'ejs:github',
        '-o', output_template,
    ]

    if audio_only:
        # Для транскрипции используем 48kbps — достаточно для Whisper и меньше размер
        bitrate = '48K' if for_transcription else '128K'
        cmd.extend([
            '-x',
            '--audio-format', 'mp3',
            '--audio-quality', bitrate,
        ])
    else:
        if quality == "best":
            fmt = 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best'
        else:
            fmt = f'bestvideo[height<={quality}][ext=mp4]+bestaudio[ext=m4a]/best[height<={quality}][ext=mp4]/best[height<={quality}]/best'
        cmd.extend(['-f', fmt, '--merge-output-format', 'mp4'])

    cmd.append(url)

    logger.info(f"[yt-dlp] Running: {' '.join(cmd[:8])}...")

    try:
        result = await asyncio.wait_for(
            asyncio.to_thread(
                subprocess.run, cmd, capture_output=True, text=True
            ),
            timeout=180
        )

        if result.returncode != 0:
            error = result.stderr or result.stdout or "Unknown error"
            for line in error.split('\n'):
                if 'ERROR' in line:
                    return None, None, line.split('ERROR')[-1].strip()[:80]
            return None, None, error[:80]

        ext = "mp3" if audio_only else "mp4"
        files = list(DOWNLOAD_DIR.glob(f"*.{ext}"))
        if not files:
            files = list(DOWNLOAD_DIR.glob("*.*"))
            files = [f for f in files if f.suffix in ('.mp3', '.mp4', '.webm', '.m4a')]

        if not files:
            return None, None, "File not found after download"

        filepath = max(files, key=lambda f: f.stat().st_mtime)
        filename = filepath.stem

        logger.info(f"[yt-dlp] Downloaded: {filepath} ({filepath.stat().st_size} bytes)")

        return filepath, filename, None

    except asyncio.TimeoutError:
        return None, None, "Timeout (3 min)"
    except Exception as e:
        return None, None, str(e)[:80]

# ═══════════════════════════════════════════════════════════
# GROQ WHISPER TRANSCRIPTION
# ═══════════════════════════════════════════════════════════

async def transcribe_with_groq(filepath: Path) -> tuple[Optional[str], Optional[str]]:
    """Транскрибирует аудио через Groq Whisper API (бесплатно, 189x real-time)"""
    if not GROQ_API_KEY:
        return None, "GROQ_API_KEY не настроен в .env"

    file_size = filepath.stat().st_size
    # Groq лимит: 25MB. При 48kbps это ~1.1 часа аудио
    if file_size > 24 * 1024 * 1024:
        size_mb = file_size / 1024 / 1024
        return None, f"Файл {size_mb:.1f} МБ превышает лимит 24 МБ. Видео слишком длинное (>1 часа)."

    def _do_transcribe():
        client = Groq(api_key=GROQ_API_KEY)
        with open(filepath, "rb") as f:
            return client.audio.transcriptions.create(
                file=(filepath.name, f.read()),
                model="whisper-large-v3-turbo",
                response_format="text",
            )

    try:
        result = await asyncio.to_thread(_do_transcribe)
        return str(result).strip(), None
    except Exception as e:
        logger.exception(f"Groq transcription error: {e}")
        return None, str(e)[:150]

# ═══════════════════════════════════════════════════════════
# PINTEREST DOWNLOADER
# ═══════════════════════════════════════════════════════════

PINTEREST_UA = (
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
    'AppleWebKit/537.36 (KHTML, like Gecko) '
    'Chrome/120.0.0.0 Safari/537.36'
)


def is_pinterest_url(url: str) -> bool:
    return bool(re.search(r'(pinterest\.\w+(?:\.\w+)?|pin\.it)', url, re.IGNORECASE))


async def resolve_pinterest_url(url: str) -> str:
    if 'pin.it' not in url:
        return url
    async with aiohttp.ClientSession() as session:
        async with session.head(
            url, allow_redirects=True,
            headers={'User-Agent': PINTEREST_UA},
            timeout=aiohttp.ClientTimeout(total=10),
        ) as resp:
            return str(resp.url)


def extract_pin_id(url: str) -> Optional[str]:
    match = re.search(r'/pin/(?:[\w-]+--)?(\d+)', url)
    return match.group(1) if match else None


async def fetch_pinterest_media(url: str) -> Optional[dict]:
    try:
        url = await resolve_pinterest_url(url)
    except Exception as e:
        logger.error(f"Pinterest resolve failed: {e}")
        return None

    pin_id = extract_pin_id(url)
    if not pin_id:
        logger.error(f"No pin ID in URL: {url}")
        return None

    headers = {
        'User-Agent': PINTEREST_UA,
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
    }

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"https://www.pinterest.com/pin/{pin_id}/",
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=15),
            ) as resp:
                if resp.status != 200:
                    logger.error(f"Pinterest page returned {resp.status}")
                    return None
                html = await resp.text()
    except Exception as e:
        logger.error(f"Pinterest page request failed: {e}")
        return None

    video_mp4s = re.findall(
        r'https://v1\.pinimg\.com/videos/[^"]+expMp4/[^"]+\.mp4', html
    )
    if video_mp4s:
        unique = list(dict.fromkeys(video_mp4s))
        return {'type': 'video', 'url': unique[0]}

    video_match = re.search(
        r'<meta\s[^>]*(?:property|name)="og:video"[^>]*content="([^"]+)"', html
    ) or re.search(
        r'<meta\s[^>]*content="([^"]+)"[^>]*(?:property|name)="og:video"', html
    )
    if video_match:
        return {'type': 'video', 'url': video_match.group(1)}

    image_match = re.search(
        r'<meta\s[^>]*(?:property|name)="og:image"[^>]*content="([^"]+)"', html
    ) or re.search(
        r'<meta\s[^>]*content="([^"]+)"[^>]*(?:property|name)="og:image"', html
    )
    if image_match:
        image_url = image_match.group(1)
        original_url = re.sub(r'/\d+x\d*/', '/originals/', image_url)
        return {'type': 'image', 'url': original_url}

    return None


async def download_file_from_url(url: str, suffix: str) -> Optional[Path]:
    DOWNLOAD_DIR.mkdir(exist_ok=True)
    filepath = DOWNLOAD_DIR / f"pin_{abs(hash(url))}{suffix}"

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=60)) as resp:
                if resp.status != 200:
                    return None
                with open(filepath, 'wb') as f:
                    async for chunk in resp.content.iter_chunked(8192):
                        f.write(chunk)
        return filepath
    except Exception as e:
        logger.error(f"Download failed: {e}")
        if filepath.exists():
            filepath.unlink()
        return None


# ═══════════════════════════════════════════════════════════
# TELEGRAM BOT
# ═══════════════════════════════════════════════════════════

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

URL_PATTERNS = {
    'youtube': r'(youtube\.com|youtu\.be)',
    'tiktok': r'(tiktok\.com|vm\.tiktok\.com)',
    'instagram': r'(instagram\.com|instagr\.am)',
    'twitter': r'(twitter\.com|x\.com)',
    'reddit': r'reddit\.com',
    'pinterest': r'(pinterest\.\w+(?:\.\w+)?|pin\.it)',
}

def detect_platform(url: str) -> str:
    for platform, pattern in URL_PATTERNS.items():
        if re.search(pattern, url, re.IGNORECASE):
            return platform
    return 'unknown'

def extract_url(text: str) -> str | None:
    match = re.search(r'https?://[^\s<>"{}|\\^`\[\]]+', text)
    return match.group(0) if match else None

def get_emoji(platform: str) -> str:
    return {'youtube': '🔴', 'tiktok': '🎵', 'instagram': '📸', 'twitter': '🐦', 'reddit': '🔶', 'pinterest': '📌'}.get(platform, '🔗')

def get_keyboard(url: str) -> InlineKeyboardMarkup:
    url_id = str(hash(url))[-8:]
    pending_downloads[url_id] = url
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🎬 1080p", callback_data=f"dl:1080:{url_id}"),
            InlineKeyboardButton(text="🎬 720p", callback_data=f"dl:720:{url_id}"),
            InlineKeyboardButton(text="🎬 480p", callback_data=f"dl:480:{url_id}"),
        ],
        [
            InlineKeyboardButton(text="🎵 MP3", callback_data=f"dl:audio:{url_id}"),
            InlineKeyboardButton(text="📝 Текст", callback_data=f"dl:transcribe:{url_id}"),
            InlineKeyboardButton(text="⚡ Best", callback_data=f"dl:best:{url_id}"),
        ],
        [
            InlineKeyboardButton(text="❌", callback_data=f"dl:cancel:{url_id}"),
        ]
    ])

def check_access(user_id: int) -> bool:
    return not ALLOWED_USERS or user_id in ALLOWED_USERS

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    if not check_access(message.from_user.id):
        return
    text = """🎬 <b>Сейвер v6.1</b>

Быстрое скачивание из:
• YouTube, TikTok, Instagram
• Twitter/X, Reddit
• 📌 Pinterest (фото и видео)

<b>Использование:</b>
Отправь ссылку → выбери формат
📝 Текст — транскрипция через Whisper AI

<b>Команды:</b>
/audio [url] — MP3
/v [url] — видео 720p"""
    await message.answer(text, parse_mode=ParseMode.HTML)

@dp.message(Command("audio"))
async def cmd_audio(message: types.Message):
    if not check_access(message.from_user.id):
        return
    url = extract_url(message.text.replace('/audio', ''))
    if url:
        await process_download(message, url, "audio")
    else:
        await message.answer("❌ /audio https://...")

@dp.message(Command("v"))
async def cmd_video(message: types.Message):
    if not check_access(message.from_user.id):
        return
    url = extract_url(message.text.replace('/v', ''))
    if url:
        await process_download(message, url, "720")
    else:
        await message.answer("❌ /v https://...")

@dp.message(F.text)
async def handle_url(message: types.Message):
    if not check_access(message.from_user.id):
        return

    text = message.text or ""

    is_group = message.chat.type in ("group", "supergroup")
    if is_group:
        bot_info = await bot.get_me()
        bot_username = f"@{bot_info.username}"
        is_reply_to_bot = (message.reply_to_message and
                          message.reply_to_message.from_user and
                          message.reply_to_message.from_user.id == bot_info.id)

        if bot_username.lower() not in text.lower() and not is_reply_to_bot:
            return

        text = text.replace(bot_username, "").replace(bot_username.lower(), "")

    url = extract_url(text)
    if not url:
        return

    if is_pinterest_url(url):
        await process_pinterest(message, url)
        return

    emoji = get_emoji(detect_platform(url))
    short = url[:45] + "..." if len(url) > 45 else url
    await message.answer(
        f"{emoji} <b>Выбери формат:</b>\n<code>{short}</code>",
        parse_mode=ParseMode.HTML,
        reply_markup=get_keyboard(url)
    )

@dp.callback_query(F.data.startswith("dl:"))
async def handle_callback(callback: CallbackQuery):
    if not check_access(callback.from_user.id):
        return

    parts = callback.data.split(":")
    if len(parts) != 3:
        return

    _, quality, url_id = parts

    if quality == "cancel":
        pending_downloads.pop(url_id, None)
        await callback.message.delete()
        return

    url = pending_downloads.pop(url_id, None)
    if not url:
        await callback.answer("Устарело")
        await callback.message.delete()
        return

    await callback.answer("⏳")
    await process_download(callback.message, url, quality, edit=True)

async def process_pinterest(message: types.Message, url: str):
    status_msg = await message.answer("📌 Скачиваю из Pinterest...")

    try:
        media = await fetch_pinterest_media(url)
        if not media:
            await status_msg.edit_text("❌ Не удалось получить медиа из этого пина")
            return

        if media['type'] == 'image':
            try:
                await message.answer_photo(photo=media['url'], caption="📌 Pinterest")
                await status_msg.delete()
                return
            except Exception:
                filepath = await download_file_from_url(media['url'], '.jpg')
        else:
            filepath = await download_file_from_url(media['url'], '.mp4')

        if not filepath or not filepath.exists():
            await status_msg.edit_text("❌ Не удалось скачать файл")
            return

        file_size = filepath.stat().st_size
        if file_size > 50 * 1024 * 1024:
            filepath.unlink()
            await status_msg.edit_text("❌ Файл > 50 МБ")
            return

        size_mb = file_size / 1024 / 1024
        await status_msg.edit_text(f"📌 Отправляю ({size_mb:.1f} МБ)...")

        file = FSInputFile(filepath)
        if media['type'] == 'video':
            await message.answer_video(file, caption="📌 Pinterest", supports_streaming=True)
        else:
            await message.answer_photo(file, caption="📌 Pinterest")

        await status_msg.delete()

    except Exception as e:
        await status_msg.edit_text(f"❌ {str(e)[:100]}")
    finally:
        if 'filepath' in locals() and filepath and filepath.exists():
            try:
                filepath.unlink()
            except Exception:
                pass


async def process_download(message: types.Message, url: str, quality: str, edit: bool = False):
    """Основная логика скачивания и транскрипции"""

    emoji = get_emoji(detect_platform(url))
    is_transcribe = quality == "transcribe"
    audio_only = quality in ("audio", "transcribe")

    q_text = "MP3" if quality == "audio" else ("📝 Транскрипция..." if is_transcribe else quality)

    status = f"{emoji} Скачиваю ({q_text})..."
    if edit:
        status_msg = message
        await status_msg.edit_text(status, reply_markup=None)
    else:
        status_msg = await message.answer(status)

    filepath = None
    try:
        filepath, filename, error = await download_media(
            url, audio_only, quality, for_transcription=is_transcribe
        )

        if error:
            await status_msg.edit_text(f"❌ {error}")
            return

        if not filepath or not filepath.exists():
            await status_msg.edit_text("❌ Файл не скачан")
            return

        # ── Транскрипция через Groq Whisper ──
        if is_transcribe:
            await status_msg.edit_text("🎙️ Транскрибирую через Whisper AI...")
            transcript, err = await transcribe_with_groq(filepath)

            if err:
                await status_msg.edit_text(f"❌ {err}")
                return

            await status_msg.delete()

            # Короткий текст — сообщением, длинный — файлом
            header = f"📝 <b>{filename}</b>\n\n"
            if len(header) + len(transcript) <= 4000:
                await message.answer(header + transcript, parse_mode=ParseMode.HTML)
            else:
                txt_path = filepath.with_suffix('.txt')
                txt_path.write_text(transcript, encoding='utf-8')
                txt_file = FSInputFile(txt_path, filename=f"{filename}.txt")
                await message.answer_document(txt_file, caption=f"📝 {filename}")
                txt_path.unlink()
            return

        # ── Обычная отправка файла ──
        file_size = filepath.stat().st_size
        if file_size > 50 * 1024 * 1024:
            await status_msg.edit_text("❌ Файл > 50 МБ. Попробуй ниже качество.")
            return

        size_mb = file_size / 1024 / 1024
        await status_msg.edit_text(f"{emoji} Отправляю ({size_mb:.1f} МБ)...")

        ext = filepath.suffix or ('.mp3' if audio_only else '.mp4')
        file = FSInputFile(filepath, filename=f"{filename}{ext}")

        if audio_only:
            await message.answer_audio(file, title=filename)
        else:
            await message.answer_video(file, caption=f"{emoji} {filename}", supports_streaming=True)

        await status_msg.delete()

    except Exception as e:
        logger.exception(f"process_download error: {e}")
        await status_msg.edit_text(f"❌ {str(e)[:100]}")

    finally:
        if filepath and filepath.exists():
            try:
                filepath.unlink()
            except Exception:
                pass

# ═══════════════════════════════════════════════════════════
# ЗАПУСК
# ═══════════════════════════════════════════════════════════

async def main():
    logger.info("🚀 Сейвер v6.1 — yt-dlp + Pinterest + Groq Whisper")

    try:
        subprocess.run(['pip', 'install', '-U', 'yt-dlp'], capture_output=True, timeout=60)
        logger.info("[yt-dlp] Updated to latest version")
    except Exception:
        pass

    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
