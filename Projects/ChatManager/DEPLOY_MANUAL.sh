#!/bin/bash
# ChatManager Manual Deploy Script
# Run this script ON THE VPS after uploading files

echo "=== ChatManager Deployment Script ==="
echo ""

# Step 1: Create directories
echo "[1/6] Creating directories..."
mkdir -p /root/ChatManager/handlers /root/ChatManager/utils
echo "✓ Directories created"

# Step 2: Check uploaded files
echo ""
echo "[2/6] Checking uploaded files..."
cd /root/ChatManager
ls -la

# Step 3: Install dependencies
echo ""
echo "[3/6] Installing dependencies..."
pip3 install -r requirements.txt
echo "✓ Dependencies installed"

# Step 4: Create systemd service for bot
echo ""
echo "[4/6] Creating systemd service for control bot..."
cat > /etc/systemd/system/chatmanager-bot.service << 'EOF'
[Unit]
Description=ChatManager Control Bot
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/root/ChatManager
ExecStart=/usr/bin/python3 bot.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF
echo "✓ Control bot service created"

# Step 5: Create systemd service for userbot
echo ""
echo "[5/6] Creating systemd service for userbot..."
cat > /etc/systemd/system/chatmanager-userbot.service << 'EOF'
[Unit]
Description=ChatManager UserBot
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/root/ChatManager
ExecStart=/usr/bin/python3 userbot.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF
echo "✓ UserBot service created"

# Step 6: Start services
echo ""
echo "[6/6] Starting services..."
systemctl daemon-reload
systemctl enable chatmanager-bot chatmanager-userbot
systemctl start chatmanager-bot chatmanager-userbot

echo ""
echo "=== Deployment complete! ==="
echo ""
echo "Check status:"
echo "  systemctl status chatmanager-bot"
echo "  systemctl status chatmanager-userbot"
echo ""
echo "View logs:"
echo "  journalctl -u chatmanager-bot -n 20 -f"
echo "  journalctl -u chatmanager-userbot -n 20 -f"
echo ""
echo "NOTE: UserBot will fail until Telegram authorization is complete."
echo "      This is expected - authorize via authorize_userbot.py"
