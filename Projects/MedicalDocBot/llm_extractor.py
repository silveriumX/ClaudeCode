"""
Извлечение структурированных полей из OCR-текста через LLM (GPT-4o-mini).

Отправляет распознанный текст медицинского документа в OpenAI API,
получает JSON с заполненными полями для таблицы.
"""
import json
import logging
from dataclasses import dataclass, asdict
from typing import Optional

import config

logger = logging.getLogger(__name__)

# Модель: gpt-4.1-mini — быстрая, точная, дешёвая ($0.40/$1.60 за 1M токенов)
# Обычная (не reasoning) модель — поддерживает temperature, response_format
_MODEL = "gpt-4.1-mini"

# Системный промпт для извлечения полей
_SYSTEM_PROMPT = """\
Ты — медицинский ассистент. Тебе дают OCR-текст медицинского документа.
Твоя задача — извлечь из него структурированные данные и вернуть JSON.

Правила:
- Если поле не удаётся определить из текста, оставь пустую строку "".
- Не выдумывай данные. Только то, что реально есть в тексте.
- Дату документа ищи в тексте (не дату загрузки). Формат: ДД.ММ.ГГГГ.
- Название документа — краткое, понятное человеку (2-5 слов).
  Примеры: "Заключение хирурга", "Анализ крови общий", "УЗИ брюшной полости",
  "Направление на госпитализацию", "Выписка из стационара".
- Тип документа — одно из: Заключение, Анализ, Выписка, Направление, Рецепт,
  Справка, Протокол, Консультация, Осмотр, УЗИ, МРТ, КТ, Рентген, ЭКГ, Другое.
- Врач — ФИО или "Фамилия И.О." врача, если указан.
- Пациент — ФИО пациента, если указано.
- Клиника — полное название учреждения.
- Направление — медицинская специализация или область тела
  (Хирургия, ЛОР, Кардиология, Урология и т.д.).
- Диагноз — основной диагноз, если указан (включая код МКБ, если есть).
- Краткое содержание — 1-2 предложения о сути документа.
- Ключевые показатели — числовые результаты анализов, если есть (показатель: значение).
- Рекомендации — что рекомендовано пациенту (кратко).

Ответь ТОЛЬКО валидным JSON (без markdown-обёртки) с этими полями:
{
  "title": "",
  "doc_type": "",
  "document_date": "",
  "doctor": "",
  "patient": "",
  "clinic": "",
  "direction": "",
  "diagnosis": "",
  "summary": "",
  "key_indicators": "",
  "recommendations": ""
}"""


@dataclass
class ExtractedFields:
    """Поля, извлечённые из OCR-текста через LLM."""
    title: str = ""
    summary: str = ""
    document_date: str = ""
    doc_type: str = ""
    doctor: str = ""
    patient: str = ""
    clinic: str = ""
    direction: str = ""
    diagnosis: str = ""
    key_indicators: str = ""
    recommendations: str = ""


def extract_fields_with_llm(ocr_text: str) -> Optional[ExtractedFields]:
    """
    Отправить OCR-текст в GPT-4o-mini, получить структурированные поля.

    Returns:
        ExtractedFields или None при ошибке.
    """
    api_key = getattr(config, "OPENAI_API_KEY", "") or ""
    if not api_key:
        logger.warning("OPENAI_API_KEY не задан — LLM-извлечение отключено")
        return None

    try:
        from openai import OpenAI
    except ImportError:
        logger.error("openai не установлен: pip install openai")
        return None

    # Обрезаем текст до ~4000 символов (достаточно для extraction, экономим токены)
    text = ocr_text[:4000] if len(ocr_text) > 4000 else ocr_text

    try:
        client = OpenAI(api_key=api_key)
        response = client.chat.completions.create(
            model=_MODEL,
            messages=[
                {"role": "system", "content": _SYSTEM_PROMPT},
                {"role": "user", "content": f"OCR-текст документа:\n\n{text}"},
            ],
            temperature=0.1,
            max_tokens=800,
            response_format={"type": "json_object"},
        )

        raw = response.choices[0].message.content
        if not raw:
            logger.warning("LLM вернул пустой ответ")
            return None

        # Модель может обернуть JSON в ```json ... ``` — убираем
        cleaned = raw.strip()
        if cleaned.startswith("```"):
            # Убираем первую строку (```json) и последнюю (```)
            lines = cleaned.splitlines()
            lines = [ln for ln in lines if not ln.strip().startswith("```")]
            cleaned = "\n".join(lines)
        data = json.loads(cleaned)
        fields = ExtractedFields(
            title=_s(data.get("title")),
            summary=_s(data.get("summary")),
            document_date=_s(data.get("document_date")),
            doc_type=_s(data.get("doc_type")),
            doctor=_s(data.get("doctor")),
            patient=_s(data.get("patient")),
            clinic=_s(data.get("clinic")),
            direction=_s(data.get("direction")),
            diagnosis=_s(data.get("diagnosis")),
            key_indicators=_s(data.get("key_indicators")),
            recommendations=_s(data.get("recommendations")),
        )

        logger.info(
            "LLM extraction: title=%r, type=%r, direction=%r",
            fields.title, fields.doc_type, fields.direction,
        )
        return fields

    except json.JSONDecodeError as e:
        logger.error("LLM вернул невалидный JSON: %s", e)
        return None
    except Exception as e:
        logger.exception("Ошибка LLM extraction: %s", e)
        return None


def _s(value) -> str:
    """Безопасно привести к строке, None -> ''."""
    if value is None:
        return ""
    return str(value).strip()
