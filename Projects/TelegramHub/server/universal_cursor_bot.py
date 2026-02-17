#!/usr/bin/env python3
"""
Universal Cursor Bot - Полноценный AI помощник в Telegram
- Голосовые сообщения (транскрибация через Whisper)
- Ответы на вопросы (Claude, GPT, Gemini)
- Изменение кода в GitHub (через Cursor Cloud Agent при команде /code)
"""
import os
import asyncio
from datetime import datetime
from pathlib import Path
import telebot
from telebot import types
from openai import OpenAI

# Опциональные провайдеры
try:
    import anthropic
except ImportError:
    anthropic = None

try:
    import google.generativeai as genai
except ImportError:
    genai = None

# === НАСТРОЙКИ ===
from dotenv import load_dotenv
load_dotenv()
TELEGRAM_TOKEN = os.environ["TELEGRAM_TOKEN"]
CURSOR_API_KEY = os.environ.get("CURSOR_API_KEY", "")
OPENAI_API_KEY = os.environ["OPENAI_API_KEY"]

# API ключи для разных провайдеров (добавьте свои если есть)
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY", "")

REPO_NAME = "silveriumX/Cloud_Cursor"
MY_USER_ID = 963129618

# Директория для временных файлов
TEMP_DIR = Path("/tmp/cursor_bot")
TEMP_DIR.mkdir(exist_ok=True)

# === ИНИЦИАЛИЗАЦИЯ ===
bot = telebot.TeleBot(TELEGRAM_TOKEN)
openai_client = OpenAI(api_key=OPENAI_API_KEY)

# Инициализация других провайдеров
anthropic_client = None
if ANTHROPIC_API_KEY:
    anthropic_client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

# Google (Gemini) - будет подключен через google-generativeai
try:
    import google.generativeai as genai
    if GOOGLE_API_KEY:
        genai.configure(api_key=GOOGLE_API_KEY)
except ImportError:
    genai = None

# История разговоров (для контекста)
conversation_history = {}

# Настройки модели для каждого пользователя
user_models = {}

# Доступные модели (как в Cursor)
AVAILABLE_MODELS = {
    # Claude (Anthropic) - самые популярные модели в Cursor
    "claude-sonnet-4.5": {
        "name": "Claude Sonnet 4.5",
        "description": "Идеальный баланс скорости и качества (по умолчанию в Cursor)",
        "provider": "anthropic",
        "model_id": "claude-sonnet-4-20250514"
    },
    "claude-opus-4.5": {
        "name": "Claude Opus 4.5",
        "description": "Самая мощная модель для сложных задач",
        "provider": "anthropic",
        "model_id": "claude-opus-4-20250514"
    },
    "claude-3.5-sonnet": {
        "name": "Claude 3.5 Sonnet",
        "description": "Предыдущее поколение Claude",
        "provider": "anthropic",
        "model_id": "claude-3-5-sonnet-20241022"
    },

    # Gemini (Google)
    "gemini-2.0-flash": {
        "name": "Gemini 2.0 Flash",
        "description": "Быстрая и бесплатная модель Google",
        "provider": "google",
        "model_id": "gemini-2.0-flash-exp"
    },

    # OpenAI (GPT)
    "gpt-4o": {
        "name": "GPT-4o",
        "description": "Новая модель OpenAI",
        "provider": "openai",
        "model_id": "gpt-4o"
    },
    "gpt-4-turbo": {
        "name": "GPT-4 Turbo",
        "description": "Быстрая версия GPT-4",
        "provider": "openai",
        "model_id": "gpt-4-turbo"
    }
}

DEFAULT_MODEL = "claude-sonnet-4.5"  # Как в Cursor по умолчанию

def get_user_model(user_id: int) -> str:
    """Получить текущую модель пользователя"""
    return user_models.get(user_id, DEFAULT_MODEL)

def set_user_model(user_id: int, model: str) -> bool:
    """Установить модель для пользователя"""
    if model in AVAILABLE_MODELS:
        user_models[user_id] = model
        return True
    return False

