# Инструкция по деплою Finance Bot v2.4.2 (CNY) на VPS

## ✅ Что изменилось в версии 2.4.2

### Новые возможности:
- ✅ Поддержка CNY (китайский юань)
- ✅ Загрузка QR-кодов в Google Drive (Alipay, WeChat)
- ✅ Текстовые реквизиты китайских карт
- ✅ Автоматическая настройка Google Sheets через скрипт
- ✅ Просмотр и редактирование CNY заявок

### Новые файлы:
- `drive_manager.py` - управление Google Drive
- `setup_cny_and_test.py` - настройка и тестирование
- Документация: `docs/CNY_IMPLEMENTATION.md`, `CNY_IMPLEMENTATION_REPORT.md`

---

## 📋 Что нужно для деплоя

### На локальной машине:
- [ ] Git репозиторий обновлён (latest commit)
- [ ] Все файлы Finance Bot на диске
- [ ] PuTTY / pscp установлены (для Windows)
- [ ] IP адрес VPS известен
- [ ] SSH доступ к VPS настроен

### На VPS:
- [ ] Ubuntu/Debian Linux
- [ ] Python 3.8+ установлен
- [ ] SSH доступ (root или sudo)
- [ ] Интернет соединение работает

### Секреты (подготовить заранее):
- [ ] Telegram Bot Token
- [ ] Google Sheets ID
- [ ] service_account.json файл

---

## 🚀 СПОСОБ 1: Быстрый деплой через pscp (Windows)

### Шаг 1: Загрузить файлы на VPS

```powershell
# Замените YOUR_VPS_IP на реальный IP
$IP = "YOUR_VPS_IP"

# Загрузить основные файлы
pscp -r Projects\FinanceBot\bot.py root@${IP}:/root/finance_bot/
pscp -r Projects\FinanceBot\config.py root@${IP}:/root/finance_bot/
pscp -r Projects\FinanceBot\sheets.py root@${IP}:/root/finance_bot/
pscp -r Projects\FinanceBot\drive_manager.py root@${IP}:/root/finance_bot/
pscp -r Projects\FinanceBot\requirements.txt root@${IP}:/root/finance_bot/
pscp -r Projects\FinanceBot\finance_bot.service root@${IP}:/root/finance_bot/
pscp -r Projects\FinanceBot\.env.example root@${IP}:/root/finance_bot/
pscp -r Projects\FinanceBot\setup_cny_and_test.py root@${IP}:/root/finance_bot/

# Загрузить папки
pscp -r Projects\FinanceBot\handlers root@${IP}:/root/finance_bot/
pscp -r Projects\FinanceBot\utils root@${IP}:/root/finance_bot/

# Загрузить service_account.json (ВАЖНО!)
pscp Projects\FinanceBot\service_account.json root@${IP}:/root/finance_bot/

# Загрузить скрипт настройки
pscp Projects\FinanceBot\vps_setup_commands.sh root@${IP}:/root/finance_bot/
```

### Шаг 2: Подключиться к VPS

```powershell
plink root@YOUR_VPS_IP
# Ввести пароль
```

### Шаг 3: Выполнить настройку

```bash
cd /root/finance_bot
bash vps_setup_commands.sh
```

### Шаг 4: Настроить .env

```bash
nano .env

# Заполнить:
TELEGRAM_BOT_TOKEN=ваш_токен_от_BotFather
GOOGLE_SHEETS_ID=id_вашей_таблицы
GOOGLE_SERVICE_ACCOUNT_FILE=service_account.json

# Ctrl+X, Y, Enter для сохранения
```

### Шаг 5: Настроить Google Sheets (создать лист CNY)

```bash
python3 setup_cny_and_test.py
```

**Ожидаемый результат:**
- ✅ Лист CNY создан
- ✅ Заголовки установлены
- ✅ Google Drive протестирован
- ✅ Тестовая CNY заявка создана

### Шаг 6: Перезапустить бота

```bash
systemctl restart finance_bot
systemctl status finance_bot
```

### Шаг 7: Проверить логи

```bash
journalctl -u finance_bot -f
```

**Должно быть:**
```
Finance Bot v2.4.2 started successfully
Bot is running...
```

---

## 🛠️ СПОСОБ 2: Ручной деплой (без pscp)

### Шаг 1: Подключиться к VPS

```bash
ssh root@YOUR_VPS_IP
```

### Шаг 2: Создать структуру

```bash
mkdir -p /root/finance_bot/handlers
mkdir -p /root/finance_bot/utils
cd /root/finance_bot
```

### Шаг 3: Создать файлы через nano

```bash
# Основные файлы
nano bot.py
# Скопировать содержимое из локального bot.py
# Ctrl+X, Y, Enter

nano config.py
# Скопировать содержимое
# Ctrl+X, Y, Enter

nano sheets.py
# Скопировать содержимое
# Ctrl+X, Y, Enter

nano drive_manager.py
# Скопировать содержимое
# Ctrl+X, Y, Enter

# Конфиги
nano requirements.txt
# Скопировать содержимое
# Ctrl+X, Y, Enter

nano .env
# Вставить:
# TELEGRAM_BOT_TOKEN=ваш_токен
# GOOGLE_SHEETS_ID=id_таблицы
# GOOGLE_SERVICE_ACCOUNT_FILE=service_account.json

nano finance_bot.service
# Скопировать содержимое из finance_bot.service
# Ctrl+X, Y, Enter
```

### Шаг 4: Создать файлы в handlers/

```bash
cd handlers
nano __init__.py
nano start.py
nano menu.py
nano request.py
nano payment.py
nano edit_handlers.py
cd ..
```

