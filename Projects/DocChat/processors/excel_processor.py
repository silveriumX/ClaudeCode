"""
Excel Processor - обработка Excel файлов (.xlsx, .xls)
"""

import pandas as pd
from io import BytesIO
from typing import Dict, List


def process_excel(file_bytes: bytes, filename: str) -> dict:
    """
    Обработка Excel файла

    Args:
        file_bytes: байты Excel файла
        filename: имя файла

    Returns:
        dict с результатами обработки
    """
    result = {
        "filename": filename,
        "type": "excel",
        "text": None,
        "sheets": [],
        "total_rows": 0
    }

    try:
        # Читаем все листы
        excel_file = BytesIO(file_bytes)
        xlsx = pd.ExcelFile(excel_file)

        text_parts = []

        for sheet_name in xlsx.sheet_names:
            df = pd.read_excel(xlsx, sheet_name=sheet_name)

            # Информация о листе
            rows, cols = df.shape
            result["sheets"].append({
                "name": sheet_name,
                "rows": rows,
                "columns": cols
            })
            result["total_rows"] += rows

            # Конвертируем в текст
            text_parts.append(f"=== Лист: {sheet_name} ({rows} строк, {cols} колонок) ===\n")

            # Если таблица небольшая - показываем полностью
            if rows <= 100:
                text_parts.append(df.to_markdown(index=False))
            else:
                # Показываем первые и последние строки
                text_parts.append("Первые 50 строк:")
                text_parts.append(df.head(50).to_markdown(index=False))
                text_parts.append(f"\n... (пропущено {rows - 100} строк) ...\n")
                text_parts.append("Последние 50 строк:")
                text_parts.append(df.tail(50).to_markdown(index=False))

            text_parts.append("\n")

        result["text"] = "\n".join(text_parts)

    except Exception as e:
        result["text"] = f"[Ошибка обработки Excel: {e}]"

    return result


def excel_to_summary(file_bytes: bytes) -> str:
    """
    Создает краткую сводку по Excel файлу
    """
    try:
        excel_file = BytesIO(file_bytes)
        xlsx = pd.ExcelFile(excel_file)

        summary_parts = ["## Структура Excel файла\n"]

        for sheet_name in xlsx.sheet_names:
            df = pd.read_excel(xlsx, sheet_name=sheet_name)
            rows, cols = df.shape

            summary_parts.append(f"### Лист: {sheet_name}")
            summary_parts.append(f"- Размер: {rows} строк × {cols} колонок")
            summary_parts.append(f"- Колонки: {', '.join(df.columns.astype(str))}")

            # Типы данных
            summary_parts.append("- Типы данных:")
            for col in df.columns:
                dtype = df[col].dtype
                non_null = df[col].count()
                summary_parts.append(f"  - {col}: {dtype} ({non_null} значений)")

            summary_parts.append("")

        return "\n".join(summary_parts)

    except Exception as e:
        return f"[Ошибка создания сводки: {e}]"
