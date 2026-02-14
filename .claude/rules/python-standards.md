---
description: Стандарты Python кода в проекте
paths:
  - "**/*.py"
---

# Python Code Standards

> Единые стандарты кодирования для всех Python файлов в проекте

---

## Импорты

### Порядок импортов:

```python
# 1. Стандартная библиотека
import json
import logging
from pathlib import Path
from typing import Optional, Dict, List

# 2. Сторонние библиотеки
import requests
from telegram import Update, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler

# 3. Локальные импорты
from .config import settings
from .utils import load_config
```

### Правила:
- Группы разделены пустой строкой
- Алфавитный порядок внутри группы
- `import` перед `from ... import ...`
- Нет `import *`

---

## Работа с путями

### ИСПОЛЬЗУЙ `pathlib.Path`:

```python
from pathlib import Path

# Путь к текущему файлу
current_file = Path(__file__)

# Путь к папке проекта
project_root = Path(__file__).parent.parent

# Путь к данным
data_path = project_root / "Data" / "config.json"

# Проверка существования
if data_path.exists():
    with open(data_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

# Создание папки
output_dir = project_root / "output"
output_dir.mkdir(parents=True, exist_ok=True)

# Список файлов
py_files = list(project_root.glob("**/*.py"))
```

### НЕ ИСПОЛЬЗУЙ `os.path`:

```python
# ПЛОХО
import os
path = os.path.join(os.path.dirname(__file__), "data", "config.json")
os.makedirs("output", exist_ok=True)
```

---

## Логирование

### Настройка в начале скрипта:

```python
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('app.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)
```

### Уровни логирования:

```python
logger.debug("Обработка пользователя ID: 12345")
logger.info("Бот запущен успешно")
logger.warning("API ключ скоро истечёт")
logger.error("Не удалось отправить сообщение пользователю")
logger.critical("База данных недоступна")
```

### Логирование исключений:

```python
try:
    result = risky_operation()
except ValueError as e:
    logger.exception(f"Ошибка валидации: {e}")
except Exception as e:
    logger.exception(f"Неожиданная ошибка: {e}")
    raise
```

### Что НЕ логировать:

```python
# НЕЛЬЗЯ - пароли и токены
logger.info(f"API key: {api_key}")

# НЕЛЬЗЯ - личные данные
logger.info(f"User: {username}, email: {email}")

# МОЖНО - без чувствительных данных
logger.info(f"API запрос выполнен успешно")
logger.info(f"User ID {user_id} аутентифицирован")
```

---

## Чтение конфигурации

### Загрузка JSON конфигов:

```python
from pathlib import Path
import json
from typing import Dict, Any

def load_config(config_name: str) -> Dict[str, Any]:
    """Загрузить конфиг из Data/"""
    config_path = Path(__file__).parent.parent / "Data" / f"{config_name}.json"

    if not config_path.exists():
        raise FileNotFoundError(f"Конфиг не найден: {config_path}")

    with open(config_path, 'r', encoding='utf-8') as f:
        return json.load(f)
```

### Переменные окружения (.env):

```python
from pathlib import Path
from dotenv import load_dotenv
import os

env_path = Path(__file__).parent / ".env"
load_dotenv(env_path)

BOT_TOKEN = os.getenv("BOT_TOKEN")
API_KEY = os.getenv("API_KEY")
DEBUG_MODE = os.getenv("DEBUG_MODE", "false").lower() == "true"
```

---

## Обработка ошибок

### Специфичные исключения:

```python
# Ловим конкретные исключения
try:
    data = json.load(f)
except json.JSONDecodeError as e:
    logger.error(f"Невалидный JSON: {e}")
    return None
except FileNotFoundError:
    logger.error(f"Файл не найден: {filepath}")
    return None
```

### Обработка HTTP запросов:

```python
import requests
from requests.exceptions import Timeout, RequestException

def fetch_data(url: str) -> Optional[dict]:
    """Безопасный HTTP запрос"""
    try:
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        return response.json()
    except Timeout:
        logger.error(f"Timeout при запросе к {url}")
        return None
    except requests.exceptions.HTTPError as e:
        logger.error(f"HTTP ошибка: {e.response.status_code}")
        return None
    except RequestException as e:
        logger.exception(f"Ошибка запроса: {e}")
        return None
```

---

## Type Hints

```python
from typing import List, Dict, Optional, Tuple, Union, TypedDict, Literal

def process_users(
    user_ids: List[int],
    settings: Dict[str, str],
    timeout: Optional[int] = None
) -> Tuple[bool, str]:
    """Обработать пользователей"""
    return True, "Успешно обработано"

class Account(TypedDict):
    name: str
    email: str
    api_key: str
    balance: float

Status = Literal["active", "inactive", "pending"]
```

---

## Именование

- **Переменные и функции:** `snake_case`
- **Классы:** `PascalCase`
- **Константы:** `UPPER_SNAKE_CASE`
- **Приватные:** `_protected_attr`, `__private_attr`

---

## Структура функций

### Docstrings (Google Style):

```python
def send_notification(
    user_id: int,
    message: str,
    priority: str = "normal"
) -> bool:
    """
    Отправить уведомление пользователю.

    Args:
        user_id: Telegram ID пользователя
        message: Текст сообщения
        priority: Приоритет ("normal", "high", "urgent")

    Returns:
        True если сообщение отправлено успешно

    Raises:
        ValueError: Если priority не входит в разрешённые значения
    """
```

### Размер функций:
- Функция делает одну вещь
- Сложная логика разбита на функции
- Не более ~50 строк на функцию

---

## Чеклист для Python файла

- [ ] Импорты в правильном порядке
- [ ] Используется `pathlib.Path` вместо `os.path`
- [ ] Настроено логирование
- [ ] Есть type hints для функций
- [ ] Есть docstrings для публичных функций
- [ ] Обработка исключений специфична
- [ ] Нет хардкоженных паролей/токенов
- [ ] Файлы открываются через `with`
- [ ] Константы в UPPER_SNAKE_CASE

---

## Полезные инструменты

```bash
# Форматирование
pip install black && black script.py
pip install isort && isort script.py

# Проверка типов
pip install mypy && mypy script.py

# Линтеры
pip install flake8 && flake8 script.py
```
