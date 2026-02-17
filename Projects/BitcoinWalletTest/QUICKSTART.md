# Быстрая памятка - Bitcoin Core 0.6.1 Wallet Test

## 1. Скачать Bitcoin Core 0.6.1

**Ссылка**: https://sourceforge.net/projects/bitcoin/files/Bitcoin/bitcoin-0.6.1/

**Файл**: bitcoin-0.6.1-win32.zip

---

## 2. Запустить помощник установки

```powershell
cd Projects\BitcoinWalletTest
powershell -ExecutionPolicy Bypass -File step_by_step.ps1
```

Помощник:
- ✅ Найдёт скачанный файл
- ✅ Распакует в `C:\BitcoinCore-0.6.1`
- ✅ Создаст папки данных
- ✅ Настроит конфигурацию
- ✅ Запустит Bitcoin Core
- ✅ Проверит версию кошелька

---

## 3. Проверить версию (через 30 сек после запуска)

```powershell
cd C:\BitcoinCore-0.6.1
.\bitcoin-cli.exe -datadir=D:\BitcoinData06 -rpcuser=testuser -rpcpassword=testpass123 getinfo
```

**Ищем**: `"walletversion": 60000` ✅

---

## 4. Зашифровать кошелёк

```powershell
.\bitcoin-cli.exe -datadir=D:\BitcoinData06 -rpcuser=testuser -rpcpassword=testpass123 encryptwallet "MyPassword123!"
```

⚠️ **Bitcoin Core закроется!**

---

## 5. Перезапустить

```powershell
.\bitcoin-qt.exe -datadir=D:\BitcoinData06
```

Подождать 10 секунд.

---

## 6. Разблокировать

```powershell
.\bitcoin-cli.exe -datadir=D:\BitcoinData06 -rpcuser=testuser -rpcpassword=testpass123 walletpassphrase "MyPassword123!" 60
```

---

## 7. Создать адрес (проверка)

```powershell
.\bitcoin-cli.exe -datadir=D:\BitcoinData06 -rpcuser=testuser -rpcpassword=testpass123 getnewaddress
```

**Если адрес создан - всё работает!** ✅

---

## 8. Сделать бэкап

```powershell
copy D:\BitcoinData06\wallet.dat C:\BitcoinBackup\wallet_backup.dat
```

---

## Итого:

✅ Кошелёк с walletversion 60000
✅ Зашифрован паролем
✅ Проверен (адрес создан)
✅ Бэкап сделан

**Готово!** 🎉

---

## Если проблемы:

- `check_wallet.ps1` - диагностика
- `SIMPLE_GUIDE.md` - полная инструкция
- `INDEX.md` - описание всех файлов
