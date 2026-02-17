#!/usr/bin/env python3
"""
SSH Helper для работы с удаленным сервером
"""
import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[1] / ".env")

import sys
import paramiko
import time

class SSHClient:
    def __init__(self, host, username, password, port=22):
        self.host = host
        self.username = username
        self.password = password
        self.port = port
        self.client = None

    def connect(self):
        """Подключение к серверу"""
        try:
            self.client = paramiko.SSHClient()
            self.client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            self.client.connect(
                self.host,
                port=self.port,
                username=self.username,
                password=self.password,
                timeout=10
            )
            return True
        except Exception as e:
            print(f"❌ Ошибка подключения: {e}", file=sys.stderr)
            return False

    def execute(self, command):
        """Выполнение команды на сервере"""
        if not self.client:
            if not self.connect():
                return None, None, 1

        try:
            stdin, stdout, stderr = self.client.exec_command(command)
            exit_code = stdout.channel.recv_exit_status()

            output = stdout.read().decode('utf-8')
            error = stderr.read().decode('utf-8')

            return output, error, exit_code
        except Exception as e:
            print(f"❌ Ошибка выполнения команды: {e}", file=sys.stderr)
            return None, str(e), 1

    def close(self):
        """Закрытие соединения"""
        if self.client:
            self.client.close()

def main():
    if len(sys.argv) < 2:
        print("Usage: python ssh_helper.py '<command>'")
        sys.exit(1)

    command = ' '.join(sys.argv[1:])

    # Данные для подключения
    ssh = SSHClient(
        host=os.getenv("VPS_LINUX_HOST"),
        username="root",
        password=os.getenv("VPS_LINUX_PASSWORD")
    )

    print(f"🔌 Подключаюсь к {ssh.host}...", file=sys.stderr)

    if not ssh.connect():
        sys.exit(1)

    print(f"✅ Подключение установлено", file=sys.stderr)
    print(f"📝 Выполняю: {command}", file=sys.stderr)
    print("-" * 60, file=sys.stderr)

    output, error, exit_code = ssh.execute(command)

    if output:
        # Используем safe_console для вывода с эмодзи
        try:
            print(output, end='')
        except UnicodeEncodeError:
            # Если не получается вывести с эмодзи, выводим в ASCII
            print(output.encode('ascii', 'replace').decode('ascii'), end='')

    if error:
        try:
            print(error, file=sys.stderr, end='')
        except UnicodeEncodeError:
            print(error.encode('ascii', 'replace').decode('ascii'), file=sys.stderr, end='')

    ssh.close()
    sys.exit(exit_code)

if __name__ == "__main__":
    main()
