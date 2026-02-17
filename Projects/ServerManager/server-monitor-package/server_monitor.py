#!/usr/bin/env python3
"""
=============================================================================
SERVER MONITOR - Автоматический мониторинг серверов + Telegram бот
=============================================================================
Описание:
- Проверяет все сервера каждые 20 минут
- Отправляет отчёты в Telegram
- Telegram бот для управления (/check, /status, /help)
Версия: 3.0
Дата: 04.01.2026
=============================================================================
"""

import logging
import time
import requests
import telebot
from datetime import datetime
from threading import Thread

import config
from server_checker import ServerChecker

# =============================================================================
# НАСТРОЙКА ЛОГИРОВАНИЯ
# =============================================================================
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# =============================================================================
# ИНИЦИАЛИЗАЦИЯ МОДУЛЕЙ
# =============================================================================
checker = ServerChecker()

# =============================================================================
# КОНСТАНТЫ
# =============================================================================
CHECK_INTERVAL = 20 * 60  # 20 минут в секундах

# =============================================================================
# ФУНКЦИЯ: Отправка уведомлений в Telegram
# =============================================================================
def send_telegram_notification(message):
    """
    Отправляет сообщение в Telegram группу/чат

    Args:
        message (str): Текст сообщения в HTML формате
    """
    if not config.TELEGRAM_TOKEN:
        logger.warning("Telegram token not configured")
        return

    if not config.TELEGRAM_CHAT_IDS:
        logger.info("No Telegram recipients configured")
        return

    try:
        bot = telebot.TeleBot(config.TELEGRAM_TOKEN)

        for chat_id in config.TELEGRAM_CHAT_IDS:
            try:
                bot.send_message(chat_id, message, parse_mode='HTML')
                logger.info(f"Telegram notification sent to {chat_id}")
            except Exception as e:
                logger.error(f"Failed to send to {chat_id}: {e}")

    except Exception as e:
        logger.error(f"Telegram error: {e}")

# =============================================================================
# ФУНКЦИЯ: Загрузка списка серверов из Google Sheets
# =============================================================================
def get_servers_from_sheets():
    """
    Получает список серверов из Google Sheets через Apps Script API

    Returns:
        list: Список словарей с данными серверов
    """
    try:
        response = requests.get(config.SHEETS_API_URL, timeout=config.API_TIMEOUT)
        data = response.json()

        if not data.get('success'):
            logger.error("Failed to get servers from Google Sheets")
            return []

        servers = []

        for server_data in data.get('data', []):
            rdp = server_data.get('rdp', '')
            parts = rdp.split(':')

            if len(parts) >= 3:
                servers.append({
                    'rdp': rdp,
                    'ip': parts[0].strip(),
                    'username': parts[1].strip(),
                    'password': ':'.join(parts[2:]).strip(),
                    'store': server_data.get('store', 'N/A'),
                    'targetCity': server_data.get('targetCity', 'N/A')
                })

        logger.info(f"Loaded {len(servers)} servers from Google Sheets")
        return servers

    except Exception as e:
        logger.error(f"Error loading servers: {e}")
        return []

