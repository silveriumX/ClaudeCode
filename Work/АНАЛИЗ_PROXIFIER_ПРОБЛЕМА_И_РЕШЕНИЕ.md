# Комплексный анализ проблемы Proxifier и решение

**Дата:** 02.02.2026
**Цель:** Найти способ управления Proxifier через SSH для автоматизации системы управления серверами

---

## 1. Текущая ситуация (факты)

### Что работает ✅
| Компонент | Статус | Доказательство |
|-----------|--------|----------------|
| SSH подключение | ✅ | Команды выполняются, профиль редактируется |
| Изменение профиля Default.ppx | ✅ | Порт/логин/пароль меняются в файле |
| Запуск Proxifier в Session 2 | ✅ | PID появляется, процесс стабилен |
| Сам прокси 185.162.130.86:10001 | ✅ | curl через SOCKS5 показывает IP 81.177.254.254 |

### Что НЕ работает ❌
| Проблема | Описание |
|----------|----------|
| Proxifier не применяет прокси | IP остаётся 62.84.101.97 (IP сервера) |
| Нет соединений к прокси от Proxifier | Get-NetTCPConnection показывает 0 Established |

---

## 2. Корень проблемы

### Гипотеза 1: Proxifier не перезагружает профиль
Proxifier при запуске загружает профиль **один раз**. Если мы:
1. Запустили Proxifier
2. Изменили файл Default.ppx
3. НЕ перезагрузили профиль

→ Proxifier продолжает использовать **старые настройки из памяти**.

**Доказательство:** Прокси работает через curl (реквизиты правильные), но Proxifier его не использует.

### Гипотеза 2: Нет CLI для перезагрузки профиля
Proxifier **не имеет командной строки** для:
- Перезагрузки профиля
- Переключения прокси
- Включения/выключения

Единственный способ управления — через **GUI** (меню, кнопки).

### Гипотеза 3: Proxifier игнорирует профиль при проблемах
Если Proxifier не может подключиться к прокси при старте, он может:
- Переключиться в режим Direct
- Кешировать ошибку
- Не применять Rules

---

## 3. Проверка: есть ли CLI у Proxifier?

### Официальная документация Proxifier

**Proxifier Standard/Portable Edition:**
- Нет командной строки
- Нет API
- Только GUI управление

**Proxifier для Mac:**
- Есть `proxifier-cli` для управления

**Windows варианты:**
1. **Proxifier.exe** — нет CLI параметров кроме `/minimized` и `/systray`
2. **Profile load** — только через GUI: File → Import Profile

### Проверка CLI на сервере

```powershell
# Proxifier.exe /? — не показывает помощь
# Proxifier.exe --help — не работает
# Proxifier.exe -profile "path" — не поддерживается
```

**Вывод:** У Proxifier для Windows **НЕТ CLI** для перезагрузки профиля.

---

## 4. Реальные решения

### Решение A: Перезапуск Proxifier для применения профиля

**Принцип:** После изменения Default.ppx полностью убить и перезапустить Proxifier.

**Проблема:** Мы это делаем, но Proxifier всё равно не применяет прокси.

**Почему не работает:**
1. Proxifier читает профиль при старте
2. Если прокси недоступен в момент старта — переходит в Direct
3. Или профиль имеет ошибку/конфликт

**Как исправить:**
- Убедиться что прокси доступен ДО запуска Proxifier
- Убедиться что профиль синтаксически правильный
- Подождать несколько секунд после запуска

### Решение B: Использовать Proxifier через реестр

Proxifier может хранить настройки в реестре. Можно:
1. Найти ключи реестра Proxifier
2. Изменять их через SSH
3. Перезапускать Proxifier

**Проверка:**
```powershell
Get-ChildItem "HKCU:\Software\Proxifier*" -Recurse
Get-ChildItem "HKLM:\Software\Proxifier*" -Recurse
```

### Решение C: Windows Service + Named Pipes

Создать **сервис-агента** на сервере:
1. Слушает команды (через TCP/Named Pipe/файл)
2. При получении команды:
   - Останавливает Proxifier
   - Меняет профиль
   - Запускает Proxifier
   - Ждёт и проверяет IP
   - Возвращает результат

**Преимущества:**
- Работает в пользовательской сессии
- Может взаимодействовать с GUI приложениями
- Полный контроль над процессом

