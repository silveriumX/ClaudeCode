# Transaction Categorizer

> Автоматическая категоризация банковских транзакций: правила по ИНН + паттерны по назначению + GPT fallback.
> Обучается на подтверждённых пользователем категориях.

---

## Когда использовать

- Нужно присвоить категорию транзакции из банковской выписки
- Разрабатываешь AccountingBot или финансовый отчёт
- Настраиваешь правила категоризации для конкретных контрагентов

---

## Таксономия категорий

Категории сопоставлены с FinanceBot для единообразия отчётности:

```python
CATEGORIES = {
    # Обязательные платежи
    "Налоги":               "Платежи в ФНС, ПФР, ФСС, страховые взносы, ЕНС",
    "Банковские расходы":   "Комиссии банка, обслуживание счёта, эквайринг",

    # Операционные расходы
    "Зарплата":             "Выплаты сотрудникам по трудовым договорам",
    "Подрядчики":           "ИП и самозанятые, договоры ГПХ",
    "Аренда":               "Офис, склад, оборудование",
    "Закупки":              "Товары для перепродажи, сырьё",
    "Логистика":            "Доставка, транспорт, фулфилмент",
    "Маркетинг":            "Реклама, продвижение, PR",
    "Сертификация":         "Сертификаты соответствия, экспертизы",
    "IT и сервисы":         "SaaS, хостинг, домены, ПО",
    "Офис":                 "Хознужды, канцелярия, уборка",

    # Доходы
    "Выручка":              "Оплаты от покупателей за товары/услуги",
    "Прочие доходы":        "Возвраты, компенсации, прочие поступления",

    # Нейтральные
    "Внутренний перевод":   "Переводы между счетами и юрлицами группы",
    "Дивиденды/вывод":      "Вывод прибыли собственнику",

    # Неопределённое
    "Прочее":               "Не удалось определить категорию",
}
```

---

## Реализация категоризатора

