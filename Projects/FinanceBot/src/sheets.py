"""
Модуль для работы с Google Sheets
Finance Bot - управление заявками, оплатами, пользователями
"""
import time
from datetime import datetime
from typing import Optional, List, Dict
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from src import config
import logging

logger = logging.getLogger(__name__)


# ===== COLUMN MAPS (0-based index) =====
# Маппинг полей -> индекс колонки для каждого типа листа
# Верифицировано по create_request()

COLUMNS_MAIN = {
    'request_id': 0, 'date': 1, 'amount': 2, 'currency': 3,
    'recipient': 4, 'card_or_phone': 5, 'bank': 6, 'details': 7,
    'purpose': 8, 'category': 9, 'status': 10, 'deal_id': 11,
    'account_name': 12, 'amount_usdt': 13, 'rate': 14,
    'executor': 15, 'author_id': 16, 'author_username': 17,
    'author_fullname': 18, 'receipt_url': 19
}

COLUMNS_USDT = {
    'request_id': 0, 'date': 1, 'amount': 2,
    'card_or_phone': 3, 'purpose': 4, 'category': 5,
    'status': 6, 'deal_id': 7, 'account_name': 8,
    'executor': 9, 'author_id': 10, 'author_username': 11,
    'author_fullname': 12, 'receipt_url': 13
}

COLUMNS_CNY = {
    'request_id': 0, 'date': 1, 'amount': 2,
    'bank': 3, 'card_or_phone': 4, 'qr_code_link': 5,
    'purpose': 6, 'category': 7, 'status': 8,
    'deal_id': 9, 'account_name': 10, 'executor': 11,
    'author_id': 12, 'author_username': 13,
    'author_fullname': 14, 'receipt_url': 15
}


def _col_map_for_currency(currency: str) -> dict:
    """Получить маппинг колонок по валюте"""
    if currency == config.CURRENCY_USDT:
        return COLUMNS_USDT
    elif currency == config.CURRENCY_CNY:
        return COLUMNS_CNY
    else:
        return COLUMNS_MAIN


class GoogleApiManager:
    """Базовый класс для работы с Google API"""

    def __init__(self, credentials_path: str, spreadsheet_id: str):
        self.credentials_path = credentials_path
        self.spreadsheet_id = spreadsheet_id

        scope = ['https://spreadsheets.google.com/feeds',
                'https://www.googleapis.com/auth/drive']
        creds = ServiceAccountCredentials.from_json_keyfile_name(
            credentials_path, scope)
        self.client = gspread.authorize(creds)
        self.spreadsheet = self.client.open_by_key(spreadsheet_id)

    def get_worksheet(self, sheet_name: str):
        """Получить лист по названию"""
        return self.spreadsheet.worksheet(sheet_name)


