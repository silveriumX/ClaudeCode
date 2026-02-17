# Config Scripts

Legacy скрипты для настройки OpenClaw на VPS.

## Важно: Пути и переменные окружения

Все скрипты теперь используют правильные пути:
- **Config directory:** `/root/.openclaw/`
- **Config file:** `/root/.openclaw/openclaw.json`
- **Env file:** `/root/.openclaw/.env`

Все скрипты поддерживают оба набора переменных окружения:
- **Новый формат:** `VPS_HOST`, `VPS_PORT`, `VPS_USER`, `VPS_PASSWORD`
- **Legacy формат:** `VOICEBOT_HOST`, `VOICEBOT_USER`, `VOICEBOT_SSH_PASS`

## Доступные скрипты

### set_env.py
Устанавливает ANTHROPIC_API_KEY в `/root/.openclaw/.env` на VPS.

**Требуемые переменные окружения:**
- `VPS_HOST` или `VOICEBOT_HOST` - IP или домен VPS
- `VPS_PASSWORD` или `VOICEBOT_SSH_PASS` - SSH пароль
- `ANTHROPIC_API_KEY` или `OPENCLAW_ANTHROPIC_KEY` - API ключ

### set_glm.py
Настраивает OpenClaw для использования GLM-4.7 через Z.AI.

**Требуемые переменные окружения:**
- `VPS_HOST` или `VOICEBOT_HOST`
- `VPS_PASSWORD` или `VOICEBOT_SSH_PASS`
- `ZAI_API_KEY` или `OPENCLAW_ZAI_API_KEY` - Z.AI API ключ
- `TELEGRAM_BOT_TOKEN` или `OPENCLAW_TELEGRAM_BOT_TOKEN` (опционально)

### fix_telegram.py
Настраивает Telegram бота в конфигурации OpenClaw.

**Требуемые переменные окружения:**
- `VPS_HOST` или `VOICEBOT_HOST`
- `VPS_PASSWORD` или `VOICEBOT_SSH_PASS`
- `TELEGRAM_BOT_TOKEN` или `OPENCLAW_TELEGRAM_BOT_TOKEN`

### verify_token.py
Проверяет валидность Telegram токена на VPS.

**Требуемые переменные окружения:**
- `VPS_HOST` или `VOICEBOT_HOST`
- `VPS_PASSWORD` или `VOICEBOT_SSH_PASS`

## Использование

```bash
# Пример с новыми переменными
$env:VPS_HOST = "195.177.94.189"
$env:VPS_PASSWORD = "your_password"
$env:ANTHROPIC_API_KEY = "sk-..."
python scripts/config/set_env.py

# Пример с legacy переменными (все еще работает)
$env:VOICEBOT_HOST = "195.177.94.189"
$env:VOICEBOT_SSH_PASS = "your_password"
$env:OPENCLAW_ANTHROPIC_KEY = "sk-..."
python scripts/config/set_env.py
```

## Миграция

Эти скрипты постепенно мигрируются в основной `vps_connect.py`.
Для новых функций используйте `vps_connect.py config <option>`.
