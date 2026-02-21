"""
Утилиты для форматирования данных
"""
from src import config


def escape_md(text: str) -> str:
    """Экранировать спецсимволы Markdown V1 в пользовательском тексте.

    Применять ко всем полям из user_data или Google Sheets перед вставкой
    в сообщения с parse_mode='Markdown'. Поля с _ * ` [ иначе ломают разметку.
    """
    if not text:
        return text if text is not None else ''
    for char in ('_', '*', '`', '[', ']', '(', ')'):
        text = text.replace(char, f'\\{char}')
    return text


def format_amount(amount, currency: str = None) -> str:
    """
    Форматировать сумму с пробелом как разделителем тысяч.
    Для USDT десятичные знаки не округляются (сохраняются как ввёл пользователь).

    Безопасно обрабатывает None, пустые строки и невалидные значения.

    Args:
        amount: Сумма (число или строка).
        currency: Валюта (config.CURRENCY_USDT и т.д.). Если USDT — без округления.

    Examples:
        >>> format_amount(1000)
        '1 000'
        >>> format_amount(1000.5)
        '1 001'
        >>> format_amount(123.456789, config.CURRENCY_USDT)
        '123.456789'
        >>> format_amount(None)
        '0'
    """
    try:
        if isinstance(amount, str):
            amount_val = float(amount) if amount else 0.0
        elif amount is None:
            amount_val = 0.0
        else:
            amount_val = float(amount)

        # USDT: сохранять все знаки после запятой (без округления)
        if currency == config.CURRENCY_USDT:
            s = f"{amount_val:.10f}".rstrip("0").rstrip(".")
            return s

        return f"{amount_val:,.0f}".replace(",", " ")
    except (ValueError, TypeError):
        return "0"


def format_currency_symbol(currency: str) -> str:
    """
    Получить символ валюты

    Examples:
        >>> format_currency_symbol('RUB')
        '₽'
    """
    symbols = {
        config.CURRENCY_RUB: '₽',
        config.CURRENCY_BYN: 'BYN',
        config.CURRENCY_KZT: '₸',
        config.CURRENCY_USDT: 'USDT',
        config.CURRENCY_CNY: '¥'
    }
    return symbols.get(currency, '₽')


def get_currency_symbols_dict() -> dict:
    """Получить словарь символов валют (для обратной совместимости)"""
    return {
        config.CURRENCY_RUB: '₽',
        config.CURRENCY_BYN: 'BYN',
        config.CURRENCY_KZT: '₸',
        config.CURRENCY_USDT: 'USDT',
        config.CURRENCY_CNY: '¥'
    }
