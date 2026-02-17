# -*- coding: utf-8 -*-
"""Create VLESS+REALITY inbound on 3X-UI via API"""
import io
import json
import os
import sys
from pathlib import Path

from dotenv import load_dotenv
import paramiko

load_dotenv(Path(__file__).resolve().parents[1] / ".env")

if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

HOST = os.getenv("VPS_VLESS_HOST")
USER = "root"
PASS = os.getenv("VPS_VLESS_PASSWORD")

# Generated keys
UUID = "00a2711a-0e0d-41a5-b446-da70f3e7a3e7"
PRIVATE_KEY = os.getenv("VLESS_PRIVATE_KEY")
PUBLIC_KEY = "V2mkZpZoj5Yoh0VZZFTYvjWsnRqCJPJUMpl7av9myUg"
SHORT_ID = "993b61a18284803a"

# Best SNI from RealiTLScanner (same subnet)
SNI_DEST = "www.cloudflare.com"

# Inbound settings JSON for 3X-UI API
inbound_settings = json.dumps({
    "clients": [
        {
            "id": UUID,
            "flow": "xtls-rprx-vision",
            "email": "user1",
            "limitIp": 0,
            "totalGB": 0,
            "expiryTime": 0,
            "enable": True,
            "tgId": "",
            "subId": "",
            "reset": 0
        }
    ],
    "decryption": "none",
    "fallbacks": []
})

stream_settings = json.dumps({
    "network": "tcp",
    "security": "reality",
    "externalProxy": [],
    "realitySettings": {
        "show": False,
        "xver": 0,
        "dest": f"{SNI_DEST}:443",
        "serverNames": [SNI_DEST],
        "privateKey": PRIVATE_KEY,
        "minClient": "",
        "maxClient": "",
        "maxTimeDiff": 0,
        "shortIds": [SHORT_ID, ""]
    },
    "tcpSettings": {
        "acceptProxyProtocol": False,
        "header": {"type": "none"}
    }
})

sniffing = json.dumps({
    "enabled": True,
    "destOverride": ["http", "tls", "quic", "fakedns"],
    "metadataOnly": False,
    "routeOnly": False
})

# Build curl command
add_inbound_data = (
    f"up=0&down=0&total=0&remark=VLESS-Reality"
    f"&enable=true&expiryTime=0"
    f"&listen="
    f"&port=443"
    f"&protocol=vless"
    f"&settings={inbound_settings}"
    f"&streamSettings={stream_settings}"
    f"&sniffing={sniffing}"
)

cmd = f"""
curl -sk -b /tmp/cookies.txt -X POST 'https://127.0.0.1:2053/panel/api/inbounds/add' \
  -H 'Content-Type: application/x-www-form-urlencoded' \
  --data-urlencode 'up=0' \
  --data-urlencode 'down=0' \
  --data-urlencode 'total=0' \
  --data-urlencode 'remark=VLESS-Reality' \
  --data-urlencode 'enable=true' \
  --data-urlencode 'expiryTime=0' \
  --data-urlencode 'listen=' \
  --data-urlencode 'port=443' \
  --data-urlencode 'protocol=vless' \
  --data-urlencode 'settings={inbound_settings}' \
  --data-urlencode 'streamSettings={stream_settings}' \
  --data-urlencode 'sniffing={sniffing}'
"""

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

print("[1/2] Logging in to 3X-UI...")
out, err, code = run(
    "curl -sk -X POST 'https://127.0.0.1:2053/login' "
    "-H 'Content-Type: application/x-www-form-urlencoded' "
    "-d 'username=admin&password=admin' "
    "-c /tmp/cookies.txt"
)
print(f"Login: {out.strip()}")

print("[2/2] Creating VLESS+Reality inbound...")
out, err, code = run(cmd)
print(f"Result: {out.strip()}")
if err.strip():
    print(f"[STDERR]: {err.strip()}")

# Now get the connection link
print("\n[3/3] Getting connection link...")
out, err, code = run(
    "curl -sk -b /tmp/cookies.txt 'https://127.0.0.1:2053/panel/api/inbounds/list'"
)
try:
    data = json.loads(out)
    if data.get("success") and data.get("obj"):
        for inb in data["obj"]:
            if inb.get("protocol") == "vless":
                port = inb.get("port")
                settings = json.loads(inb.get("settings", "{}"))
                stream = json.loads(inb.get("streamSettings", "{}"))
                clients = settings.get("clients", [])
                reality = stream.get("realitySettings", {})

                if clients:
                    c = clients[0]
                    uid = c.get("id")
                    flow = c.get("flow", "")
                    pub_key = PUBLIC_KEY
                    sni = SNI_DEST
                    sid = SHORT_ID
                    fp = "chrome"

                    link = (
                        f"vless://{uid}@{HOST}:{port}"
                        f"?type=tcp&security=reality"
                        f"&pbk={pub_key}"
                        f"&fp={fp}"
                        f"&sni={sni}"
                        f"&sid={sid}"
                        f"&flow={flow}"
                        f"#VLESS-Reality"
                    )
                    print(f"\n{'='*60}")
                    print(f"VLESS+REALITY CONNECTION LINK:")
                    print(f"{'='*60}")
                    print(link)
                    print(f"{'='*60}")
                    print(f"\nPublic Key: {pub_key}")
                    print(f"UUID: {uid}")
                    print(f"SNI: {sni}")
                    print(f"ShortID: {sid}")
    else:
        print(f"API response: {out[:500]}")
except json.JSONDecodeError:
    print(f"Raw response: {out[:500]}")