# =============================================================================
# ФУНКЦИЯ: Проверка всех серверов
# =============================================================================
def check_all_servers():
    """
    Главная функция проверки всех серверов

    Выполняет:
    1. Загрузку списка серверов
    2. Проверку каждого сервера
    3. Обновление Google Sheets
    4. Формирование и отправку Telegram отчёта

    Returns:
        tuple: (results, errors) - результаты проверки и список ошибок
    """
    logger.info("=" * 50)
    logger.info("Starting server check cycle")
    logger.info("=" * 50)

    # --- ЗАГРУЗКА СЕРВЕРОВ ---
    servers = get_servers_from_sheets()

    if not servers:
        logger.warning("No servers to check")
        return [], []

    # --- ИНИЦИАЛИЗАЦИЯ ---
    errors = []
    results = []

    # --- ПРОВЕРКА КАЖДОГО СЕРВЕРА ---
    for server in servers:
        try:
            logger.info(f"Checking {server['ip']}")

            # Проверка статуса
            result = checker.check_full_status(
                server['ip'],
                server['username'],
                server['password']
            )

            # --- ФОРМИРОВАНИЕ РЕЗУЛЬТАТА ДЛЯ КОЛОНКИ AK ---
            if result['success']:
                check_result_text = f"✅ Автопроверка ({datetime.now().strftime('%H:%M:%S')})\n"
                check_result_text += f"IP: {result['currentIp']}\n"
                check_result_text += f"Город: {result['currentCity']}\n"
                check_result_text += f"Proxifier: {'✅' if result['statusProxy'] == 'OK' else '❌'}\n"
                check_result_text += f"AnyDesk: {'✅' if result['anydesk'] else '❌'}\n"
                check_result_text += f"RustDesk: {'✅' if result['rustdesk'] else '❌'}"
            else:
                check_result_text = f"❌ Автопроверка: сервер недоступен ({datetime.now().strftime('%H:%M:%S')})"

            # --- ПОДГОТОВКА ДАННЫХ ДЛЯ GOOGLE SHEETS ---
            update_data = {
                'rdp': server['rdp'],
                'datetime': datetime.now().strftime('%d.%m.%Y %H:%M:%S'),
                'checkServerResult': check_result_text  # ⭐ НОВАЯ КОЛОНКА AK
            }
            update_data.update(result)

            # --- ОБНОВЛЕНИЕ GOOGLE SHEETS ---
            requests.post(
                config.SHEETS_API_URL,
                json=update_data,
                headers={'Content-Type': 'application/json'},
                timeout=config.API_TIMEOUT
            )

            logger.info(f"[{server['ip']}] {result['statusMachine']} | {result['statusProxy']}")

            # --- СОХРАНЕНИЕ ДЛЯ TELEGRAM ОТЧЁТА ---
            server_info = {
                'store': server['store'],
                'ip': server['ip'],
                'actualIp': result.get('currentIp', 'ERROR'),
                'targetCity': server['targetCity'],
                'actualCity': result.get('currentCity', 'ERROR'),
                'status': result['statusMachine'],
                'proxyStatus': result['statusProxy'],
                'success': result['success']
            }
            results.append(server_info)

            # --- СБОР ОШИБОК ---
            if not result['success']:
                errors.append(f"❌ {server['store']} ({server['ip']}): {result['statusMachine']}")
            elif result['statusProxy'] != 'OK':
                errors.append(f"⚠️ {server['store']} ({server['ip']}): {result['statusProxy']}")

        except Exception as e:
            logger.error(f"Error checking {server['ip']}: {e}")
            errors.append(f"❌ {server['store']} ({server['ip']}): {str(e)}")

            results.append({
                'store': server['store'],
                'ip': server['ip'],
                'actualIp': 'ERROR',
                'targetCity': server['targetCity'],
                'actualCity': 'ERROR',
                'status': 'ERROR',
                'proxyStatus': 'ERROR',
                'success': False
            })

    # --- ФОРМИРОВАНИЕ TELEGRAM ОТЧЁТА ---
    if config.TELEGRAM_TOKEN and config.TELEGRAM_CHAT_IDS:
        message = "📊 <b>Отчёт о проверке серверов</b>\n"
        message += f"🕐 {datetime.now().strftime('%d.%m.%Y %H:%M:%S')}\n\n"

        online_count = sum(1 for srv in results if srv['success'])
        offline_count = len(results) - online_count

        for srv in results:
            status_icon = "✅" if srv['success'] else "❌"
            message += f"{status_icon} <b>{srv['store']}</b>\n"
            message += f"   RDP: {srv['ip']}\n"
            message += f"   IP на выходе: {srv.get('actualIp', 'N/A')}\n"
            message += f"   Город: {srv['targetCity']} → {srv['actualCity']}\n"
            message += f"   Статус: {srv['status']}\n\n"

        message += f"📈 <b>Итого:</b>\n"
        message += f"✅ Онлайн: {online_count}\n"
        message += f"❌ Офлайн/Ошибки: {offline_count}\n"

        if errors:
            message += f"\n🚨 <b>Проблемы:</b>\n"
            for err in errors[:5]:
                message += f"{err}\n"
            if len(errors) > 5:
                message += f"... и ещё {len(errors) - 5}"

        send_telegram_notification(message)

    logger.info("=" * 50)
    logger.info(f"Check cycle completed. Errors: {len(errors)}")
    logger.info("=" * 50)

    return results, errors

