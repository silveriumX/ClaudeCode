"""
OCR через Google Cloud Vision API.
Распознаёт текст из изображений; для PDF конвертирует первую страницу.
Возвращает полный текст и извлечённые поля (дата документа, тип, клиника и т.д.).
"""
import logging
import os
import re
from dataclasses import dataclass, field
from typing import Optional

import config

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Credentials
# ---------------------------------------------------------------------------

def _get_vision_credentials():
    """Service Account для Vision API (тот же файл, что для Drive/Sheets)."""
    path = getattr(config, "GOOGLE_SERVICE_ACCOUNT_FILE", None) or "service_account_medical.json"
    if path and os.path.isfile(path):
        from google.oauth2.service_account import Credentials
        return Credentials.from_service_account_file(path)
    return None


# ---------------------------------------------------------------------------
# OCR
# ---------------------------------------------------------------------------

def ocr_image_bytes(image_bytes: bytes, mime_type: str = "image/jpeg") -> Optional[str]:
    """
    Отправить изображение в Cloud Vision API, получить полный текст.
    Поддерживает image/* и application/pdf (первые 5 страниц).
    Returns: полный текст или None.
    """
    try:
        from google.cloud import vision
    except ImportError:
        logger.error("google-cloud-vision не установлен: pip install google-cloud-vision")
        return None

    creds = _get_vision_credentials()
    if not creds:
        logger.error("Vision: нет credentials (service account)")
        return None

    client = vision.ImageAnnotatorClient(credentials=creds)

    if mime_type and mime_type.lower() == "application/pdf":
        return _ocr_pdf(client, image_bytes)

    image = vision.Image(content=image_bytes)
    # DOCUMENT_TEXT_DETECTION лучше для документов (сохраняет структуру)
    response = client.document_text_detection(image=image)

    if response.error.message:
        logger.error("Vision API error: %s", response.error.message)
        return None

    annotation = response.full_text_annotation
    if not annotation:
        if response.text_annotations:
            raw = response.text_annotations[0].description
            if raw:
                result = _format_and_clean(raw)
                logger.info("Vision: распознано %d символов (text_annotations)", len(result))
                return result
        logger.info("Vision: текст не распознан")
        return None

    # Собираем текст по блокам и параграфам для красивого форматирования
    formatted = _format_from_annotation(annotation)
    if not formatted:
        logger.info("Vision: текст не распознан")
        return None

    logger.info("Vision: распознано %d символов (форматировано)", len(formatted))
    return formatted


def _format_from_annotation(annotation) -> str:
    """
    Форматировать текст по блокам и параграфам из full_text_annotation.
    Каждый блок — отдельный абзац; параграфы внутри блока через перенос строки.
    Убирает мусорные строки (короткие обрывки, UI-элементы).
    """
    paragraphs = []
    for page in annotation.pages:
        for block in page.blocks:
            block_lines = []
            for paragraph in block.paragraphs:
                words = []
                for word in paragraph.words:
                    word_text = "".join(s.text for s in word.symbols)
                    words.append(word_text)
                line = " ".join(words)
                if line.strip():
                    block_lines.append(line.strip())
            if block_lines:
                paragraphs.append("\n".join(block_lines))

    # Склеиваем блоки двойным переносом (абзацы)
    raw_text = "\n\n".join(paragraphs)
    return _format_and_clean(raw_text)


def _format_and_clean(text: str) -> str:
    """
    Очистить текст от мусорных строк:
    - Убрать строки из 1-2 символов (обрывки OCR)
    - Убрать типичные UI-элементы (Яндекс.Карты, кнопки и т.п.)
    - Убрать множественные пустые строки
    """
    # UI-мусор, который Vision подхватывает с экрана
    _TRASH_PATTERNS = {
        "яндекс.карты", "яндекс . карты", "google maps", "2gis",
        "пожалуйста , оставьте отзыв", "пожалуйста, оставьте отзыв",
        "помогите другим найти", "врачакиру", "врачу", "ВРАЧ",
    }

    lines = text.splitlines()
    cleaned = []
    for line in lines:
        stripped = line.strip()
        # Пропускаем пустые строки (сохраняем один пустой для абзацев)
        if not stripped:
            if cleaned and cleaned[-1] != "":
                cleaned.append("")
            continue
        # Пропускаем строки из 1-2 символов (обрывки)
        if len(stripped) <= 2:
            continue
        # Пропускаем UI-мусор
        if stripped.lower() in _TRASH_PATTERNS:
            continue
        # Пропускаем строки, которые состоят только из имени/фамилии обрывков (одно слово < 7 символов)
        # если они идут подряд — это часто OCR-артефакты разбитого текста
        cleaned.append(stripped)

    # Убираем завершающие пустые строки
    while cleaned and cleaned[-1] == "":
        cleaned.pop()

    return "\n".join(cleaned)