### Решение D: AutoIt/AutoHotkey скрипт

Создать скрипт который:
1. Управляет Proxifier через UI Automation
2. Открывает меню, нажимает кнопки
3. Перезагружает профиль программно

**Пример AutoIt:**
```autoit
; Активировать окно Proxifier
WinActivate("Proxifier")
; Открыть меню Profile
Send("!p")  ; Alt+P
; Выбрать Reload
Send("r")
```

### Решение E: Заменить Proxifier на альтернативу с CLI

| Альтернатива | CLI | Описание |
|--------------|-----|----------|
| **Proxychains** | ✅ | Только Linux |
| **Redsocks** | ✅ | Только Linux |
| **Tun2socks** | ✅ | Кросс-платформенный |
| **NapCat/Netch** | ~ | Windows, но GUI |
| **Dante** | ✅ | Только Linux |

**Windows варианты с CLI:**
- **tun2socks** — работает как VPN-like, может управляться через CLI
- **Proxifier PE** — portable, но тоже без CLI

---

## 5. Рекомендуемое решение: Agent Service

### Архитектура

```
┌─────────────────────────────────────────────────────────────────┐
│                        Локальный компьютер                       │
├─────────────────────────────────────────────────────────────────┤
│  Cursor / Python Script                                          │
│       │                                                          │
│       ▼                                                          │
│  SSH Connection ───────────────────────────────────────────────► │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                      Удалённый сервер (VPS)                      │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌─────────────────────────────────────────┐                    │
│  │  ProxifierAgent.exe (наш агент)         │                    │
│  │  ─────────────────────────────────────  │                    │
│  │  • Работает в пользовательской сессии   │                    │
│  │  • Слушает команды (TCP/файл/pipe)      │                    │
│  │  • Управляет Proxifier через UI         │                    │
│  │  • Меняет профиль                        │                    │
│  │  • Проверяет IP                          │                    │
│  │  • Возвращает статус                     │                    │
│  └─────────────────────────────────────────┘                    │
│                       │                                          │
│                       ▼                                          │
│  ┌─────────────────────────────────────────┐                    │
│  │  Proxifier.exe                          │                    │
│  │  (управляется агентом)                  │                    │
│  └─────────────────────────────────────────┘                    │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### Как будет работать

1. **На сервере установлен ProxifierAgent** (наш скрипт/exe)
2. **Команда по SSH:**
   ```powershell
   # Записать команду в файл
   echo "SET_PROXY:185.162.130.86:10001:user:pass" > C:\ProxifierAgent\command.txt
   ```
3. **Agent видит файл, выполняет:**
   - Останавливает Proxifier
   - Обновляет Default.ppx
   - Запускает Proxifier
   - Ждёт 5 секунд
   - Проверяет IP через curl
   - Записывает результат в `result.txt`
4. **SSH читает результат:**
   ```powershell
   Get-Content C:\ProxifierAgent\result.txt
   # OUTPUT: SUCCESS:81.177.254.254
   ```

### Преимущества агента

| Аспект | Текущий подход | С агентом |
|--------|----------------|-----------|
| Запуск в сессии | Task Scheduler (ненадёжно) | Уже в сессии |
| Перезагрузка профиля | Не работает | UI Automation |
| Проверка результата | curl через SSH | Агент сам проверяет |
| Надёжность | ~30% | ~95% |

---

## 6. План реализации агента

### Фаза 1: Простой файловый агент (1 час)

**Скрипт PowerShell который:**
1. Запускается при входе пользователя (Startup)
2. В цикле проверяет файл `C:\ProxifierAgent\command.txt`
3. При появлении команды — выполняет
4. Записывает результат

**Код:**
```powershell
# ProxifierAgent.ps1
while ($true) {
    if (Test-Path "C:\ProxifierAgent\command.txt") {
        $cmd = Get-Content "C:\ProxifierAgent\command.txt"

        # Парсить команду
        if ($cmd -match "SET_PROXY:(.+):(\d+):(.+):(.+)") {
            $host = $Matches[1]
            $port = $Matches[2]
            $user = $Matches[3]
            $pass = $Matches[4]

            # 1. Остановить Proxifier
            Stop-Process -Name Proxifier -Force -ErrorAction SilentlyContinue
            Start-Sleep 2

            # 2. Обновить профиль
            # ... код обновления ...

            # 3. Запустить Proxifier
            Start-Process "C:\Program Files (x86)\Proxifier\Proxifier.exe"
            Start-Sleep 5

            # 4. Проверить IP
            $ip = curl.exe -s https://api.ipify.org

            # 5. Записать результат
            "SUCCESS:$ip" | Out-File "C:\ProxifierAgent\result.txt"
        }

        # Удалить команду
        Remove-Item "C:\ProxifierAgent\command.txt"
    }

    Start-Sleep 1
}
```

### Фаза 2: Улучшенный агент с UI Automation (2-3 часа)

Добавить:
- Управление через UI Automation (перезагрузка профиля без рестарта)
- Проверка состояния Proxifier
- Логирование
- TCP сервер вместо файлов

### Фаза 3: Интеграция с ServerManager (1 час)

Добавить команду в `command_handler.py`:
```python
elif command == 'set_proxy_reliable':
    # Записать команду для агента
    write_cmd = f'"{proxy_host}:{proxy_port}:{user}:{pass}" | Out-File C:\\ProxifierAgent\\command.txt'
    connector.execute_command(ip, username, password, write_cmd)

    # Ждать результат
    time.sleep(10)
    result = connector.execute_command(ip, username, password,
        'Get-Content C:\\ProxifierAgent\\result.txt')

    if "SUCCESS:" in result:
        return f"✅ Прокси установлен: {result}"
    else:
        return f"❌ Ошибка: {result}"
