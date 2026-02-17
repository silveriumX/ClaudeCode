# Интеграция с Google Docs

> **Важно:** Google Docs НЕ являются обычными текстовыми файлами. Их нельзя напрямую редактировать в Cursor как .md файлы.

---

## Варианты интеграции

### Вариант 1: Google Drive + Markdown (Рекомендуется)

Храните Markdown файлы в Google Drive, редактируйте в Cursor.

**Настройка:**

1. Установите [Google Drive для Windows](https://www.google.com/drive/download/)
2. Синхронизируйте папку с инструкциями
3. Откройте эту папку в Cursor

```
G:\Мой диск\Instructions\  ← Эту папку открываете в Cursor
├── server_setup.md
├── images/
│   └── step1.png
└── ...
```

**Преимущества:**
- Файлы синхронизируются автоматически
- Можно редактировать в Cursor как обычно
- Доступ с любого устройства через Google Drive

**Недостатки:**
- Это НЕ Google Docs, а обычные Markdown файлы в облаке

---

### Вариант 2: Экспорт Google Docs → Cursor → Импорт обратно

Workflow для работы с существующими Google Docs:

```
Google Doc (исходник)
    ↓ Скачать как .docx или PDF
Cursor (переработка)
    ↓ Конвертировать в нужный формат
Google Drive (результат)
    ↓ Загрузить или создать новый Google Doc
```

**Шаги:**

1. В Google Docs: Файл → Скачать → PDF или Microsoft Word (.docx)
2. В Cursor: Переработать через Claude
3. Загрузить результат в Google Drive

---

### Вариант 3: Google Docs API (Программный доступ)

Для автоматизации можно использовать Google Docs API.

**Установка:**

```bash
pip install google-api-python-client google-auth-httplib2 google-auth-oauthlib
```

**Пример скрипта для чтения Google Doc:**

```python
# scripts/google_docs_reader.py
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials

def read_google_doc(document_id: str, credentials_path: str) -> str:
    """Читает текст из Google Doc."""
    creds = Credentials.from_authorized_user_file(credentials_path)
    service = build('docs', 'v1', credentials=creds)

    document = service.documents().get(documentId=document_id).execute()

    text_content = []
    for element in document.get('body', {}).get('content', []):
        if 'paragraph' in element:
            for text_run in element['paragraph'].get('elements', []):
                if 'textRun' in text_run:
                    text_content.append(text_run['textRun']['content'])

    return ''.join(text_content)
```

**Ограничения:**
- Требует OAuth настройки
- Изображения извлекаются отдельно через Drive API
- Форматирование теряется при простом чтении

---

## Работа с изображениями

### Проблема

Google Docs хранит изображения внутри документа. При экспорте в PDF они сохраняются, но при экспорте в текст — теряются.

### Решение 1: Скачать как HTML

1. Файл → Скачать → Веб-страница (.html, в архиве)
2. В архиве будет папка `images/` со всеми изображениями
3. Используйте эти изображения в Markdown

### Решение 2: Скриншоты

Если изображений немного:
1. Откройте Google Doc
2. Сделайте скриншоты (Win+Shift+S)
3. Сохраните в папку `images/`

### Решение 3: Скрипт извлечения

```python
# Скачайте Google Doc как .docx, затем:
pip install python-docx

from docx import Document
from docx.opc.constants import RELATIONSHIP_TYPE as RT
import os

def extract_images_from_docx(docx_path: str, output_folder: str = "images"):
    """Извлекает изображения из .docx файла."""
    os.makedirs(output_folder, exist_ok=True)

    doc = Document(docx_path)

    for i, rel in enumerate(doc.part.rels.values()):
        if "image" in rel.target_ref:
            image_data = rel.target_part.blob
            ext = rel.target_ref.split('.')[-1]

            filename = f"image_{i+1}.{ext}"
            filepath = os.path.join(output_folder, filename)

            with open(filepath, 'wb') as f:
                f.write(image_data)

            print(f"Saved: {filename}")

# Использование:
# extract_images_from_docx("document.docx", "./images")
```

---

## Рекомендуемый Workflow

```
┌─────────────────────────────────────────────────────────┐
│                   ПОЛУЧЕНИЕ ДОКУМЕНТА                    │
├─────────────────────────────────────────────────────────┤
│                                                         │
│   Google Doc ──► Скачать как .docx ──► Локальный файл   │
│                                                         │
│   PDF ────────────────────────────────► Локальный файл   │
│                                                         │
└─────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────┐
│                 ИЗВЛЕЧЕНИЕ ИЗОБРАЖЕНИЙ                   │
├─────────────────────────────────────────────────────────┤
│                                                         │
│   .docx ──► extract_images_from_docx() ──► ./images/    │
│                                                         │
│   .pdf  ──► extract_images_from_pdf.py  ──► ./images/   │
│                                                         │
└─────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────┐
│                  ПЕРЕРАБОТКА В CURSOR                    │
├─────────────────────────────────────────────────────────┤
│                                                         │
│   1. Прикрепить PDF/docx в чат                          │
│   2. Запросить переработку по стандарту                 │
│   3. Получить Markdown с плейсхолдерами                 │
│   4. Заменить плейсхолдеры на реальные пути             │
│                                                         │
└─────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────┐
│                   СОХРАНЕНИЕ РЕЗУЛЬТАТА                  │
├─────────────────────────────────────────────────────────┤
│                                                         │
│   Markdown ──► Google Drive папка (синхронизация)       │
│                                                         │
│   Markdown ──► Pandoc ──► PDF ──► Google Drive          │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

---

## Быстрые команды

### Конвертация Markdown → PDF

```powershell
# Добавить в PATH (один раз)
$env:Path += ";C:\Program Files\wkhtmltopdf\bin"

# Конвертация
pandoc input.md -o output.pdf --pdf-engine=wkhtmltopdf
```

### Конвертация с оглавлением

```powershell
pandoc input.md -o output.pdf --pdf-engine=wkhtmltopdf --toc
```

### Извлечение изображений из PDF

```powershell
cd Scripts/InstructionTools
python extract_images_from_pdf.py "путь/к/файлу.pdf"
```

---

## Установленные инструменты

| Инструмент | Версия | Назначение |
|------------|--------|------------|
| Pandoc | 3.8.3 | Конвертация между форматами |
| wkhtmltopdf | 0.12.6 | Генерация PDF из HTML |
| PyMuPDF | 1.26.7 | Извлечение изображений из PDF |
| Pillow | - | Обработка изображений |

---

## FAQ

**Q: Могу ли я редактировать Google Doc прямо в Cursor?**
A: Нет. Google Docs — это не текстовые файлы. Используйте Markdown в Google Drive.

**Q: Как синхронизировать изображения?**
A: Храните изображения в папке `images/` рядом с .md файлом. При синхронизации через Google Drive они загрузятся автоматически.

**Q: Можно ли автоматизировать полностью?**
A: Частично. Извлечение текста автоматизируется, но размещение изображений в нужных местах требует ручной работы или продвинутого скрипта с AI.

---

**Дата:** 22.01.2026
