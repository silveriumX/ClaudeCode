#!/bin/bash
# Авторизация UserBot для ChatManager
# Запустить на VPS: ssh root@195.177.94.189
# Затем: cd /root/ChatManager && bash authorize_userbot_vps.sh

echo "=========================================="
echo "ChatManager UserBot Authorization"
echo "=========================================="
echo ""

# Остановить сервис чтобы избежать конфликтов
echo "[1/4] Stopping userbot service..."
systemctl stop chatmanager-userbot

# Запустить авторизацию
echo ""
echo "[2/4] Starting authorization process..."
echo "You will need to:"
echo "  - Enter your phone number (with country code, e.g. +79123456789)"
echo "  - Enter code from Telegram (sent to Saved Messages)"
echo "  - Enter 2FA password if enabled"
echo ""
echo "Starting in 3 seconds..."
sleep 3

python3 authorize_userbot.py

# Проверить что session создан
if [ -f "chat_admin.session" ]; then
    echo ""
    echo "[3/4] Session file created successfully"
    echo "Session file size: $(du -h chat_admin.session | cut -f1)"

    # Запустить сервис
    echo ""
    echo "[4/4] Starting userbot service..."
    systemctl start chatmanager-userbot
    sleep 3

    # Проверить статус
    echo ""
    echo "=========================================="
    echo "Service Status:"
    echo "=========================================="
    systemctl status chatmanager-userbot --no-pager

    echo ""
    echo "=========================================="
    echo "Recent Logs:"
    echo "=========================================="
    journalctl -u chatmanager-userbot -n 20 --no-pager

    echo ""
    echo "=========================================="
    if systemctl is-active --quiet chatmanager-userbot; then
        echo "SUCCESS! UserBot is running"
    else
        echo "WARNING: UserBot may have errors, check logs above"
    fi
    echo "=========================================="
else
    echo ""
    echo "[ERROR] Session file not created"
    echo "Authorization may have failed"
    echo "Try running: python3 authorize_userbot.py"
fi