```python
from dataclasses import dataclass
from decimal import Decimal
from typing import Optional
import re
import logging

logger = logging.getLogger(__name__)


@dataclass
class CategoryResult:
    category: str        # Название категории
    confidence: float    # Уверенность от 0.0 до 1.0
    method: str          # 'inn_rule' | 'pattern' | 'gpt' | 'default'
    reason: str          # Объяснение для пользователя


# ============================================================
# СЛОЙ 1: Правила по ИНН контрагента (confidence = 1.0)
# Хранятся в Google Sheets: лист "Контрагенты" колонки ИНН|Категория
# ============================================================

# Системные ИНН — всегда одна категория
SYSTEM_INN_RULES: dict[str, str] = {
    "7727406020": "Налоги",          # ФНС России / Казначейство России
    "7730176610": "Налоги",          # ФСС РФ
    "7703363868": "Налоги",          # ПФР
    "7736050003": "Налоги",          # Социальный фонд России
}

# Маски ИНН по первым цифрам (УФК = Казначейство)
INN_PREFIX_RULES: dict[str, str] = {
    # Все УФК (Управление федерального казначейства) — налоги
}


def categorize_by_inn(inn: Optional[str], category_cache: dict[str, str]) -> Optional[CategoryResult]:
    """
    Категоризация по ИНН контрагента.

    Args:
        inn: ИНН контрагента
        category_cache: Словарь {inn: category} загруженный из листа "Контрагенты" в Sheets

    Returns:
        CategoryResult если правило найдено, иначе None
    """
    if not inn:
        return None

    # Системные ИНН (захардкожены)
    if inn in SYSTEM_INN_RULES:
        return CategoryResult(
            category=SYSTEM_INN_RULES[inn],
            confidence=1.0,
            method="inn_rule",
            reason=f"Системный ИНН {inn} (ФНС/ФСС/ПФР)",
        )

    # Пользовательский кэш из Google Sheets
    if inn in category_cache:
        return CategoryResult(
            category=category_cache[inn],
            confidence=1.0,
            method="inn_rule",
            reason=f"Известный контрагент (ИНН {inn})",
        )

    return None


# ============================================================
# СЛОЙ 2: Паттерны по назначению платежа (confidence = 0.85-0.95)
# ============================================================

# Паттерны: (regex_pattern, category, confidence, description)
PURPOSE_PATTERNS: list[tuple[str, str, float, str]] = [
    # Налоги — очень высокая уверенность
    (r"единый\s+налоговый\s+платеж|ЕНС|НДС\s+\d+/\d+|страховые\s+взносы|НДФЛ", "Налоги", 0.95, "ЕНС/НДС/взносы"),
    (r"налог\s+на\s+прибыль|налог\s+на\s+имущество|земельный\s+налог|транспортный\s+налог", "Налоги", 0.93, "Прямые налоги"),
    (r"уплата.{0,20}налог|платеж.{0,20}бюджет|в\s+счет\s+уплаты", "Налоги", 0.88, "Бюджетный платёж"),

    # Банковские расходы
    (r"комиссия\s+за\s+(обслуживание|проведение|операци|эквайр|снятие)", "Банковские расходы", 0.97, "Комиссия банка"),
    (r"ежемесячное\s+обслуживание|плата\s+за\s+обслуживание", "Банковские расходы", 0.97, "Обслуживание счёта"),
    (r"интернет.банк|смс.информирование|выпуск\s+карты", "Банковские расходы", 0.90, "Банковский сервис"),

    # Зарплата
    (r"заработная\s+плата|зарплата|выплата\s+за\s+(январ|феврал|март|апрел|май|июн|июл|август|сентябр|октябр|ноябр|декабр)", "Зарплата", 0.92, "Выплата зарплаты"),
    (r"аванс.{0,10}зарплат|выплата.{0,10}сотрудник", "Зарплата", 0.88, "Выплата сотруднику"),

    # Аренда
    (r"аренда.{0,20}(офис|помещени|склад|земл|оборудован)", "Аренда", 0.92, "Аренда"),
    (r"за\s+аренду|арендная\s+плата|арендный\s+платеж", "Аренда", 0.90, "Аренда"),
    (r"коммунальн|электроэнерги|водоснабжени|теплоснабжени", "Аренда", 0.82, "Коммунальные услуги"),

    # Закупки товаров
    (r"за\s+товар|оплата\s+товар|поставка\s+товар|в\s+т\.ч\.\s+НДС", "Закупки", 0.88, "Оплата товаров"),
    (r"по\s+договору.{0,30}(поставк|купли-продажи)", "Закупки", 0.85, "Договор поставки"),

    # Логистика
    (r"доставка|транспортировк|перевозк|логистик|фулфилмент|складск", "Логистика", 0.87, "Логистика"),

    # Маркетинг
    (r"реклам|маркетинг|продвижени|SEO|контекстн", "Маркетинг", 0.87, "Реклама"),

    # Сертификация
    (r"сертификат|соответстви|экспертиз|испытани|декларац", "Сертификация", 0.90, "Сертификация"),

    # IT
    (r"хостинг|домен|лицензи.{0,10}(ПО|программ)|SaaS|подписк.{0,10}сервис", "IT и сервисы", 0.88, "IT сервисы"),

    # Внутренние переводы — ВАЖНО: приоритет по ключевым словам
    (r"перевод\s+между\s+счетами|внутрифирменный\s+перевод|перевод\s+собственных", "Внутренний перевод", 0.95, "Внутренний перевод"),
    (r"пополнение\s+(корпоративного\s+)?счёта|зачисление\s+на\s+счёт", "Внутренний перевод", 0.85, "Внутренний перевод"),

    # Выручка (для входящих платежей)
    (r"за\s+(товар|услуги|работы|поставку)|оплата\s+по\s+(счету|договору)", "Выручка", 0.80, "Оплата за товары/услуги"),

    # Дивиденды
    (r"дивиденд|распределение\s+прибыли", "Дивиденды/вывод", 0.93, "Дивиденды"),
]

_COMPILED_PATTERNS = [
    (re.compile(pattern, re.IGNORECASE), category, confidence, reason)
    for pattern, category, confidence, reason in PURPOSE_PATTERNS
]


def categorize_by_purpose(
    purpose: str,
    counterparty_name: str,
    direction: str,
) -> Optional[CategoryResult]:
    """
    Категоризация по назначению платежа и имени контрагента.

    Args:
        purpose: Назначение платежа из выписки
        counterparty_name: Название контрагента
        direction: 'IN' или 'OUT'

    Returns:
        CategoryResult если паттерн найден, иначе None
    """
    text = f"{purpose} {counterparty_name}".lower()

    best_match = None
    best_confidence = 0.0

    for compiled, category, confidence, reason in _COMPILED_PATTERNS:
        if compiled.search(text):
            # Входящие: не применяем категории расходов с высокой уверенностью
            if direction == "IN" and category not in ("Выручка", "Прочие доходы", "Внутренний перевод"):
                confidence *= 0.6  # Снижаем уверенность для расходных категорий у приходов

            if confidence > best_confidence:
                best_confidence = confidence
                best_match = (category, reason)

    if best_match and best_confidence >= 0.75:
        return CategoryResult(
            category=best_match[0],
            confidence=best_confidence,
            method="pattern",
            reason=f"Паттерн: {best_match[1]}",
        )

    return None


# ============================================================
# СЛОЙ 3: GPT fallback (confidence = 0.65-0.85)
# ============================================================

async def categorize_by_gpt(
    purpose: str,
    counterparty_name: str,
    amount: Decimal,
    direction: str,
    openai_client,
) -> CategoryResult:
    """
    Категоризация через GPT-4o-mini как последний fallback.

    Args:
        openai_client: Инициализированный AsyncOpenAI клиент

    Returns:
        CategoryResult с category и confidence от GPT
    """
    categories_list = "\n".join(f"- {k}: {v}" for k, v in CATEGORIES.items())

    prompt = f"""Классифицируй банковскую транзакцию российского бизнеса.

Направление: {"ПРИХОД" if direction == "IN" else "РАСХОД"}
Сумма: {amount:,.2f} руб.
Контрагент: {counterparty_name}
Назначение платежа: {purpose}

Доступные категории:
{categories_list}

Ответь СТРОГО в формате JSON:
{{"category": "Название категории", "confidence": 0.75, "reason": "Краткое объяснение"}}

Правила:
- confidence от 0.0 до 1.0 (насколько уверен в выборе)
- Если явно не понятно — используй "Прочее" с низкой confidence
- "Внутренний перевод" только если контрагент — то же юрлицо/ИП или явно написано "перевод между счетами"
"""

    try:
        response = await openai_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1,
            max_tokens=150,
            response_format={"type": "json_object"},
        )
        result = response.choices[0].message.content
        import json
        data = json.loads(result)

        category = data.get("category", "Прочее")
        if category not in CATEGORIES:
            category = "Прочее"

        return CategoryResult(
            category=category,
            confidence=float(data.get("confidence", 0.65)),
            method="gpt",
            reason=data.get("reason", "GPT категоризация"),
        )

    except Exception as e:
        logger.warning(f"GPT категоризация не удалась: {e}")
        return CategoryResult(
            category="Прочее",
            confidence=0.0,
            method="default",
            reason="Ошибка GPT, требует ручной разметки",
        )


# ============================================================
# ГЛАВНАЯ ФУНКЦИЯ: Полный пайплайн категоризации
# ============================================================

async def categorize_transaction(
    purpose: str,
    counterparty_name: str,
    counterparty_inn: Optional[str],
    amount: Decimal,
    direction: str,
    inn_cache: dict[str, str],
    openai_client=None,
    confidence_threshold: float = 0.80,
) -> CategoryResult:
    """
    Полный пайплайн категоризации: ИНН → Паттерн → GPT.

    Args:
        purpose: Назначение платежа
        counterparty_name: Название контрагента
        counterparty_inn: ИНН контрагента
        amount: Сумма транзакции
        direction: 'IN' или 'OUT'
        inn_cache: Словарь {inn: category} из листа "Контрагенты"
        openai_client: OpenAI клиент (если None — пропускается GPT слой)
        confidence_threshold: Порог уверенности для авто-принятия (по умолчанию 0.80)

    Returns:
        CategoryResult с category, confidence, method
        Если confidence < threshold → нужно запросить подтверждение у пользователя
    """
    # Слой 1: ИНН
    result = categorize_by_inn(counterparty_inn, inn_cache)
    if result and result.confidence >= confidence_threshold:
        return result

    # Слой 2: Паттерны
    result = categorize_by_purpose(purpose, counterparty_name, direction)
    if result and result.confidence >= confidence_threshold:
        return result

    # Слой 3: GPT (если доступен)
    if openai_client:
        result = await categorize_by_gpt(
            purpose, counterparty_name, amount, direction, openai_client
        )
        return result

    # Fallback
    return CategoryResult(
        category="Прочее",
        confidence=0.0,
        method="default",
        reason="Не удалось определить категорию",
    )


def needs_confirmation(result: CategoryResult, threshold: float = 0.80) -> bool:
    """Нужно ли запросить подтверждение у пользователя."""
    return result.confidence < threshold


# ============================================================
# ОБУЧЕНИЕ: Сохранение подтверждённых категорий
# ============================================================

def update_inn_cache(
    sheets_manager,
    inn: str,
    counterparty_name: str,
    confirmed_category: str,
) -> None:
    """
    Сохранить подтверждённую категорию для ИНН в Google Sheets.
    Лист "Контрагенты": [ИНН, Название, Категория, Дата добавления]

    После этого следующие транзакции с тем же ИНН получат confidence=1.0
    без обращения к GPT.
    """
    from datetime import date
    sheets_manager.append_row(
        sheet_name="Контрагенты",
        row=[inn, counterparty_name, confirmed_category, date.today().isoformat()],
    )
    logger.info(f"ИНН {inn} ({counterparty_name}) → {confirmed_category} сохранён в Sheets")
```