class SheetsManager(GoogleApiManager):
    """Менеджер для работы с таблицами Finance Bot (14 колонок)"""

    def __init__(self):
        super().__init__(
            credentials_path=config.GOOGLE_SERVICE_ACCOUNT_FILE,
            spreadsheet_id=config.GOOGLE_SHEETS_ID
        )
        self.journal_sheet = self.get_worksheet(config.SHEET_JOURNAL)

        # Лист пользователей ОБЯЗАТЕЛЕН
        try:
            self.users_sheet = self.get_worksheet(config.SHEET_USERS)
        except Exception as e:
            logger.error(f"List 'Polzovateli' ne najden! Neobhodimo sozdat: {e}")
            self.users_sheet = None

        # Кэш пользователей: {telegram_id: (user_dict, expires_at)}
        # Снижает количество обращений к Sheets API с 3-5 до 1 за сессию
        self._user_cache: Dict[int, tuple] = {}
        self._user_cache_ttl: float = 60.0  # секунд

        # Кэш маппинга заголовков: {tuple(headers): hdr_map}
        # _find_columns_by_headers парсит заголовки при каждом запросе —
        # кеш устраняет повторную работу пока схема не меняется
        self._hdr_cache: Dict[tuple, dict] = {}

    # ===== HELPER: sheet by currency =====

    def _get_sheet_for_currency(self, currency: str):
        """Получить worksheet для указанной валюты"""
        if currency == config.CURRENCY_USDT:
            return self.get_worksheet(config.SHEET_USDT)
        elif currency == config.CURRENCY_CNY:
            return self.get_worksheet(config.SHEET_CNY)
        else:
            return self.journal_sheet  # Основные (RUB, BYN, KZT)

    def _sheet_name_for_currency(self, currency: str) -> str:
        """Имя листа для валюты"""
        if currency == config.CURRENCY_USDT:
            return config.SHEET_USDT
        elif currency == config.CURRENCY_CNY:
            return config.SHEET_CNY
        else:
            return config.SHEET_JOURNAL

    def _find_columns_by_headers(self, headers: list) -> dict:
        """
        Динамически определить индексы колонок по заголовкам.

        Результат кешируется по tuple(headers) — повторный вызов с теми же
        заголовками возвращает кешированный dict без пересчёта. Кеш валиден
        пока схема листа не меняется (перезапуск бота сбрасывает кеш).

        Returns:
            dict: {'status': idx, 'executor': idx, 'date': idx, ...}
        """
        cache_key = tuple(headers)
        if cache_key in self._hdr_cache:
            return self._hdr_cache[cache_key]

        col_map = {}
        for idx, header in enumerate(headers):
            # Заменяем переносы строк на пробелы (Google Sheets может переносить заголовки)
            h = header.strip().replace('\n', ' ').lower()

            if h in ['статус', 'status']:
                col_map['status'] = idx
            elif h in ['исполнитель', 'executor']:
                col_map['executor'] = idx
            elif h in ['дата', 'date']:
                col_map['date'] = idx
            elif 'сумма' in h and 'usdt' not in h:
                col_map['amount'] = idx
            elif h in ['валюта', 'currency']:
                col_map['currency'] = idx
            elif h in ['получатель', 'recipient']:
                col_map['recipient'] = idx
            elif 'карт' in h or 'телефон' in h or 'номер' in h:
                col_map['card_or_phone'] = idx
            elif h in ['банк', 'bank']:
                col_map['bank'] = idx
            elif h in ['назначение', 'purpose']:
                col_map['purpose'] = idx
            elif h in ['категория', 'category']:
                col_map['category'] = idx
            elif h in ['id заявки', 'request_id']:
                col_map['request_id'] = idx
            elif h in ['id сделки', 'deal_id', 'id транзакции', 'transaction_id', 'txid']:
                col_map['deal_id'] = idx
            elif 'аккаунт' in h or 'account' in h:
                col_map['account_name'] = idx
            elif 'usdt' in h:
                col_map['amount_usdt'] = idx
            elif 'курс' in h or 'rate' in h:
                col_map['rate'] = idx
            elif 'адрес' in h or 'кошел' in h:
                col_map['card_or_phone'] = idx
            elif 'реквизит' in h:
                col_map['details'] = idx
            elif 'qr' in h:
                col_map['qr_code_link'] = idx
            elif h in ['способ оплаты', 'payment method']:
                col_map['bank'] = idx
            elif 'telegram' in h and 'id' in h:
                col_map['author_id'] = idx
            elif 'username' in h:
                col_map['author_username'] = idx
            elif 'полное имя' in h or 'full name' in h:
                col_map['author_fullname'] = idx
            elif ('ссылка' in h and 'чек' in h) or 'receipt' in h:
                col_map['receipt_url'] = idx
            elif 'чек' in h and 'receipt_url' not in col_map:
                col_map['receipt_url'] = idx

        self._hdr_cache[cache_key] = col_map
        return col_map

    # ===== MISSING METHODS (needed by payment handler) =====

    def find_request_row(self, date: str, amount: float,
                         currency: str = None) -> Optional[int]:
        """
        Найти номер строки заявки (1-based) по дате и сумме.

        Args:
            date: Дата заявки (DD.MM.YYYY)
            amount: Сумма заявки
            currency: Валюта (если None - ищет в Основные)

        Returns:
            Номер строки (1-based) или None
        """
        try:
            sheet = self._get_sheet_for_currency(currency or config.CURRENCY_RUB)
            all_values = sheet.get_all_values()

            if not all_values or len(all_values) < 2:
                return None

            for i, row in enumerate(all_values[1:], start=2):  # start=2 for 1-based, skip header
                if len(row) < 3:
                    continue

                row_date = row[1]  # B: Дата (index 1 for all sheets)
                try:
                    row_amount = float(row[2]) if row[2] else 0.0
                except (ValueError, TypeError):
                    continue

                if row_date == date and abs(row_amount - amount) < 0.01:
                    # Если указана валюта и это лист Основные - проверяем D
                    if currency and currency not in (config.CURRENCY_USDT, config.CURRENCY_CNY):
                        row_currency = row[3] if len(row) > 3 else ''
                        if row_currency and row_currency != currency:
                            continue
                    return i

            return None
        except Exception as e:
            logger.error(f"find_request_row error: {e}")
            return None

    def find_request_row_by_id(self, request_id: str, currency: str = None) -> Optional[tuple]:
        """
        Найти строку по request_id. Возвращает (row_number, sheet, currency).

        Ищет во всех активных листах если currency не указана.
        """
        sheets_to_search = []
        if currency:
            sheets_to_search.append((self._sheet_name_for_currency(currency), currency))
        else:
            sheets_to_search = [
                (config.SHEET_JOURNAL, config.CURRENCY_RUB),
                (config.SHEET_USDT, config.CURRENCY_USDT),
                (config.SHEET_CNY, config.CURRENCY_CNY),
            ]

        for sheet_name, sheet_currency in sheets_to_search:
            try:
                sheet = self.get_worksheet(sheet_name)
                all_values = sheet.get_all_values()
                if not all_values or len(all_values) < 2:
                    continue

                for i, row in enumerate(all_values[1:], start=2):
                    if len(row) > 0 and row[0] == request_id:
                        return (i, sheet, sheet_currency)
            except Exception:
                continue

        return None

    def get_request_by_id(self, date: str, amount: float,
                          currency: str = None) -> Optional[Dict]:
        """
        Получить заявку по дате и сумме.
        Колонки определяются ДИНАМИЧЕСКИ по заголовкам.
        """
        try:
            if currency in (config.CURRENCY_USDT, config.CURRENCY_CNY):
                sheet = self._get_sheet_for_currency(currency)
            else:
                sheet = self.journal_sheet
                currency = currency or config.CURRENCY_RUB

            all_values = sheet.get_all_values()
            if not all_values or len(all_values) < 2:
                return None

            # Динамический маппинг
            headers = all_values[0]
            hdr_map = self._find_columns_by_headers(headers)

            date_idx = hdr_map.get('date', 1)   # fallback to B
            amount_idx = hdr_map.get('amount', 2)  # fallback to C

            for row in all_values[1:]:
                if len(row) <= max(date_idx, amount_idx):
                    continue

                row_date = row[date_idx]
                try:
                    row_amount = float(row[amount_idx]) if row[amount_idx] else 0.0
                except (ValueError, TypeError):
                    continue

                if row_date == date and abs(row_amount - amount) < 0.01:
                    return self._row_to_dict_dynamic(row, hdr_map, currency)

            return None
        except Exception as e:
            logger.error(f"get_request_by_id error: {e}")
            return None

    def _row_to_dict(self, row: list, currency: str) -> Dict:
        """Преобразовать строку таблицы в словарь по маппингу колонок (hardcoded)"""
        col_map = _col_map_for_currency(currency)
        result = {'currency': currency}

        for field, idx in col_map.items():
            if idx < len(row):
                value = row[idx]
                if field in ('amount', 'amount_usdt', 'rate'):
                    try:
                        value = float(value) if value else 0.0
                    except (ValueError, TypeError):
                        value = 0.0
                result[field] = value
            else:
                result[field] = '' if field not in ('amount', 'amount_usdt', 'rate') else 0.0

        result['sheet_name'] = self._sheet_name_for_currency(currency)
        return result

    @staticmethod
    def _row_to_dict_dynamic(row: list, hdr_map: dict, currency: str) -> Dict:
        """Преобразовать строку в словарь по ДИНАМИЧЕСКОМУ маппингу заголовков."""
        result = {'currency': currency}

        for field, idx in hdr_map.items():
            if idx < len(row):
                value = row[idx]
                if field in ('amount', 'amount_usdt', 'rate'):
                    try:
                        value = float(value) if value else 0.0
                    except (ValueError, TypeError):
                        value = 0.0
                result[field] = value
            else:
                result[field] = '' if field not in ('amount', 'amount_usdt', 'rate') else 0.0

        return result

    # ===== EXECUTOR METHODS =====

    def _get_requests_filtered(self, executor_name: str,
                               target_status: str) -> List[Dict]:
        """
        Базовый метод: поиск заявок по исполнителю и статусу.

        Использует ДИНАМИЧЕСКОЕ определение колонок по заголовкам,
        чтобы не зависеть от точного порядка колонок в таблице.

        Args:
            executor_name: ФИО исполнителя (точное совпадение)
            target_status: Статус для фильтрации (Создана/Оплачена)
        """
        results = []

        sheets_config = [
            (config.SHEET_JOURNAL, config.CURRENCY_RUB),
            (config.SHEET_USDT, config.CURRENCY_USDT),
            (config.SHEET_CNY, config.CURRENCY_CNY),
        ]

        for sheet_name, default_currency in sheets_config:
            try:
                sheet = self.get_worksheet(sheet_name)
                all_values = sheet.get_all_values()

                if not all_values or len(all_values) < 2:
                    continue

                # ДИНАМИЧЕСКОЕ определение колонок из заголовков
                headers = all_values[0]
                hdr_map = self._find_columns_by_headers(headers)

                status_idx = hdr_map.get('status')
                executor_idx = hdr_map.get('executor')

                if status_idx is None or executor_idx is None:
                    logger.warning(
                        f"Sheet '{sheet_name}': status_idx={status_idx}, "
                        f"executor_idx={executor_idx}. Headers: {headers}"
                    )
                    continue

                logger.debug(
                    f"Sheet '{sheet_name}': status at col {status_idx}, "
                    f"executor at col {executor_idx}"
                )

                for row in all_values[1:]:
                    if len(row) <= max(status_idx, executor_idx):
                        continue

                    row_status = row[status_idx].strip()
                    row_executor = row[executor_idx].strip()

                    if row_status == target_status and row_executor == executor_name:
                        # Определяем валюту
                        currency_idx = hdr_map.get('currency')
                        if currency_idx is not None and len(row) > currency_idx and row[currency_idx]:
                            actual_currency = row[currency_idx]
                        else:
                            actual_currency = default_currency

                        # Собираем данные из строки, используя динамические индексы
                        request_data = {
                            'currency': actual_currency,
                            'sheet_name': sheet_name,
                        }
                        for field, idx in hdr_map.items():
                            if idx < len(row):
                                value = row[idx]
                                if field in ('amount', 'amount_usdt', 'rate'):
                                    try:
                                        value = float(value) if value else 0.0
                                    except (ValueError, TypeError):
                                        value = 0.0
                                request_data[field] = value
                            else:
                                request_data[field] = '' if field not in ('amount', 'amount_usdt', 'rate') else 0.0

                        results.append(request_data)

            except Exception as e:
                logger.error(f"_get_requests_filtered error for {sheet_name}: {e}")
                continue

        return results

    def get_assigned_requests(self, executor_name: str) -> List[Dict]:
        """
        Получить заявки, назначенные исполнителю.
        Статус = "Создана", колонка "Исполнитель" = executor_name.
        Колонки определяются ДИНАМИЧЕСКИ по заголовкам таблицы.
        """
        return self._get_requests_filtered(executor_name, config.STATUS_CREATED)

    def get_payments_by_executor(self, executor_name: str) -> List[Dict]:
        """
        Получить все оплаченные заявки по имени исполнителя.
        Статус = "Оплачена", колонка "Исполнитель" = executor_name.
        Сортировка по дате (новые первые).
        """
        payments = self._get_requests_filtered(executor_name, config.STATUS_PAID)

        # Сортировка по дате (новые первые)
        try:
            payments.sort(
                key=lambda x: datetime.strptime(x.get('date', '01.01.2000'), '%d.%m.%Y'),
                reverse=True
            )
        except Exception:
            pass

        return payments

    def get_users_by_role(self, role: str) -> List[Dict]:
        """
        Получить всех пользователей с указанной ролью.

        Args:
            role: Роль (owner/manager/executor/report)

        Returns:
            Список пользователей [{telegram_id, name, username, role}]
        """
        users = []
        if not self.users_sheet:
            return users

        try:
            all_values = self.users_sheet.get_all_values()
            if len(all_values) < 2:
                return users

            # Определяем индексы колонок по заголовкам
            headers = all_values[0]
            header_map = {}
            for idx, header in enumerate(headers):
                h = header.strip().lower()
                if 'telegram' in h and 'id' in h:
                    header_map['telegram_id'] = idx
                elif h in ['имя', 'name']:
                    header_map['name'] = idx
                elif 'username' in h:
                    header_map['username'] = idx
                elif h in ['роль', 'role']:
                    header_map['role'] = idx

            if 'telegram_id' not in header_map or 'role' not in header_map:
                return users

            role_map = {
                'владелец': config.ROLE_OWNER, 'owner': config.ROLE_OWNER,
                'менеджер': config.ROLE_MANAGER, 'manager': config.ROLE_MANAGER,
                'исполнитель': config.ROLE_EXECUTOR, 'executor': config.ROLE_EXECUTOR,
                'учёт': config.ROLE_REPORT, 'учет': config.ROLE_REPORT, 'report': config.ROLE_REPORT,
            }

            for row in all_values[1:]:
                if len(row) <= header_map['role']:
                    continue

                raw_role = row[header_map['role']].strip().lower()
                normalized_role = role_map.get(raw_role, raw_role)

                if normalized_role == role:
                    tid_idx = header_map['telegram_id']
                    name_idx = header_map.get('name')
                    uname_idx = header_map.get('username')

                    users.append({
                        'telegram_id': row[tid_idx] if len(row) > tid_idx else '',
                        'name': row[name_idx] if name_idx is not None and len(row) > name_idx else '',
                        'username': row[uname_idx] if uname_idx is not None and len(row) > uname_idx else '',
                        'role': role
                    })

            return users
        except Exception as e:
            logger.error(f"get_users_by_role error: {e}")
            return []

    def create_request(self,
                      recipient: str,
                      amount: float,
                      card_or_phone: str,
                      bank: str,
                      purpose: str,
                      category: str = 'Прочее',
                      sheet_name: str = None,
                      currency: str = 'RUB',
                      author_id: str = '',
                      author_username: str = '',
                      author_fullname: str = '',
                      qr_code_link: str = None) -> Optional[str]:
        """
        Создать новую заявку
        Поддержка разных валют: RUB, BYN, KZT, USDT, CNY

        Args:
            recipient: ФИО получателя (пусто для USDT/CNY)
            amount: Сумма
            card_or_phone: Номер карты/телефона/кошелька/реквизитов
            bank: Название банка (пусто для USDT, метод оплаты для CNY)
            purpose: Назначение платежа
            category: Категория
            sheet_name: Название листа (авто по валюте если не указан)
            currency: Валюта (RUB/BYN/KZT/USDT/CNY)
            author_id: Telegram ID инициатора
            author_username: Telegram Username инициатора
            author_fullname: Полное имя инициатора
            qr_code_link: Ссылка на QR-код в Google Drive (только для CNY)

        Returns:
            ID заявки в формате REQ-YYYYMMDD-HHMMSS-XXX
        """
        try:
            import uuid
            from datetime import datetime

            # Определяем лист только по валюте (дашборд и формулы — в таблице)
            # RUB, BYN, KZT → Основные; USDT → USDT; CNY → CNY
            if not sheet_name:
                if currency == 'USDT':
                    sheet_name = config.SHEET_USDT
                elif currency == 'CNY':
                    sheet_name = config.SHEET_CNY
                else:
                    sheet_name = config.SHEET_JOURNAL  # Основные (RUB, BYN, KZT)

            # Генерируем уникальный ID заявки
            now = datetime.now()
            timestamp = now.strftime('%Y%m%d-%H%M%S')
            short_uuid = str(uuid.uuid4())[:8].upper()
            request_id = f"REQ-{timestamp}-{short_uuid}"

            date = now.strftime('%d.%m.%Y')

            recipient = (recipient or '')[:config.MAX_RECIPIENT_LEN]
            card_or_phone = (card_or_phone or '')[:500]
            bank = (bank or '')[:200]
            purpose = (purpose or '')[:config.MAX_PURPOSE_LEN]
            qr_code_link = (qr_code_link or '')[:1000]  # Ограничиваем длину ссылки

            # Для CNY - 14 колонок (A-N): ID, Дата, Сумма, Способ оплаты, Реквизиты/QR, Ссылка на QR, Назначение, Категория, Статус, ID сделки, Аккаунт, Исполнитель, Telegram ID, Username, Полное имя
            if currency == 'CNY':
                row = [
                    request_id,                    # A: ID заявки
                    date,                          # B: Дата
                    amount,                        # C: Сумма CNY
                    bank,                          # D: Способ оплаты (Alipay/WeChat/Bank_card)
                    card_or_phone,                 # E: Текстовые реквизиты
                    qr_code_link,                  # F: Ссылка на QR-код (Google Drive)
                    purpose,                       # G: Назначение
                    category,                      # H: Категория
                    config.STATUS_CREATED,         # I: Статус
                    '',                            # J: ID сделки
                    '',                            # K: Название аккаунта
                    '',                            # L: Исполнитель
                    author_id,                     # M: Telegram ID инициатора
                    author_username,               # N: Username инициатора
                    author_fullname                # O: Полное имя инициатора
                ]
            # Для USDT - 13 колонок (A-M): добавлен ID и колонки инициатора
            elif currency == 'USDT':
                row = [
                    request_id,                    # A: ID заявки
                    date,                          # B: Дата
                    amount,                        # C: Сумма USDT
                    card_or_phone,                 # D: Адрес кошелька
                    purpose,                       # E: Назначение
                    category,                      # F: Категория
                    config.STATUS_CREATED,         # G: Статус
                    '',                            # H: ID транзакции
                    '',                            # I: Название аккаунта
                    '',                            # J: Исполнитель
                    author_id,                     # K: Telegram ID инициатора
                    author_username,               # L: Username инициатора
                    author_fullname                # M: Полное имя инициатора
                ]
            else:
                # Для RUB/BYN/KZT - 19 колонок (A-S): ID, Дата, СУММА, ВАЛЮТА (!!!), Получатель...
                row = [
                    request_id,                    # A: ID заявки
                    date,                          # B: Дата
                    amount,                        # C: Сумма RUB
                    currency,                      # D: Валюта
                    recipient,                     # E: Получатель
                    card_or_phone,                 # F: Номер карты/телефона
                    bank,                          # G: Банк
                    '',                            # H: Реквизиты (формула будет добавлена)
                    purpose,                       # I: Назначение
                    category,                      # J: Категория
                    config.STATUS_CREATED,         # K: Статус
                    '',                            # L: ID сделки
                    '',                            # M: Название аккаунта
                    '',                            # N: Сумма USDT
                    '',                            # O: Курс
                    '',                            # P: Исполнитель
                    author_id,                     # Q: Telegram ID инициатора
                    author_username,               # R: Username инициатора
                    author_fullname                # S: Полное имя инициатора
                ]

            # Получаем лист и добавляем строку
            sheet = self.get_worksheet(sheet_name)
            row_number = len(sheet.get_all_values()) + 1  # Номер новой строки

            sheet.append_row(row, value_input_option='USER_ENTERED')

            # Добавляем формулу для столбца "Реквизиты" (H) только для RUB/BYN/KZT
            # Формат: Номер/телефон (новая строка) Банк (новая строка) Получатель
            if currency not in ['USDT', 'CNY']:
                formula = f'=IF(OR(ISBLANK(E{row_number}),ISBLANK(F{row_number}),ISBLANK(G{row_number})),"",F{row_number}&CHAR(10)&G{row_number}&CHAR(10)&E{row_number})'
                sheet.update_cell(row_number, 8, formula)  # H: Реквизиты

            logger.info(f"Zajavka sozdana: {request_id} ({date}, {amount} {currency} -> {sheet_name})")
            return request_id
        except Exception as e:
            logger.exception(f"create_request error: {e}")
            return None

    def create_fact_expense(self, amount: float, recipient: str, purpose: str,
                           author_id: str, author_username: str, author_fullname: str) -> Optional[str]:
        """
        Создать запись о фактическом расходе (наличные RUB)
        Структура как у листа "Основные" (19 колонок A-S)

        Args:
            amount: Сумма расхода
            recipient: Получатель (кому выплачено)
            purpose: Назначение (за что)
            author_id: Telegram ID автора
            author_username: Username автора
            author_fullname: Полное имя автора

        Returns:
            ID записи или None при ошибке
        """
        try:
            # Генерируем ID записи
            now = datetime.now()
            date = now.strftime('%d.%m.%Y')
            expense_id = f"FACT-{now.strftime('%Y%m%d-%H%M%S')}-{str(author_id)[-3:]}"

            # Получаем или создаем лист "Фактические расходы"
            try:
                sheet = self.get_worksheet(config.SHEET_FACT_EXPENSES)
            except Exception:
                # Создаем лист, если не существует
                sheet = self.spreadsheet.add_worksheet(
                    title=config.SHEET_FACT_EXPENSES,
                    rows=1000,
                    cols=20
                )
                # Добавляем заголовки (как у Основных)
                headers = [
                    'ID заявки',           # A
                    'Дата',                # B
                    'Сумма',               # C
                    'Валюта',              # D
                    'Получатель',          # E
                    'Номер карты/телефона',# F
                    'Банк',                # G
                    'Реквизиты',           # H
                    'Назначение',          # I
                    'Категория',           # J
                    'Статус',              # K
                    'ID сделки',           # L
                    'Название аккаунта',   # M
                    'Сумма USDT',          # N
                    'Курс',                # O
                    'Исполнитель',         # P
                    'Telegram ID инициатора', # Q
                    'Username инициатора', # R
                    'Полное имя инициатора' # S
                ]
                sheet.append_row(headers)
                logger.info(f"Sozdан лист '{config.SHEET_FACT_EXPENSES}' s zagolovkami")

            # Формируем строку данных (как у RUB - 19 колонок)
            row = [
                expense_id,               # A: ID записи
                date,                     # B: Дата
                amount,                   # C: Сумма
                'RUB',                    # D: Валюта (всегда RUB для наличных)
                recipient,                # E: Получатель
                'Наличные',               # F: Номер карты/телефона -> "Наличные"
                '',                       # G: Банк (пусто для наличных)
                '',                       # H: Реквизиты
                purpose,                  # I: Назначение
                'Операционка',            # J: Категория (можно потом автоматизировать)
                config.STATUS_PAID,       # K: Статус "Оплачена" (как на основных листах)
                '',                       # L: ID сделки
                '',                       # M: Название аккаунта
                '',                       # N: Сумма USDT
                '',                       # O: Курс
                author_fullname,          # P: Исполнитель (тот кто внес = тот кто выплатил)
                author_id,                # Q: Telegram ID
                author_username,          # R: Username
                author_fullname           # S: Полное имя
            ]

            sheet.append_row(row, value_input_option='USER_ENTERED')

            logger.info(f"Fact expense created: {expense_id} ({date}, {amount} RUB -> {recipient})")
            return expense_id

        except Exception as e:
            logger.error(f"Oshibka sozdanija fakta: {e}")
            import traceback
            traceback.print_exc()
            return None

    def update_request_fields(self, date: str, amount: float,
                             recipient: Optional[str] = None,
                             card_or_phone: Optional[str] = None,
                             bank: Optional[str] = None,
                             new_amount: Optional[float] = None,
                             purpose: Optional[str] = None,
                             currency: Optional[str] = None) -> bool:
        """
        Обновить редактируемые поля заявки
        Реквизиты (H) обновятся автоматически формулой

        Args:
            date: Дата заявки
            amount: Сумма заявки
            recipient: Новый получатель (опционально)
            card_or_phone: Новый номер/телефон/кошелек (опционально)
            bank: Новый банк (опционально)
            new_amount: Новая сумма (опционально)
            purpose: Новое назначение (опционально)
            currency: Валюта для определения листа (RUB/BYN/USDT)
        """
        try:
            logger.debug(f"update_request_fields: date={date}, amount={amount}, currency={currency}")
            logger.debug(f"Обновляемые поля: recipient={recipient}, card_or_phone={card_or_phone}, bank={bank}, new_amount={new_amount}, purpose={purpose}")

            # Находим заявку по дате и сумме (используем request_id из строки)
            # Ищем во всех листах (в т.ч. Разные выплаты, USDT Зарплаты и CNY)
            request = None
            for sheet_name_check in [config.SHEET_JOURNAL, config.SHEET_OTHER_PAYMENTS, config.SHEET_USDT_SALARIES, config.SHEET_USDT, config.SHEET_CNY]:
                try:
                    sheet_check = self.get_worksheet(sheet_name_check)
                    all_values_check = sheet_check.get_all_values()
                    for row in all_values_check[1:]:
                        if len(row) >= 3:
                            try:
                                row_amount = float(row[2]) if row[2] else 0.0
                                row_date = row[1]
                            except (ValueError, TypeError):
                                continue
                            if row_date == date and abs(row_amount - float(amount)) < 0.01:
                                request = {'request_id': row[0], 'sheet_name': sheet_name_check, 'currency': currency or row[3] if len(row) > 3 else config.CURRENCY_RUB}
                                break
                    if request:
                        break
                except Exception as e:
                    logger.warning(f"update_request_fields: sheet '{sheet_name_check}' error: {e}")
                    continue

            if not request:
                logger.error(f"Zajavka ne najdena: {date}, {amount}, {currency}")
                return False

            logger.debug(f"Найдена заявка: request_id={request.get('request_id')}, sheet={request['sheet_name']}")

            # Определяем лист и находим номер строки
            sheet_name = request['sheet_name']
            sheet = self.get_worksheet(sheet_name)

            all_values = sheet.get_all_values()
            row_number = None

            # Ищем строку с точным совпадением даты и суммы (NEW STRUCTURE: дата в B, сумма в C)
            for i, row in enumerate(all_values[1:], start=2):  # Пропускаем заголовки
                if len(row) < 3:
                    continue
                try:
                    # Для ВСЕХ листов сумма в колонке C (индекс 2)
                    row_amount = float(row[2]) if row[2] else 0.0  # C: Сумма
                    row_date = row[1]  # B: Дата
                except (ValueError, TypeError):
                    row_amount = 0.0
                    row_date = ''

                if row_date == date and abs(row_amount - float(amount)) < 0.01:
                    row_number = i
                    break

            if not row_number:
                logger.error(f"Stroka zajavki ne najdena: {date}, {amount}")
                return False

            logger.debug(f"Найдена строка: row_number={row_number}")

            # Обновляем только переданные поля в зависимости от типа листа
            # NEW STRUCTURE:
            # CNY (A-O): ID, Дата, Сумма, Способ оплаты, Реквизиты, QR-код, Назначение, ...
            # USDT (A-M): ID, Дата, Сумма, Кошелёк, Назначение, ...
            # RUB/BYN (A-S): ID, Дата, СУММА, ВАЛЮТА, Получатель, Номер, Банк, Реквизиты, Назначение, ...
            if request.get('currency') == config.CURRENCY_CNY:
                # CNY: структура A-O
                if new_amount is not None:
                    sheet.update_cell(row_number, 3, new_amount)  # C: Сумма CNY
                    logger.debug(f"Обновлена сумма CNY: {new_amount}")

                if card_or_phone is not None:
                    sheet.update_cell(row_number, 5, card_or_phone)  # E: Текстовые реквизиты
                    logger.debug(f"Обновлены реквизиты CNY: {card_or_phone}")

                if purpose is not None:
                    sheet.update_cell(row_number, 7, purpose)  # G: Назначение
                    logger.debug(f"Обновлено назначение CNY: {purpose}")
            elif request.get('currency') == config.CURRENCY_USDT:
                # USDT: структура A-M
                if new_amount is not None:
                    sheet.update_cell(row_number, 3, new_amount)  # C: Сумма USDT
                    logger.debug(f"Обновлена сумма USDT: {new_amount}")

                if card_or_phone is not None:
                    sheet.update_cell(row_number, 4, card_or_phone)  # D: Кошелёк
                    logger.debug(f"Обновлён кошелёк: {card_or_phone}")

                if purpose is not None:
                    sheet.update_cell(row_number, 5, purpose)  # E: Назначение
                    logger.debug(f"Обновлено назначение: {purpose}")
            else:
                # RUB/BYN: структура A-S (C=Сумма, D=Валюта)
                if new_amount is not None:
                    sheet.update_cell(row_number, 3, new_amount)  # C: Сумма
                    logger.debug(f"Обновлена сумма RUB/BYN: {new_amount}")

                if recipient is not None:
                    sheet.update_cell(row_number, 5, recipient)  # E: Получатель
                    logger.debug(f"Обновлён получатель: {recipient}")

                if card_or_phone is not None:
                    sheet.update_cell(row_number, 6, card_or_phone)  # F: Номер
                    logger.debug(f"Обновлен номер: {card_or_phone}")

                if bank is not None:
                    sheet.update_cell(row_number, 7, bank)  # G: Банк
                    logger.debug(f"Обновлен банк: {bank}")

                if purpose is not None:
                    sheet.update_cell(row_number, 9, purpose)  # I: Назначение
                    logger.debug(f"Обновлено назначение: {purpose}")

                # H (Реквизиты) обновится автоматически формулой!

            logger.info(f"Polja obnovleny: {date}, {amount}, {currency}")
            return True
        except Exception as e:
            logger.exception(f"update_request_fields error: {e}")
            return False

    def get_requests_by_status(self, status, author_id: str = None) -> List[Dict]:
        """
        Получить все заявки с определенным статусом из всех листов.

        Для RUB/BYN листов колонки определяются ДИНАМИЧЕСКИ по заголовкам.
        Для USDT/CNY листов используются fallback-индексы.

        Args:
            status: Статус заявки (str) или список статусов (list[str]).
                    Например: config.STATUS_CREATED или
                    [config.STATUS_CREATED, config.STATUS_PAID]
            author_id: Telegram ID автора (опционально)
        """
        statuses_set = {status} if isinstance(status, str) else set(status)
        requests = []

        # Конфигурация листов: (имя листа, валюта по умолчанию, fallback_status_idx, fallback_author_idx)
        sheets_config = [
            (config.SHEET_JOURNAL, config.CURRENCY_RUB, 10, 16),
            (config.SHEET_OTHER_PAYMENTS, config.CURRENCY_BYN, 10, 16),
            (config.SHEET_USDT_SALARIES, config.CURRENCY_USDT, 6, 10),
            (config.SHEET_USDT, config.CURRENCY_USDT, 6, 10),
            (config.SHEET_CNY, config.CURRENCY_CNY, 8, 12)
        ]

        for sheet_name, default_currency, fallback_status_idx, fallback_author_idx in sheets_config:
            try:
                sheet = self.get_worksheet(sheet_name)
                all_values = sheet.get_all_values()

                if not all_values or len(all_values) < 2:
                    continue

                headers = all_values[0]
                rows = all_values[1:]

                # Динамическое определение индексов из заголовков
                hdr_map = self._find_columns_by_headers(headers)
                status_index = hdr_map.get('status', fallback_status_idx)
                author_index = hdr_map.get('author_id', fallback_author_idx)
                amount_index = hdr_map.get('amount', 2)

                for row in rows:
                    if len(row) <= status_index or row[status_index] not in statuses_set:
                        continue

                    # Фильтрация по автору (если указан)
                    if author_id and author_index is not None:
                        row_author_id = str(row[author_index]) if len(row) > author_index else ''
                        if len(row) <= author_index or str(row[author_index]) != str(author_id):
                            continue

                    # Безопасная конвертация суммы
                    try:
                        amount_value = float(row[amount_index]) if len(row) > amount_index and row[amount_index] else 0.0
                    except (ValueError, TypeError):
                        amount_value = 0.0

                    # Формируем данные в зависимости от типа листа
                    if default_currency == config.CURRENCY_CNY:
                        # CNY: структура A-O (15 колонок)
                        request_data = {
                            'request_id': row[0] if len(row) > 0 else '',           # A: ID заявки
                            'date': row[1] if len(row) > 1 else '',                 # B: Дата
                            'amount': amount_value,                                  # C: Сумма CNY
                            'recipient': '',                                         # Нет получателя для CNY
                            'card_or_phone': row[4] if len(row) > 4 else '',        # E: Текстовые реквизиты
                            'bank': row[3] if len(row) > 3 else '',                 # D: Способ оплаты (Alipay/WeChat/Bank_card)
                            'details': '',                                           # Нет отдельного поля реквизитов
                            'qr_code_link': row[5] if len(row) > 5 else '',         # F: Ссылка на QR-код
                            'purpose': row[6] if len(row) > 6 else '',              # G: Назначение
                            'category': row[7] if len(row) > 7 else '',             # H: Категория
                            'status': row[8] if len(row) > 8 else '',               # I: Статус
                            'deal_id': row[9] if len(row) > 9 else '',              # J: ID сделки
                            'account_name': row[10] if len(row) > 10 else '',       # K: Название аккаунта
                            'executor': row[11] if len(row) > 11 else '',           # L: Исполнитель
                            'author_id': row[12] if len(row) > 12 else '',          # M: Telegram ID
                            'author_username': row[13] if len(row) > 13 else '',    # N: Username
                            'author_fullname': row[14] if len(row) > 14 else '',    # O: Полное имя
                            'receipt_link': row[15] if len(row) > 15 else '',       # P: Ссылка на чек (если есть)
                            'currency': default_currency,
                            'sheet_name': sheet_name
                        }
                    elif default_currency == config.CURRENCY_USDT:
                        # USDT: структура A-N (14 колонок)
                        request_data = {
                            'request_id': row[0] if len(row) > 0 else '',           # A: ID заявки
                            'date': row[1] if len(row) > 1 else '',                 # B: Дата
                            'amount': amount_value,                                  # C: Сумма USDT
                            'recipient': '',                                         # Нет получателя для USDT
                            'card_or_phone': row[3] if len(row) > 3 else '',        # D: Адрес кошелька
                            'bank': '',                                              # Нет банка для USDT
                            'details': '',                                           # Нет реквизитов
                            'purpose': row[4] if len(row) > 4 else '',              # E: Назначение
                            'category': row[5] if len(row) > 5 else '',             # F: Категория
                            'status': row[6] if len(row) > 6 else '',               # G: Статус
                            'deal_id': row[7] if len(row) > 7 else '',              # H: ID транзакции
                            'account_name': row[8] if len(row) > 8 else '',         # I: Название аккаунта
                            'executor': row[9] if len(row) > 9 else '',             # J: Исполнитель
                            'author_id': row[10] if len(row) > 10 else '',          # K: Telegram ID
                            'author_username': row[11] if len(row) > 11 else '',    # L: Username
                            'author_fullname': row[12] if len(row) > 12 else '',    # M: Полное имя
                            'receipt_link': row[13] if len(row) > 13 else '',       # N: Ссылка на чек
                            'currency': default_currency,
                            'sheet_name': sheet_name
                        }
                    else:
                        # RUB/BYN: динамический маппинг по заголовкам
                        hdr_map = self._find_columns_by_headers(headers)
                        request_data = self._row_to_dict_dynamic(row, hdr_map, default_currency)

                        # amount уже прочитана выше
                        request_data['amount'] = amount_value

                        # Определяем валюту из данных
                        currency_idx = hdr_map.get('currency')
                        if currency_idx is not None and len(row) > currency_idx and row[currency_idx]:
                            request_data['currency'] = row[currency_idx]

                        request_data['sheet_name'] = sheet_name

                    requests.append(request_data)

            except Exception as e:
                logger.exception(f"get_requests_by_status: sheet '{sheet_name}' error: {e}")
                continue

        return requests

    def get_all_requests(self, status: Optional[str] = None) -> List[Dict]:
        """
        Получить все заявки из всех листов (опционально фильтр по статусу).

        Args:
            status: Статус заявки или None для всех статусов

        Returns:
            Список заявок отсортированных по дате (новые первыми)
        """
        if status is not None:
            return self.get_requests_by_status(status)

        all_requests = []
        for s in [config.STATUS_CREATED, config.STATUS_PAID, config.STATUS_CANCELLED]:
            all_requests.extend(self.get_requests_by_status(s))
        return all_requests

    def assign_executor(self, request_id: str, executor_name: str) -> bool:
        """
        Назначить исполнителя для заявки (обновить поле «Исполнитель»).

        Args:
            request_id: ID заявки
            executor_name: ФИО/имя исполнителя

        Returns:
            True если успешно
        """
        try:
            request = self.get_request_by_request_id(request_id)
            if not request:
                logger.error(f"assign_executor: заявка не найдена: {request_id}")
                return False

            sheet_name = request['sheet_name']
            currency = request['currency']
            sheet = self.get_worksheet(sheet_name)

            all_values = sheet.get_all_values()
            row_num = None
            for i, row in enumerate(all_values[1:], start=2):
                if len(row) >= 1 and row[0] == request_id:
                    row_num = i
                    break

            if not row_num:
                logger.error(f"assign_executor: строка не найдена: {request_id}")
                return False

            # Определяем колонку исполнителя (1-based для update_cell)
            if currency == config.CURRENCY_USDT:
                executor_col = 10  # J: Исполнитель
            elif currency == config.CURRENCY_CNY:
                executor_col = 12  # L: Исполнитель
            else:
                # RUB/BYN: динамически по заголовкам
                headers = all_values[0]
                hdr_map = self._find_columns_by_headers(headers)
                executor_idx = hdr_map.get('executor')
                if executor_idx is None:
                    logger.error(f"assign_executor: колонка executor не найдена в {sheet_name}")
                    return False
                executor_col = executor_idx + 1  # 0-indexed → 1-based

            sheet.update_cell(row_num, executor_col, executor_name)
            logger.info(f"assign_executor: {request_id} → {executor_name}")
            return True

        except Exception as e:
            logger.error(f"assign_executor error: {e}")
            import traceback
            traceback.print_exc()
            return False


    def get_request_by_request_id(self, request_id: str) -> Optional[Dict]:
        """
        Получить заявку по уникальному ID заявки

        Args:
            request_id: Уникальный ID заявки (формат REQ-YYYYMMDD-HHMMSS-XXX)

        Returns:
            Dict с данными заявки или None
        """
        # Ищем во всех листах
        sheets_to_search = [
            (config.SHEET_JOURNAL, config.CURRENCY_RUB),
            (config.SHEET_OTHER_PAYMENTS, config.CURRENCY_BYN),
            (config.SHEET_USDT_SALARIES, config.CURRENCY_USDT),
            (config.SHEET_USDT, config.CURRENCY_USDT),
            (config.SHEET_CNY, config.CURRENCY_CNY)
        ]

        for sheet_name, sheet_currency in sheets_to_search:
            try:
                sheet = self.get_worksheet(sheet_name)
                all_values = sheet.get_all_values()

                if not all_values or len(all_values) < 2:
                    continue

                rows = all_values[1:]  # Пропускаем заголовки

                for row in rows:
                    if len(row) < 1:
                        continue

                    # Сравниваем ID заявки (первая колонка)
                    if row[0] == request_id:
                        # Формируем данные в зависимости от типа листа
                        if sheet_currency == config.CURRENCY_CNY:
                            try:
                                row_amount = float(row[2]) if len(row) > 2 and row[2] else 0.0
                            except (ValueError, TypeError):
                                row_amount = 0.0

                            return {
                                'request_id': row[0] if len(row) > 0 else '',           # A: ID заявки
                                'date': row[1] if len(row) > 1 else '',                 # B: Дата
                                'amount': row_amount,                                    # C: Сумма CNY
                                'recipient': '',                                         # Нет получателя для CNY
                                'card_or_phone': row[4] if len(row) > 4 else '',        # E: Текстовые реквизиты
                                'bank': row[3] if len(row) > 3 else '',                 # D: Способ оплаты (Alipay/WeChat/Bank_card)
                                'qr_code_link': row[5] if len(row) > 5 else '',         # F: Ссылка на QR-код
                                'purpose': row[6] if len(row) > 6 else '',              # G: Назначение
                                'category': row[7] if len(row) > 7 else '',             # H: Категория
                                'status': row[8] if len(row) > 8 else '',               # I: Статус
                                'deal_id': row[9] if len(row) > 9 else '',              # J: ID сделки
                                'account_name': row[10] if len(row) > 10 else '',       # K: Название аккаунта
                                'executor': row[11] if len(row) > 11 else '',           # L: Исполнитель
                                'author_id': row[12] if len(row) > 12 else '',          # M: Telegram ID
                                'author_username': row[13] if len(row) > 13 else '',    # N: Username
                                'author_fullname': row[14] if len(row) > 14 else '',    # O: Полное имя
                                'receipt_link': row[15] if len(row) > 15 else '',       # P: Ссылка на чек (если есть)
                                'currency': sheet_currency,
                                'sheet_name': sheet_name
                            }
                        elif sheet_currency == config.CURRENCY_USDT:
                            try:
                                row_amount = float(row[2]) if len(row) > 2 and row[2] else 0.0
                            except (ValueError, TypeError):
                                row_amount = 0.0

                            return {
                                'request_id': row[0] if len(row) > 0 else '',
                                'date': row[1] if len(row) > 1 else '',
                                'amount': row_amount,
                                'recipient': '',
                                'card_or_phone': row[3] if len(row) > 3 else '',
                                'bank': '',
                                'details': '',
                                'purpose': row[4] if len(row) > 4 else '',
                                'category': row[5] if len(row) > 5 else '',
                                'status': row[6] if len(row) > 6 else '',
                                'deal_id': row[7] if len(row) > 7 else '',
                                'account_name': row[8] if len(row) > 8 else '',
                                'executor': row[9] if len(row) > 9 else '',
                                'author_id': row[10] if len(row) > 10 else '',
                                'author_username': row[11] if len(row) > 11 else '',
                                'author_fullname': row[12] if len(row) > 12 else '',
                                'receipt_link': row[13] if len(row) > 13 else '',
                                'currency': sheet_currency,
                                'sheet_name': sheet_name
                            }
                        else:
                            # Динамический маппинг по заголовкам
                            hdr_map = self._find_columns_by_headers(all_values[0])
                            result = self._row_to_dict_dynamic(row, hdr_map, sheet_currency)

                            # Определяем валюту из данных
                            currency_idx = hdr_map.get('currency')
                            if currency_idx is not None and len(row) > currency_idx and row[currency_idx]:
                                result['currency'] = row[currency_idx]

                            result['sheet_name'] = sheet_name
                            return result
            except Exception as e:
                logger.exception(f"get_request_by_request_id: sheet '{sheet_name}' error: {e}")
                continue

        return None



    def update_request_status_by_id(self, request_id: str, new_status: str) -> bool:
        """
        Обновить статус заявки по уникальному ID

        Args:
            request_id: Уникальный ID заявки (формат REQ-YYYYMMDD-HHMMSS-XXX)
            new_status: Новый статус (Создана/Оплачена/Отменена)

        Returns:
            True если успешно
        """
        try:
            logger.debug(f"update_request_status_by_id: request_id={request_id}, new_status={new_status}")

            # Получаем полные данные заявки
            request = self.get_request_by_request_id(request_id)
            if not request:
                logger.error(f"Zajavka ne najdena: {request_id}")
                return False

            # Определяем лист
            sheet_name = request['sheet_name']
            currency = request['currency']
            sheet = self.get_worksheet(sheet_name)

            all_values = sheet.get_all_values()
            row_number = None

            # Ищем строку по request_id (колонка A)
            for i, row in enumerate(all_values[1:], start=2):
                if len(row) < 1:
                    continue

                if row[0] == request_id:
                    row_number = i
                    break

            if not row_number:
                logger.error(f"Stroka zajavki ne najdena: {request_id}")
                return False

            # Определяем колонку статуса в зависимости от валюты
            if currency == config.CURRENCY_USDT:
                status_col = 7   # G: Статус
            elif currency == config.CURRENCY_CNY:
                status_col = 9  # I: Статус
            else:
                status_col = 11  # K: Статус (Основные)

            logger.debug(f"Обновление статуса: row={row_number}, col={status_col}, value={new_status}")
            sheet.update_cell(row_number, status_col, new_status)
            logger.info(f"Status obnovlen: {request_id} -> {new_status}")
            return True
        except Exception as e:
            logger.exception(f"update_request_status_by_id error: {e}")
            return False

    def update_request_qr_code(self, request_id: str, qr_code_link: str) -> bool:
        """
        Обновить ссылку на QR-код в заявке CNY

        Args:
            request_id: Уникальный ID заявки
            qr_code_link: Новая ссылка на QR-код в Google Drive

        Returns:
            True если успешно
        """
        try:
            logger.debug(f"update_request_qr_code: request_id={request_id}")

            # Получаем полные данные заявки
            request = self.get_request_by_request_id(request_id)
            if not request:
                logger.error(f"Заявка не найдена: {request_id}")
                return False

            if request['currency'] != config.CURRENCY_CNY:
                logger.error(f"Заявка не CNY: {request_id}")
                return False

            # Определяем лист
            sheet_name = request['sheet_name']
            sheet = self.get_worksheet(sheet_name)

            all_values = sheet.get_all_values()
            row_number = None

            # Ищем строку по request_id (колонка A)
            for i, row in enumerate(all_values[1:], start=2):
                if len(row) < 1:
                    continue

                if row[0] == request_id:
                    row_number = i
                    break

            if not row_number:
                logger.error(f"Строка заявки не найдена: {request_id}")
                return False

            # Для CNY QR-код в колонке F (6)
            qr_col = 6

            logger.debug(f"Обновление QR-кода: row={row_number}, col={qr_col}")
            sheet.update_cell(row_number, qr_col, qr_code_link)
            logger.info(f"QR-код обновлён: {request_id}")
            return True
        except Exception as e:
            logger.exception(f"update_request_qr_code error: {e}")
            return False

    def complete_payment(self, date: str, amount: float, executor_name: str,
                        deal_id: str = '', account_name: str = '',
                        amount_usdt: Optional[float] = None,
                        currency: str = None,
                        request_id: str = '') -> bool:
        """
        Завершить оплату заявки.

        Обновляет статус на "Оплачена", записывает ID сделки, аккаунт,
        сумму USDT. НЕ перезаписывает исполнителя (он уже назначен).

        Колонки определяются ДИНАМИЧЕСКИ по заголовкам таблицы.
        Поиск строки: приоритет request_id, потом date+amount.
        """
        try:
            currency = currency or config.CURRENCY_RUB

            # Приоритет: поиск по request_id (надежнее)
            row_num = None
            sheet = None
            if request_id:
                result = self.find_request_row_by_id(request_id, currency)
                if result:
                    row_num, sheet, currency = result
                    logger.info(f"complete_payment: found by request_id={request_id}, row={row_num}")

            # Fallback: поиск по дате и сумме
            if not row_num:
                sheet = self._get_sheet_for_currency(currency)
                if date and amount:
                    row_num = self.find_request_row(date, amount, currency)

            if not row_num:
                logger.error(f"Zajavka ne najdena: request_id={request_id}, date={date}, amount={amount}, currency={currency}")
                return False

            if sheet is None:
                sheet = self._get_sheet_for_currency(currency)

            # Получаем данные и заголовки
            all_values = sheet.get_all_values()
            if not all_values or len(all_values) < 2:
                logger.error(f"complete_payment: sheet empty for {currency}")
                return False

            # Динамический маппинг колонок
            headers = all_values[0]
            hdr_map = self._find_columns_by_headers(headers)

            # Собираем все изменения и отправляем одним batch_update.
            # Это атомарно: либо все поля записываются, либо ни одно.
            # Предотвращает частично записанную оплату при сбое сети.
            updates: list[gspread.Cell] = []

            status_idx = hdr_map.get('status')
            if status_idx is not None:
                updates.append(gspread.Cell(row_num, status_idx + 1, config.STATUS_PAID))

            deal_idx = hdr_map.get('deal_id')
            if deal_id and deal_idx is not None:
                updates.append(gspread.Cell(row_num, deal_idx + 1, deal_id))

            account_idx = hdr_map.get('account_name')
            if account_name and account_idx is not None:
                updates.append(gspread.Cell(row_num, account_idx + 1, account_name))

            usdt_idx = hdr_map.get('amount_usdt')
            if amount_usdt is not None and usdt_idx is not None:
                updates.append(gspread.Cell(row_num, usdt_idx + 1, amount_usdt))
                rate_idx = hdr_map.get('rate')
                amount_idx = hdr_map.get('amount')
                if rate_idx is not None and amount_idx is not None:
                    amount_col_letter = chr(ord('A') + amount_idx)
                    usdt_col_letter = chr(ord('A') + usdt_idx)
                    updates.append(gspread.Cell(
                        row_num, rate_idx + 1,
                        f'={amount_col_letter}{row_num}/{usdt_col_letter}{row_num}'
                    ))

            if updates:
                sheet.update_cells(updates, value_input_option='USER_ENTERED')

            logger.info(
                f"Payment completed: {date}, {amount} {currency}, "
                f"executor={executor_name}, deal_id={deal_id}"
            )
            return True
        except Exception as e:
            logger.exception(f"complete_payment error: {e}")
            return False

    def update_receipt_url(self, date: str, amount: float,
                           currency: str, receipt_url: str,
                           request_id: str = '') -> bool:
        """
        Записать URL чека в таблицу.
        Колонка "Чек" определяется ДИНАМИЧЕСКИ по заголовкам.
        Поиск строки: приоритет request_id, потом date+amount.
        """
        try:
            sheet = None
            row_num = None

            # Приоритет: поиск по request_id
            if request_id:
                result = self.find_request_row_by_id(request_id, currency)
                if result:
                    row_num, sheet, currency = result

            # Fallback: date+amount
            if not row_num:
                sheet = self._get_sheet_for_currency(currency)
                if date and amount:
                    row_num = self.find_request_row(date, amount, currency)

            if not row_num:
                logger.error(f"update_receipt_url: row not found request_id={request_id}, {date}, {amount}")
                return False

            if sheet is None:
                sheet = self._get_sheet_for_currency(currency)

            # Динамический поиск колонки "Чек"
            all_values = sheet.get_all_values()
            if not all_values:
                return False

            hdr_map = self._find_columns_by_headers(all_values[0])
            receipt_col = hdr_map.get('receipt_url')

            if receipt_col is None:
                logger.warning(
                    f"receipt_url column not found in headers: {all_values[0]}. "
                    f"Skipping receipt URL save."
                )
                return False

            sheet.update_cell(row_num, receipt_col + 1, receipt_url)
            logger.info(f"Receipt URL saved: {date}, {amount} -> {receipt_url}")
            return True
        except Exception as e:
            logger.error(f"update_receipt_url error: {e}")
            return False

    def append_usdt_payment(self, date: str, amount_usdt: float,
                           wallet: str, purpose: str, category: str,
                           status: str, transaction_id: str, account_name: str,
                           executor_name: str) -> bool:
        """
        Дописать строку на лист USDT (9 колонок)

        ФИНАЛЬНАЯ структура USDT:
        A: Дата
        B: Сумма USDT (не RUB!)
        C: Адрес кошелька
        D: Назначение
        E: Категория
        F: Статус
        G: ID транзакции (не ID сделки!)
        H: Название аккаунта
        I: Исполнитель

        НЕТ: Суммы RUB, Курса, Получателя, Банка, Реквизитов
        """
        try:
            sheet_name = config.SHEET_USDT
            try:
                sheet = self.get_worksheet(sheet_name)
            except Exception:
                # Лист не найден — создаём с правильными заголовками (9 колонок)
                logger.info(f"create_usdt_request_legacy: лист '{sheet_name}' не найден, создаём")
                sheet = self.spreadsheet.add_worksheet(title=sheet_name, rows=500, cols=9)
                headers = [
                    'Дата', 'Сумма USDT', 'Адрес кошелька', 'Назначение', 'Категория',
                    'Статус', 'ID транзакции', 'Название аккаунта', 'Исполнитель'
                ]
                sheet.update(values=[headers], range_name='A1:I1')

            # Формируем строку: 9 колонок
            row = [
                date,           # A: Дата
                amount_usdt,    # B: Сумма USDT
                wallet,         # C: Адрес кошелька
                purpose,        # D: Назначение
                category,       # E: Категория
                status,         # F: Статус
                transaction_id, # G: ID транзакции
                account_name,   # H: Название аккаунта
                executor_name   # I: Исполнитель
            ]

            sheet.append_row(row, value_input_option='USER_ENTERED')

            return True
        except Exception as e:
            logger.exception(f"create_usdt_request_legacy error: {e}")
            return False

    def get_user(self, telegram_id: int) -> Optional[Dict]:
        """
        Получить данные пользователя из листа Пользователи

        УЛУЧШЕНО: Автоматическое определение колонок по заголовкам
        Не зависит от порядка колонок в таблице
        """
        if not self.users_sheet:
            logger.error("Лист Пользователи недоступен!")
            return None

        # Проверяем кэш — если данные свежие, не идём в Sheets
        try:
            tid_key = int(telegram_id)
        except (ValueError, TypeError):
            tid_key = None
        if tid_key is not None:
            cached = self._user_cache.get(tid_key)
            if cached is not None:
                user_dict, expires_at = cached
                if time.monotonic() < expires_at:
                    return user_dict

        try:
            all_values = self.users_sheet.get_all_values()
            if len(all_values) < 2:  # Нет данных кроме заголовков
                return None

            # Читаем заголовки (первая строка) и создаём mapping
            headers = all_values[0]
            header_map = {}

            for idx, header in enumerate(headers):
                header_lower = header.strip().lower()

                # Telegram ID (поддерживаем разные варианты)
                if 'telegram' in header_lower and 'id' in header_lower:
                    header_map['telegram_id'] = idx
                # Имя / Name
                elif header_lower in ['имя', 'name', 'ім\'я', 'имя пользователя']:
                    header_map['name'] = idx
                # Username
                elif 'username' in header_lower or header_lower == 'user':
                    header_map['username'] = idx
                # Роль / Role
                elif header_lower in ['роль', 'role', 'роля']:
                    header_map['role'] = idx

            # Проверяем что нашли обязательные колонки
            if 'telegram_id' not in header_map or 'role' not in header_map:
                logger.error(f"Не найдены обязательные колонки в листе Пользователи. Найдено: {header_map}")
                logger.error(f"Заголовки листа: {headers}")
                return None

            tid = int(telegram_id)
            tid_str = str(tid)  # "8450372644" -- без пробелов, точек, E+

            # Маппинг русских названий ролей на ключи
            role_map = {
                'владелец': config.ROLE_OWNER,
                'owner': config.ROLE_OWNER,
                'менеджер': config.ROLE_MANAGER,
                'manager': config.ROLE_MANAGER,
                'исполнитель': config.ROLE_EXECUTOR,
                'executor': config.ROLE_EXECUTOR,
                'учёт': config.ROLE_REPORT,
                'учет': config.ROLE_REPORT,
                'report': config.ROLE_REPORT,
            }

            # Ищем пользователя в строках (пропускаем заголовок)
            for row in all_values[1:]:
                if len(row) <= header_map['telegram_id']:
                    continue

                raw_id = row[header_map['telegram_id']]
                if not raw_id:
                    continue

                # Надёжное сравнение Telegram ID:
                # Google Sheets может вернуть число как "8450372644",
                # "8.45037E+09" (научная нотация), "8 450 372 644" (с пробелами)
                # или "8450372644.0" (float). Обрабатываем все варианты.
                match = False
                clean_id = str(raw_id).strip().replace(' ', '').replace('\u00a0', '')

                # 1. Прямое строковое сравнение (самый быстрый путь)
                if clean_id == tid_str:
                    match = True
                else:
                    # 2. Через float -> int (обрабатывает "8450372644.0" и науч. нотацию)
                    try:
                        parsed = int(float(clean_id))
                        if parsed == tid:
                            match = True
                        else:
                            logger.debug(
                                f"ID mismatch: raw='{raw_id}', "
                                f"parsed={parsed}, expected={tid}"
                            )
                    except (TypeError, ValueError):
                        # 3. Убираем все не-цифры и сравниваем
                        digits_only = ''.join(c for c in clean_id if c.isdigit())
                        if digits_only == tid_str:
                            match = True

                if match:
                    name_idx = header_map.get('name')
                    username_idx = header_map.get('username')
                    role_idx = header_map['role']

                    name = row[name_idx] if name_idx is not None and len(row) > name_idx else ''
                    username = row[username_idx] if username_idx is not None and len(row) > username_idx else ''
                    role_raw = row[role_idx] if len(row) > role_idx else ''

                    role_str = (str(role_raw).strip().lower() if role_raw else '').strip()
                    role = role_map.get(role_str) or (role_str if role_str else None)

                    logger.info(
                        f"User {tid} found: raw_id='{raw_id}', "
                        f"role={role}, name={name}"
                    )

                    result = {
                        'telegram_id': raw_id,
                        'name': name,
                        'username': username,
                        'role': role
                    }
                    if tid_key is not None:
                        self._user_cache[tid_key] = (result, time.monotonic() + self._user_cache_ttl)
                    return result

            logger.warning(f"User {telegram_id} NOT found in sheet. Checked {len(all_values)-1} rows.")
            return None

        except Exception as e:
            logger.error(f"Ошибка при получении пользователя {telegram_id}: {e}")
            import traceback
            traceback.print_exc()
            return None

    def get_all_users(self) -> List[Dict]:
        """
        Получить всех пользователей из листа Пользователи.

        Returns:
            Список dict с ключами: telegram_id (int), name, username, role.
            Пустой список [] если лист недоступен или не содержит данных.
            Роль нормализована к config.ROLE_* константам (не русские строки).
            telegram_id всегда int (Google Sheets может хранить как "8.45E+09").

        Side effects:
            - Читает Google Sheets (1 API вызов).
            - НЕ изменяет данные в таблице.

        Invariants:
            - Строки с невалидным/пустым telegram_id пропускаются.
            - Пользователи с неизвестной ролью включаются с role='' (не None).
        """
        if not self.users_sheet:
            return []
        try:
            all_values = self.users_sheet.get_all_values()
            if len(all_values) < 2:
                return []

            headers = all_values[0]
            header_map: Dict[str, int] = {}
            for idx, header in enumerate(headers):
                h = header.strip().lower()
                if 'telegram' in h and 'id' in h:
                    header_map['telegram_id'] = idx
                elif h in ['имя', 'name']:
                    header_map['name'] = idx
                elif 'username' in h:
                    header_map['username'] = idx
                elif h in ['роль', 'role']:
                    header_map['role'] = idx

            if 'telegram_id' not in header_map or 'role' not in header_map:
                return []

            role_map = {
                'владелец': config.ROLE_OWNER, 'owner': config.ROLE_OWNER,
                'менеджер': config.ROLE_MANAGER, 'manager': config.ROLE_MANAGER,
                'исполнитель': config.ROLE_EXECUTOR, 'executor': config.ROLE_EXECUTOR,
                'учёт': config.ROLE_REPORT, 'учет': config.ROLE_REPORT, 'report': config.ROLE_REPORT,
            }

            users = []
            for row in all_values[1:]:
                tid_idx = header_map['telegram_id']
                if not row or len(row) <= tid_idx or not row[tid_idx]:
                    continue
                role_raw = (
                    row[header_map['role']].strip().lower()
                    if len(row) > header_map['role'] else ''
                )
                name_idx = header_map.get('name')
                uname_idx = header_map.get('username')
                try:
                    tid = int(float(row[tid_idx].strip()))
                except (ValueError, TypeError):
                    continue
                users.append({
                    'telegram_id': tid,
                    'name': row[name_idx] if name_idx is not None and len(row) > name_idx else '',
                    'username': row[uname_idx] if uname_idx is not None and len(row) > uname_idx else '',
                    'role': role_map.get(role_raw, role_raw),
                })
            return users
        except Exception as e:
            logger.error(f"get_all_users error: {e}")
            return []

    def update_user_role(self, telegram_id: int, new_role: str) -> bool:
        """
        Обновить роль пользователя в листе Пользователи.

        Args:
            telegram_id: Telegram ID пользователя.
            new_role: Новая роль в русском формате ('Владелец', 'Менеджер',
                      'Исполнитель', 'Учёт'). Используй ROLE_TO_SHEET из owner.py.

        Returns:
            True  — роль обновлена.
            False — пользователь не найден или лист недоступен.

        Side effects:
            - Пишет в Google Sheets: update_cell(row, role_col, new_role).
            - Изменяется ТОЛЬКО ячейка роли. Остальные колонки не трогаются.

        Invariants:
            - Количество строк в таблице не меняется.
            - Имя, username, telegram_id пользователя не изменяются.

        Preconditions:
            - new_role должна быть русским названием роли (не config.ROLE_*).
        """
        if not self.users_sheet:
            return False
        try:
            all_values = self.users_sheet.get_all_values()
            if len(all_values) < 2:
                return False

            headers = all_values[0]
            tid_col = role_col = None
            for idx, header in enumerate(headers):
                h = header.strip().lower()
                if 'telegram' in h and 'id' in h:
                    tid_col = idx
                elif h in ['роль', 'role']:
                    role_col = idx

            if tid_col is None or role_col is None:
                logger.error("update_user_role: колонки telegram_id или role не найдены")
                return False

            for row_idx, row in enumerate(all_values[1:], start=2):
                if len(row) <= tid_col or not row[tid_col]:
                    continue
                raw = str(row[tid_col]).strip().replace(' ', '').replace('\u00a0', '')
                match = False
                try:
                    match = int(float(raw)) == telegram_id
                except (ValueError, TypeError):
                    match = raw == str(telegram_id)
                if match:
                    self.users_sheet.update_cell(row_idx, role_col + 1, new_role)
                    self._user_cache.pop(telegram_id, None)
                    logger.info(f"update_user_role: {telegram_id} → {new_role}")
                    return True

            logger.warning(f"update_user_role: пользователь {telegram_id} не найден")
            return False
        except Exception as e:
            logger.error(f"update_user_role error: {e}")
            return False

    def deactivate_user(self, telegram_id: int) -> bool:
        """
        Деактивировать пользователя — очистить ячейку роли.

        Решение зафиксировано в ADR-001: очищаем роль, не удаляем строку.
        Это сохраняет историю и позволяет реактивировать через update_user_role().

        Args:
            telegram_id: Telegram ID пользователя.

        Returns:
            True  — роль очищена.
            False — пользователь не найден или лист недоступен.

        Side effects:
            - Пишет в Google Sheets: update_cell(row, role_col, '').
            - ТОЛЬКО ячейка роли устанавливается в пустую строку.
            - После этого get_user_role(telegram_id) вернёт None → доступ закрыт.

        Invariants:
            - Строка пользователя НЕ удаляется (delete_rows НЕ вызывается).
            - Количество строк в таблице не меняется.
            - Имя, username, telegram_id пользователя не изменяются.
            - Операция обратима: вызови update_user_role() для реактивации.
        """
        if not self.users_sheet:
            return False
        try:
            all_values = self.users_sheet.get_all_values()
            if len(all_values) < 2:
                return False

            headers = all_values[0]
            tid_col = role_col = None
            for idx, header in enumerate(headers):
                h = header.strip().lower()
                if 'telegram' in h and 'id' in h:
                    tid_col = idx
                elif h in ['роль', 'role']:
                    role_col = idx

            if tid_col is None or role_col is None:
                logger.error("deactivate_user: колонки telegram_id или role не найдены")
                return False

            for row_idx, row in enumerate(all_values[1:], start=2):
                if len(row) <= tid_col or not row[tid_col]:
                    continue
                raw = str(row[tid_col]).strip().replace(' ', '').replace('\u00a0', '')
                match = False
                try:
                    match = int(float(raw)) == telegram_id
                except (ValueError, TypeError):
                    match = raw == str(telegram_id)
                if match:
                    self.users_sheet.update_cell(row_idx, role_col + 1, '')
                    self._user_cache.pop(telegram_id, None)
                    logger.info(f"deactivate_user: роль {telegram_id} очищена")
                    return True

            logger.warning(f"deactivate_user: пользователь {telegram_id} не найден")
            return False
        except Exception as e:
            logger.error(f"deactivate_user error: {e}")
            return False

    def add_user(self, telegram_id: int, name: str, username: str, role: str) -> bool:
        """
        Добавить пользователя в лист Пользователи

        Args:
            telegram_id: ID пользователя в Telegram
            name: ФИО или имя
            username: Username в Telegram (с @ или без)
            role: owner/manager/executor
        """
        if not self.users_sheet:
            logger.error("add_user: лист Пользователи недоступен")
            return False

        # Проверяем что такого пользователя ещё нет
        existing = self.get_user(telegram_id)
        if existing:
            logger.warning(f"add_user: пользователь {telegram_id} уже существует")
            return False

        try:
            row = [telegram_id, name, username, role]
            self.users_sheet.append_row(row, value_input_option='USER_ENTERED')
            logger.info(f"Polzovatel {name} ({role}) dobavlen")
            return True
        except Exception as e:
            logger.exception(f"add_user error: {e}")
            return False

    def check_user_permission(self, telegram_id: int, required_role: str) -> bool:
        """
        Проверить права пользователя

        Args:
            telegram_id: ID пользователя
            required_role: Требуемая роль (owner/manager/executor)

        Returns:
            True если у пользователя есть права
        """
        user = self.get_user(telegram_id)
        if not user:
            return False

        role_hierarchy = {
            'owner': 3,
            'manager': 2,
            'executor': 1
        }

        user_role = (user.get('role') or '').strip().lower()
        req_role = (required_role or '').strip().lower()
        user_level = role_hierarchy.get(user_role, 0)
        required_level = role_hierarchy.get(req_role, 0)

        return user_level >= required_level

    def get_user_role(self, telegram_id: int) -> Optional[str]:
        """
        Получить роль пользователя

        Returns:
            'owner', 'manager', 'executor' или None если пользователь не найден
        """
        user = self.get_user(telegram_id)
        if not user:
            return None
        return user.get('role')

    def is_user_active(self, telegram_id: int) -> bool:
        """
        Проверить активен ли пользователь (существует в листе Пользователи)

        Returns:
            True если пользователь существует
        """
        user = self.get_user(telegram_id)
        return user is not None

    def log_event(self, event_type: str, user_id: int, username: str,
                 request_id: str = '', details: str = '') -> bool:
        """Логирование событий"""
        try:
            return True
        except Exception as e:
            logger.exception(f"log_event error: {e}")
            return False

    def get_wallets_list(self) -> list:
        """
        Получить список кошельков для оплаты

        ВРЕМЕННАЯ ЗАГЛУШКА: возвращает фиксированный список
        В будущем можно добавить отдельный лист "Кошельки"
        """
        return [
            "Alice (основной)",
            "Bob (резервный)",
            "Charlie (VIP)",
            "Diana (быстрый)"
        ]

    def approve_request(self, request_id: str, wallet: str) -> bool:
        """
        Одобрить заявку и назначить кошелек

        Args:
            request_id: ID заявки в формате "дата_сумма"
            wallet: Выбранный кошелек

        Returns:
            True если успешно
        """
        try:
            # Парсим request_id
            parts = request_id.rsplit('_', 1)
            if len(parts) != 2:
                logger.error(f"Nevernyj format request_id: {request_id}")
                return False

            date, amount_str = parts
            try:
                amount = float(amount_str)
            except ValueError:
                logger.error(f"Nevernaja summa v request_id: {amount_str}")
                return False

            # Находим строку
            row = self.find_request_row(date, amount)
            if not row:
                logger.error(f"Zajavka ne najdena: {date}, {amount}")
                return False

            # Обновляем статус на "Оплачена" (упрощенно - одобрение = сразу готова к оплате)
            # Можно добавить отдельный статус "Одобрена" если нужно
            self.journal_sheet.update_cell(row, 9, config.STATUS_CREATED)  # Оставляем "Создана"

            # Записываем кошелек в колонку "Название аккаунта" (K)
            self.journal_sheet.update_cell(row, 11, wallet)

            logger.info(f"Zajavka odobrena: {request_id}, koshelek: {wallet}")
            return True

        except Exception as e:
            logger.exception(f"approve_request error: {e}")
            return False