### Шаг 5: Создать файлы в utils/

```bash
cd utils
nano __init__.py
nano auth.py
nano categories.py
nano formatters.py
cd ..
```

### Шаг 6: Загрузить service_account.json

```bash
nano service_account.json
# Вставить содержимое JSON файла
# Ctrl+X, Y, Enter
```

### Шаг 7: Выполнить настройку

```bash
# Установить зависимости
apt update
apt install -y python3 python3-pip
pip3 install --upgrade pip
pip3 install -r requirements.txt

# Настроить systemd
cp finance_bot.service /etc/systemd/system/
systemctl daemon-reload
systemctl enable finance_bot
systemctl start finance_bot

# Проверить статус
systemctl status finance_bot
```

### Шаг 8: Настроить Google Sheets

```bash
python3 setup_cny_and_test.py
```

---

## 📊 Проверка работы

### 1. Проверить статус systemd

```bash
systemctl status finance_bot
```

**Ожидается:**
```
● finance_bot.service - Finance Bot - Telegram bot for finance management
   Loaded: loaded
   Active: active (running)
```

### 2. Проверить логи

```bash
journalctl -u finance_bot -n 50
```

**Не должно быть:**
- ❌ Error
- ❌ Failed
- ❌ Exception

**Должно быть:**
- ✅ Bot started
- ✅ Polling started

### 3. Проверить в Telegram

1. Открыть бота
2. Отправить `/start`
3. Проверить что меню появилось
4. Создать тестовую заявку

### 4. Проверить Google Sheets

1. Открыть таблицу
2. Проверить что лист "CNY" существует
3. Проверить заголовки (16 колонок)

### 5. Проверить Google Drive

1. Создать CNY заявку с QR-кодом
2. Проверить что файл появился в Google Drive
3. Проверить что ссылка работает

---

## 🔧 Управление ботом

### Основные команды:

```bash
# Запустить
systemctl start finance_bot

# Остановить
systemctl stop finance_bot

# Перезапустить
systemctl restart finance_bot

# Статус
systemctl status finance_bot

# Логи
journalctl -u finance_bot -f          # В реальном времени
journalctl -u finance_bot -n 100      # Последние 100 строк
journalctl -u finance_bot --since "1 hour ago"
```

### Обновление бота:

```bash
# 1. Загрузить новые файлы через pscp
pscp bot.py root@YOUR_VPS_IP:/root/finance_bot/

# 2. Подключиться к VPS
ssh root@YOUR_VPS_IP

# 3. Перезапустить
systemctl restart finance_bot

# 4. Проверить логи
journalctl -u finance_bot -f
```

---

## 🐛 Troubleshooting

### Бот не запускается

**Проблема:** `systemctl status finance_bot` показывает `failed`

**Решение:**
```bash
# Посмотреть ошибку
journalctl -u finance_bot -n 50

# Запустить вручную для диагностики
cd /root/finance_bot
python3 bot.py

# Типичные причины:
# 1. Неверный TOKEN
nano .env  # Проверить

# 2. Нет service_account.json
ls -la service_account.json

# 3. Нет зависимостей
pip3 install -r requirements.txt
```

### Google Sheets не работает

**Проблема:** Ошибки при создании заявок

**Решение:**
```bash
# Проверить что service_account.json есть
cat service_account.json

# Проверить что credentials правильные
python3 -c "import gspread; from oauth2client.service_account import ServiceAccountCredentials; print('OK')"

# Запустить настройку заново
python3 setup_cny_and_test.py
```

### Google Drive не загружает QR-коды

**Проблема:** QR-коды не появляются в Drive

**Решение:**
```bash
# Проверить drive_manager.py
python3 -c "from drive_manager import DriveManager; print('OK')"

# Проверить логи
journalctl -u finance_bot -n 100 | grep -i drive
```

### Бот работает, но не отвечает

**Проблема:** Статус `active`, но бот не реагирует

**Решение:**
```bash
# 1. Проверить логи
journalctl -u finance_bot -f

# 2. Проверить что токен правильный
# @BotFather -> /mybots -> выбрать бота -> API Token

# 3. Убить дубликаты если есть
ps aux | grep bot.py
kill <PID>

# 4. Перезапустить
systemctl restart finance_bot
```

---

## 📄 Чеклист деплоя

### Перед деплоем:
- [ ] Все изменения закоммичены в Git
- [ ] Локальный бот работает
- [ ] requirements.txt обновлён
- [ ] .env.example актуален
- [ ] service_account.json готов

### Во время деплоя:
- [ ] Файлы загружены на VPS
- [ ] Зависимости установлены
- [ ] .env создан и заполнен
- [ ] service_account.json загружен
- [ ] Service скопирован в /etc/systemd/system/
- [ ] systemctl daemon-reload выполнен
- [ ] systemctl enable выполнен
- [ ] setup_cny_and_test.py выполнен

### После деплоя:
- [ ] systemctl status показывает `active (running)`
- [ ] Логи не содержат ошибок
- [ ] Бот отвечает в Telegram
- [ ] Лист CNY создан в Google Sheets
- [ ] QR-коды загружаются в Google Drive
- [ ] Заявки создаются успешно

---

## 📞 Поддержка

При проблемах:

1. Проверить логи: `journalctl -u finance_bot -n 100`
2. Запустить вручную: `cd /root/finance_bot && python3 bot.py`
3. Прочитать документацию:
   - `CNY_IMPLEMENTATION_REPORT.md`
   - `docs/CNY_IMPLEMENTATION.md`

---

**Версия:** 2.4.2
**Дата:** 02.02.2026
**Finance Bot готов к production! 🚀**
