# Bitcoin Core 0.6.1 - Установка и создание кошелька walletversion 60000

## Пошаговая инструкция для Windows

### Шаг 1: Скачивание Bitcoin Core 0.6.1

1. Откройте ссылку в браузере:
   ```
   https://sourceforge.net/projects/bitcoin/files/Bitcoin/bitcoin-0.6.1/
   ```

2. Скачайте файл для Windows:
   - **bitcoin-0.6.1-win32-setup.exe** (установщик) - РЕКОМЕНДУЕТСЯ
   - или **bitcoin-0.6.1-win32.zip** (портативная версия)

3. Дождитесь завершения загрузки (примерно 10-15 МБ)

---

### Шаг 2: Установка Bitcoin Core 0.6.1

#### Вариант A: Установщик (.exe)

1. Запустите скачанный `bitcoin-0.6.1-win32-setup.exe`
2. Выберите папку установки: **`C:\BitcoinCore-0.6.1`**
   - ⚠️ НЕ устанавливайте в Program Files (могут быть проблемы с правами)
   - Создайте отдельную папку, чтобы не перепутать с другими версиями
3. Завершите установку

#### Вариант B: Портативная версия (.zip)

1. Распакуйте `bitcoin-0.6.1-win32.zip`
2. Скопируйте содержимое в папку: **`C:\BitcoinCore-0.6.1`**

---

### Шаг 3: Проверка установки

Откройте PowerShell и выполните:

```powershell
cd C:\BitcoinCore-0.6.1
dir
```

Вы должны увидеть файлы:
- `bitcoin-qt.exe` - главная программа с GUI
- `bitcoind.exe` - демон (без GUI)
- `bitcoin-cli.exe` - утилита для команд

---

### Шаг 4: Создание отдельной папки для данных

Создайте отдельную папку для кошелька и блокчейна:

```powershell
mkdir D:\BitcoinData06
```

⚠️ **Важно**: Используем отдельный `datadir`, чтобы не затронуть ваш основной Bitcoin Core (если он установлен)

---

### Шаг 5: Первый запуск Bitcoin Core 0.6.1

Запустите Bitcoin Core с отдельным datadir:

```powershell
cd C:\BitcoinCore-0.6.1
.\bitcoin-qt.exe -datadir=D:\BitcoinData06
```

**Что произойдёт:**
1. Откроется окно Bitcoin Core
2. Начнётся синхронизация блокчейна (это займёт МНОГО времени)
3. **Автоматически создастся файл `wallet.dat`** в папке `D:\BitcoinData06`

⚠️ **Для теста нам НЕ нужна полная синхронизация!**
Достаточно, чтобы создался файл `wallet.dat`.

---

### Шаг 6: Проверка создания кошелька

Откройте НОВОЕ окно PowerShell (не закрывайте Bitcoin Core!) и проверьте:

```powershell
dir D:\BitcoinData06\wallet.dat
```

Если файл есть - **отлично!** Кошелёк создан.

---

### Шаг 7: Проверка версии кошелька через bitcoin-cli

В том же окне PowerShell выполните:

```powershell
cd C:\BitcoinCore-0.6.1
.\bitcoin-cli.exe -datadir=D:\BitcoinData06 getinfo
```

**Ожидаемый результат:**
```json
{
  "version": 60001,
  "protocolversion": 60001,
  "walletversion": 60000,
  ...
}
```

✅ **Важно**: `"walletversion": 60000` - это то, что нам нужно!

Если команда не работает (RPC не запущен), нужно:
1. Закрыть Bitcoin-Qt (File → Exit)
2. Создать файл `bitcoin.conf` (см. ниже)
3. Запустить снова

---

### Шаг 8: Настройка RPC (если нужно)

Если `bitcoin-cli` не работает, создайте файл конфигурации:

1. Создайте файл `D:\BitcoinData06\bitcoin.conf`:

```ini
# Включить RPC сервер
server=1

# RPC аутентификация
rpcuser=testuser
rpcpassword=testpass123

# Порт RPC (по умолчанию 8332)
rpcport=8332
```

2. Перезапустите Bitcoin Core:

```powershell
cd C:\BitcoinCore-0.6.1
.\bitcoin-qt.exe -datadir=D:\BitcoinData06
```

3. Проверьте снова:

```powershell
.\bitcoin-cli.exe -datadir=D:\BitcoinData06 -rpcuser=testuser -rpcpassword=testpass123 getinfo
```

