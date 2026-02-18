---
description: Telegram bot message safety - parse_mode, try/except scope, notifications. Apply to all Telegram bot handlers with dynamic content.
paths:
  - "**/handlers/*.py"
  - "**/*bot*.py"
  - "**/telegram*.py"
---

# Telegram Message Safety

> Правила безопасного формирования сообщений в Telegram-ботах.
> Нарушение этих правил приводит к тихим ошибкам, двойным уведомлениям и потере данных.

---

## 1. parse_mode='Markdown' (v1) с динамическим контентом — ЗАПРЕЩЕНО

Markdown v1 ломается на любом из символов: `_  *  [  ]  (  )  ~  \`` если они появляются в динамических данных (имена, суммы, URL-адреса).

### Частый случай: URL от Google Drive

Google Drive file ID содержит `_`:
```
https://drive.google.com/file/d/1BfvEO3j_7uhw4tf5A9ymlyYHRymKus9A/view
                                        ^--- ломает Markdown v1
```

Telegram вернёт `400 Bad Request: Can't parse entities` — и это исключение может вызвать повторное уведомление или потерю ответа пользователю.

### Правило

```python
# НЕЛЬЗЯ — Markdown v1 с любым динамическим текстом
await message.reply_text(f"Ссылка: {url}", parse_mode='Markdown')

# МОЖНО — без parse_mode для сообщений с URL или пользовательскими данными
await message.reply_text(f"Ссылка: {url}")

# МОЖНО — Markdown только для статичного текста
await message.reply_text("*Заявка оплачена*", parse_mode='Markdown')

# МОЖНО — MarkdownV2 с экранированием (для смешанного контента)
from telegram.helpers import escape_markdown
safe_url = escape_markdown(url, version=2)
await message.reply_text(f"Ссылка: {safe_url}", parse_mode='MarkdownV2')
```

### Для кликабельных ссылок с динамическим URL

```python
# HTML безопаснее Markdown для динамических ссылок
await message.reply_text(
    f'<a href="{url}">Открыть чек</a>',
    parse_mode='HTML'
)

# Или InlineKeyboardButton — самый надёжный способ
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
keyboard = [[InlineKeyboardButton("Открыть чек", url=url)]]
await message.reply_text("Чек загружен", reply_markup=InlineKeyboardMarkup(keyboard))
```

---

## 2. Узкий try/except — уведомления вне блока загрузки

### Проблема

Широкий `try/except` вокруг загрузки файла + уведомления = двойное уведомление при ошибке `reply_text`:

```python
# НЕЛЬЗЯ — одна ошибка в reply_text вызывает второе уведомление
try:
    url = drive.upload(file)
    sheets.save(url)
    await notify_owners(url)         # ← первое уведомление
    await message.reply_text(url)    # ← если здесь ошибка Markdown...
except Exception as e:
    await notify_owners(error=True)  # ← ...срабатывает второй notify!
    await message.reply_text("Ошибка")
```

### Правило

```python
# МОЖНО — try/except только вокруг операции загрузки
upload_url = None
try:
    file_bytes = await file.download_as_bytearray()
    upload_url = drive.upload(file_bytes)
except Exception as e:
    logger.error(f"Upload failed: {e}")

# Уведомления и ответы — вне try/except загрузки
if upload_url:
    sheets.save(upload_url)
    await notify_owners(url=upload_url)
    await message.reply_text(f"Загружено: {upload_url}")  # без parse_mode
else:
    await notify_owners(error=True)
    await message.reply_text("Ошибка загрузки")
```

---

## 3. Порядок: сначала бизнес-логика, потом уведомления

Уведомление должно уходить **после** того, как все данные записаны:

```python
# НЕЛЬЗЯ — уведомление до записи в таблицу
await notify_owners(...)     # owner получит уведомление
sheets.complete_payment(...) # но если это упадёт — данные не записаны

# МОЖНО — сначала запись, потом уведомление
sheets.complete_payment(...)
await notify_owners(...)
```

Если уведомление нужно включать данные из нескольких шагов (например, факт оплаты + чек), **откладывай уведомление** до конца всех шагов, сохраняя промежуточные данные в `context.user_data`.

---

## 4. Хранить в user_data всё что нужно для финального уведомления

Если уведомление owner составное (данные из нескольких шагов):

```python
# В начале флоу — сохраняем всё
context.user_data['executor_name'] = executor_name
context.user_data['deal_id'] = deal_id
context.user_data['amount_usdt'] = amount_usdt
context.user_data['payment_request'] = request

# В финальной функции — читаем из user_data
async def notify_owners(context, receipt_url=None, receipt_error=False):
    request = context.user_data.get('payment_request', {})
    executor = context.user_data.get('executor_name', '')
    ...
```

---

## Чеклист перед отправкой сообщения с динамическим контентом

- [ ] Нет `parse_mode='Markdown'` если в тексте есть URL, имена, суммы
- [ ] Для кликабельных ссылок: HTML (`<a href>`) или кнопка (`InlineKeyboardButton`)
- [ ] try/except охватывает только операцию (upload, API call), не notify/reply
- [ ] Уведомление owner отправляется один раз, после всех записей в БД
- [ ] Данные для финального уведомления сохранены в `context.user_data` заранее
