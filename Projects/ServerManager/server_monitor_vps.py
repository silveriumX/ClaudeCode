#!/usr/bin/env python3
"""
SERVER MONITOR v4.1 - with session monitoring + target city
"""

import logging
import time
import requests
import telebot
from datetime import datetime
from threading import Thread

import config
from server_checker import ServerChecker
from session_checker import SessionChecker

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

checker = ServerChecker()
session_checker = SessionChecker()

CHECK_INTERVAL = 20 * 60

def send_telegram_notification(message):
    if not config.TELEGRAM_TOKEN:
        return
    if not config.TELEGRAM_CHAT_IDS:
        return
    try:
        bot = telebot.TeleBot(config.TELEGRAM_TOKEN)
        for chat_id in config.TELEGRAM_CHAT_IDS:
            try:
                bot.send_message(chat_id, message, parse_mode='HTML')
            except Exception as e:
                logger.error(f"Failed to send to {chat_id}: {e}")
    except Exception as e:
        logger.error(f"Telegram error: {e}")

def get_servers_from_sheets():
    try:
        response = requests.get(config.SHEETS_API_URL, timeout=config.API_TIMEOUT)
        data = response.json()
        if not data.get('success'):
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
        logger.info(f"Loaded {len(servers)} servers")
        return servers
    except Exception as e:
        logger.error(f"Error loading servers: {e}")
        return []

def check_all_servers():
    logger.info("=" * 50)
    logger.info("Starting server check cycle")

    servers = get_servers_from_sheets()
    if not servers:
        return [], []

    errors = []
    results = []

    for server in servers:
        try:
            logger.info(f"Checking {server['ip']}")

            result = checker.check_full_status(
                server['ip'],
                server['username'],
                server['password']
            )

            # Check sessions
            busy_status = 'N/A'
            client_ip = ''
            try:
                session_result = session_checker.check_sessions(
                    server['ip'],
                    server['username'],
                    server['password']
                )
                busy_status = session_result.get('busyStatus', 'N/A')
                client_ip = session_result.get('clientIp', '')
                result['busyStatus'] = busy_status
                result['clientIp'] = client_ip
            except Exception as e:
                logger.warning(f"Session check failed: {e}")

            if result['success']:
                check_result_text = f"✅ Автопроверка ({datetime.now().strftime('%H:%M:%S')})\n"
                check_result_text += f"IP: {result['currentIp']}\n"
                check_result_text += f"Город: {result['currentCity']}\n"
                check_result_text += f"Proxifier: {'✅' if result['statusProxy'] == 'OK' else '❌'}\n"
                check_result_text += f"AnyDesk: {'✅' if result['anydesk'] else '❌'}\n"
                check_result_text += f"RustDesk: {'✅' if result['rustdesk'] else '❌'}\n"
                check_result_text += f"Статус: {busy_status}"
                if client_ip:
                    check_result_text += f"\nКлиент IP: {client_ip}"
            else:
                check_result_text = f"❌ Автопроверка: сервер недоступен ({datetime.now().strftime('%H:%M:%S')})"

            update_data = {
                'rdp': server['rdp'],
                'datetime': datetime.now().strftime('%d.%m.%Y %H:%M:%S'),
                'checkServerResult': check_result_text,
                'busyStatus': busy_status,
                'clientIp': client_ip
            }
            update_data.update(result)

            requests.post(
                config.SHEETS_API_URL,
                json=update_data,
                headers={'Content-Type': 'application/json'},
                timeout=config.API_TIMEOUT
            )

            server_info = {
                'store': server['store'],
                'ip': server['ip'],
                'actualIp': result.get('currentIp', 'ERROR'),
                'targetCity': server['targetCity'],
                'actualCity': result.get('currentCity', 'ERROR'),
                'status': result['statusMachine'],
                'proxyStatus': result['statusProxy'],
                'busyStatus': busy_status,
                'clientIp': client_ip,
                'success': result['success']
            }
            results.append(server_info)

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
                'busyStatus': 'N/A',
                'clientIp': '',
                'success': False
            })

    # Telegram report
    if config.TELEGRAM_TOKEN and config.TELEGRAM_CHAT_IDS:
        message = "📊 <b>Отчёт о проверке серверов</b>\n"
        message += f"🕐 {datetime.now().strftime('%d.%m.%Y %H:%M:%S')}\n\n"

        online_count = sum(1 for srv in results if srv['success'])
        offline_count = len(results) - online_count
        busy_count = sum(1 for srv in results if 'Занят' in srv.get('busyStatus', ''))
        free_count = sum(1 for srv in results if srv.get('busyStatus') == 'Свободен')

        for srv in results:
            status_icon = "✅" if srv['success'] else "❌"
            busy_icon = "🔴" if 'Занят' in srv.get('busyStatus', '') else "🟢"

            message += f"{status_icon} <b>{srv['store']}</b>\n"
            message += f"   RDP: {srv['ip']}\n"
            message += f"   IP: {srv.get('actualIp', 'N/A')}\n"
            message += f"   Город: {srv['targetCity']} → {srv['actualCity']}\n"
            message += f"   {busy_icon} {srv.get('busyStatus', 'N/A')}"
            if srv.get('clientIp'):
                message += f" (с {srv['clientIp']})"
            message += "\n\n"

        message += f"📈 <b>Итого:</b>\n"
        message += f"✅ Онлайн: {online_count} | ❌ Офлайн: {offline_count}\n"
        message += f"🟢 Свободно: {free_count} | 🔴 Занято: {busy_count}\n"

        if errors:
            message += f"\n🚨 <b>Проблемы:</b>\n"
            for err in errors[:5]:
                message += f"{err}\n"
            if len(errors) > 5:
                message += f"... и ещё {len(errors) - 5}"

        send_telegram_notification(message)

    logger.info(f"Check completed. Errors: {len(errors)}")
    return results, errors

