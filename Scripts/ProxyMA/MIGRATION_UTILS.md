# Миграция на Utils/proxyma_api.py

Единый модуль для работы с Proxyma API: **`Utils/proxyma_api.py`**.

## Использование

```python
import sys
from pathlib import Path

# Добавить корень репозитория в путь (если скрипт запускается из Scripts/ProxyMA/)
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from Utils.proxyma_api import ProxymaAPI, load_accounts

# Загрузка аккаунтов из Data/proxyma_data_complete.json
accounts = load_accounts()
for email, data in accounts.items():
    api_key = data.get("profile", {}).get("api_key") or data.get("api_key")
    if not api_key:
        continue
    client = ProxymaAPI(api_key)
    packages = client.get_packages()
    # ...
```

## Что даёт

- Один источник логики (balance, packages, package_info).
- Учётные данные только из `Data/proxyma_data_complete.json` (без хардкода).
- Соответствие правилу `.cursor/rules/proxyma-api-standards.mdc`.

## Старые файлы

- `proxyma_api.py`, `proxyma_api_working.py`, `proxyma_api_correct.py` — по мере переноса логики на `Utils/proxyma_api.py` можно оставлять как обёртки или удалять после проверки.