def _ocr_pdf(client, pdf_bytes: bytes) -> Optional[str]:
    """OCR для PDF через batch_annotate_files (до 5 страниц)."""
    from google.cloud import vision

    input_config = vision.InputConfig(
        content=pdf_bytes,
        mime_type="application/pdf",
    )
    feature = vision.Feature(type_=vision.Feature.Type.DOCUMENT_TEXT_DETECTION)
    request = vision.AnnotateFileRequest(
        input_config=input_config,
        features=[feature],
        pages=[1, 2, 3, 4, 5],  # первые 5 страниц
    )
    response = client.batch_annotate_files(requests=[request])

    paragraphs = []
    for file_resp in response.responses:
        for page_resp in file_resp.responses:
            if page_resp.error.message:
                logger.error("Vision PDF page error: %s", page_resp.error.message)
                continue
            annotation = page_resp.full_text_annotation
            if annotation:
                page_text = _format_from_annotation(annotation)
                if page_text:
                    paragraphs.append(page_text)

    full_text = "\n\n---\n\n".join(paragraphs)  # разделитель между страницами
    if full_text:
        logger.info("Vision PDF: распознано %d символов", len(full_text))
    else:
        logger.info("Vision PDF: текст не распознан")
    return full_text or None


# ---------------------------------------------------------------------------
# Извлечение полей из распознанного текста
# ---------------------------------------------------------------------------

@dataclass
class ExtractedFields:
    """Поля, извлечённые из OCR-текста."""
    title: str = ""             # Умное название документа
    summary: str = ""           # Краткое содержание
    document_date: str = ""     # Дата документа
    doc_type: str = ""          # Тип (Заключение, Анализ, ...)
    doctor: str = ""            # ФИО врача / специалист
    patient: str = ""           # ФИО пациента
    clinic: str = ""            # Клиника / учреждение
    direction: str = ""         # Направление (часть тела / тема)
    diagnosis: str = ""         # Диагноз
    key_indicators: str = ""    # Ключевые показатели
    recommendations: str = ""   # Рекомендации


# ---------------------------------------------------------------------------
# Регулярные выражения и справочники
# ---------------------------------------------------------------------------

# Дата: DD.MM.YYYY, DD/MM/YYYY, DD-MM-YYYY
_DATE_RE = re.compile(r'\b(\d{1,2}[./\-]\d{1,2}[./\-]\d{2,4})\b')

# Типы документов (приоритет — порядок в списке)
_DOC_TYPES = [
    ("заключение", "Заключение"),
    ("выписка", "Выписка"),
    ("выписной эпикриз", "Выписной эпикриз"),
    ("протокол операции", "Протокол операции"),
    ("протокол", "Протокол"),
    ("направление", "Направление"),
    ("рецепт", "Рецепт"),
    ("справка", "Справка"),
    ("консультация", "Консультация"),
    ("осмотр", "Осмотр"),
    ("результат анализ", "Результат анализов"),
    ("анализ", "Анализ"),
    ("узи", "УЗИ"),
    ("мрт", "МРТ"),
    ("рентген", "Рентген"),
    ("экг", "ЭКГ"),
    ("эндоскопия", "Эндоскопия"),
    ("гистолог", "Гистология"),
    ("цитолог", "Цитология"),
    ("биопсия", "Биопсия"),
]

