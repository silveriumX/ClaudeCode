---
description: Стандарты SSH деплоя на VPS через paramiko
paths:
  - "**/deploy*.py"
  - "**/deploy*.sh"
---

# VPS SSH Deployment Standards

## SSH Подключение через Paramiko

**ВСЕГДА используй `paramiko` для SSH подключений:**

```python
import paramiko
import sys
import os

def create_ssh_client(host, port, username, password):
    """Создание SSH клиента с правильными настройками"""
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    try:
        client.connect(host, port=port, username=username, password=password, timeout=30)
        return client
    except Exception as e:
        print(f"Ошибка подключения: {e}", file=sys.stderr)
        return None
```

## Хранение Credentials

**НИКОГДА не храни credentials в коде!**

### Метод 1: Файл .credentials (рекомендуется)
```python
def load_credentials():
    creds_file = os.path.join(os.path.dirname(__file__), ".credentials")
    creds = {}
    with open(creds_file, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, value = line.split('=', 1)
                creds[key.strip()] = value.strip()
    return creds
```

### Метод 2: Переменные окружения
```python
VPS_HOST = os.getenv('VPS_HOST')
VPS_USER = os.getenv('VPS_USER')
VPS_PASSWORD = os.getenv('VPS_PASSWORD')
VPS_PORT = int(os.getenv('VPS_PORT', 22))
```

## Выполнение команд на сервере

```python
def run_command(ssh, command, timeout=120):
    """Выполнение команды на удаленном сервере"""
    print(f"  -> {command[:80]}...")
    stdin, stdout, stderr = ssh.exec_command(command, timeout=timeout)
    exit_code = stdout.channel.recv_exit_status()
    output = stdout.read().decode('utf-8', errors='ignore')
    error = stderr.read().decode('utf-8', errors='ignore')

    if exit_code != 0 and error:
        print(f"    ERROR: {error[:200]}")
    elif output:
        out_clean = output.strip()[:100]
        if out_clean:
            print(f"    OK: {out_clean}")

    return exit_code, output, error
```

## Передача файлов (SFTP)

```python
def upload_file(ssh, local_path, remote_path):
    sftp = ssh.open_sftp()
    try:
        sftp.put(local_path, remote_path)
        print(f"Загружен: {local_path} -> {remote_path}")
    finally:
        sftp.close()

def upload_directory(ssh, local_dir, remote_dir):
    sftp = ssh.open_sftp()
    try:
        for root, dirs, files in os.walk(local_dir):
            for file in files:
                local_file = os.path.join(root, file)
                relative_path = os.path.relpath(local_file, local_dir)
                remote_file = os.path.join(remote_dir, relative_path).replace('\\', '/')
                remote_file_dir = os.path.dirname(remote_file)
                run_command(ssh, f"mkdir -p {remote_file_dir}")
                sftp.put(local_file, remote_file)
                print(f"  + {relative_path}")
    finally:
        sftp.close()
```

## Структура Deploy Script

```python
#!/usr/bin/env python3
"""Deploy Script для [ИМЯ ПРОЕКТА]"""
import paramiko
import os
import sys
from pathlib import Path

PROJECT_DIR = Path(__file__).parent
REMOTE_DIR = "/opt/your_project"
SERVICE_NAME = "your_service"

def main():
    creds = load_credentials()

    ssh = create_ssh_client(
        creds['VPS_HOST'], int(creds.get('VPS_PORT', 22)),
        creds['VPS_USER'], creds['VPS_PASSWORD']
    )
    if not ssh:
        sys.exit(1)

    try:
        # 1. Остановка сервиса
        run_command(ssh, f"systemctl stop {SERVICE_NAME} || true")

        # 2. Backup
        run_command(ssh, f"cp -r {REMOTE_DIR} {REMOTE_DIR}.backup.$(date +%Y%m%d_%H%M%S) || true")

        # 3. Создание директорий
        run_command(ssh, f"mkdir -p {REMOTE_DIR}")

        # 4. Загрузка файлов
        for local_path in PROJECT_DIR.glob("*.py"):
            upload_file(ssh, str(local_path), f"{REMOTE_DIR}/{local_path.name}")

        # 5. Установка зависимостей
        run_command(ssh, f"cd {REMOTE_DIR} && pip3 install -r requirements.txt -q", timeout=180)

        # 6. Systemd и запуск
        create_systemd_service(ssh, SERVICE_NAME, REMOTE_DIR)
        run_command(ssh, "systemctl daemon-reload")
        run_command(ssh, f"systemctl enable {SERVICE_NAME}")
        run_command(ssh, f"systemctl restart {SERVICE_NAME}")

        # 7. Проверка
        exit_code, output, _ = run_command(ssh, f"systemctl status {SERVICE_NAME} --no-pager")
        if "active (running)" in output:
            print("\nДЕПЛОЙ УСПЕШЕН!")
        else:
            print(f"\nПроблемы с запуском. Логи: journalctl -u {SERVICE_NAME} -n 50 --no-pager")
    finally:
        ssh.close()
```

## Создание Systemd Service

```python
def create_systemd_service(ssh, service_name, working_dir, exec_start=None):
    if exec_start is None:
        exec_start = f"/usr/bin/python3 {working_dir}/bot.py"

    service_content = f"""[Unit]
Description={service_name.replace('_', ' ').title()}
After=network.target

[Service]
Type=simple
WorkingDirectory={working_dir}
ExecStart={exec_start}
Restart=always
RestartSec=10
Environment=PYTHONUNBUFFERED=1

[Install]
WantedBy=multi-user.target
"""
    service_cmd = f"""cat > /etc/systemd/system/{service_name}.service << 'ENDSERVICE'
{service_content}
ENDSERVICE"""

    run_command(ssh, service_cmd)
```

## Управление сервисами

```python
def service_status(ssh, service_name):
    run_command(ssh, f"systemctl status {service_name} --no-pager")

def service_restart(ssh, service_name):
    run_command(ssh, f"systemctl restart {service_name}")

def service_logs(ssh, service_name, lines=50):
    run_command(ssh, f"journalctl -u {service_name} -n {lines} --no-pager")
```

## Best Practices

1. **Всегда используй timeout** при выполнении команд
2. **Создавай backup** перед обновлением файлов
3. **Проверяй статус** после деплоя
4. **Используй systemd** для автозапуска сервисов
5. **Добавляй .credentials в .gitignore**
6. **Используй try-finally** для гарантированного закрытия соединения
7. **Устанавливай `PYTHONUNBUFFERED=1`** для Python сервисов
8. **Используй `--no-pager`** для systemctl команд в скриптах
9. **Проверяй exit_code** после критичных команд

## Troubleshooting

- **SSH не подключается** — проверь host, port, username, password, firewall, sshd status
- **Сервис не запускается** — `journalctl -u service_name -n 50`, права на файлы, путь Python
- **Файлы не загружаются** — права на директорию, место на диске (`df -h`)
