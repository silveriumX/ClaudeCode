#!/usr/bin/env python3
"""
=============================================================================
PROXYMA MONITOR - Автоматический мониторинг Proxyma пакетов
=============================================================================
Описание:
- Проверяет Proxyma пакеты каждые 3 часа
- Записывает результат для каждого сервера в Google Sheets
- Группирует данные для Telegram отчёта (без дубликатов)
- Отправляет алерты при проблемах
Версия: 3.1
Дата: 04.01.2026
=============================================================================
"""

import logging
import requests
import telebot
from datetime import datetime
from collections import defaultdict

import config
from proxyma_api import ProxymaAPI

# =============================================================================
# НАСТРОЙКА ЛОГИРОВАНИЯ
# =============================================================================
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# =============================================================================
# ФУНКЦИЯ: Отправка уведомлений в Telegram
# =============================================================================
def send_telegram_notification(message):
    """
    Отправляет сообщение в Telegram группу/чат

    Args:
        message (str): Текст сообщения в HTML формате
    """
    if not config.TELEGRAM_TOKEN or not config.TELEGRAM_CHAT_IDS:
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
# ФУНКЦИЯ: Загрузка серверов с Proxyma из Google Sheets
# =============================================================================
def get_servers_from_sheets():
    """
    Загружает список серверов с провайдером Proxyma из Google Sheets

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
            proxy_provider = server_data.get('proxyProvider', '')
            proxy_key = server_data.get('proxyKey', '')
            proxyma_api_key = server_data.get('proxymaApiKey', '')

            # Только серверы с Proxyma
            if proxy_provider and proxy_provider.lower() == 'proxyma' and proxy_key and proxyma_api_key:
                # Парсинг RDP для получения IP
                rdp = server_data.get('rdp', '')
                ip = rdp.split(':')[0] if ':' in rdp else 'N/A'

                servers.append({
                    'rdp': rdp,
                    'ip': ip,
                    'store': server_data.get('store', 'N/A'),
                    'proxyKey': proxy_key,
                    'proxymaApiKey': proxyma_api_key
                })

        logger.info(f"Found {len(servers)} servers with Proxyma")
        return servers

    except Exception as e:
        logger.error(f"Error loading servers: {e}")
        return []

# =============================================================================
# ФУНКЦИЯ: Проверка Proxyma пакета для одного сервера
# =============================================================================
def check_proxyma_package(server):
    """
    Проверяет Proxyma пакет для одного сервера

    Args:
        server (dict): Данные сервера

    Returns:
        dict: Данные пакета или None при ошибке
    """
    try:
        logger.info(f"Checking Proxyma package for {server['ip']} ({server['store']})")

        proxyma = ProxymaAPI(server['proxymaApiKey'])

        # --- ПОЛУЧЕНИЕ ИНФОРМАЦИИ О ПАКЕТЕ ---
        info = proxyma.get_package_info(server['proxyKey'])
        if not info:
            logger.error(f"Failed to get package info for {server['proxyKey']}")
            return None

        # --- ПОЛУЧЕНИЕ НАЗВАНИЯ ПАКЕТА ---
        packages = proxyma.get_packages()
        pkg_name = "Unknown"
        for pkg in packages:
            if pkg['package_key'] == server['proxyKey']:
                pkg_name = pkg['title']
                break

        # --- ПОЛУЧЕНИЕ БАЛАНСА И ЦЕНЫ ---
        balance = proxyma.get_balance()
        tariff_price = proxyma.get_tariff_price(pkg_name)

        # --- РАСЧЁТ МЕТРИК ---
        traffic_used = info['traffic']['usage']
        traffic_limit = info['traffic']['limit']
        traffic_left = traffic_limit - traffic_used
        traffic_percent = (traffic_used / traffic_limit * 100) if traffic_limit > 0 else 0

        # Расчёт дней до истечения
        try:
            expire_date = datetime.strptime(info['expired_at'], '%Y-%m-%d')
            days_left = (expire_date - datetime.now()).days
        except:
            days_left = 0

        # --- ОПРЕДЕЛЕНИЕ УРОВНЯ АЛЕРТА ---
        alert_level = None
        if days_left < 5:
            alert_level = "🚨 КРИТИЧНО"

        if traffic_percent > 80:
            if not alert_level:
                alert_level = "⚠️ ВНИМАНИЕ"

        # --- ФОРМИРОВАНИЕ РЕЗУЛЬТАТА ДЛЯ КОЛОНКИ AL ---
        check_result_text = f"✅ Proxyma ({datetime.now().strftime('%H:%M:%S')})\n"
        check_result_text += f"Пакет: {pkg_name}\n"
        check_result_text += f"Трафик: {traffic_used:.2f} / {traffic_limit} GB\n"
        check_result_text += f"Осталось: {traffic_left:.2f} GB ({100 - traffic_percent:.1f}%)\n"
        check_result_text += f"Истекает: {info['expired_at']} ({days_left} дней)\n"
        if alert_level:
            check_result_text += f"{alert_level}\n"
        check_result_text += f"Баланс: ${balance}"

        # --- ПОДГОТОВКА ДАННЫХ ДЛЯ GOOGLE SHEETS ---
        proxy_data = {
            'rdp': server['rdp'],
            'proxyName': pkg_name,
            'proxyLimit': traffic_limit,
            'proxyUsed': round(traffic_used, 2),
            'proxyLeft': round(traffic_left, 2),
            'proxyExpires': info['expired_at'],
            'proxyCheckTime': datetime.now().strftime('%d.%m.%Y %H:%M:%S'),
            'proxyBalance': balance if balance else 'N/A',
            'proxyPrice': tariff_price if tariff_price else 'N/A',
            'checkProxyResult': check_result_text
        }

        # --- ОБНОВЛЕНИЕ GOOGLE SHEETS ---
        requests.post(
            config.SHEETS_API_URL,
            json=proxy_data,
            headers={'Content-Type': 'application/json'},
            timeout=config.API_TIMEOUT
        )

        logger.info(f"[{server['ip']}] {pkg_name}: {traffic_used:.2f}/{traffic_limit} GB, {days_left} days left")

        # --- ВОЗВРАТ ДАННЫХ ДЛЯ TELEGRAM ОТЧЁТА ---
        return {
            'store': server['store'],
            'ip': server['ip'],
            'package_key': server['proxyKey'],
            'package_name': pkg_name,
            'traffic_used': traffic_used,
            'traffic_limit': traffic_limit,
            'traffic_left': traffic_left,
            'traffic_percent': traffic_percent,
            'expires': info['expired_at'],
            'days_left': days_left,
            'balance': balance,
            'price': tariff_price,
            'alert_level': alert_level
        }

    except Exception as e:
        logger.error(f"Error checking Proxyma for {server['ip']}: {e}")
        return None

# =============================================================================
# ФУНКЦИЯ: Группировка данных для Telegram отчёта
# =============================================================================
def group_packages_for_telegram(results):
    """
    Группирует результаты по (package_key, магазин) для Telegram отчёта

    Args:
        results (list): Список результатов проверки

    Returns:
        dict: Сгруппированные пакеты
    """
    grouped = {}

    for result in results:
        if not result:
            continue

        key = (result['package_key'], result['store'])

        if key not in grouped:
            # Первый сервер с этим пакетом
            grouped[key] = result.copy()
            grouped[key]['servers'] = [result['ip']]
        else:
            # Добавляем IP к существующему пакету
            grouped[key]['servers'].append(result['ip'])

    return grouped

# =============================================================================
# ФУНКЦИЯ: Формирование Telegram отчёта
# =============================================================================
def send_proxyma_report(grouped_packages):
    """
    Формирует и отправляет Telegram отчёт о Proxyma пакетах

    Args:
        grouped_packages (dict): Сгруппированные пакеты
    """
    if not config.TELEGRAM_TOKEN or not config.TELEGRAM_CHAT_IDS:
        return

    if not grouped_packages:
        return

    # --- ЗАГОЛОВОК ---
    message = "📊 <b>Отчёт о проверке Proxyma</b>\n"
    message += f"🕐 {datetime.now().strftime('%d.%m.%Y %H:%M:%S')}\n\n"

    # --- ИНФОРМАЦИЯ О КАЖДОМ ПАКЕТЕ ---
    total_traffic_used = 0
    total_traffic_limit = 0
    critical_count = 0
    warning_count = 0

    for (package_key, store), info in grouped_packages.items():
        # Иконка по уровню алерта
        if info['alert_level'] and '🚨' in info['alert_level']:
            icon = "🚨"
            critical_count += 1
        elif info['alert_level']:
            icon = "⚠️"
            warning_count += 1
        else:
            icon = "✅"

        message += f"{icon} <b>{info['store']} - {info['package_name']}</b>\n"
        message += f"   Серверы: {', '.join(info['servers'])}\n"
        message += f"   Трафик: {info['traffic_used']:.2f} / {info['traffic_limit']} GB "
        message += f"({100 - info['traffic_percent']:.0f}% свободно)\n"
        message += f"   Истекает: {info['expires']} ({info['days_left']} дней)\n"
        message += f"   Баланс: ${info['balance']}\n"

        if info['alert_level']:
            message += f"   {info['alert_level']}\n"

        message += "\n"

        total_traffic_used += info['traffic_used']
        total_traffic_limit += info['traffic_limit']

    # --- СБОР АЛЕРТОВ БЕЗ ДУБЛИКАТОВ ---
    alerts = []
    for (package_key, store), info in grouped_packages.items():
        if info['days_left'] < 5:
            alerts.append(f"🚨 {info['store']} - {info['package_name']}: осталось {info['days_left']} дней!")

        if info['traffic_percent'] > 80:
            alerts.append(f"⚠️ {info['store']} - {info['package_name']}: использовано {info['traffic_percent']:.0f}% трафика")

    # --- ИТОГОВАЯ СТАТИСТИКА ---
    message += f"📈 <b>Итого:</b>\n"
    message += f"📦 Пакетов: {len(grouped_packages)}\n"
    message += f"📊 Общий трафик: {total_traffic_used:.2f} / {total_traffic_limit} GB\n"

    if critical_count > 0:
        message += f"🚨 Критичных: {critical_count}\n"
    if warning_count > 0:
        message += f"⚠️ Требуют внимания: {warning_count}\n"

    # --- АЛЕРТЫ ---
    if alerts:
        message += f"\n🔔 <b>Уведомления:</b>\n"
        for alert in alerts[:10]:
            message += f"{alert}\n"
        if len(alerts) > 10:
            message += f"... и ещё {len(alerts) - 10}"

    send_telegram_notification(message)

# =============================================================================
# ФУНКЦИЯ: Проверка всех Proxyma пакетов
# =============================================================================
def check_all_proxyma():
    """
    Главная функция проверки всех Proxyma пакетов

    Выполняет:
    1. Загрузку серверов
    2. Проверку каждого сервера
    3. Обновление Google Sheets
    4. Группировку для Telegram
    5. Отправку отчёта

    Returns:
        tuple: (results, grouped_packages)
    """
    logger.info("=" * 50)
    logger.info("Starting Proxyma check cycle")
    logger.info("=" * 50)

    servers = get_servers_from_sheets()

    if not servers:
        logger.warning("No Proxyma packages to check")
        return [], {}

    # --- ПРОВЕРКА КАЖДОГО СЕРВЕРА ---
    results = []
    success_count = 0
    error_count = 0

    for server in servers:
        result = check_proxyma_package(server)

        if result:
            success_count += 1
            results.append(result)
        else:
            error_count += 1

    # --- ГРУППИРОВКА ДЛЯ TELEGRAM ---
    grouped_packages = group_packages_for_telegram(results)

    # --- ОТПРАВКА TELEGRAM ОТЧЁТА ---
    if config.TELEGRAM_TOKEN and config.TELEGRAM_CHAT_IDS:
        send_proxyma_report(grouped_packages)

    logger.info("=" * 50)
    logger.info(f"Proxyma check completed. Success: {success_count}, Errors: {error_count}")
    logger.info(f"Unique packages: {len(grouped_packages)}")
    logger.info("=" * 50)

    return results, grouped_packages

# =============================================================================
# ТОЧКА ВХОДА
# =============================================================================
if __name__ == "__main__":
    check_all_proxyma()
