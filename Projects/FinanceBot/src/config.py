"""
Конфигурация Finance Bot
"""
import os
from dotenv import load_dotenv

# Загрузка переменных из .env
load_dotenv()

# Telegram Bot
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')

# Google Sheets
GOOGLE_SHEETS_ID = os.getenv('GOOGLE_SHEETS_ID')
GOOGLE_SERVICE_ACCOUNT_FILE = os.getenv('GOOGLE_SERVICE_ACCOUNT_FILE', 'service_account.json')

# Google Drive - OAuth (для загрузки QR от имени пользователя)
GOOGLE_DRIVE_CLIENT_ID = os.getenv('GOOGLE_DRIVE_CLIENT_ID', '')
GOOGLE_DRIVE_CLIENT_SECRET = os.getenv('GOOGLE_DRIVE_CLIENT_SECRET', '')
GOOGLE_DRIVE_REFRESH_TOKEN = os.getenv('GOOGLE_DRIVE_REFRESH_TOKEN', '')
# Папка для QR-кодов (ID папки на вашем Drive)
GOOGLE_DRIVE_FOLDER_ID = os.getenv('GOOGLE_DRIVE_FOLDER_ID', '')

# Названия листов
SHEET_USERS = 'Пользователи'
# Основные: все выплаты в RUB, BYN, KZT (зарплаты и прочее; дашборд — формулами)
SHEET_JOURNAL = 'Основные'
# Разные выплаты: только чтение старых заявок (новые не пишутся)
SHEET_OTHER_PAYMENTS = 'Разные выплаты'
SHEET_BALANCE = 'Расчетный баланс'
SHEET_ACCOUNTS = 'Баланс счетов'
# USDT Зарплаты: только чтение старых заявок (новые не пишутся)
SHEET_USDT_SALARIES = 'USDT Зарплаты'
# USDT: все выплаты в крипте
SHEET_USDT = 'USDT'
# CNY: все выплаты в юанях (китайские платежные системы)
SHEET_CNY = 'CNY'
# Фактические расходы (без заявок, сразу факт)
SHEET_FACT_EXPENSES = 'Фактические расходы'
# Лог событий создаётся ботом при первом логировании
SHEET_LOG = 'Лог событий'

# Роли пользователей
ROLE_OWNER = 'owner'
ROLE_MANAGER = 'manager'
ROLE_EXECUTOR = 'executor'
ROLE_REPORT = 'report'  # Учетчик фактических расходов

# Статусы пользователей
USER_STATUS_ACTIVE = 'active'
USER_STATUS_BLOCKED = 'blocked'

# Статусы заявок
STATUS_CREATED = 'Создана'
STATUS_CANCELLED = 'Отменена'
STATUS_PAID = 'Оплачена'
STATUS_FACT = 'Факт'  # Фактический расход (без заявки)

# Валюты
CURRENCY_RUB = 'RUB'
CURRENCY_BYN = 'BYN'
CURRENCY_KZT = 'KZT'
CURRENCY_USDT = 'USDT'
CURRENCY_CNY = 'CNY'

CURRENCIES = {
    CURRENCY_RUB: '🇷🇺 RUB (Россия)',
    CURRENCY_BYN: '🇧🇾 BYN (Беларусь)',
    CURRENCY_KZT: '🇰🇿 KZT (Казахстан)',
    CURRENCY_USDT: '💰 USDT (Крипто)',
    CURRENCY_CNY: '🇨🇳 CNY (Китай)'
}

# Способы оплаты
PAYMENT_METHODS = ['Карта', 'СБП', 'Крипта']

# Китайские платежные системы
CNY_PAYMENT_METHODS = {
    'alipay': 'Alipay',
    'wechat': 'WeChat Pay',
    'bank_card': 'Китайская банковская карта'
}

# Ограничения длины текстовых полей (Google Sheets лимит ячейки 50000 символов)
MAX_RECIPIENT_LEN = 500
MAX_PURPOSE_LEN = 1000
MAX_DETAILS_LEN = 2000
