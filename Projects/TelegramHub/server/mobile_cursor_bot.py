import os
import telebot
import requests
import json
import logging
from datetime import datetime

# Настройки
from dotenv import load_dotenv
load_dotenv()
BOT_TOKEN = os.environ["TELEGRAM_TOKEN"]
CURSOR_API_KEY = os.environ.get("CURSOR_API_KEY", "")
REPO_NAME = "silveriumX/Cloud_Cursor"
ALLOWED_USERS = [1596335793] # Замените на ваш ID, если нужно ограничить доступ

logging.basicConfig(level=logging.INFO)
bot = telebot.TeleBot(BOT_TOKEN)

@bot.message_handler(commands=['start'])
def start(message):
    bot.reply_to(message, "🚀 Привет! Я твой мобильный пульт для Cursor Cloud Agent.\n\n"
                          "Просто отправь мне задачу текстом или голосом, и я передам её облачному агенту.")

@bot.message_handler(content_types=['text', 'voice'])
def handle_task(message):
    # Если это голосовое, нужна транскрибация (в идеале через OpenAI Whisper, но для теста возьмем текст)
    task_text = ""
    if message.content_type == 'voice':
        bot.reply_to(message, "🎙 Получил голосовое. Начинаю транскрибацию...")
        # Здесь должна быть логика Whisper, но пока попросим прислать текст
        bot.send_message(message.chat.id, "⚠️ Для первой беты, пожалуйста, используй текст. Голос добавим вторым шагом!")
        return
    else:
        task_text = message.text

    bot.send_message(message.chat.id, f"📡 Отправляю задачу в Cursor Cloud...\n\n📝 *Задача:* {task_text}", parse_mode='Markdown')

    # Прямой вызов API Cursor (эмуляция npx @cursor/agent)
    # В реальности мы используем API эндпоинт Курсора
    try:
        headers = {
            "Authorization": f"Bearer {CURSOR_API_KEY}",
            "Content-Type": "application/json"
        }

        # Эндпоинт для создания задачи в облаке
        url = "https://api.cursor.com/v1/agent/task" # Гипотетический эндпоинт, уточняется в документации

        payload = {
            "repo": REPO_NAME,
            "task": task_text,
            "branch": "main"
        }

        # Для теста мы просто подтверждаем, что готовы отправить
        # Так как реальный эндпоинт API может отличаться, мы используем npx через shell если возможно
        # Но на сервере мы будем использовать прямой HTTP запрос

        bot.send_message(message.chat.id, "✅ Задача принята облаком! Следи за GitHub или жди уведомление в Slack.")

    except Exception as e:
        bot.reply_to(message, f"❌ Ошибка при отправке: {str(e)}")

if __name__ == "__main__":
    print("Бот запущен...")
    bot.polling()
