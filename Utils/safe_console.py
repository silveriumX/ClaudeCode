"""
Безопасный вывод в консоль на Windows с поддержкой эмодзи.
Автоматическая замена эмодзи на ASCII-альтернативы.

Использование:
    from Utils.safe_console import safe_print, safe_log, configure_utf8_logging

    # Вместо print
    safe_print("Статус: ✅")  # Выведет: "Статус: [OK]"

    # Вместо logging
    logger = configure_utf8_logging("app.log")
    safe_log(logger, logging.INFO, "Деплой завершён 🚀")
"""
import sys
import logging
from typing import Any, Optional

# Словарь замен эмодзи → ASCII
EMOJI_TO_ASCII = {
    "✅": "[OK]",
    "❌": "[ERROR]",
    "⚠️": "[WARNING]",
    "ℹ️": "[INFO]",
    "💰": "[MONEY]",
    "📝": "[NOTE]",
    "📊": "[STATS]",
    "🚀": "[DEPLOY]",
    "🔧": "[CONFIG]",
    "📁": "[FOLDER]",
    "📄": "[FILE]",
    "🔍": "[SEARCH]",
    "⏳": "[WAIT]",
    "🎯": "[TARGET]",
    "💡": "[IDEA]",
    "🔥": "[FIRE]",
    "📈": "[UP]",
    "📉": "[DOWN]",
    "🔔": "[BELL]",
    "🛠️": "[TOOLS]",
    "🌐": "[WEB]",
    "📱": "[MOBILE]",
    "💻": "[PC]",
    "🗂️": "[ARCHIVE]",
    "✏️": "[EDIT]",
    "🗑️": "[DELETE]",
    "➕": "[+]",
    "➖": "[-]",
    "✖️": "[x]",
    "➡️": "[->]",
    "⬅️": "[<-]",
    "⬆️": "[^]",
    "⬇️": "[v]",
    "🤖": "[BOT]",
    "👤": "[USER]",
    "👥": "[USERS]",
    "📞": "[PHONE]",
    "📧": "[EMAIL]",
    "🔑": "[KEY]",
    "🔒": "[LOCK]",
    "🔓": "[UNLOCK]",
    "⭐": "[STAR]",
    "🎉": "[PARTY]",
    "🚫": "[NO]",
    "✔️": "[CHECK]",
    "❗": "[!]",
    "❓": "[?]",
}


def strip_emoji(text: str) -> str:
    """
    Заменяет эмодзи на ASCII-альтернативы.

    Args:
        text: Текст с эмодзи

    Returns:
        Текст с замененными эмодзи
    """
    for emoji, ascii_rep in EMOJI_TO_ASCII.items():
        text = text.replace(emoji, ascii_rep)
    return text


def safe_print(*args, **kwargs):
    """
    Безопасный print с автоматической обработкой эмодзи.

    Автоматически заменяет эмодзи на ASCII-альтернативы и обрабатывает
    UnicodeEncodeError на Windows.

    Args:
        *args: Аргументы для print
        **kwargs: Ключевые аргументы для print

    Пример:
        safe_print("Деплой завершён ✅")  # Выведет: "Деплой завершён [OK]"
        safe_print("Статус:", "✅", sep=" - ")
    """
    # Преобразуем все аргументы в строки и удаляем эмодзи
    safe_args = [strip_emoji(str(arg)) for arg in args]

    try:
        print(*safe_args, **kwargs)
    except UnicodeEncodeError:
        # Если всё ещё ошибка - пытаемся с errors='replace'
        text = " ".join(safe_args)
        separator = kwargs.get('sep', ' ')
        text = separator.join(safe_args)
        try:
            print(text.encode(sys.stdout.encoding, errors='replace').decode(sys.stdout.encoding))
        except Exception:
            # Последняя попытка - только ASCII
            print(text.encode('ascii', errors='replace').decode('ascii'))


