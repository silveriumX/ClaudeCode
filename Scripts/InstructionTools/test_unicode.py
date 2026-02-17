#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Тест работы с Unicode/эмодзи на Windows.
Проверяет работу safe_console модуля.
"""
import sys
import logging
from pathlib import Path

# Добавляем корень репозитория в путь
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from Utils.safe_console import safe_print, configure_utf8_logging, safe_log, strip_emoji


def print_header(title: str):
    """Печатает заголовок раздела"""
    safe_print("\n" + "=" * 70)
    safe_print(f"  {title}")
    safe_print("=" * 70)


def test_encoding_info():
    """Показывает информацию о текущей кодировке"""
    print_header("ИНФОРМАЦИЯ О КОДИРОВКЕ")
    safe_print(f"Платформа: {sys.platform}")
    safe_print(f"Python версия: {sys.version}")
    safe_print(f"stdout encoding: {sys.stdout.encoding}")
    safe_print(f"stderr encoding: {sys.stderr.encoding}")
    safe_print(f"filesystem encoding: {sys.getfilesystemencoding()}")


def test_safe_print():
    """Тестирует safe_print с различными эмодзи"""
    print_header("ТЕСТ safe_print()")

    test_cases = [
        "✅ Успех",
        "❌ Ошибка",
        "⚠️ Предупреждение",
        "ℹ️ Информация",
        "💰 Финансы: 1000 руб",
        "📝 Заметка",
        "📊 Статистика",
        "🚀 Деплой запущен",
        "🔧 Конфигурация",
        "🤖 Бот активен",
        "Микс: ✅❌⚠️💰📝🚀",
    ]

    for i, test in enumerate(test_cases, 1):
        safe_print(f"{i}. {test}")


def test_strip_emoji():
    """Тестирует замену эмодзи на ASCII"""
    print_header("ТЕСТ strip_emoji()")

    test_cases = [
        "Деплой завершён ✅",
        "Ошибка подключения ❌",
        "Статус: ✅ Работает",
        "💰 Баланс: 5000₽ 📊",
        "🚀 Запуск → ✅ Успех",
    ]

    for original in test_cases:
        stripped = strip_emoji(original)
        safe_print(f"Оригинал: {original}")
        safe_print(f"После:    {stripped}")
        safe_print("")


def test_logging():
    """Тестирует логирование с эмодзи"""
    print_header("ТЕСТ LOGGING")

    log_file = Path(__file__).parent / "test_unicode.log"

    # Настройка logger
    logger = configure_utf8_logging(str(log_file), level=logging.DEBUG)

    safe_print(f"Логи записываются в: {log_file}")
    safe_print("")

    # Различные уровни логирования
    safe_log(logger, logging.DEBUG, "🔍 DEBUG: поиск данных")
    safe_log(logger, logging.INFO, "ℹ️ INFO: информационное сообщение")
    safe_log(logger, logging.WARNING, "⚠️ WARNING: предупреждение")
    safe_log(logger, logging.ERROR, "❌ ERROR: ошибка обработки")
    safe_log(logger, logging.CRITICAL, "🔥 CRITICAL: критическая ошибка")

    # Логирование с параметрами
    user_id = 12345
    amount = 1000
    safe_log(logger, logging.INFO, "💰 Пользователь %d пополнил счёт на %d руб", user_id, amount)

    safe_print("")
    safe_print(f"✅ Логи успешно записаны в {log_file.name}")


def test_real_world_scenario():
    """Имитирует реальный сценарий использования"""
    print_header("РЕАЛЬНЫЙ СЦЕНАРИЙ: ДЕПЛОЙ СКРИПТ")

    # Имитация деплоя
    safe_print("🚀 Начинаем деплой...")
    safe_print("")

    steps = [
        ("📁 Проверка файлов", True),
        ("🔧 Загрузка конфигурации", True),
        ("🌐 Подключение к VPS", True),
        ("📤 Загрузка файлов", True),
        ("🔄 Перезапуск сервисов", True),
        ("✅ Проверка статуса", True),
    ]

    for step, success in steps:
        safe_print(f"  {step}...", end=" ")
        if success:
            safe_print("✅")
        else:
            safe_print("❌")

    safe_print("")
    safe_print("✅ Деплой завершён успешно!")


def test_mixed_content():
    """Тестирует смешанный контент (кириллица + эмодзи)"""
    print_header("ТЕСТ: КИРИЛЛИЦА + ЭМОДЗИ")

    safe_print("Привет! 👋")
    safe_print("Статус бота: ✅ Активен")
    safe_print("Баланс: 💰 5000₽")
    safe_print("Заявки: 📝 10 шт")
    safe_print("Ошибок: ❌ 0")
    safe_print("Система работает нормально ✅")


def test_error_handling():
    """Тестирует обработку ошибок"""
    print_header("ТЕСТ: ОБРАБОТКА ОШИБОК")

    try:
        safe_print("Попытка вывода с эмодзи ✅")
        safe_print("Если видите этот текст - всё работает!")
    except Exception as e:
        safe_print(f"❌ Ошибка: {e}")
    else:
        safe_print("✅ Ошибок не обнаружено")


def main():
    """Главная функция - запускает все тесты"""
    safe_print("\n")
    safe_print("╔" + "═" * 68 + "╗")
    safe_print("║" + " " * 15 + "ТЕСТ МОДУЛЯ safe_console.py" + " " * 25 + "║")
    safe_print("╚" + "═" * 68 + "╝")

    try:
        test_encoding_info()
        test_safe_print()
        test_strip_emoji()
        test_logging()
        test_real_world_scenario()
        test_mixed_content()
        test_error_handling()

        # Итог
        print_header("ИТОГ")
        safe_print("✅ Все тесты пройдены успешно!")
        safe_print("")
        safe_print("Если вы видите [OK], [ERROR] вместо эмодзи - это нормально.")
        safe_print("Модуль safe_console автоматически заменяет эмодзи на ASCII.")
        safe_print("")
        safe_print("Проверьте файл test_unicode.log - в нём должны быть все логи.")

    except Exception as e:
        safe_print(f"\n❌ Ошибка при выполнении тестов: {e}")
        import traceback
        safe_print(traceback.format_exc())
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