# Специальности врачей (для определения направления, если нет прямых ключевых слов)
_SPECIALTIES = [
    ("хирург", "Хирургия"),
    ("онколог", "Онкология"),
    ("терапевт", "Терапия"),
    ("кардиолог", "Кардиология"),
    ("невролог", "Неврология"),
    ("ортопед", "Ортопедия"),
    ("офтальмолог", "Офтальмология"),
    ("окулист", "Офтальмология"),
    ("лор", "ЛОР"),
    ("отоларинголог", "ЛОР"),
    ("уролог", "Урология"),
    ("гинеколог", "Гинекология"),
    ("дерматолог", "Дерматология"),
    ("эндокринолог", "Эндокринология"),
    ("гастроэнтеролог", "Гастроэнтерология"),
    ("пульмонолог", "Пульмонология"),
    ("проктолог", "Проктология"),
    ("стоматолог", "Стоматология"),
    ("аллерголог", "Аллергология"),
    ("ревматолог", "Ревматология"),
    ("психиатр", "Психиатрия"),
    ("психотерапевт", "Психотерапия"),
    ("нефролог", "Нефрология"),
    ("гематолог", "Гематология"),
    ("инфекционист", "Инфекционные болезни"),
    ("анестезиолог", "Анестезиология"),
    ("реаниматолог", "Реаниматология"),
    ("флеболог", "Флебология"),
    ("маммолог", "Маммология"),
    ("сосудист", "Сосудистая хирургия"),
]

# Направления (темы здоровья)
_DIRECTIONS = [
    ("ринопласт", "Ринопластика"),
    ("септопласт", "Септопластика"),
    ("нос", "ЛОР / Нос"),
    ("перегородк", "ЛОР / Нос"),
    ("позвоноч", "Позвоночник"),
    ("грыж", "Грыжа"),
    ("спин", "Позвоночник"),
    ("колен", "Колени / Суставы"),
    ("сустав", "Колени / Суставы"),
    ("мениск", "Колени / Суставы"),
    ("геморро", "Проктология"),
    ("зуб", "Стоматология"),
    ("имплант", "Стоматология"),
    ("родинк", "Дерматология"),
    ("меланом", "Онкология / Дерматология"),
    ("щитовид", "Эндокринология"),
    ("диабет", "Эндокринология"),
    ("серд", "Кардиология"),
    ("давлен", "Кардиология"),
    ("желуд", "Гастроэнтерология"),
    ("кишечник", "Гастроэнтерология"),
    ("печен", "Гастроэнтерология"),
    ("почк", "Нефрология / Урология"),
    ("глаз", "Офтальмология"),
    ("зрен", "Офтальмология"),
    ("ухо", "ЛОР"),
    ("горл", "ЛОР"),
    ("лёгк", "Пульмонология"),
    ("бронх", "Пульмонология"),
    ("аллерг", "Аллергология"),
    ("витамин", "Анализы"),
    ("гемоглобин", "Анализы крови"),
    ("лейкоцит", "Анализы крови"),
    ("холестерин", "Анализы крови"),
    ("гормон", "Анализы / Эндокринология"),
    ("кров", "Анализы крови"),
    ("мочев", "Анализы мочи"),
    ("онкомаркер", "Онкология"),
    ("химиотерап", "Онкология"),
]

# ФИО врача
_DOCTOR_RE = re.compile(
    r'(?:врач|доктор|специалист|хирург|терапевт|консультант)[:\s]*'
    r'([А-ЯЁ][а-яё]+\s+[А-ЯЁ][а-яё]*(?:\s+[А-ЯЁ][а-яё]*)?)',
    re.IGNORECASE,
)
# Паттерн ФИО в конце документа: "Фамилия И.О." или "Фамилия Имя Отчество, врач-..."
_DOCTOR_SIGN_RE = re.compile(
    r'([А-ЯЁ][а-яё]+\s+[А-ЯЁ]\.\s*[А-ЯЁ]\.?)[\s,]*(?:врач|хирург|терапевт|доктор)',
    re.IGNORECASE,
)

# ФИО пациента
_PATIENT_RE = re.compile(
    r'(?:пациент|больной|ФИО|ф\.и\.о|фамилия)[:\s]*'
    r'([А-ЯЁ][а-яё]+\s+[А-ЯЁ][а-яё]*(?:\s+[А-ЯЁ][а-яё]*)?)',
    re.IGNORECASE,
)

# Клиники / лаборатории
_CLINIC_RE = re.compile(
    r'(?:клиника|больница|госпиталь|лаборатория|мед\.?\s*центр|поликлиника|'
    r'центр(?:альн\w*)?|диспансер|санаторий|институт|'
    r'инвитро|гемотест|helix|хеликс|cmd|ситилаб|kdl|'
    r'ООО|ЗАО|АО)\s*[«"]?([^«»"\n]{3,60})',
    re.IGNORECASE,
)

