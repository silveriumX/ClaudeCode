#!/usr/bin/env python3
"""
Verify /authorize command is working
"""
import paramiko
import os
import sys

VPS_HOST = "195.177.94.189"
VPS_USER = "root"
VPS_PASSWORD = os.getenv("VPS_PASSWORD", "")

# Windows Unicode fix
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    except AttributeError:
        pass

def verify_authorize():
    """Проверяет наличие /authorize функционала"""
    print(f"[INFO] Connecting to {VPS_HOST}...")

    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    try:
        ssh.connect(VPS_HOST, username=VPS_USER, timeout=10)
    except:
        ssh.connect(VPS_HOST, username=VPS_USER, password=VPS_PASSWORD, timeout=10)

    print("[OK] Connected\n")

    # 1. Проверка bot.py - регистрация handler
    print("=== 1. Checking bot.py ===")
    stdin, stdout, stderr = ssh.exec_command("grep -n 'authorize_conv_handler' /root/ChatManager/bot.py")
    result = stdout.read().decode('utf-8', errors='replace')
    if result:
        print("[OK] authorize_conv_handler registered in bot.py:")
        for line in result.strip().split('\n'):
            print(f"  Line {line}")
    else:
        print("[ERROR] authorize_conv_handler not found in bot.py")

    # 2. Проверка handlers/authorize.py - существует
    print("\n=== 2. Checking handlers/authorize.py ===")
    stdin, stdout, stderr = ssh.exec_command("ls -lh /root/ChatManager/handlers/authorize.py")
    result = stdout.read().decode('utf-8', errors='replace')
    if result:
        print(f"[OK] {result.strip()}")
    else:
        print("[ERROR] authorize.py not found")

    # 3. Проверка импорта USERBOT_SESSION (не USERBOT_SESSION_NAME)
    print("\n=== 3. Checking USERBOT_SESSION import ===")
    stdin, stdout, stderr = ssh.exec_command("grep 'from config import' /root/ChatManager/handlers/authorize.py | head -1")
    result = stdout.read().decode('utf-8', errors='replace')
    if 'USERBOT_SESSION' in result and 'USERBOT_SESSION_NAME' not in result:
        print(f"[OK] Correct import: {result.strip()}")
    else:
        print(f"[WARNING] Import line: {result.strip()}")

    # 4. Проверка /authorize в help
    print("\n=== 4. Checking /authorize in help ===")
    stdin, stdout, stderr = ssh.exec_command("grep -A 1 '/authorize' /root/ChatManager/handlers/start.py")
    result = stdout.read().decode('utf-8', errors='replace')
    if result:
        print("[OK] /authorize found in help:")
        print(f"  {result.strip()}")

    # 5. Финальный статус бота
    print("\n=== 5. Bot Status ===")
    stdin, stdout, stderr = ssh.exec_command("systemctl is-active chatmanager-bot")
    is_active = stdout.read().decode().strip()

    if is_active == 'active':
        print("[OK] Bot is RUNNING")
    else:
        print(f"[ERROR] Bot status: {is_active}")

    # 6. Последние 5 строк логов
    print("\n=== 6. Recent Logs (last 5 lines) ===")
    stdin, stdout, stderr = ssh.exec_command("journalctl -u chatmanager-bot -n 5 --no-pager")
    logs = stdout.read().decode('utf-8', errors='replace')
    print(logs)

    ssh.close()

    print("\n" + "="*50)
    print("DEPLOYMENT VERIFICATION COMPLETE")
    print("="*50)
    print("\n[NEXT STEP] Test /authorize command in Telegram:")
    print("  1. Open @IamCreatorBot (or your bot)")
    print("  2. Send /start")
    print("  3. Send /authorize")
    print("  4. Follow the prompts to authorize UserBot")

if __name__ == "__main__":
    try:
        verify_authorize()
    except Exception as e:
        print(f"\n[ERROR] {e}")
        import traceback
        traceback.print_exc()