# =============================================================================
# TELEGRAM БОТ - Обработчики команд
# =============================================================================
def start_telegram_bot():
    """
    Запускает Telegram бота для приёма команд

    Команды:
    /check - запустить проверку всех серверов
    /status - показать статистику
    /help - список команд
    """
    if not config.TELEGRAM_TOKEN:
        logger.warning("Telegram bot disabled: no token configured")
        return

    try:
        bot = telebot.TeleBot(config.TELEGRAM_TOKEN)

        # --- КОМАНДА: /check ---
        @bot.message_handler(commands=['check'])
        def handle_check(message):
            """Запуск проверки всех серверов по команде"""
            logger.info(f"Telegram command /check from {message.chat.id}")

            # Отправка уведомления о начале проверки
            bot.send_message(message.chat.id, "🔄 Запускаю проверку всех серверов...", parse_mode='HTML')

            # Запуск проверки
            results, errors = check_all_servers()

            # Отправка результата уже произошла в check_all_servers()
            bot.send_message(message.chat.id, "✅ Проверка завершена! Результаты выше.", parse_mode='HTML')

        # --- КОМАНДА: /status ---
        @bot.message_handler(commands=['status'])
        def handle_status(message):
            """Показать общую статистику серверов"""
            logger.info(f"Telegram command /status from {message.chat.id}")

            try:
                servers = get_servers_from_sheets()

                msg = "📊 <b>Статистика серверов</b>\n\n"
                msg += f"📈 Всего серверов: {len(servers)}\n"
                msg += f"⏰ Интервал проверки: {CHECK_INTERVAL // 60} минут\n"
                msg += f"🕐 Время: {datetime.now().strftime('%d.%m.%Y %H:%M:%S')}\n\n"
                msg += "Используйте /check для запуска проверки"

                bot.send_message(message.chat.id, msg, parse_mode='HTML')

            except Exception as e:
                bot.send_message(message.chat.id, f"❌ Ошибка: {str(e)}", parse_mode='HTML')

        # --- КОМАНДА: /help ---
        @bot.message_handler(commands=['help', 'start'])
        def handle_help(message):
            """Показать список команд"""
            logger.info(f"Telegram command /help from {message.chat.id}")

            msg = "🤖 <b>Бот мониторинга серверов</b>\n\n"
            msg += "<b>Доступные команды:</b>\n"
            msg += "/check - Запустить проверку всех серверов\n"
            msg += "/status - Показать статистику\n"
            msg += "/help - Показать эту справку\n\n"
            msg += f"⏰ Автоматическая проверка каждые {CHECK_INTERVAL // 60} минут"

            bot.send_message(message.chat.id, msg, parse_mode='HTML')

        # --- ЗАПУСК БОТА ---
        logger.info("Telegram bot started")
        bot.infinity_polling()

    except Exception as e:
        logger.error(f"Telegram bot error: {e}")

# =============================================================================
# ГЛАВНАЯ ФУНКЦИЯ: Основной цикл мониторинга
# =============================================================================
def main():
    """
    Главный цикл программы

    Запускает:
    1. Telegram бота в отдельном потоке
    2. Цикл автоматической проверки каждые 20 минут
    """
    logger.info("=" * 50)
    logger.info("Server Monitor Started")
    logger.info(f"Check interval: {CHECK_INTERVAL // 60} minutes")
    logger.info(f"Telegram chats: {config.TELEGRAM_CHAT_IDS}")
    logger.info("=" * 50)

    # --- УВЕДОМЛЕНИЕ О ЗАПУСКЕ ---
    startup_msg = "🚀 <b>Мониторинг серверов запущен</b>\n\n"
    startup_msg += f"⏰ Интервал проверки: {CHECK_INTERVAL // 60} минут\n"
    startup_msg += f"📅 Время запуска: {datetime.now().strftime('%d.%m.%Y %H:%M:%S')}\n\n"
    startup_msg += "💬 Используйте команду /check для ручной проверки"
    send_telegram_notification(startup_msg)

    # --- ЗАПУСК TELEGRAM БОТА В ОТДЕЛЬНОМ ПОТОКЕ ---
    if config.TELEGRAM_TOKEN:
        bot_thread = Thread(target=start_telegram_bot, daemon=True)
        bot_thread.start()
        logger.info("Telegram bot thread started")

    # --- ОСНОВНОЙ ЦИКЛ МОНИТОРИНГА ---
    while True:
        try:
            check_all_servers()

            logger.info(f"Sleeping for {CHECK_INTERVAL // 60} minutes...")
            time.sleep(CHECK_INTERVAL)

        except KeyboardInterrupt:
            logger.info("Monitor stopped by user")
            break

        except Exception as e:
            logger.error(f"Error in main loop: {e}")
            time.sleep(60)

# =============================================================================
# ТОЧКА ВХОДА
# =============================================================================
if __name__ == "__main__":
    main()
