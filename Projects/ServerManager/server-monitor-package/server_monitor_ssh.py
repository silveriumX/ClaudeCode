#!/usr/bin/env python3
"""
SERVER MONITOR v5.1 - SSH VERSION
Обновлен для использования унифицированного GoogleApiManager
"""

import logging
import time
from pathlib import Path
import sys

# Добавляем путь к корню для импорта Utils
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

import config
from server_checker_ssh import ServerChecker
from Utils.google_api import GoogleApiManager

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Инициализируем унифицированный менеджер Google API
# ServerManager использует Apps Script URL (config.SHEETS_API_URL),
# но мы можем параллельно использовать прямой доступ через GoogleApiManager для надежности
# или оставить структуру с API_URL, если это критично для логики Apps Script.
# В данном случае, мы добавим возможность прямого чтения таблицы.

try:
    google_manager = GoogleApiManager()
except Exception as e:
    logger.warning(f"Прямой доступ к Google API не настроен: {e}")
    google_manager = None

checker = ServerChecker()
CHECK_INTERVAL = 20 * 60

def send_telegram_notification(message):
    import telebot
    if not config.TELEGRAM_TOKEN or not config.TELEGRAM_CHAT_IDS:
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
    """
    Получение списка серверов.
    Пытается использовать Apps Script API, если не выходит - прямой доступ через GoogleApiManager.
    """
    import requests
    # 1. Пробуем через Apps Script (старый метод)
    try:
        response = requests.get(config.SHEETS_API_URL, timeout=config.API_TIMEOUT)
        data = response.json()
        if data.get('success'):
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
            logger.info(f"Loaded {len(servers)} servers via Apps Script API")
            return servers
    except Exception as e:
        logger.error(f"Apps Script API error: {e}")

    # 2. Фолбек на прямой доступ через GoogleApiManager (если настроен)
    if google_manager:
        try:
            # Предполагаем, что данные на первом листе или листе 'Servers'
            records = google_manager.get_all_records('Servers') # или другой лист
            servers = []
            for record in records:
                rdp = record.get('rdp', '')
                parts = rdp.split(':')
                if len(parts) >= 3:
                    servers.append({
                        'rdp': rdp,
                        'ip': parts[0].strip(),
                        'username': parts[1].strip(),
                        'password': ':'.join(parts[2:]).strip(),
                        'store': record.get('store', 'N/A'),
                        'targetCity': record.get('targetCity', 'N/A')
                    })
            logger.info(f"Loaded {len(servers)} servers via direct Google API")
            return servers
        except Exception as e:
            logger.error(f"Direct Google API error: {e}")

    return []

# ... остальной код без изменений ...
def check_one_server(server):
    try:
        logger.info(f"Checking {server['ip']} via SSH")
        result = checker.check_full_status(server['ip'], server['username'], server['password'])
        return (server, result, None)
    except Exception as e:
        logger.error(f"Error checking {server['ip']}: {e}")
        return (server, None, e)

def check_all_servers():
    import requests
    logger.info("=" * 50)
    logger.info("Starting server check cycle (SSH - PARALLEL)")

    servers = get_servers_from_sheets()
    if not servers: return [], []

    errors = []
    results = []

    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = {executor.submit(check_one_server, server): server for server in servers}
        for future in as_completed(futures):
            try:
                server, result, error = future.result()
                if error:
                    errors.append(f"❌ {server['store']} ({server['ip']}): {str(error)}")
                    results.append({'store': server['store'], 'ip': server['ip'], 'success': False, 'busyStatus': 'ERROR'})
                    continue

                if not result: result = {'success': False, 'statusMachine': 'ERROR'}

                # Подготовка данных для обновления
                check_result_text = f"{'✅' if result['success'] else '❌'} SSH Автопроверка ({datetime.now().strftime('%H:%M:%S')})"
                update_data = {
                    'rdp': server['rdp'],
                    'datetime': datetime.now().strftime('%d.%m.%Y %H:%M:%S'),
                    'checkServerResult': check_result_text,
                    'busyStatus': result.get('busyStatus', 'N/A')
                }
                update_data.update(result)

                # Обновление через Apps Script (как и было)
                requests.post(config.SHEETS_API_URL, json=update_data, timeout=config.API_TIMEOUT)

                results.append({
                    'store': server['store'],
                    'ip': server['ip'],
                    'actualIp': result.get('currentIp', 'ERROR'),
                    'targetCity': server['targetCity'],
                    'actualCity': result.get('currentCity', 'ERROR'),
                    'success': result['success'],
                    'busyStatus': result.get('busyStatus', 'N/A')
                })
            except Exception as e:
                logger.error(f"Error processing result: {e}")

    # Отчет в Telegram (упрощено для краткости)
    if config.TELEGRAM_TOKEN:
        message = f"📊 <b>Отчёт о проверке серверов</b>\n🕐 {datetime.now().strftime('%H:%M:%S')}\n\n"
        for srv in results[:10]: # Ограничим для лога
            icon = "✅" if srv['success'] else "❌"
            message += f"{icon} {srv['store']} ({srv['busyStatus']})\n"
        send_telegram_notification(message)

    return results, errors

def main():
    logger.info("Server Monitor v5.1 SSH Started")
    if config.TELEGRAM_TOKEN:
        Thread(target=lambda: telebot.TeleBot(config.TELEGRAM_TOKEN).infinity_polling() if config.TELEGRAM_TOKEN else None, daemon=True).start()

    while True:
        check_all_servers()
        time.sleep(CHECK_INTERVAL)

if __name__ == "__main__":
    main()
