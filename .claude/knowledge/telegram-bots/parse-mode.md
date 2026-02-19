---
description: parse_mode safety in Telegram bots. Markdown v1 fails silently on dynamic content (URLs, names, amounts) containing special characters. Decision tree: static text → Markdown OK; dynamic content → HTML or no parse_mode; dynamic clickable link → InlineKeyboardButton.
---

# Parse Mode Safety

Markdown v1 is the most common source of silent 400 errors in production Telegram bots. The failure mode is specific: the Telegram API returns `400 Bad Request: Can't parse entities` — and this gets caught by a wide [[try-except-scope]], which then triggers [[notification-ordering]] violations.

## What Breaks Markdown v1

Any of these characters in dynamic content:

```
_  *  [  ]  (  )  ~  `  >  #  +  -  =  |  {  }  .  !
```

**The most common real-world trigger:** Google Drive file IDs contain `_`:
```
https://drive.google.com/file/d/1BfvEO3j_7uhw4tf5A9ymlyYHRymKus9A/view
                                        ^--- breaks Markdown v1
```

User names with underscores, amounts like `1_000`, and any URL will eventually hit this.

## Decision Tree

```
Is the text fully static (no variables)?
├── YES → parse_mode='Markdown' is fine
└── NO → Does it contain a clickable URL that must be a hyperlink?
         ├── YES → Use InlineKeyboardButton (most reliable) or HTML <a href>
         └── NO → Use parse_mode='HTML' or no parse_mode
```

## Code Patterns

```python
# WRONG — Markdown v1 with any dynamic string
await message.reply_text(f"Ссылка: {url}", parse_mode='Markdown')

# CORRECT — no parse_mode for messages with URLs or user data
await message.reply_text(f"Ссылка: {url}")

# CORRECT — Markdown only for fully static text
await message.reply_text("*Заявка оплачена*", parse_mode='Markdown')

# CORRECT — HTML is safe for mixed static + dynamic
await message.reply_text(
    f'Оплата <b>{amount} USDT</b>\nЧек: <a href="{url}">открыть</a>',
    parse_mode='HTML'
)

# CORRECT — InlineKeyboardButton is the most reliable for clickable dynamic URLs
keyboard = [[InlineKeyboardButton("Открыть чек", url=url)]]
await message.reply_text(
    f"Чек загружен: {amount} USDT",
    reply_markup=InlineKeyboardMarkup(keyboard)
)

# CORRECT — MarkdownV2 with escaping (when Markdown formatting is required)
from telegram.helpers import escape_markdown
safe_name = escape_markdown(user_name, version=2)
safe_amount = escape_markdown(str(amount), version=2)
await message.reply_text(
    f"*Платёж от* {safe_name}: `{safe_amount} USDT`",
    parse_mode='MarkdownV2'
)
```

## HTML Entities to Escape

When building HTML messages manually, escape these in dynamic content:

```python
def safe_html(text: str) -> str:
    return text.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
```

Or use `telegram.helpers.escape_markdown(text, version=2)` for MarkdownV2.

## Why This Interacts with try/except

When a `parse_mode='Markdown'` call fails with 400, it raises `telegram.error.BadRequest`. If this call is inside a broad `try/except Exception`, the except block will run — often a second notification path. See [[try-except-scope]] for how to scope exception handlers to prevent this.

## Checklist

- [ ] No `parse_mode='Markdown'` if the string contains any variable (`f"..."` with `{...}`)
- [ ] Dynamic URLs → no parse_mode, HTML, or InlineKeyboardButton
- [ ] User names from Telegram → escape before embedding in formatted text
- [ ] Amounts, IDs, file paths → treat as potentially containing special chars
