---
description: Запрет на создание новых deploy-скриптов. Использовать только vps_connect.py
paths:
  - "**/deploy*.py"
  - "**/deploy*.sh"
  - "**/check_*.py"
  - "**/upload_*.py"
  - "**/connect_*.py"
  - "**/ssh_*.py"
  - "**/vps_*.py"
---

# VPS Deployment — ПРАВИЛА

## ЗАПРЕЩЕНО создавать новые файлы для деплоя

**НИКОГДА не создавай:**
- deploy_*.py / deploy_*.sh
- check_*.py / check_server.py
- upload_*.py / upload_to_vps.py
- connect_*.py / ssh_*.py
- Любые скрипты для подключения к VPS

## Что делать вместо этого

В каждом проекте уже есть `vps_connect.py` — единственный инструмент для работы с VPS.

```bash
python vps_connect.py status       # статус бота
python vps_connect.py logs [N]     # логи
python vps_connect.py errors [N]   # ошибки
python vps_connect.py restart      # перезапуск
python vps_connect.py deploy       # загрузить файлы + перезапуск
python vps_connect.py shell <cmd>  # SSH команда
```

Нужна новая функция — **добавь её в существующий vps_connect.py**, не создавай новый файл.

## Credentials

Все VPS-креды хранятся в `.env` каждого проекта:
- VPS_HOST, VPS_PORT, VPS_USER, VPS_PASSWORD, VPS_REMOTE_DIR

**НИКОГДА не хардкодь пароли, токены, ключи в коде.**

## SSH через Paramiko

```python
import paramiko
from dotenv import load_dotenv

load_dotenv()
client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect(os.environ["VPS_HOST"], port=int(os.getenv("VPS_PORT", "22")),
               username=os.environ["VPS_USER"], password=os.environ["VPS_PASSWORD"])
```
