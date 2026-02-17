"""
Скрипт для замены print с [DEBUG] на logger.debug в sheets.py
"""
import re

# Читаем файл
with open('C:/Users/Admin/Documents/Cursor/Projects/FinanceBot/sheets.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Заменяем print(f"[DEBUG] ...") на logger.debug(f"...")
content = re.sub(r'print\(f"\[DEBUG\] (.*?)"\)', r'logger.debug(f"\1")', content)

# Заменяем print(f"ERROR: ...") на logger.error(f"...")
content = re.sub(r'print\(f"ERROR: (.*?)"\)', r'logger.error(f"\1")', content)

# Заменяем print(f"OK: ...") на logger.info(f"...")
content = re.sub(r'print\(f"OK: (.*?)"\)', r'logger.info(f"\1")', content)

# Сохраняем
with open('C:/Users/Admin/Documents/Cursor/Projects/FinanceBot/sheets.py', 'w', encoding='utf-8') as f:
    f.write(content)

print("OK: Заменено print на logger")
print("  - DEBUG -> logger.debug()")
print("  - ERROR -> logger.error()")
print("  - OK -> logger.info()")
