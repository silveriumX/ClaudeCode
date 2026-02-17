# Список тестов Finance Bot (план: курс формулой, USDT, третий лист)

## 1. Структурные тесты (без Google API)

Запуск: `python run_tests.py` — сначала выполняются эти тесты.

| № | Тест | Что проверяет |
|---|------|----------------|
| 1 | **Config: USDT & Payment Methods** | `config.SHEET_USDT` задан; `PAYMENT_METHODS` содержит «Карта», «СБП», «Крипта». |
| 2 | **create_request: 20 columns (A–T)** | В `create_request` строка журнала имеет 20 элементов; есть комментарии для S и T. |
| 3 | **complete_payment: signature & columns** | Сигнатура `(request_id, executor_name, amount_usdt=None)`; нет `rate`; обновляются колонки 2, 16, 17, 18; при USDT — 20; колонка 19 не обновляется. |
| 4 | **get_request_by_id: amount_usdt in dict** | В возвращаемом словаре есть ключ `amount_usdt` (из колонки «Сумма USDT»). |
| 5 | **append_usdt_payment: formula on correct row** | После `append_row` номер строки для формулы курса считается через `len(sheet.col_values(1))`. |
| 6 | **payment.py: no ENTER_RATE** | В `payment.py` нет состояния `ENTER_RATE` и обработчика `enter_rate`; есть `ENTER_AMOUNT_USDT` и `enter_amount_usdt`. |
| 7 | **fix_sheets_structure: journal 20 cols** | В эталоне журнала в `fix_sheets_structure.py` есть «Сумма USDT» и упоминание листа USDT. |
| 8 | **SHEETS_STRUCTURE.md: column T & formula S** | В документации описаны колонка T «Сумма USDT», формула для S и лист USDT. |
| 9 | **Backward compat: get_request_by_id safe** | Используется `record.get('Сумма USDT')` — при отсутствии колонки T возвращается `None`, без ошибки. |

## 2. Интеграционные тесты (требуют .env и доступ к Google Таблице)

Выполняются после структурных при наличии `GOOGLE_SHEETS_ID` и `service_account.json`.

| № | Тест | Что проверяет |
|---|------|----------------|
| 1 | **Configuration Validation** | TELEGRAM_BOT_TOKEN, GOOGLE_SHEETS_ID, service_account.json, роли. |
| 2 | **Google Sheets Connection** | Подключение к API; наличие листов: Пользователи, Журнал операций, Расчетный баланс; опционально: Баланс счетов, Лог событий, USDT. |
| 3 | **Users Sheet Structure** | Заголовки: Telegram ID, Username, ФИО, Роль, Статус; загрузка записей; роли из config. |
| 4 | **Journal Sheet Structure** | Заголовки журнала A–T (в т.ч. Курс USDT/RUB, Сумма USDT); при отсутствии T — предупреждение; заявки REQ-; статусы. |
| 5 | **Balance Sheets** | Доступ к листам «Баланс счетов» и «Расчетный баланс». |
| 6 | **Event Logging** | Лист «Лог событий» с заголовками (новый или старый формат). |
| 7 | **Data Integrity** | Уникальность ID заявок; наличие автора и суммы у проверяемых записей. |

## 3. Обратная совместимость (не ломаем текущие таблицы)

- **Журнал:** если колонки T («Сумма USDT») нет — тест журнала выдаёт предупреждение; `get_request_by_id` не падает (`.get('Сумма USDT')`).
- **Лог событий:** допускается старый формат заголовков (Событие, Пользователь) и новый (Тип события, User ID, Username, ID заявки).
- **Статусы заявок:** при некорректном или «дата в статусе» (смещение колонок) — предупреждение, не падение теста.
- **Лист USDT:** опциональный; отсутствие не считается ошибкой.

## Запуск

```bash
cd Projects/FinanceBot
python run_tests.py
```

Структурные тесты выполняются всегда; интеграционные — при доступной таблице. При отсутствии учётных данных интеграционная часть пропускается с сообщением.