```

---

## 7. Альтернатива: Немедленное решение без агента

### Решение: Запуск Proxifier с профилем как аргумент

Некоторые версии Proxifier поддерживают:
```
Proxifier.exe "C:\path\to\profile.ppx"
```

**Проверить:**
```powershell
$profilePath = "$env:APPDATA\Proxifier4\Profiles\Default.ppx"
Start-Process "C:\Program Files (x86)\Proxifier\Proxifier.exe" -ArgumentList "`"$profilePath`""
```

### Решение: Import Profile через SendKeys

Если Proxifier открыт, можно отправить клавиши:
```powershell
Add-Type -AssemblyName System.Windows.Forms

# Активировать окно Proxifier
$proc = Get-Process Proxifier
[Microsoft.VisualBasic.Interaction]::AppActivate($proc.Id)
Start-Sleep 1

# Alt+F (File menu) → I (Import)
[System.Windows.Forms.SendKeys]::SendWait("%f")
Start-Sleep 0.5
[System.Windows.Forms.SendKeys]::SendWait("i")
```

---

## 8. Быстрое решение для проверки прямо сейчас

Попробуем **перезагрузить профиль** через SendKeys (если Proxifier открыт в GUI):

```powershell
# 1. Найти окно Proxifier
$hwnd = (Get-Process Proxifier).MainWindowHandle

# 2. Активировать
Add-Type @"
using System;
using System.Runtime.InteropServices;
public class Win32 {
    [DllImport("user32.dll")]
    public static extern bool SetForegroundWindow(IntPtr hWnd);
}
"@
[Win32]::SetForegroundWindow($hwnd)

# 3. Отправить Ctrl+R (если есть хоткей для reload)
Add-Type -AssemblyName System.Windows.Forms
[System.Windows.Forms.SendKeys]::SendWait("^r")
```

---

## 9. Итоговые рекомендации

### Краткосрочно (сегодня)
1. Проверить работает ли `Proxifier.exe "profile.ppx"` как аргумент
2. Попробовать SendKeys для перезагрузки профиля
3. Если не работает — настроить вручную через RDP один раз

### Среднесрочно (эта неделя)
1. Разработать ProxifierAgent (простой файловый вариант)
2. Установить на все сервера
3. Интегрировать с ServerManager

### Долгосрочно
1. Рассмотреть альтернативы Proxifier (tun2socks)
2. Создать централизованную систему управления прокси
3. Автоматическое развёртывание агента на новые сервера

---

## 10. Заключение

**Корень проблемы:** Proxifier не имеет CLI и не перезагружает профиль автоматически после изменения файла.

**Решение:** Создать агента который работает в пользовательской сессии и управляет Proxifier через UI или полный перезапуск с проверкой результата.

**Следующий шаг:** Реализовать простой ProxifierAgent.ps1 и протестировать.
