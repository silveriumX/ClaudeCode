---
name: unicode-fixer
description: Инструментарий и инструкции для исправления проблем с кодировкой UTF-8 и эмодзи в Python и PowerShell, особенно на Windows.
---

# Unicode & Emoji Fixer

## Быстрые фиксы

### Python (Windows Console Fix)
Если скрипт падает при `print()` с эмодзи:
```python
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
```

### Python (File Operations)
Всегда используй `pathlib` с явной кодировкой:
```python
from pathlib import Path
content = Path("file.md").read_text(encoding="utf-8")
Path("output.txt").write_text("Done", encoding="utf-8")
```

### PowerShell (Output Fix)
```powershell
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
```

---

## Диагностика

Если видишь ошибку:
`UnicodeEncodeError: 'charmap' codec can't encode characters in position...`

Это означает: Python пытается вывести UTF-8 символы (эмодзи/кириллицу) в консоль, настроенную на `cp1251` или `cp866`.

**Решение:**
1. Проверь `sys.stdout.encoding`
2. Используй `io.TextIOWrapper` для принудительного UTF-8
3. Убедись, что в `.env` нет скрытых символов в другой кодировке

---

## Правила для агента

При создании любого нового скрипта:
1. **Всегда** добавляй `encoding='utf-8'` в `open()`
2. **Всегда** проверяй платформу (`sys.platform == 'win32'`) и патчи `stdout`
3. **Никогда** не полагайся на системную кодировку по умолчанию

### Шаблон для начала скрипта на Windows:

```python
import sys, io

if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')
```
