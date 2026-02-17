# Настройка автоматического GitHub бэкапа

## Шаг 1: Создать приватный репозиторий на GitHub

1. Зайди на https://github.com/new
2. Repository name: `cursor-workspace` (или любое название)
3. Description: `Личная рабочая папка`
4. **Private** ✓ (важно!)
5. **НЕ ставь галочки** на README, .gitignore, license
6. Create repository

GitHub покажет команды для подключения — не закрывай страницу.

---

## Шаг 2: Подключить папку к GitHub

Открой PowerShell в папке Cursor:

```powershell
cd C:\Users\Admin\Documents\Cursor

# Инициализировать репозиторий
git init

# Добавить remote (замени USERNAME на свой GitHub username)
git remote add origin https://github.com/USERNAME/cursor-workspace.git

# Первый коммит
git add .
git commit -m "Initial commit"

# Установить ветку main
git branch -M main

# Запушить
git push -u origin main
```

При запросе логина/пароля:
- Username: твой GitHub username
- Password: **Personal Access Token** (не обычный пароль!)

---

## Шаг 3: Создать Personal Access Token

GitHub больше не принимает пароли для Git. Нужен токен:

1. https://github.com/settings/tokens
2. Generate new token → **Classic**
3. Note: `Cursor workspace`
4. Expiration: **No expiration** (или 1 год)
5. Scopes: ✓ **repo** (все галочки под repo)
6. Generate token
7. **Скопируй токен** (покажется только один раз!)

### Сохрани токен локально

```powershell
# Сохранить креды чтобы не вводить каждый раз
git config --global credential.helper wincred
```

При следующем `git push` введи:
- Username: твой GitHub username
- Password: **токен** (не пароль!)

Windows сохранит и больше не будет спрашивать.

---

## Шаг 4: Протестировать автокоммит

```powershell
cd C:\Users\Admin\Documents\Cursor
.\auto_commit.ps1
```

Должно закоммитить и запушить изменения.

---

## Шаг 5: Настроить автозапуск (каждые 30 минут)

### Открой Task Scheduler
```powershell
taskschd.msc
```

### Создай задачу:

**General:**
- Name: `Auto GitHub Backup`

**Triggers:**
- New... → Daily
- Repeat task every: **30 minutes**
- For a duration of: **Indefinitely**

**Actions:**
- Program/script: `powershell.exe`
- Arguments: `-ExecutionPolicy Bypass -File "C:\Users\Admin\Documents\Cursor\auto_commit.ps1"`

**Conditions:**
- Убрать "Start only if on AC power"

**Settings:**
- Allow task to be run on demand: ✓

---

## Готово!

Теперь:
- Каждые 30 минут автоматически коммит + пуш
- Все файлы сохраняются в приватном репозитории
- `CREDENTIALS.md` и приватные данные исключены через `.gitignore`

---

## Полезные команды

```powershell
# Запустить вручную
.\auto_commit.ps1

# Посмотреть историю
git log --oneline

# Посмотреть что будет сохранено
git status

# Клонировать на другом компе
git clone https://github.com/USERNAME/cursor-workspace.git
```

---

## Восстановление данных

Если что-то случится с компом:
1. Установи Cursor
2. `git clone https://github.com/USERNAME/cursor-workspace.git`
3. Все файлы на месте