---

## Интеграция в Telegram-бот

```python
# Использование в AccountingBot при импорте выписки
async def process_transactions_with_categorization(transactions, sheets, openai_client):
    inn_cache = sheets.get_inn_category_cache()  # {inn: category} из листа Контрагенты

    confirmed = []
    needs_review = []

    for tx in transactions:
        result = await categorize_transaction(
            purpose=tx.purpose,
            counterparty_name=tx.counterparty_name,
            counterparty_inn=tx.counterparty_inn,
            amount=tx.amount,
            direction=tx.direction,
            inn_cache=inn_cache,
            openai_client=openai_client,
        )

        if needs_confirmation(result):
            needs_review.append((tx, result))
        else:
            confirmed.append((tx, result))

    return confirmed, needs_review
```

---

## Порог уверенности

| confidence | Действие |
|-----------|---------|
| ≥ 0.90 | Авто-категоризация, записываем сразу |
| 0.75–0.89 | Авто с пометкой "проверь при случае" |
| < 0.75 | Запрашиваем подтверждение у пользователя |
| 0.0 | Обязательно нужна ручная разметка |

---

## Связанные скиллы

- `/bank-statement-parser` — Парсинг выписок (входные данные)
- `/bank-import-bot` — Telegram-бот (использует этот модуль)
- `/financial-journal-schema` — Куда записываются категоризированные данные
