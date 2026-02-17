#!/usr/bin/env python3
"""
Загрузка файла на VPS через SFTP
"""
import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[1] / ".env")

import sys
import paramiko
from pathlib import Path

def upload_file(local_path: str, remote_path: str):
    """Загрузить файл на VPS"""
    host = os.getenv("VPS_LINUX_HOST")
    username = "root"
    password = os.getenv("VPS_LINUX_PASSWORD")

    try:
        # Подключение
        print(f"Connecting to {host}...")
        transport = paramiko.Transport((host, 22))
        transport.connect(username=username, password=password)

        # SFTP клиент
        sftp = paramiko.SFTPClient.from_transport(transport)

        # Загрузка файла
        print(f"Uploading {local_path} -> {remote_path}")
        sftp.put(local_path, remote_path)

        print(f"SUCCESS: File uploaded!")

        # Закрытие соединения
        sftp.close()
        transport.close()

        return True

    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return False

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python upload_to_vps.py <local_file> <remote_file>")
        sys.exit(1)

    local_path = sys.argv[1]
    remote_path = sys.argv[2]

    if not Path(local_path).exists():
        print(f"ERROR: Local file not found: {local_path}")
        sys.exit(1)

    success = upload_file(local_path, remote_path)
    sys.exit(0 if success else 1)
