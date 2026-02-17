"""
Загрузка персон из YAML и решение «комментировать или нет».
"""
import random
from pathlib import Path
from typing import Any

import yaml


def load_personas(path: Path) -> list[dict[str, Any]]:
    with open(path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    return data if isinstance(data, list) else []


def should_comment(persona: dict[str, Any]) -> bool:
    """Решаем по вероятности персоны, оставлять ли комментарий."""
    p = persona.get("probability", 0.5)
    return random.random() < p


def get_persona_by_id(personas: list[dict], persona_id: str) -> dict[str, Any] | None:
    for p in personas:
        if p.get("id") == persona_id:
            return p
    return None