def get_ai_response(user_id: int, user_message: str) -> str:
    """Получить ответ от AI с поддержкой всех провайдеров"""

    # Получаем историю разговора
    if user_id not in conversation_history:
        conversation_history[user_id] = []

    history = conversation_history[user_id]
    history.append({"role": "user", "content": user_message})

    # Ограничиваем историю последними 10 сообщениями
    if len(history) > 20:
        history = history[-20:]

    # Получаем выбранную модель
    model_key = get_user_model(user_id)
    model_info = AVAILABLE_MODELS[model_key]
    provider = model_info["provider"]
    model_id = model_info["model_id"]

    system_prompt = "Ты - умный AI-помощник Cursor. Отвечай максимально полезно и структурированно. Если вопрос про код - давай примеры. Пиши на русском."

    try:
        # === ANTHROPIC (Claude) ===
        if provider == "anthropic":
            if not anthropic_client:
                return "❌ Claude API не настроен. Добавьте ANTHROPIC_API_KEY в переменные окружения или переключитесь на другую модель (/models)"

            # Конвертируем историю для Claude
            claude_messages = []
            for msg in history:
                claude_messages.append({
                    "role": msg["role"],
                    "content": msg["content"]
                })

            response = anthropic_client.messages.create(
                model=model_id,
                max_tokens=4000,
                system=system_prompt,
                messages=claude_messages
            )

            ai_response = response.content[0].text

        # === GOOGLE (Gemini) ===
        elif provider == "google":
            if not genai:
                return "❌ Gemini API не настроен. Установите google-generativeai или переключитесь на другую модель (/models)"

            model = genai.GenerativeModel(model_id)

            # Конвертируем историю для Gemini
            chat = model.start_chat(history=[])

            # Добавляем системный промпт как первое сообщение
            full_message = f"{system_prompt}\n\n{user_message}"

            response = chat.send_message(full_message)
            ai_response = response.text

        # === OPENAI (GPT) ===
        else:  # provider == "openai"
            response = openai_client.chat.completions.create(
                model=model_id,
                messages=[
                    {"role": "system", "content": system_prompt},
                    *history
                ],
                max_tokens=2000,
                temperature=0.7
            )

            ai_response = response.choices[0].message.content

        # Сохраняем ответ в историю
        history.append({"role": "assistant", "content": ai_response})
        conversation_history[user_id] = history

        return ai_response

    except Exception as e:
        error_msg = str(e)

        # Дружелюбные сообщения об ошибках
        if "api_key" in error_msg.lower() or "authentication" in error_msg.lower():
            return f"❌ Проблема с API ключом для {model_info['name']}.\n\nПопробуйте другую модель: /models"

        return f"❌ Ошибка {model_info['name']}: {error_msg}\n\nПопробуйте /reset или смените модель /models"


def send_to_cloud_agent(task: str) -> str:
    """Отправить задачу в Cursor Cloud Agent (заглушка - реальный API пока в бете)"""
    # TODO: Когда появится публичный API Cursor Cloud Agent, здесь будет реальный запрос
    return f"✅ Задача принята Cloud Agent!\n\n📝 Задача: {task}\n\n⚠️ Функция Cloud Agent пока в разработке. Следите за обновлениями Cursor API."


@bot.message_handler(commands=['start'])
def cmd_start(message):
    user_id = message.from_user.id
    current_model = get_user_model(user_id)
    model_name = AVAILABLE_MODELS[current_model]['name']

    bot.reply_to(message,
        "🚀 **Universal Cursor Bot**\n\n"
        "Я - твой AI-помощник с полным функционалом Cursor!\n\n"
        "**Что я умею:**\n"
        "💬 Отвечать на любые вопросы\n"
        "🎙 Понимать голосовые сообщения\n"
        "💻 Работать с кодом (команда /code)\n"
        "🤖 Переключать модели AI\n\n"
        "**Примеры:**\n"
        "• `Объясни async/await в Python`\n"
        "• `Как работает React hooks?`\n"
        "• `/code создай auth.py с логином`\n"
        "• `/models` - выбрать другую модель\n\n"
        f"**Текущая модель:** {model_name}\n\n"
        "**Команды:**\n"
        "/models - доступные модели AI\n"
        "/reset - сбросить историю\n"
        "/help - помощь",
        parse_mode='Markdown'
    )


@bot.message_handler(commands=['reset'])
def cmd_reset(message):
    user_id = message.from_user.id
    if user_id in conversation_history:
        conversation_history[user_id] = []
    bot.reply_to(message, "✅ История разговора сброшена. Начнем с чистого листа!")


@bot.message_handler(commands=['help'])
def cmd_help(message):
    bot.reply_to(message,
        "**📚 Как пользоваться ботом:**\n\n"
        "**1. Обычные вопросы (по умолчанию):**\n"
        "Просто напиши вопрос текстом или голосом\n\n"
        "**2. Работа с кодом в GitHub:**\n"
        "`/code [задача]` - изменить код в репозитории\n\n"
        "**3. Голосовые:**\n"
        "Отправь голосовое - я транскрибирую и отвечу\n\n"
        "**4. Модели AI:**\n"
        "`/models` - список доступных моделей\n"
        "`/model [название]` - переключить модель\n\n"
        "**5. Контекст:**\n"
        "Я помню последние 10 сообщений нашего диалога\n"
        "`/reset` - сбросить контекст",
        parse_mode='Markdown'
    )


@bot.message_handler(commands=['models'])
def cmd_models(message):
    """Показать доступные модели"""
    user_id = message.from_user.id
    current_model = get_user_model(user_id)

    text = "**🤖 Доступные модели AI:**\n\n"

    for model_id, info in AVAILABLE_MODELS.items():
        is_current = "✅ " if model_id == current_model else "○ "
        text += f"{is_current}**{info['name']}** (`{model_id}`)\n"
        text += f"  _{info['description']}_\n\n"

    text += f"\n**Текущая модель:** {AVAILABLE_MODELS[current_model]['name']}\n\n"
    text += "Переключить: `/model [название]`\n"
    text += "Пример: `/model gpt-4o`"

    bot.reply_to(message, text, parse_mode='Markdown')


