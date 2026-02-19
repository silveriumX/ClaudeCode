# /python-project-init — Инициализация Python проекта

Настраивает полную инфраструктуру для нового Python проекта:
venv, task runner, pytest, gitignore.

## Когда вызывать
- При старте нового Python проекта
- Когда в проекте нет venv, тестов, task runner'а
- По запросу: "инициализируй проект", "настрой тест-инфраструктуру", "/python-project-init"

## Алгоритм выполнения

### 1. Определить корень проекта
Найти директорию проекта (где будет src/ или основной код).

### 2. Создать venv
```bash
python -m venv .venv
```

### 3. Установить базовые пакеты
```bash
.venv/Scripts/pip install pytest==7.4.* pytest-asyncio==0.21.* invoke
# Если Telegram-бот:
.venv/Scripts/pip install python-telegram-bot==21.7
# Если Google Sheets:
.venv/Scripts/pip install gspread google-auth
```

**КРИТИЧНО:** pytest-asyncio НЕ выше 0.21.x — на 0.25+ 330 падений с PTB.

### 4. Создать pyproject.toml

```toml
[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]
pythonpath = [".", "src"]
markers = [
    "integration: требует реальных API",
    "security: тесты безопасности/авторизации",
]
filterwarnings = [
    "ignore::pytest.PytestCollectionWarning",
]
```

### 5. Создать tests/conftest.py

```python
"""Shared fixtures для всего проекта."""
import sys
import pytest

# Исключить legacy-тесты из автосборки pytest (если есть)
collect_ignore: list[str] = []

# ── Event loop (Windows fix для pytest-asyncio 0.21.x) ────────────────────────
@pytest.fixture(scope="session")
def event_loop_policy():
    if sys.platform == "win32":
        import asyncio
        return asyncio.WindowsSelectorEventLoopPolicy()
    return None
```

Добавлять проект-специфичные fixtures по мере необходимости.

### 6. Создать tasks.py (invoke — работает на Windows)

```python
import os
import sys
from pathlib import Path
from invoke import task

os.environ.setdefault("PYTHONUTF8", "1")
os.environ.setdefault("PYTHONIOENCODING", "utf-8")

ROOT = Path(__file__).parent
PY = str(ROOT / ".venv" / ("Scripts" if sys.platform == "win32" else "bin") / "python")

@task
def install(c):
    """Установить зависимости."""
    c.run(f'"{PY}" -m pip install -r requirements.txt')

@task
def test(c):
    """Запустить pytest тесты."""
    c.run(f'"{PY}" -m pytest tests/ -v')

@task
def lint(c):
    """Проверить код (если установлен ruff/flake8)."""
    c.run(f'"{PY}" -m ruff check src/ tests/ || echo "ruff не установлен"')
```

Дополнять task'ами под проект (deploy, logs и т.д.).

### 7. Создать Makefile (для Linux/VPS)

```makefile
SHELL := bash
.SHELLFLAGS := -eu -o pipefail -c

PY := .venv/bin/python

.PHONY: help venv install test

help:
	@grep -E '^[a-z]+:' Makefile | sed 's/:.*//' | tr '\n' ' '

venv:
	python3 -m venv .venv

install: venv
	$(PY) -m pip install -r requirements.txt

test:
	$(PY) -m pytest tests/ -v
```

### 8. Добавить .venv/ в .gitignore

```
.venv/
__pycache__/
*.pyc
.pytest_cache/
```

### 9. Создать tests/__init__.py (пустой)

## Результат

После выполнения скилла:
```
project/
├── .venv/              — изолированное окружение
├── pyproject.toml      — конфиг pytest
├── tasks.py            — inv test, inv deploy (Windows)
├── Makefile            — make test, make deploy (Linux)
├── tests/
│   ├── __init__.py
│   └── conftest.py     — базовые fixtures
└── .gitignore          — .venv/ исключён
```

**Проверить:**
```bash
.venv/Scripts/python -m invoke test   # Windows
make test                              # Linux
```

## Правила

- `.venv/` ВСЕГДА в корне проекта (не глобально)
- pytest-asyncio НЕ выше 0.21.x если используется PTB
- `PYTHONUTF8=1` через `os.environ.setdefault` (не через `env=` в c.run)
- collect_ignore только в conftest.py (не в pyproject.toml)
