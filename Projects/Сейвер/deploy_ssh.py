# -*- coding: utf-8 -*-
"""
SSH Deploy Script для Сейвер v6.0
"""
import os
import paramiko
import time
import sys
import io
from pathlib import Path
from dotenv import load_dotenv

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

load_dotenv(Path(__file__).parent / ".env")

HOST = os.getenv("SSH_HOST")
PORT = int(os.getenv("SSH_PORT", "22"))
USERNAME = os.getenv("SSH_USERNAME")
PASSWORD = os.getenv("SSH_PASSWORD")

SYSTEMD_SERVICE = '''[Unit]
Description=Saver Bot
After=network.target

[Service]
Type=simple
WorkingDirectory=/root/media_downloader_bot
ExecStart=/root/media_downloader_bot/venv/bin/python3 /root/media_downloader_bot/bot.py
Restart=always
RestartSec=10
Environment=PYTHONUNBUFFERED=1

[Install]
WantedBy=multi-user.target
'''


def run_command(ssh, command, timeout=120):
    print(f"  -> {command[:80]}...")
    stdin, stdout, stderr = ssh.exec_command(command, timeout=timeout)
    exit_code = stdout.channel.recv_exit_status()
    output = stdout.read().decode('utf-8', errors='ignore')
    error = stderr.read().decode('utf-8', errors='ignore')

    if exit_code != 0 and error:
        print(f"    ! {error[:200]}")
    elif output:
        out_clean = output.strip()[:100]
        if out_clean:
            print(f"    OK: {out_clean}")

    return exit_code, output, error


def main():
    print("=" * 60)
    print("  DEPLOY: Сейвер v6.0 (yt-dlp + Pinterest)")
    print("=" * 60)
    print(f"\n[*] Connecting to {HOST}...")

    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    try:
        ssh.connect(HOST, PORT, USERNAME, PASSWORD, timeout=30)
        print("[+] Connected!\n")

        # Шаг 1: Зависимости
        print("[1/5] Installing/updating dependencies...")
        run_command(ssh, "/root/media_downloader_bot/venv/bin/pip install -U yt-dlp python-dotenv aiohttp -q", timeout=120)

        # Шаг 2: Загрузка файлов
        print("\n[2/5] Uploading files...")
        sftp = ssh.open_sftp()

        local_dir = Path(__file__).parent
        for filename in ('bot.py', '.env'):
            local_path = local_dir / filename
            remote_path = f'/root/media_downloader_bot/{filename}'
            with open(local_path, 'r', encoding='utf-8') as f:
                content = f.read()
            with sftp.file(remote_path, 'w') as rf:
                rf.write(content)
            print(f"    OK: {filename} uploaded")

        sftp.close()

        # Шаг 3: Обновление systemd
        print("\n[3/5] Updating systemd...")
        service_cmd = f'''cat > /etc/systemd/system/media_downloader.service << 'ENDSERVICE'
{SYSTEMD_SERVICE}
ENDSERVICE'''
        run_command(ssh, service_cmd)
        run_command(ssh, "systemctl daemon-reload")

        # Шаг 4: Перезапуск
        print("\n[4/5] Restarting bot...")
        run_command(ssh, "systemctl restart media_downloader")
        time.sleep(2)

        # Шаг 5: Проверка
        print("\n[5/5] Checking status...")
        exit_code, output, error = run_command(ssh, "systemctl is-active media_downloader")

        if "active" in output:
            print("\n" + "=" * 60)
            print("  SUCCESS! Сейвер v6.0 is running!")
            print("=" * 60)
        else:
            print("\n[!] Issues detected")
            run_command(ssh, "journalctl -u media_downloader -n 20 --no-pager")

    except Exception as e:
        print(f"[-] Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        ssh.close()
        print("\n[*] Connection closed")


if __name__ == "__main__":
    main()
