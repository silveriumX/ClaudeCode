#!/usr/bin/env python3
import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[2] / ".env")

import paramiko

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect(os.getenv("VPS_DOWNLOAD_HOST"), username='root', password=os.getenv("VPS_DOWNLOAD_PASSWORD"), timeout=15)

sftp = client.open_sftp()
sftp.get('/opt/server-monitor/server_checker.py', 'server_checker_vps.py')
sftp.close()

print("Downloaded server_checker.py")
client.close()
