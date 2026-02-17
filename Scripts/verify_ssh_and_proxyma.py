#!/usr/bin/env python3
import os
from pathlib import Path
from dotenv import load_dotenv
load_dotenv(Path(__file__).resolve().parents[1] / ".env")

"""
Проверка:
1) SSH к серверу — доступ к файлу Proxifier (реквизиты/маршруты).
2) Proxyma API — создание прокси-листа по api_key и package_key.

Реквизиты: задать в .env (SSH_HOST, SSH_USER, SSH_PASS, PROXYMA_API_KEY, PROXYMA_PACKAGE_KEY)
или передать при запуске. Не коммитить секреты в репо.
"""
import base64
import json
import os
import sys
from pathlib import Path

# Добавляем путь к server-monitor-package для импорта
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "Projects" / "ServerManager" / "server-monitor-package"))

import requests

def _env(key: str, default: str = "") -> str:
    return os.environ.get(key, default).strip()

# --- Конфиг: из .env или переменных окружения ---
SSH_HOST = _env("SSH_HOST", "62.84.101.97")
SSH_USER = _env("SSH_USER", "Administrator")
SSH_PASS = _env("SSH_PASS", os.getenv("VPS_WIN_PASSWORD"))
PROXYMA_API_KEY = _env("PROXYMA_API_KEY", "n2yhff6z7fC1VBBKi8QvoGeSr9LYm5Li")
PROXYMA_PACKAGE_KEY = _env("PROXYMA_PACKAGE_KEY", "1fb08611c4d557ac8f22")


def check_ssh_and_proxifier():
    """Подключение по SSH и проверка доступа к профилю Proxifier."""
    try:
        import paramiko
    except ImportError:
        print("❌ SSH: модуль paramiko не установлен. pip install paramiko")
        return False

    print("\n--- 1) SSH и файл Proxifier ---")
    print(f"   Подключение к {SSH_HOST} как {SSH_USER}...")

    # Команда: найти профиль Proxifier и вывести путь + есть ли ProxyList
    ps_cmd = r'''
$paths = @(
    "$env:APPDATA\Proxifier4\Profiles\Default.ppx",
    "$env:ProgramData\Proxifier\Default.ppx",
    "C:\ProgramData\Proxifier\Default.ppx"
)
$found = $null
foreach ($p in $paths) {
    if (Test-Path $p) { $found = $p; break }
}
if ($found) {
    Write-Output "PROFILE_PATH:$found"
    $c = [IO.File]::ReadAllText($found)
    if ($c -match '<ProxyList>.*?</ProxyList>') { Write-Output "HAS_PROXYLIST:YES" } else { Write-Output "HAS_PROXYLIST:NO" }
    # Показать первый прокси (без пароля)
    if ($c -match '<ProxyList>(.*?)</ProxyList>') { Write-Output "SNIPPET:" + $Matches[1].Substring(0, [Math]::Min(200, $Matches[1].Length)) }
} else {
    Write-Output "PROFILE_PATH:NOT_FOUND"
}
'''
    encoded = base64.b64encode(ps_cmd.encode('utf-16le')).decode('ascii')
    full_cmd = f"powershell.exe -NoProfile -NonInteractive -EncodedCommand {encoded}"

    client = None
    try:
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        client.connect(
            SSH_HOST,
            username=SSH_USER,
            password=SSH_PASS,
            timeout=15,
            look_for_keys=False,
            allow_agent=False,
        )
        stdin, stdout, stderr = client.exec_command(full_cmd, timeout=60)
        out = stdout.read().decode("utf-8", errors="ignore").strip()
        err = stderr.read().decode("utf-8", errors="ignore").strip()
        if err and not out:
            print(f"   stderr: {err[:300]}")
        if out:
            for line in out.splitlines():
                if line.startswith("PROFILE_PATH:"):
                    print(f"   Профиль: {line.replace('PROFILE_PATH:', '')}")
                elif line.startswith("HAS_PROXYLIST:"):
                    print(f"   ProxyList в файле: {line.replace('HAS_PROXYLIST:', '')}")
                elif line.startswith("SNIPPET:"):
                    print(f"   Фрагмент ProxyList: {line.replace('SNIPPET:', '')[:150]}...")
            if "PROFILE_PATH:NOT_FOUND" in out:
                print("   Итог: профиль Proxifier не найден на сервере.")
                return False
            print("   Итог: по SSH можно читать и при необходимости менять реквизиты/маршруты в .ppx (как в set_proxy).")
            return True
        return False
    except paramiko.AuthenticationException:
        print("   Ошибка: неверный логин/пароль SSH.")
        return False
    except Exception as e:
        print(f"   Ошибка SSH: {e}")
        return False
    finally:
        if client:
            client.close()


def check_proxyma_create_proxy():
    """Проверка создания прокси-листа в Proxyma по API."""
    print("\n--- 2) Proxyma API — создание прокси-листа ---")
    headers = {
        "api-key": PROXYMA_API_KEY,
        "Content-Type": "application/json",
    }
    # Сначала проверяем, что api_key принимается (список пакетов)
    try:
        r = requests.get(
            "https://api.proxyma.io/api/residential/packages",
            headers=headers,
            timeout=15,
        )
        if r.status_code == 200:
            data = r.json()
            pkgs = data.get("packages", [])
            our = [p for p in pkgs if p.get("package_key") == PROXYMA_PACKAGE_KEY]
            if our:
                print(f"   Пакет {PROXYMA_PACKAGE_KEY} найден, статус: {our[0].get('status')}")
            else:
                print(f"   Пакет {PROXYMA_PACKAGE_KEY} не в списке (в списке {len(pkgs)} пакетов)")
        else:
            print(f"   GET packages: HTTP {r.status_code}")
    except Exception as e:
        print(f"   GET packages: {e}")
    url = "https://api.proxyma.io/api/create/proxy"
    # Минимальный набор полей по документации
    body = {
        "package_key": PROXYMA_PACKAGE_KEY,
        "list_name": "test_list_verify_script",
        "list_login": "test_login_verify",
        "country_code": "UA",
        "region_name": "Cherkasy Oblast",
        "city": "Cherkasy",
        "rotation_period": -1,
        "format": 4,
    }
    try:
        r = requests.post(url, json=body, headers=headers, timeout=30)
        text = r.text
        try:
            data = r.json()
            text = json.dumps(data, ensure_ascii=False, indent=2)
        except Exception:
            pass
        if r.status_code == 200:
            print("   Ответ 200. Создание прокси-листа через API возможно.")
            print("   Пример ответа (фрагмент):", text[:400])
            return True
        print(f"   Ответ HTTP {r.status_code}: {text[:500]}")
        if r.status_code == 401:
            print("   Проверьте api_key (в заголовке api-key).")
        if r.status_code == 400:
            print("   Проверьте package_key и обязательные поля (country_code, region_name, city и т.д.).")
        return False
    except Exception as e:
        print(f"   Ошибка запроса: {e}")
        return False


def main():
    print("Проверка SSH (Proxifier) и Proxyma API")
    ok_ssh = check_ssh_and_proxifier()
    ok_api = check_proxyma_create_proxy()
    print("\n--- Итог ---")
    print(f"   SSH + Proxifier: {'OK' if ok_ssh else 'FAIL'}")
    print(f"   Proxyma create proxy: {'OK' if ok_api else 'FAIL'}")
    return 0 if (ok_ssh and ok_api) else 1


if __name__ == "__main__":
    sys.exit(main())
