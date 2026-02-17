"""
Веб-интерфейс для авторизации Telegram аккаунтов
Запуск: python auth_web.py
Открыть: http://127.0.0.1:8766
"""
import asyncio
from pathlib import Path
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
import uvicorn
from telethon import TelegramClient
from telethon.errors import SessionPasswordNeededError, PhoneCodeInvalidError

# Настройки
SESSIONS_DIR = Path(__file__).parent.parent / "accounts" / "sessions"
SESSIONS_DIR.mkdir(parents=True, exist_ok=True)

API_ID = 2040
API_HASH = "b18441a1ff607e10a989891a5462e627"

app = FastAPI()

# Текущая авторизация
current_auth = {"client": None, "phone": None}


def get_next_account_name():
    """Генерирует следующее имя аккаунта"""
    existing = list(SESSIONS_DIR.glob("*.session"))
    return f"account_{len(existing) + 1}"


@app.get("/", response_class=HTMLResponse)
async def index():
    return """<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>TelegramHub - Auth</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, sans-serif;
            background: #0f0f0f; color: #eee;
            min-height: 100vh; padding: 40px;
        }
        .container { max-width: 500px; margin: 0 auto; }
        h1 { text-align: center; margin-bottom: 30px; color: #0088cc; }

        .card {
            background: #1a1a1a; border-radius: 12px; padding: 24px;
            margin-bottom: 20px;
        }
        .card h3 { margin-bottom: 16px; color: #0088cc; }

        .accounts { margin-bottom: 20px; }
        .account {
            display: flex; justify-content: space-between;
            padding: 10px 14px; background: #222; border-radius: 8px;
            margin-bottom: 8px; border-left: 3px solid #4caf50;
        }
        .account .name { font-weight: 500; }
        .account .info { color: #888; font-size: 13px; }

        .form-group { margin-bottom: 16px; }
        label { display: block; margin-bottom: 6px; color: #888; }
        input {
            width: 100%; padding: 14px; border: 1px solid #333;
            background: #222; color: #eee; border-radius: 8px;
            font-size: 18px;
        }
        input:focus { outline: none; border-color: #0088cc; }

        button {
            width: 100%; padding: 14px; border: none; border-radius: 8px;
            background: #0088cc; color: white; font-size: 16px;
            cursor: pointer;
        }
        button:hover { background: #0077b5; }

        .step { display: none; }
        .step.active { display: block; }

        .msg { padding: 12px; border-radius: 8px; margin-bottom: 16px; }
        .msg.error { background: #4a1515; color: #ff6b6b; }
        .msg.success { background: #1a3a1a; color: #6bff6b; }
        .msg.info { background: #1a2a3a; color: #6bbbff; }

        .btn-cancel { background: #333; margin-top: 10px; }
        .btn-green { background: #4caf50; }

        .no-accounts { color: #666; text-align: center; padding: 20px; }
    </style>
</head>
<body>
    <div class="container">
        <h1>TelegramHub</h1>

        <div class="card">
            <h3>Authorized Accounts</h3>
            <div id="accounts" class="accounts">
                <div class="no-accounts">Loading...</div>
            </div>
        </div>

        <div class="card">
            <h3>Add Account</h3>
            <div id="msg"></div>

            <div class="step active" id="step1">
                <div class="form-group">
                    <label>Phone number with country code</label>
                    <input type="tel" id="phone" placeholder="+79123456789" autofocus>
                </div>
                <button onclick="sendCode()">Send Code</button>
            </div>

            <div class="step" id="step2">
                <div class="form-group">
                    <label>Code from Telegram</label>
                    <input type="text" id="code" placeholder="12345" maxlength="6">
                </div>
                <button onclick="verifyCode()">Verify</button>
                <button class="btn-cancel" onclick="reset()">Cancel</button>
            </div>

            <div class="step" id="step3">
                <div class="form-group">
                    <label>2FA Password</label>
                    <input type="password" id="password" placeholder="Your password">
                </div>
                <button onclick="verify2FA()">Submit</button>
                <button class="btn-cancel" onclick="reset()">Cancel</button>
            </div>
        </div>

        <div class="card" style="text-align: center;">
            <button class="btn-green" onclick="location.href='http://127.0.0.1:8765'">
                Open Dashboard
            </button>
        </div>
    </div>

    <script>
        function msg(text, type='info') {
            const el = document.getElementById('msg');
            el.className = 'msg ' + type;
            el.textContent = text;
            el.style.display = text ? 'block' : 'none';
        }

        function step(n) {
            document.querySelectorAll('.step').forEach(s => s.classList.remove('active'));
            document.getElementById('step' + n).classList.add('active');
        }

        function reset() {
            step(1);
            document.getElementById('phone').value = '';
            document.getElementById('code').value = '';
            document.getElementById('password').value = '';
            msg('');
        }

        async function loadAccounts() {
            const res = await fetch('/api/accounts');
            const data = await res.json();
            const el = document.getElementById('accounts');

            if (data.accounts.length === 0) {
                el.innerHTML = '<div class="no-accounts">No accounts yet</div>';
                return;
            }

            el.innerHTML = data.accounts.map(a => `
                <div class="account">
                    <span class="name">${a.name}</span>
                    <span class="info">${a.info}</span>
                    <button onclick="deleteAccount('${a.name}')" style="background: #c0392b; padding: 4px 10px; border-radius: 4px; font-size: 12px; margin-left: 10px;">Delete</button>
                </div>
            `).join('');
        }

        async function sendCode() {
            const phone = document.getElementById('phone').value.trim();
            if (!phone) { msg('Enter phone number', 'error'); return; }

            msg('Sending code...', 'info');

            const res = await fetch('/api/send_code', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({phone})
            });

            const data = await res.json();
            if (data.success) {
                msg(data.hint || 'Code sent! Check Telegram', 'success');
                step(2);
                document.getElementById('code').focus();
            } else {
                msg(data.error, 'error');
            }
        }

        async function verifyCode() {
            const code = document.getElementById('code').value.trim();
            if (!code) { msg('Enter code', 'error'); return; }

            msg('Verifying...', 'info');

            const res = await fetch('/api/verify_code', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({code})
            });

            const data = await res.json();
            if (data.success) {
                msg('Success! ' + data.user, 'success');
                reset();
                loadAccounts();
            } else if (data.need_2fa) {
                msg('Enter 2FA password', 'info');
                step(3);
                document.getElementById('password').focus();
            } else {
                msg(data.error, 'error');
            }
        }

        async function verify2FA() {
            const password = document.getElementById('password').value;
            if (!password) { msg('Enter password', 'error'); return; }

            msg('Verifying...', 'info');

            const res = await fetch('/api/verify_2fa', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({password})
            });

            const data = await res.json();
            if (data.success) {
                msg('Success! ' + data.user, 'success');
                reset();
                loadAccounts();
            } else {
                msg(data.error, 'error');
            }
        }

        async function deleteAccount(name) {
            if (!confirm(`Delete account "${name}"? This will remove the session file.`)) return;

            const res = await fetch('/api/delete_account', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({name})
            });

            const data = await res.json();
            if (data.success) {
                msg('Account deleted', 'success');
                loadAccounts();
            } else {
                msg(data.error, 'error');
            }
        }

        // Enter key support
        document.getElementById('phone').onkeypress = e => { if(e.key==='Enter') sendCode(); };
        document.getElementById('code').onkeypress = e => { if(e.key==='Enter') verifyCode(); };
        document.getElementById('password').onkeypress = e => { if(e.key==='Enter') verify2FA(); };

        loadAccounts();
    </script>
</body>
</html>"""