def start_telegram_bot():
    if not config.TELEGRAM_TOKEN:
        return
    try:
        bot = telebot.TeleBot(config.TELEGRAM_TOKEN)

        @bot.message_handler(commands=['check'])
        def handle_check(message):
            bot.send_message(message.chat.id, "🔄 Запускаю проверку...", parse_mode='HTML')
            check_all_servers()
            bot.send_message(message.chat.id, "✅ Проверка завершена!", parse_mode='HTML')

        @bot.message_handler(commands=['status'])
        def handle_status(message):
            servers = get_servers_from_sheets()
            msg = f"📊 <b>Статистика</b>\n\n"
            msg += f"📈 Серверов: {len(servers)}\n"
            msg += f"⏰ Интервал: {CHECK_INTERVAL // 60} мин\n"
            msg += f"🕐 {datetime.now().strftime('%d.%m.%Y %H:%M:%S')}"
            bot.send_message(message.chat.id, msg, parse_mode='HTML')

        @bot.message_handler(commands=['help', 'start'])
        def handle_help(message):
            msg = "🤖 <b>Бот мониторинга v4.1</b>\n\n"
            msg += "/check - Проверить все сервера\n"
            msg += "/status - Статистика\n"
            msg += "/help - Справка\n\n"
            msg += f"⏰ Авто-проверка каждые {CHECK_INTERVAL // 60} мин"
            bot.send_message(message.chat.id, msg, parse_mode='HTML')

        logger.info("Telegram bot started")
        bot.infinity_polling()
    except Exception as e:
        logger.error(f"Bot error: {e}")

def main():
    logger.info("Server Monitor v4.1 Started")

    startup_msg = "🚀 <b>Мониторинг v4.1 запущен</b>\n\n"
    startup_msg += f"⏰ Интервал: {CHECK_INTERVAL // 60} мин\n"
    startup_msg += f"📅 {datetime.now().strftime('%d.%m.%Y %H:%M:%S')}\n\n"
    startup_msg += "🆕 Мониторинг сессий + целевой город"
    send_telegram_notification(startup_msg)

    if config.TELEGRAM_TOKEN:
        bot_thread = Thread(target=start_telegram_bot, daemon=True)
        bot_thread.start()

    while True:
        try:
            check_all_servers()
            logger.info(f"Sleeping {CHECK_INTERVAL // 60} min...")
            time.sleep(CHECK_INTERVAL)
        except KeyboardInterrupt:
            break
        except Exception as e:
            logger.error(f"Error: {e}")
            time.sleep(60)

if __name__ == "__main__":
    main()