@bot.message_handler(commands=['model'])
def cmd_model(message):
    """Переключить модель"""
    user_id = message.from_user.id
    args = message.text.split(maxsplit=1)

    if len(args) < 2:
        current_model = get_user_model(user_id)
        bot.reply_to(
            message,
            f"**Текущая модель:** {AVAILABLE_MODELS[current_model]['name']}\n\n"
            f"Доступные модели: `/models`\n"
            f"Переключить: `/model [название]`",
            parse_mode='Markdown'
        )
        return

    new_model = args[1].strip()

    if set_user_model(user_id, new_model):
        model_info = AVAILABLE_MODELS[new_model]
        bot.reply_to(
            message,
            f"✅ Модель изменена!\n\n"
            f"**{model_info['name']}**\n"
            f"_{model_info['description']}_\n\n"
            f"Теперь все ответы будут генерироваться с помощью этой модели.",
            parse_mode='Markdown'
        )
    else:
        bot.reply_to(
            message,
            f"❌ Модель `{new_model}` не найдена.\n\n"
            f"Доступные модели: `/models`",
            parse_mode='Markdown'
        )


@bot.message_handler(commands=['code'])
def cmd_code(message):
    """Команда для работы с Cloud Agent"""
    task = message.text.replace('/code', '').strip()

    if not task:
        bot.reply_to(message, "❌ Укажите задачу после /code\n\nПример:\n`/code создай файл test.py`", parse_mode='Markdown')
        return

    bot.send_message(message.chat.id, "🔄 Отправляю задачу в Cursor Cloud Agent...")
    result = send_to_cloud_agent(task)
    bot.send_message(message.chat.id, result, parse_mode='Markdown')


@bot.message_handler(content_types=['voice'])
def handle_voice(message):
    """Обработка голосовых сообщений"""
    try:
        user_id = message.from_user.id
        current_model = get_user_model(user_id)
        model_name = AVAILABLE_MODELS[current_model]['name']

        # Уведомляем пользователя
        status_msg = bot.reply_to(message, "🎙 Транскрибирую голосовое...")

        # Скачиваем файл
        file_info = bot.get_file(message.voice.file_id)
        downloaded_file = bot.download_file(file_info.file_path)

        # Сохраняем временно
        voice_path = TEMP_DIR / f"voice_{user_id}_{datetime.now().timestamp()}.ogg"
        with open(voice_path, 'wb') as f:
            f.write(downloaded_file)

        # Транскрибируем
        with open(voice_path, "rb") as audio_file:
            transcript = openai_client.audio.transcriptions.create(
                model="whisper-1",
                file=audio_file,
                language="ru"
            )

        transcribed_text = transcript.text

        # Удаляем временный файл
        voice_path.unlink()

        # Обновляем статус
        bot.edit_message_text(
            f"✅ Расшифровка: _{transcribed_text}_\n\n🤔 Думаю над ответом ({model_name})...",
            message.chat.id,
            status_msg.message_id,
            parse_mode='Markdown'
        )

        # Получаем ответ от AI
        ai_response = get_ai_response(user_id, transcribed_text)

        # Отправляем финальный ответ с указанием модели
        footer = f"\n\n_— {model_name}_"
        bot.send_message(
            message.chat.id,
            f"**Ваш вопрос:** {transcribed_text}\n\n**Ответ:**\n{ai_response}{footer}",
            parse_mode='Markdown'
        )

    except Exception as e:
        bot.reply_to(message, f"❌ Ошибка обработки голосового: {str(e)}")


@bot.message_handler(content_types=['text'])
def handle_text(message):
    """Обработка текстовых сообщений"""
    user_id = message.from_user.id
    user_message = message.text

    # Показываем какая модель отвечает
    current_model = get_user_model(user_id)
    model_name = AVAILABLE_MODELS[current_model]['name']

    status_msg = bot.send_message(message.chat.id, f"🤔 Думаю ({model_name})...")

    try:
        # Получаем ответ от AI
        ai_response = get_ai_response(user_id, user_message)

        # Удаляем статус и отправляем ответ
        bot.delete_message(message.chat.id, status_msg.message_id)

        # Добавляем информацию о модели в конец (маленькими буквами)
        footer = f"\n\n_— {model_name}_"
        bot.send_message(message.chat.id, ai_response + footer, parse_mode='Markdown')

    except Exception as e:
        bot.edit_message_text(
            f"❌ Ошибка: {str(e)}",
            message.chat.id,
            status_msg.message_id
        )


if __name__ == "__main__":
    print("=" * 60)
    print("Universal Cursor Bot запущен...")
    print("=" * 60)
    print("Режимы:")
    print("  💬 Текст -> AI ответ")
    print("  🎙 Голос -> Транскрибация + AI ответ")
    print("  💻 /code -> Cloud Agent (в разработке)")
    print("=" * 60)
    bot.infinity_polling()