@app.get("/api/accounts")
async def get_accounts():
    accounts = []
    for session_file in sorted(SESSIONS_DIR.glob("*.session")):
        name = session_file.stem
        info = "Unknown"

        try:
            client = TelegramClient(str(session_file.with_suffix("")), API_ID, API_HASH)
            await client.connect()
            if await client.is_user_authorized():
                me = await client.get_me()
                info = f"{me.first_name} +{me.phone}"
            await client.disconnect()
        except Exception as e:
            info = f"Error: {e}"

        accounts.append({"name": name, "info": info})

    return {"accounts": accounts}


@app.post("/api/send_code")
async def send_code(request: Request):
    global current_auth

    data = await request.json()
    phone = data.get("phone", "").strip()

    if not phone:
        return {"success": False, "error": "Phone required"}

    print(f"\n[AUTH] Sending code to: {phone}")

    # Закрываем предыдущий клиент
    if current_auth["client"]:
        try:
            await current_auth["client"].disconnect()
        except:
            pass

    # Создаём новый клиент с параметрами устройства
    account_name = get_next_account_name()
    session_path = SESSIONS_DIR / account_name

    print(f"[AUTH] Session: {session_path}")

    client = TelegramClient(
        str(session_path),
        API_ID,
        API_HASH,
        device_model="Desktop",
        system_version="Windows 10",
        app_version="4.16.8",
        lang_code="en",
        system_lang_code="en-US"
    )

    try:
        print("[AUTH] Connecting to Telegram...")
        await client.connect()
        print("[AUTH] Connected! Sending code request...")

        result = await client.send_code_request(phone)

        print(f"[AUTH] Code sent! Type: {result.type}")
        print(f"[AUTH] phone_code_hash: {result.phone_code_hash[:10]}...")

        current_auth = {"client": client, "phone": phone, "phone_code_hash": result.phone_code_hash}

        # Определяем куда пришёл код
        code_type = str(result.type)
        if "App" in code_type:
            hint = "Code sent to Telegram app (check messages from 'Telegram')"
        elif "Sms" in code_type:
            hint = "Code sent via SMS"
        elif "Call" in code_type:
            hint = "You will receive a phone call"
        else:
            hint = f"Code type: {code_type}"

        print(f"[AUTH] {hint}")
        return {"success": True, "hint": hint}
    except Exception as e:
        print(f"[AUTH] ERROR: {type(e).__name__}: {e}")
        try:
            await client.disconnect()
        except:
            pass
        return {"success": False, "error": str(e)}


