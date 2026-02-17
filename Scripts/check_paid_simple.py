"""
Проверка всех оплаченных заявок
"""
import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[1] / ".env")

import paramiko

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(os.getenv("VPS_LINUX_HOST"), username='root', password=os.getenv("VPS_LINUX_PASSWORD"))

script = """
cd /root/finance_bot
python3 << 'PYTHON'
from sheets import SheetsManager
import config

sheets = SheetsManager()
paid = sheets.get_requests_by_status(config.STATUS_PAID)
print(f"Total paid requests: {len(paid)}")

for i, r in enumerate(paid[:10], 1):
    print(f"{i}. {r.get('request_id')}")
    print(f"   Author: {r.get('author_id')}")
    print(f"   Amount: {r.get('amount')}")
    print(f"   Sheet: {r.get('sheet_name')}")
    print()
PYTHON
"""

stdin, stdout, stderr = ssh.exec_command(script)
print(stdout.read().decode('utf-8', errors='replace'))
error = stderr.read().decode('utf-8', errors='replace')
if error:
    print("ERRORS:")
    print(error)

ssh.close()
