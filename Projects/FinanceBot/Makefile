# FinanceBot Makefile
# На Linux/Mac: make test, make deploy, etc.
# На Windows Git Bash: используй tasks.py (inv test, inv deploy)
# Требует: make (на Linux уже есть, на Windows: scoop install make)

SHELL := bash
.SHELLFLAGS := -eu -o pipefail -c
.DEFAULT_GOAL := help

# Пути к Python в зависимости от ОС
ifeq ($(OS), Windows_NT)
    PY  := .venv/Scripts/python
    PIP := .venv/Scripts/pip
else
    PY  := .venv/bin/python
    PIP := .venv/bin/pip
endif

.PHONY: help venv install test test-block4 test-usdt deploy logs restart status clean

help:  ## Показать список команд
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## / \
	  {printf "  \033[36m%-15s\033[0m %s\n", $$1, $$2}' $(MAKEFILE_LIST)

# ── Окружение ──────────────────────────────────────────────────────────────────

venv: .venv  ## Создать виртуальное окружение

.venv:
	python3 -m venv .venv
	$(PIP) install --upgrade pip --quiet
	$(PIP) install -r requirements.txt --quiet
	$(PIP) install "pytest==7.4.*" "pytest-asyncio==0.21.*" invoke --quiet
	@echo "✅ .venv создан"

install: .venv  ## Обновить зависимости
	$(PIP) install -r requirements.txt --quiet
	@echo "✅ Зависимости установлены"

# ── Тесты ─────────────────────────────────────────────────────────────────────

test: .venv  ## Запустить ВСЕ тесты
	PYTHONUTF8=1 $(PY) -m pytest tests/ -v

test-block4: .venv  ## Тесты Block 4 (управление пользователями)
	PYTHONUTF8=1 $(PY) -m pytest tests/ -v -k "block4"

test-usdt: .venv  ## Тесты USDT платежей
	PYTHONUTF8=1 $(PY) tests/test_usdt_fixes.py

# ── VPS ────────────────────────────────────────────────────────────────────────

deploy: .venv  ## Задеплоить на VPS
	$(PY) vps_connect.py deploy

logs:  ## Смотреть логи бота на VPS (последние 50 строк)
	$(PY) vps_connect.py logs 50

errors:  ## Смотреть только ОШИБКИ на VPS
	$(PY) vps_connect.py errors 30

restart:  ## Перезапустить бот на VPS
	$(PY) vps_connect.py restart

status:  ## Статус бота на VPS (RAM, диск, uptime)
	$(PY) vps_connect.py status

# ── Утилиты ────────────────────────────────────────────────────────────────────

clean:  ## Удалить кэши Python
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -name "*.pyc" -delete 2>/dev/null || true
	rm -rf .pytest_cache .mypy_cache .ruff_cache
	@echo "✅ Кэши удалены"