# Диагноз
_DIAGNOSIS_RE = re.compile(
    r'(?:диагноз|ds|д[иі]агн)[.:\s]*([^\n]{5,150})',
    re.IGNORECASE,
)

# Рекомендации
_RECOMMEND_RE = re.compile(
    r'((?:рекомендовано|рекомендуется|рекомендации|назначен[оиа]|'
    r'контроль|повторить|повторный|'
    r'через\s+\d+\s*(?:мес|нед|дн|год))[^\n]{0,150})',
    re.IGNORECASE,
)


def extract_fields(text: str) -> ExtractedFields:
    """Извлечь структурированные поля из OCR-текста."""
    fields = ExtractedFields()
    if not text:
        return fields

    text_lower = text.lower()
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]

    # --- Тип документа ---
    for keyword, label in _DOC_TYPES:
        if keyword in text_lower:
            fields.doc_type = label
            break

    # --- Направление (тема здоровья) ---
    for keyword, label in _DIRECTIONS:
        if keyword in text_lower:
            fields.direction = label
            break

    # Если направление не найдено, определяем по специальности врача
    if not fields.direction:
        for keyword, label in _SPECIALTIES:
            if keyword in text_lower:
                fields.direction = label
                break

    # --- Умное название документа ---
    # Формат: "{Тип}: {Направление}" или первая значимая строка
    fields.title = _build_smart_title(fields.doc_type, fields.direction, lines)

    # --- Краткое содержание (первые строки, до ~250 символов) ---
    summary_lines = []
    summary_len = 0
    for ln in lines[:10]:
        if summary_len + len(ln) > 250:
            break
        summary_lines.append(ln)
        summary_len += len(ln)
    fields.summary = " | ".join(summary_lines) if summary_lines else ""

    # --- Дата документа ---
    dates = _DATE_RE.findall(text)
    if dates:
        fields.document_date = dates[0]

    # --- Врач ---
    m = _DOCTOR_RE.search(text)
    if m:
        fields.doctor = m.group(1).strip()[:80]
    else:
        m = _DOCTOR_SIGN_RE.search(text)
        if m:
            fields.doctor = m.group(1).strip()[:80]

    # --- Пациент ---
    m = _PATIENT_RE.search(text)
    if m:
        fields.patient = m.group(1).strip()[:80]

    # --- Клиника ---
    m = _CLINIC_RE.search(text)
    if m:
        fields.clinic = m.group(0).strip()[:80]

    # --- Диагноз ---
    m = _DIAGNOSIS_RE.search(text)
    if m:
        fields.diagnosis = m.group(1).strip()[:200]

    # --- Ключевые показатели (если похоже на анализы) ---
    if any(kw in text_lower for kw in ("результат", "анализ", "норм", "референ", "показател")):
        indicator_re = re.compile(r'^(.{5,40}?)\s+([\d.,]+)\s', re.MULTILINE)
        indicators = indicator_re.findall(text)
        if indicators:
            fields.key_indicators = "; ".join(
                f"{name.strip()}: {val}" for name, val in indicators[:8]
            )

    # --- Рекомендации ---
    recs = _RECOMMEND_RE.findall(text)
    if recs:
        fields.recommendations = "; ".join(r.strip() for r in recs[:5])

    return fields


def _build_smart_title(doc_type: str, direction: str, lines: list) -> str:
    """Составить умное название документа на основе типа, направления и текста."""
    parts = []
    if doc_type:
        parts.append(doc_type)
    if direction:
        parts.append(direction)

    if parts:
        title = " - ".join(parts)
        # Если заголовок слишком общий (только тип), попробуем добавить контекст
        if len(parts) == 1 and lines:
            # Берём первую значимую строку (не дату, не короткую)
            for ln in lines[:5]:
                if len(ln) > 10 and not _DATE_RE.match(ln):
                    title = f"{parts[0]}: {ln[:80]}"
                    break
        return title[:120]

    # Если ничего не определилось — первая значимая строка
    for ln in lines[:5]:
        if len(ln) > 10:
            return ln[:120]
    return "Медицинский документ"
