# Работа с Excel и таблицами в Cursor

> Способы просмотра, редактирования и автоматизации работы с .xlsx/.xls и CSV в рамках Cursor.

---

## 1. Excel MCP Server (рекомендуется для AI)

**Что даёт:** Агент в Cursor может по твоей просьбе читать и изменять Excel-файлы: листы, ячейки, формулы, форматирование, сводные таблицы, графики. Microsoft Excel не нужен.

**Уже добавлено в проект:** в `.cursor/mcp.json` настроен сервер `excel` с транспортом stdio.

### Установка зависимости

Сервер запускается через **uvx** (пакет [uv](https://github.com/astral-sh/uv)). Если `uv` ещё не установлен:

**Вариант A — установить uv (рекомендуется):**
```powershell
# Windows (PowerShell)
irm https://astral.sh/uv/install.ps1 | iex
```
После установки перезапусти Cursor. Команда `uvx excel-mcp-server stdio` будет доступна.

**Вариант B — без uv (только pip):**

1. Установить пакет:
   ```powershell
   pip install excel-mcp-server
   ```
2. В `.cursor/mcp.json` заменить блок `excel` на:
   ```json
   "excel": {
     "command": "python",
     "args": ["-m", "excel_mcp_server", "stdio"]
   }
   ```

### Использование

После перезапуска Cursor (или перезагрузки MCP) в чате можно писать, например:

- «Прочитай лист "Выплаты" из `Projects/Финансовая система/Выплаты xRocket - рубли .xlsx` и покажи первые 20 строк»
- «В файле Журнал_операций___МН.xlsx добавь на лист X строку с датой 12.02.2026, суммой 5000, категорией Y»
- «Создай сводную таблицу по столбцу "Категория" в файле Z»

Путь к файлу указывается в запросе; при stdio сервер работает с любыми путями в рамках рабочей папки.

**Требования:** Python 3.10+

---

## 2. Расширение Omegasheets (просмотр и правка в редакторе)

**Что даёт:** Открытие .xlsx/.xls и CSV прямо в Cursor как таблицу: просмотр, редактирование, формулы, условное форматирование.

**Как подключить:**

1. Открыть панель расширений: `Ctrl+Shift+X`.
2. Найти **Omegasheets** (или **Omega Sheets**).
3. Установить.
4. Открыть любой .xlsx/.xls или .csv — файл откроется в виде таблицы.

Подходит, когда нужно визуально смотреть или править ячейки без запросов к агенту.

---

## 3. CSV в Cursor

- **Просмотр/редактирование:** расширение **Edit CSV** или **Omegasheets** (CSV поддерживается).
- **В коде:** читать/писать через Python (`csv`, `pandas.read_csv`) или в чате попросить агента «прочитай этот CSV и сделай X».

---

## 4. Python-скрипты (openpyxl / pandas)

В проекте уже есть зависимости с `openpyxl` (например, `Scripts/mcp-document-processor`, `Projects/DocChat`). Для своих скриптов:

```python
# Чтение
import pandas as pd
df = pd.read_excel("path/to/file.xlsx", sheet_name="Лист1")

# или openpyxl для тонкого контроля
from openpyxl import load_workbook
wb = load_workbook("path/to/file.xlsx", read_only=True, data_only=True)
ws = wb["Имя листа"]
for row in ws.iter_rows(min_row=1, max_row=100, values_only=True):
    print(row)
```

Удобно для автоматизации, пайплайнов и одноразовых задач по твоим файлам в `Projects/Финансовая система/`.

---

## Кратко

| Задача | Способ |
|--------|--------|
| Попросить AI прочитать/изменить Excel | **Excel MCP** (уже в mcp.json, нужен uv или pip) |
| Открыть .xlsx как таблицу в редакторе | Расширение **Omegasheets** |
| Работа с CSV в редакторе | **Edit CSV** или **Omegasheets** |
| Свои скрипты по .xlsx | **pandas** / **openpyxl** в Python |

---

**Связанные файлы:**
- Конфиг MCP: `.cursor/mcp.json`
- Проект с примерами Excel: `Projects/Финансовая система/`
- Документация по типам файлов: `Documentation/Cursor/ОПТИМИЗАЦИЯ_РАБОТЫ_С_AI.md` (раздел про *.xlsx)
