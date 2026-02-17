"""
Figma API Connection Script
Работает с Personal Access Token (альтернатива MCP для automation)
"""

import requests
import os
import json
from pathlib import Path
from dotenv import load_dotenv
from typing import Dict, Optional
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Загрузить .env
env_path = Path(__file__).parent.parent / ".env"
load_dotenv(env_path)

FIGMA_API_TOKEN = os.getenv("FIGMA_API_TOKEN")
FIGMA_BASE_URL = "https://api.figma.com/v1"


def get_file_info(file_key: str) -> Optional[Dict]:
    """
    Получить информацию о Figma файле.

    Args:
        file_key: File key из URL (например, UQqv5JHrrB1WtU6I7l0xNr)

    Returns:
        Данные файла или None при ошибке

    Example:
        >>> info = get_file_info("UQqv5JHrrB1WtU6I7l0xNr")
        >>> print(info['name'])
        'NEXR-STORE3-Red'
    """
    if not FIGMA_API_TOKEN:
        logger.error("FIGMA_API_TOKEN не найден в .env файле")
        logger.info("Получите токен: Figma → Settings → Personal access tokens")
        return None

    url = f"{FIGMA_BASE_URL}/files/{file_key}"
    headers = {"X-Figma-Token": FIGMA_API_TOKEN}

    try:
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()

        data = response.json()

        logger.info(f"✓ Файл: {data.get('name')}")
        logger.info(f"✓ Последнее изменение: {data.get('lastModified')}")
        logger.info(f"✓ Версия: {data.get('version')}")

        return data

    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 403:
            logger.error("403 Forbidden - проверьте FIGMA_API_TOKEN")
        elif e.response.status_code == 404:
            logger.error("404 Not Found - файл не найден или нет доступа")
        else:
            logger.error(f"HTTP Error: {e}")
        return None

    except Exception as e:
        logger.error(f"Ошибка: {e}")
        return None


def list_pages(file_key: str) -> Optional[list]:
    """
    Получить список страниц в файле.

    Args:
        file_key: File key из URL

    Returns:
        Список страниц с их названиями и node IDs
    """
    data = get_file_info(file_key)
    if not data:
        return None

    pages = []
    for page in data.get('document', {}).get('children', []):
        pages.append({
            'id': page.get('id'),
            'name': page.get('name'),
            'type': page.get('type')
        })
        logger.info(f"  - Страница: {page.get('name')} (ID: {page.get('id')})")

    return pages


def get_components(file_key: str) -> Optional[Dict]:
    """
    Получить все компоненты из файла.

    Args:
        file_key: File key из URL

    Returns:
        Словарь компонентов
    """
    url = f"{FIGMA_BASE_URL}/files/{file_key}/components"
    headers = {"X-Figma-Token": FIGMA_API_TOKEN}

    try:
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()

        data = response.json()
        components = data.get('meta', {}).get('components', {})

        logger.info(f"✓ Найдено компонентов: {len(components)}")

        for comp_id, comp_data in list(components.items())[:5]:  # Первые 5
            logger.info(f"  - {comp_data.get('name')}")

        return components

    except Exception as e:
        logger.error(f"Ошибка получения компонентов: {e}")
        return None


def save_file_structure(file_key: str, output_path: Path) -> bool:
    """
    Сохранить структуру файла в JSON.

    Args:
        file_key: File key из URL
        output_path: Путь для сохранения JSON

    Returns:
        True если успешно сохранено
    """
    data = get_file_info(file_key)
    if not data:
        return False

    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    logger.info(f"✓ Структура сохранена: {output_path}")
    return True


# Использование
if __name__ == "__main__":
    # File key из вашей ссылки
    FILE_KEY = "UQqv5JHrrB1WtU6I7l0xNr"

    logger.info("=" * 60)
    logger.info("Проверка подключения к Figma API")
    logger.info("=" * 60)

    # 1. Получить информацию о файле
    logger.info("\n1. Информация о файле:")
    file_info = get_file_info(FILE_KEY)

    if file_info:
        # 2. Список страниц
        logger.info("\n2. Страницы в файле:")
        pages = list_pages(FILE_KEY)

        # 3. Компоненты
        logger.info("\n3. Компоненты в файле:")
        components = get_components(FILE_KEY)

        # 4. Сохранить структуру
        logger.info("\n4. Сохранение структуры:")
        output = Path(__file__).parent / "figma_structure.json"
        save_file_structure(FILE_KEY, output)

        logger.info("\n" + "=" * 60)
        logger.info("✓ Подключение работает!")
        logger.info("=" * 60)
    else:
        logger.error("\n" + "=" * 60)
        logger.error("✗ Не удалось подключиться к Figma")
        logger.error("=" * 60)
        logger.info("\nДля настройки:")
        logger.info("1. Figma → Settings → Personal access tokens")
        logger.info("2. Generate new token")
        logger.info("3. Добавить в .env: FIGMA_API_TOKEN=figd_xxxx")
