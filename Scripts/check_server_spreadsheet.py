"""
Проверка какая таблица открывается на сервере
"""
import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[1] / ".env")

import paramiko

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(os.getenv("VPS_LINUX_HOST"), username='root', password=os.getenv("VPS_LINUX_PASSWORD"))

commands = [
    ("GOOGLE_SHEETS_ID from config", "cd /root/finance_bot && python3 -c 'import config; print(config.GOOGLE_SHEETS_ID)'"),
    ("Spreadsheet title", "cd /root/finance_bot && python3 -c 'from sheets import SheetsManager; sheets = SheetsManager(); print(sheets.spreadsheet.title)'"),
    ("All sheets", "cd /root/finance_bot && python3 -c 'from sheets import SheetsManager; sheets = SheetsManager(); [print(s.title) for s in sheets.spreadsheet.worksheets()]'"),
]

for label, cmd in commands:
    print(f"\n{label}:")
    stdin, stdout, stderr = ssh.exec_command(cmd)
    print(stdout.read().decode('utf-8', errors='replace'))

ssh.close()