---

### Шаг 9: Шифрование кошелька паролем

⚠️ **ВАЖНО**: После шифрования Bitcoin Core автоматически остановится!

Выполните команду:

```powershell
.\bitcoin-cli.exe -datadir=D:\BitcoinData06 encryptwallet "YourSecurePassword123!"
```

Замените `YourSecurePassword123!` на свой пароль.

**Что произойдёт:**
1. Кошелёк будет зашифрован
2. Bitcoin Core закроется
3. Теперь для отправки средств нужен пароль

---

### Шаг 10: Перезапуск и проверка

1. Запустите Bitcoin Core снова:

```powershell
.\bitcoin-qt.exe -datadir=D:\BitcoinData06
```

2. Разблокируйте кошелёк на 60 секунд:

```powershell
.\bitcoin-cli.exe -datadir=D:\BitcoinData06 walletpassphrase "YourSecurePassword123!" 60
```

3. Создайте тестовый адрес:

```powershell
.\bitcoin-cli.exe -datadir=D:\BitcoinData06 getnewaddress
```

Если команда вернула Bitcoin адрес - **всё работает!** ✅

---

### Шаг 11: Резервная копия

⚠️ **КРИТИЧНО**: Сделайте резервную копию кошелька!

```powershell
# Создайте папку для бэкапа
mkdir C:\BitcoinBackup

# Скопируйте wallet.dat
copy D:\BitcoinData06\wallet.dat C:\BitcoinBackup\wallet.dat
```

Сохраните эту копию в надёжное место:
- На внешний диск
- В облако (зашифрованное)
- На USB-флешку

---

## Автоматизированный тест

Для автоматической проверки всех шагов используйте скрипт:

```powershell
python test_bitcoin_wallet.py
```

Этот скрипт:
1. Проверит наличие файлов
2. Запустит Bitcoin Core
3. Проверит версию кошелька
4. Зашифрует паролем
5. Разблокирует и создаст адрес
6. Выведет полный отчёт

---

## Чеклист готовности

- [ ] Bitcoin Core 0.6.1 скачан
- [ ] Установлен в `C:\BitcoinCore-0.6.1`
- [ ] Создана папка `D:\BitcoinData06`
- [ ] Bitcoin Core запущен с `-datadir`
- [ ] Файл `wallet.dat` создан
- [ ] Команда `getinfo` работает
- [ ] `walletversion = 60000` ✅
- [ ] Кошелёк зашифрован паролем
- [ ] Создана резервная копия `wallet.dat`

---

## Возможные проблемы

### Проблема: "bitcoin-cli не найден"

**Решение**: Проверьте путь:
```powershell
cd C:\BitcoinCore-0.6.1
dir bitcoin-cli.exe
```

### Проблема: "error: couldn't connect to server"

**Решение**:
1. Bitcoin-Qt не запущен - запустите его
2. RPC не включён - создайте `bitcoin.conf` (Шаг 8)
3. Ждите 10-15 секунд после запуска

### Проблема: "error: incorrect rpcuser or rpcpassword"

**Решение**: Добавьте параметры в команду:
```powershell
.\bitcoin-cli.exe -datadir=D:\BitcoinData06 -rpcuser=testuser -rpcpassword=testpass123 getinfo
```

### Проблема: Синхронизация блокчейна идёт долго

**Решение**: Для теста синхронизация НЕ нужна! Можно остановить Bitcoin Core после создания `wallet.dat`.

---

## Что дальше?

После создания кошелька с `walletversion 60000`:

1. **Резервная копия** - обязательно сохраните `wallet.dat`
2. **Запишите пароль** - без него не сможете получить доступ к средствам
3. **Миграция** - можно открыть этот `wallet.dat` в современном Bitcoin Core
4. **Использование** - кошелёк готов для приёма/отправки Bitcoin

---

## Безопасность

⚠️ **Bitcoin Core 0.6.1 - устаревшая версия (2012 год)!**

- Не используйте для реальных средств в интернете
- Только для теста и создания кошелька
- Для постоянной работы - используйте актуальную версию Bitcoin Core

---

## Контакты и помощь

Если возникли проблемы на любом шаге - опишите:
1. На каком шаге застряли
2. Какая ошибка появилась
3. Что показывает команда `getinfo`

Готов помочь на каждом этапе!
