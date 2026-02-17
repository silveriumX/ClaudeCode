# 🚀 Быстрый старт: Командная работа в 5 шагов

## Для Администратора

### 1️⃣ Создать командный репозиторий (2 минуты)
```
https://github.com/new
→ Repository name: team-workspace
→ Private ✓
→ Create repository
```

### 2️⃣ Перенести проекты (5 минут)
```powershell
cd C:\Users\Admin\Documents\
mkdir TeamCursor
cd TeamCursor
git clone https://github.com/USERNAME/team-workspace.git
cd team-workspace

# Копировать проекты
Copy-Item "C:\Users\Admin\Documents\Cursor\CreatorBot" -Destination . -Recurse
Copy-Item "C:\Users\Admin\Documents\Cursor\VoiceBot" -Destination . -Recurse

git add .
git commit -m "Initial setup"
git push origin main
```

### 3️⃣ Защитить конфиденциальные данные (2 минуты)
Создать `.gitignore`:
```
*CREDENTIALS*.md
*.env
Зарплаты/
Финансы/
```

### 4️⃣ Добавить сотрудников (1 минута на человека)
```
https://github.com/USERNAME/team-workspace
→ Settings → Collaborators → Add people
→ Выбрать роль: Write (для разработчиков)
```

### 5️⃣ Настроить защиту main (2 минуты)
```
Settings → Branches → Add rule
→ Branch name: main
→ ✓ Require pull request before merging
→ ✓ Require approvals: 1
```

---

## Для Сотрудника

### 1️⃣ Принять приглашение
Проверь email от GitHub → Accept invitation

### 2️⃣ Клонировать репозиторий
```powershell
cd C:\Projects
git clone https://github.com/USERNAME/team-workspace.git
cd team-workspace
```

### 3️⃣ Настроить credentials
```powershell
# Скопировать шаблон
Copy-Item CREDENTIALS.example.md CREDENTIALS.md

# Заполнить своими данными в Cursor
cursor CREDENTIALS.md
```

### 4️⃣ Первая задача - создать ветку
```powershell
git checkout -b feature/my-first-task
# Внести изменения в коде
git add .
git commit -m "feat: my first contribution"
git push origin feature/my-first-task
```

### 5️⃣ Создать Pull Request
```
На GitHub появится кнопка "Compare & pull request"
→ Описать что сделано
→ Create pull request
→ Дождаться review от админа
```

---

## 📖 Ежедневная работа

### Начало дня
```powershell
cd team-workspace
git checkout main
git pull origin main
git checkout -b feature/new-task
```

### Во время работы
```powershell
# Сохранить изменения
git add .
git commit -m "feat: описание изменения"

# Периодически пушить
git push origin feature/new-task
```

### Конец дня / задача готова
```powershell
# Запушить последние изменения
git push origin feature/new-task

# На GitHub:
# → Create Pull Request
# → Попросить review
```

---

## 🎯 Две папки в Cursor

### Вариант 1: Открывать отдельно (ПРОСТОЙ)

**Личная работа:**
```powershell
cd C:\Users\Admin\Documents\Cursor
cursor .
```

**Командная работа:**
```powershell
cd C:\Users\Admin\Documents\TeamCursor\team-workspace
cursor .
```

### Вариант 2: Одно окно (УДОБНЫЙ)

Создать `workspace.code-workspace`:
```json
{
  "folders": [
    {
      "name": "💼 Командное",
      "path": "C:\\Users\\Admin\\Documents\\TeamCursor\\team-workspace"
    },
    {
      "name": "🔒 Личное",
      "path": "C:\\Users\\Admin\\Documents\\Cursor"
    }
  ]
}
```

Открыть в Cursor: `File → Open Workspace from File`

**Важно:** Следи в какой папке делаешь коммиты!

---

## ⚡ Шпаргалка команд

### Базовые команды
```powershell
git status                    # Что изменилось
git log --oneline            # История коммитов
git branch                   # Список веток
git checkout main            # Переключиться на main
git pull origin main         # Обновить main
```

### Работа с ветками
```powershell
git checkout -b feature/name # Создать и переключиться
git branch -d feature/name   # Удалить локальную ветку
git push -d origin feature/name # Удалить удаленную ветку
```

### Отмена изменений
```powershell
git checkout -- file.py      # Отменить изменения в файле
git reset HEAD file.py       # Убрать из staged
git reset --soft HEAD~1      # Отменить последний коммит
```

### Конфликты
```powershell
git merge main               # Смержить main в свою ветку
# Решить конфликты в Cursor
git add .
git commit -m "merge: resolved conflicts"
```

---

## 🚨 Правила безопасности

### ✅ ВСЕГДА:
- Работай в отдельной ветке
- Используй понятные commit messages
- Делай `git pull` перед началом работы
- Проверяй `.gitignore` перед коммитом

### ❌ НИКОГДА:
- Не коммить пароли/токены/ключи
- Не пушить напрямую в `main`
- Не удалять чужой код без обсуждения
- Не коммить файлы >50MB

### 🆘 Если закоммитил credentials:
```powershell
# СРОЧНО!
git rm --cached CREDENTIALS.md
git commit -m "fix: remove credentials"
git push origin your-branch

# Сообщить админу
# Сменить все ключи/токены
```

---

## 📞 Получить помощь

1. **Проблемы с Git:**
   - Читай подробную инструкцию: `TEAM_GITHUB_SETUP.md`
   - Google: "git [твоя проблема]"
   - ChatGPT / Cursor Chat

2. **Проблемы с кодом:**
   - Создай Issue на GitHub
   - Напиши в командный чат
   - Попроси code review

3. **Не понятен workflow:**
   - Перечитай `TEAM_GITHUB_SETUP.md`
   - Попроси админа показать на примере

---

## ✅ Чеклист готовности

### Админ:
- [ ] Создан `team-workspace` репозиторий
- [ ] Добавлен `.gitignore`
- [ ] Проекты перенесены
- [ ] Сотрудники приглашены
- [ ] Защита `main` настроена
- [ ] README с инструкциями создан

### Сотрудник:
- [ ] GitHub аккаунт создан
- [ ] Приглашение принято
- [ ] Репозиторий клонирован
- [ ] CREDENTIALS.md настроен
- [ ] Тестовая ветка создана
- [ ] Первый PR отправлен

---

**Готово! Начинай работать 🎉**

Подробности: `TEAM_GITHUB_SETUP.md`
