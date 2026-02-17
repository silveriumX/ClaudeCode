"""
Единый модуль для работы с Proxyma API.
Используй этот модуль во всех скриптах вместо дублирования кода.
Учётные данные — из Data/proxyma_data_complete.json (не хардкодить).
Документация: Documentation/API/PROXYMA_API_FINAL_REPORT.md
"""

import json
import logging
from pathlib import Path
from typing import Any, Optional

import requests

logger = logging.getLogger(__name__)

# Residential API (обычные ключи из кабинета)
BASE_URL_RESIDENTIAL = "https://api.proxyma.io/api/residential"
DEFAULT_TIMEOUT = 30


def load_accounts(data_path: Optional[Path] = None) -> dict[str, Any]:
    """
    Загрузить аккаунты из Data/proxyma_data_complete.json.
    Ключ — email, значение — данные аккаунта (profile.api_key, packages и т.д.).
    """
    if data_path is None:
        data_path = Path(__file__).resolve().parent.parent / "Data" / "proxyma_data_complete.json"
    if not data_path.exists():
        logger.warning("Файл учётных данных не найден: %s", data_path)
        return {}
    with data_path.open("r", encoding="utf-8") as f:
        return json.load(f)


class ProxymaAPI:
    """
    Клиент Proxyma API (Residential).
    Заголовок: api-key (не Bearer).
    """

    def __init__(self, api_key: str, package_key: Optional[str] = None):
        self.api_key = api_key
        self.package_key = package_key
        self._headers = {
            "api-key": api_key,
            "Content-Type": "application/json",
        }

    def _request(
        self,
        method: str,
        path: str,
        base: str = BASE_URL_RESIDENTIAL,
        **kwargs: Any,
    ) -> Optional[dict[str, Any]]:
        url = f"{base.rstrip('/')}/{path.lstrip('/')}"
        kwargs.setdefault("timeout", DEFAULT_TIMEOUT)
        kwargs.setdefault("headers", self._headers)
        try:
            resp = requests.request(method, url, **kwargs)
            if resp.status_code == 200:
                return resp.json()
            logger.error("Proxyma API %s %s: HTTP %s %s", method, path, resp.status_code, resp.text[:200])
            return None
        except Exception as e:
            logger.exception("Proxyma API request failed: %s", e)
            return None

    def get_packages(self) -> Optional[dict[str, Any]]:
        """Список пакетов (residential)."""
        return self._request("GET", "packages")

    def get_package_info(self, package_key: Optional[str] = None) -> Optional[dict[str, Any]]:
        """
        Информация о пакете по package_key.
        Возвращает dict с status, created_at, expired_at, days_left, traffic и т.д.
        """
        key = package_key or self.package_key
        if not key:
            logger.error("package_key не указан")
            return None
        data = self.get_packages()
        if not data:
            return None
        packages = data.get("packages", [])
        for pkg in packages:
            if pkg.get("package_key") == key:
                return {
                    "status": pkg.get("status"),
                    "created_at": pkg.get("created_at"),
                    "expired_at": pkg.get("expired_at"),
                    "days_left": pkg.get("days_left"),
                    "traffic": {
                        "limit": pkg.get("tariff", {}).get("traffic", 0),
                        "usage": pkg.get("traffic_used") or 0,
                    },
                }
        logger.warning("Пакет %s не найден", key)
        return None
