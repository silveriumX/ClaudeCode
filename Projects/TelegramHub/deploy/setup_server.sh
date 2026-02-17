#!/bin/bash
# TelegramHub Server Setup Script
# Run as root: sudo bash setup_server.sh

set -e

echo "=== TelegramHub Server Setup ==="

# Configuration
INSTALL_DIR="/opt/telegramhub"
SERVICE_USER="telegramhub"
LOG_DIR="/var/log/telegramhub"
PYTHON_VERSION="python3.11"

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    echo "Please run as root (sudo bash setup_server.sh)"
    exit 1
fi

echo "[1/7] Installing system dependencies..."
apt-get update
apt-get install -y python3.11 python3.11-venv python3-pip git

echo "[2/7] Creating service user..."
if ! id "$SERVICE_USER" &>/dev/null; then
    useradd -r -s /bin/false -m -d "$INSTALL_DIR" "$SERVICE_USER"
    echo "User $SERVICE_USER created"
else
    echo "User $SERVICE_USER already exists"
fi

echo "[3/7] Creating directories..."
mkdir -p "$INSTALL_DIR"
mkdir -p "$LOG_DIR"
mkdir -p "$INSTALL_DIR/accounts/sessions"
mkdir -p "$INSTALL_DIR/context/active_chats"
mkdir -p "$INSTALL_DIR/context/pending_replies"
mkdir -p "$INSTALL_DIR/context/summaries"
mkdir -p "$INSTALL_DIR/context/exports"
mkdir -p "$INSTALL_DIR/drafts"
mkdir -p "$INSTALL_DIR/data"
mkdir -p "$INSTALL_DIR/logs"

echo "[4/7] Copying files..."
# Copy server files
cp -r server/* "$INSTALL_DIR/server/" 2>/dev/null || mkdir -p "$INSTALL_DIR/server"
cp server/*.py "$INSTALL_DIR/server/"
cp server/requirements.txt "$INSTALL_DIR/server/"

# Copy other necessary files
cp -r accounts/sessions/*.session "$INSTALL_DIR/accounts/sessions/" 2>/dev/null || true
cp -r data/* "$INSTALL_DIR/data/" 2>/dev/null || true

echo "[5/7] Setting up Python virtual environment..."
$PYTHON_VERSION -m venv "$INSTALL_DIR/venv"
"$INSTALL_DIR/venv/bin/pip" install --upgrade pip
"$INSTALL_DIR/venv/bin/pip" install -r "$INSTALL_DIR/server/requirements.txt"

echo "[6/7] Setting permissions..."
chown -R "$SERVICE_USER:$SERVICE_USER" "$INSTALL_DIR"
chown -R "$SERVICE_USER:$SERVICE_USER" "$LOG_DIR"
chmod 750 "$INSTALL_DIR"
chmod 750 "$INSTALL_DIR/accounts/sessions"
chmod 600 "$INSTALL_DIR/accounts/sessions"/*.session 2>/dev/null || true

echo "[7/7] Installing systemd service..."
cp deploy/telegramhub.service /etc/systemd/system/
systemctl daemon-reload
systemctl enable telegramhub

echo ""
echo "=== Setup Complete ==="
echo ""
echo "Next steps:"
echo "1. Copy your Telegram session files to: $INSTALL_DIR/accounts/sessions/"
echo "2. Set your AI API key (optional):"
echo "   Edit /etc/systemd/system/telegramhub.service"
echo "   Or create $INSTALL_DIR/.env with AI_API_KEY=your_key"
echo ""
echo "3. Start the service:"
echo "   systemctl start telegramhub"
echo ""
echo "4. Check status:"
echo "   systemctl status telegramhub"
echo "   journalctl -u telegramhub -f"
echo ""
echo "5. Access the dashboard:"
echo "   http://your-server-ip:8765"
echo ""
echo "For security, consider:"
echo "- Setting up nginx reverse proxy with HTTPS"
echo "- Configuring firewall to restrict access"
echo "- Using SSH tunnel for remote access"
echo ""