@app.post("/api/verify_code")
async def verify_code(request: Request):
    global current_auth

    if not current_auth["client"]:
        return {"success": False, "error": "Send code first"}

    data = await request.json()
    code = data.get("code", "").strip()

    client = current_auth["client"]
    phone = current_auth["phone"]

    try:
        await client.sign_in(phone, code)
        me = await client.get_me()
        await client.disconnect()
        current_auth = {"client": None, "phone": None}
        return {"success": True, "user": f"{me.first_name} (@{me.username or 'N/A'})"}
    except SessionPasswordNeededError:
        return {"success": False, "need_2fa": True}
    except PhoneCodeInvalidError:
        return {"success": False, "error": "Invalid code. Try again."}
    except Exception as e:
        return {"success": False, "error": str(e)}


@app.post("/api/verify_2fa")
async def verify_2fa(request: Request):
    global current_auth

    if not current_auth["client"]:
        return {"success": False, "error": "No session"}

    data = await request.json()
    password = data.get("password", "")

    client = current_auth["client"]

    try:
        await client.sign_in(password=password)
        me = await client.get_me()
        await client.disconnect()
        current_auth = {"client": None, "phone": None}
        return {"success": True, "user": f"{me.first_name} (@{me.username or 'N/A'})"}
    except Exception as e:
        return {"success": False, "error": str(e)}


@app.post("/api/delete_account")
async def delete_account(request: Request):
    """Delete an account (session file)"""
    data = await request.json()
    name = data.get("name", "").strip()

    if not name:
        return {"success": False, "error": "Account name required"}

    session_file = SESSIONS_DIR / f"{name}.session"
    journal_file = SESSIONS_DIR / f"{name}.session-journal"

    if not session_file.exists():
        return {"success": False, "error": "Session file not found"}

    try:
        # Delete session file
        session_file.unlink()
        print(f"[AUTH] Deleted: {session_file}")

        # Delete journal file if exists
        if journal_file.exists():
            journal_file.unlink()
            print(f"[AUTH] Deleted: {journal_file}")

        return {"success": True}
    except Exception as e:
        return {"success": False, "error": str(e)}


if __name__ == "__main__":
    print("\n" + "="*50)
    print("  TelegramHub - Authorization")
    print("="*50)
    print("\n  Open: http://127.0.0.1:8766\n")

    uvicorn.run(app, host="127.0.0.1", port=8766, log_level="warning")
