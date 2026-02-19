"""
FinanceBot task runner (invoke)
================================
Используется на Windows Git Bash где make может быть недоступен.

Установка: pip install invoke  (уже в .venv)
Запуск:    inv --list          — список команд
           inv test            — запустить тесты
           inv deploy          — задеплоить на VPS
           inv logs            — логи бота на VPS
"""
import os
import sys
from pathlib import Path

from invoke import task

# UTF-8 вывод на Windows — устанавливаем один раз при импорте модуля
os.environ.setdefault("PYTHONUTF8", "1")
os.environ.setdefault("PYTHONIOENCODING", "utf-8")

# Путь к Python внутри venv
ROOT = Path(__file__).parent
if sys.platform == "win32":
    PY = str(ROOT / ".venv" / "Scripts" / "python.exe")
else:
    PY = str(ROOT / ".venv" / "bin" / "python")


# ── Окружение ──────────────────────────────────────────────────────────────────

@task
def install(c):
    """Установить/обновить зависимости в .venv"""
    c.run(f'"{PY}" -m pip install -r requirements.txt --quiet')
    print("✅ Зависимости установлены")


# ── Тесты ─────────────────────────────────────────────────────────────────────

@task
def test(c):
    """Запустить ВСЕ тесты"""
    c.run(f'"{PY}" -m pytest tests/ -v')


@task
def test_block4(c):
    """Тесты Block 4 (новый pytest-формат, когда появятся)"""
    c.run(f'"{PY}" -m pytest tests/ -v -k "block4"')


@task
def test_block4_legacy(c):
    """Тесты Block 4 — legacy runner (текущие тесты)"""
    c.run(f'"{PY}" tests/test_block4_users.py')


@task
def test_usdt(c):
    """Тесты USDT — legacy runner"""
    c.run(f'"{PY}" tests/test_usdt_fixes.py')


@task
def test_legacy(c):
    """Запустить ВСЕ legacy-тесты (block4 + usdt)"""
    print("=== Block 4 ===")
    c.run(f'"{PY}" tests/test_block4_users.py')
    print("\n=== USDT ===")
    c.run(f'"{PY}" tests/test_usdt_fixes.py')


# ── VPS ────────────────────────────────────────────────────────────────────────

@task
def deploy(c):
    """Задеплоить код на VPS и перезапустить бота"""
    c.run(f'"{PY}" vps_connect.py deploy')


@task
def logs(c, n=50):
    """Смотреть логи бота на VPS (последние N строк, default=50)"""
    c.run(f'"{PY}" vps_connect.py logs {n}')


@task
def errors(c, n=30):
    """Смотреть только ОШИБКИ на VPS"""
    c.run(f'"{PY}" vps_connect.py errors {n}')


@task
def restart(c):
    """Перезапустить бот на VPS"""
    c.run(f'"{PY}" vps_connect.py restart')


@task
def status(c):
    """Статус бота на VPS (RAM, диск, uptime)"""
    c.run(f'"{PY}" vps_connect.py status')


# ── Утилиты ────────────────────────────────────────────────────────────────────

@task
def clean(c):
    """Удалить кэши Python"""
    c.run('find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true')
    c.run('find . -name "*.pyc" -delete 2>/dev/null || true')
    c.run('rm -rf .pytest_cache .mypy_cache 2>/dev/null || true')
    print("✅ Кэши удалены")
