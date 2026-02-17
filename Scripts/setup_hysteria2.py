import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[1] / ".env")

# -*- coding: utf-8 -*-
"""Create Hysteria2 inbound on 3X-UI via API"""
import sys, io, json, paramiko, urllib.parse

if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

HOST = os.getenv("VPS_VLESS_HOST")
USER = "root"
PASS = os.getenv("VPS_VLESS_PASSWORD")

def run(command, timeout=60):
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(HOST, username=USER, password=PASS, timeout=15)
    stdin, stdout, stderr = client.exec_command(command, timeout=timeout)
    out = stdout.read().decode("utf-8", errors="replace")
    err = stderr.read().decode("utf-8", errors="replace")
    code = stdout.channel.recv_exit_status()
    client.close()
    return out, err, code

# Step 1: Generate self-signed cert for Hysteria2
print("[1/4] Generating self-signed certificate...")
out, err, code = run(
    "mkdir -p /etc/hysteria && "
    "openssl ecparam -genkey -name prime256v1 -out /etc/hysteria/private.key && "
    "openssl req -new -x509 -days 36500 -key /etc/hysteria/private.key "
    "-out /etc/hysteria/cert.pem -subj '/CN=www.cloudflare.com' && "
    "echo 'Cert OK'"
)
print(out.strip())

# Step 2: Login
print("[2/4] Logging in...")
out, err, code = run(
    "curl -sk -X POST 'https://127.0.0.1:2053/login' "
    "-H 'Content-Type: application/x-www-form-urlencoded' "
    "-d 'username=admin&password=admin' "
    "-c /tmp/cookies.txt"
)
print(f"Login: {out.strip()}")

# Step 3: Create Hysteria2 inbound via writing a temp JSON and using curl @file
settings = {
    "clients": [
        {
            "password": "Taurus2025vpn",
            "email": "hy2user1",
            "limitIp": 0,
            "totalGB": 0,
            "expiryTime": 0,
            "enable": True,
            "tgId": "",
            "subId": "",
            "reset": 0
        }
    ]
}

stream_settings = {
    "network": "tcp",
    "security": "tls",
    "tlsSettings": {
        "serverName": "",
        "minVersion": "1.2",
        "maxVersion": "1.3",
        "cipherSuites": "",
        "rejectUnknownSni": False,
        "disableSystemRoot": False,
        "enableSessionResumption": False,
        "certificates": [
            {
                "certificateFile": "/etc/hysteria/cert.pem",
                "keyFile": "/etc/hysteria/private.key",
                "ocspStapling": 3600,
                "oneTimeLoading": False,
                "usage": "encipherment",
                "buildChain": False,
                "buildChainBefore": False
            }
        ],
        "alpn": ["h3"],
        "settings": {
            "allowInsecure": False,
            "fingerprint": "chrome"
        }
    }
}

sniffing = {
    "enabled": True,
    "destOverride": ["http", "tls", "quic", "fakedns"],
    "metadataOnly": False,
    "routeOnly": False
}

# Build form data properly
form_data = {
    "up": "0",
    "down": "0",
    "total": "0",
    "remark": "Hysteria2-Backup",
    "enable": "true",
    "expiryTime": "0",
    "listen": "",
    "port": "8443",
    "protocol": "hysteria2",
    "settings": json.dumps(settings),
    "streamSettings": json.dumps(stream_settings),
    "sniffing": json.dumps(sniffing)
}

# Write form data to a temp file as JSON, then use curl with it
form_json = json.dumps(form_data)

print("[3/4] Creating Hysteria2 inbound...")
# Write the JSON payload to a file on the server
run(f"cat > /tmp/hy2_payload.json << 'ENDOFPAYLOAD'\n{form_json}\nENDOFPAYLOAD")

# Use Python on the server to send the request properly
python_script = '''
import json, urllib.request, urllib.parse, ssl, http.cookiejar

# Read cookies
cj = http.cookiejar.MozillaCookieJar('/tmp/cookies.txt')
cj.load(ignore_discard=True, ignore_expires=True)

# Read payload
with open('/tmp/hy2_payload.json') as f:
    form_data = json.load(f)

# URL-encode the form data
encoded = urllib.parse.urlencode(form_data).encode('utf-8')

# Create request
ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

opener = urllib.request.build_opener(
    urllib.request.HTTPCookieProcessor(cj),
    urllib.request.HTTPSHandler(context=ctx)
)

req = urllib.request.Request(
    'https://127.0.0.1:2053/panel/api/inbounds/add',
    data=encoded,
    headers={'Content-Type': 'application/x-www-form-urlencoded'},
    method='POST'
)

resp = opener.open(req)
print(resp.read().decode())
'''

run(f"cat > /tmp/hy2_create.py << 'ENDOFSCRIPT'\n{python_script}\nENDOFSCRIPT")
out, err, code = run("python3 /tmp/hy2_create.py")
print(f"Result: {out.strip()}")
if err.strip():
    print(f"[STDERR]: {err.strip()}")

# Step 4: Generate connection link
print("\n[4/4] Hysteria2 connection link:")
hy2_link = f"hysteria2://Taurus2025vpn@{HOST}:8443?insecure=1&sni=www.cloudflare.com#Hysteria2-Backup"
print(f"{'='*60}")
print(hy2_link)
print(f"{'='*60}")