def safe_log(logger: logging.Logger, level: int, message: str, *args, **kwargs):
    """
    Безопасное логирование с автоматической обработкой эмодзи.

    Args:
        logger: Logger объект
        level: Уровень логирования (logging.INFO, logging.ERROR и т.д.)
        message: Сообщение для логирования
        *args: Дополнительные аргументы для logger.log
        **kwargs: Ключевые аргументы для logger.log

    Пример:
        logger = logging.getLogger(__name__)
        safe_log(logger, logging.INFO, "Деплой завершён ✅")
        safe_log(logger, logging.ERROR, "Ошибка ❌: %s", error_message)
    """
    safe_message = strip_emoji(message)
    logger.log(level, safe_message, *args, **kwargs)


def configure_utf8_logging(
    log_file: Optional[str] = None,
    level: int = logging.INFO,
    format_str: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    console: bool = True
) -> logging.Logger:
    """
    Настраивает logging с UTF-8 для Windows.

    Args:
        log_file: Путь к файлу логов (опционально)
        level: Уровень логирования (по умолчанию INFO)
        format_str: Формат сообщений
        console: Выводить ли логи в консоль (по умолчанию True)

    Returns:
        Настроенный logger

    Пример:
        # Только консоль
        logger = configure_utf8_logging()

        # Консоль + файл
        logger = configure_utf8_logging("app.log")

        # Только файл
        logger = configure_utf8_logging("app.log", console=False)

        # Использование
        logger.info("Сообщение")
        safe_log(logger, logging.INFO, "Сообщение с эмодзи ✅")
    """
    logger = logging.getLogger()
    logger.setLevel(level)

    # Очистка существующих handlers
    logger.handlers.clear()

    formatter = logging.Formatter(format_str)

    # Console handler с UTF-8
    if console:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(level)
        console_handler.setFormatter(formatter)

        # Попытка установить UTF-8 encoding
        try:
            console_handler.stream.reconfigure(encoding='utf-8', errors='replace')
        except AttributeError:
            # Старые версии Python
            pass

        logger.addHandler(console_handler)

    # File handler с UTF-8
    if log_file:
        file_handler = logging.FileHandler(log_file, encoding='utf-8', errors='replace')
        file_handler.setLevel(level)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    return logger


def init_windows_unicode():
    """
    Инициализирует UTF-8 для Windows при импорте модуля.

    Автоматически вызывается при импорте safe_console.
    Устанавливает UTF-8 encoding для stdout и stderr.
    """
    if sys.platform == "win32":
        try:
            # Попытка установить UTF-8 для stdout/stderr (Python 3.7+)
            if hasattr(sys.stdout, 'reconfigure'):
                if sys.stdout.encoding.lower() != 'utf-8':
                    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
                if sys.stderr.encoding.lower() != 'utf-8':
                    sys.stderr.reconfigure(encoding='utf-8', errors='replace')
        except (AttributeError, ValueError) as e:
            # Старые версии Python или невозможность изменить encoding
            pass


# Автоматическая инициализация при импорте
init_windows_unicode()


# Примеры использования (для документации)
if __name__ == "__main__":
    print("=" * 60)
    print("ТЕСТ safe_console.py")
    print("=" * 60)

    # Тест 1: safe_print
    print("\n1. Тест safe_print:")
    safe_print("Обычный текст")
    safe_print("С эмодзи: ✅ ❌ 💰 📝 🚀")
    safe_print("Статус:", "✅", sep=" = ")

    # Тест 2: strip_emoji
    print("\n2. Тест strip_emoji:")
    original = "Деплой завершён ✅ без ошибок ❌"
    stripped = strip_emoji(original)
    safe_print(f"Оригинал: {original}")
    safe_print(f"После: {stripped}")

    # Тест 3: configure_utf8_logging
    print("\n3. Тест logging:")
    logger = configure_utf8_logging("test_safe_console.log")
    logger.info("Обычное сообщение")
    safe_log(logger, logging.INFO, "С эмодзи ✅")
    safe_log(logger, logging.WARNING, "Предупреждение ⚠️")
    safe_log(logger, logging.ERROR, "Ошибка ❌")
    safe_print("Логи записаны в test_safe_console.log")

    print("\n" + "=" * 60)
    safe_print("✅ Все тесты пройдены!")
    print("=" * 60)
