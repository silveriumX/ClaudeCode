# 🚀 FinanceBot - Production Deployment Guide

**Complete guide for deploying FinanceBot to production VPS**

---

## 📋 Table of Contents

1. [Prerequisites](#prerequisites)
2. [Server Setup](#server-setup)
3. [Application Deployment](#application-deployment)
4. [Configuration](#configuration)
5. [Service Management](#service-management)
6. [Monitoring](#monitoring)
7. [Troubleshooting](#troubleshooting)
8. [Rollback Procedure](#rollback-procedure)
9. [Security Checklist](#security-checklist)

---

## Prerequisites

### Required Access
- ✅ VPS SSH access (root or sudo user)
- ✅ GitHub repository access
- ✅ Google Cloud Console access
- ✅ Telegram Bot Token
- ✅ Google Sheets ID

### Required Files
- ✅ `service_account.json` - Google Service Account credentials
- ✅ `.env` - Environment variables
- ✅ `requirements.txt` - Python dependencies

### Local Tools
- ✅ SSH client
- ✅ Python 3.10+
- ✅ Git
- ✅ Text editor

---

## Server Setup

### 1. Connect to VPS

```bash
ssh root@195.177.94.189
```

### 2. Update System

```bash
apt update && apt upgrade -y
```

### 3. Install Required Packages

```bash
# Python 3.10+
apt install python3 python3-pip python3-venv -y

# System utilities
apt install git curl wget nano htop -y

# SSL certificates (if needed)
apt install certbot -y
```

### 4. Create Application Directory

```bash
mkdir -p /root/finance_bot
cd /root/finance_bot
```

---

## Application Deployment

### Method 1: Git Clone (Recommended)

```bash
# Clone repository
cd /root
git clone https://github.com/yourusername/finance_bot.git

# Or pull latest changes
cd /root/finance_bot
git pull origin main
```

### Method 2: Direct File Upload

```powershell
# From local machine (Windows PowerShell)
scp -r C:\Path\To\FinanceBot\* root@195.177.94.189:/root/finance_bot/
```

```bash
# Or use SFTP
sftp root@195.177.94.189
put -r /local/path/to/financebot/* /root/finance_bot/
```

### 3. Setup Python Environment

```bash
cd /root/finance_bot

# Create virtual environment
python3 -m venv venv

# Activate virtual environment
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

---

## Configuration

### 1. Environment Variables

Create `/root/finance_bot/.env`:

```bash
nano /root/finance_bot/.env
```

Add:

```env
# Telegram
TELEGRAM_BOT_TOKEN=your_bot_token_here

# Google Sheets
GOOGLE_SHEETS_ID=your_sheet_id
GOOGLE_SERVICE_ACCOUNT_FILE=service_account.json

# Google Drive (for QR codes)
GOOGLE_DRIVE_CLIENT_ID=your_client_id
GOOGLE_DRIVE_CLIENT_SECRET=your_client_secret
GOOGLE_DRIVE_REFRESH_TOKEN=your_refresh_token
GOOGLE_DRIVE_FOLDER_ID=your_folder_id
```

**Security:** Ensure proper permissions
```bash
chmod 600 /root/finance_bot/.env
```

### 2. Service Account File

Upload `service_account.json`:

```bash
# From local machine
scp service_account.json root@195.177.94.189:/root/finance_bot/

# Set permissions
chmod 600 /root/finance_bot/service_account.json
```

### 3. Verify Configuration

```bash
cd /root/finance_bot
source venv/bin/activate
python3 -c "from config import *; print('Config OK')"
```

---

## Service Management

### 1. Create systemd Service

Create `/etc/systemd/system/finance_bot.service`:

```bash
nano /etc/systemd/system/finance_bot.service
```

Add:

```ini
[Unit]
Description=Finance Bot - Telegram Bot for Financial Requests
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/root/finance_bot
Environment="PATH=/root/finance_bot/venv/bin"
ExecStart=/root/finance_bot/venv/bin/python3 /root/finance_bot/bot.py
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
```

### 2. Enable and Start Service

```bash
# Reload systemd
systemctl daemon-reload

# Enable auto-start on boot
systemctl enable finance_bot

# Start service
systemctl start finance_bot

# Check status
systemctl status finance_bot
```

### 3. Service Commands

```bash
# Start
systemctl start finance_bot

# Stop
systemctl stop finance_bot

# Restart
systemctl restart finance_bot

# Status
systemctl status finance_bot

# View logs
journalctl -u finance_bot -f

# View last 100 lines
journalctl -u finance_bot -n 100

# View logs since yesterday
journalctl -u finance_bot --since yesterday
```

---

## Monitoring

### 1. Check Bot Health

```bash
# Is service running?
systemctl is-active finance_bot

# Process count
ps aux | grep "finance_bot.*bot.py" | grep -v grep | wc -l

# Last 10 log lines
journalctl -u finance_bot -n 10 --no-pager
```

### 2. Resource Usage

```bash
# CPU and memory
htop

# Disk space
df -h

# Service resource usage
systemctl status finance_bot
```

### 3. Log Analysis

```bash
# Error count in last hour
journalctl -u finance_bot --since "1 hour ago" | grep -i error | wc -l

# Search for specific error
journalctl -u finance_bot | grep "Google Sheets API"

# Export logs to file
journalctl -u finance_bot --since "2 days ago" > /tmp/bot_logs.txt
```

---

## Troubleshooting

### Common Issues

#### 1. Bot Not Starting

**Check logs:**
```bash
journalctl -u finance_bot -n 50
```

**Common causes:**
- Missing .env file
- Invalid credentials
- Port already in use
- Missing dependencies

**Solution:**
```bash
# Verify files exist
ls -la /root/finance_bot/.env
ls -la /root/finance_bot/service_account.json

# Test config
cd /root/finance_bot
source venv/bin/activate
python3 -c "import config; print(config.TELEGRAM_BOT_TOKEN[:10])"

# Reinstall dependencies
pip install -r requirements.txt --force-reinstall
```

#### 2. Google Sheets Connection Failed

**Error:** "Failed to connect to Google Sheets"

**Check:**
```bash
# Service account permissions
python3 -c "from sheets import SheetsManager; s = SheetsManager(); print('OK')"

# Sheet ID correct
grep GOOGLE_SHEETS_ID /root/finance_bot/.env
```

**Solution:**
- Verify service account has access to sheet
- Check sheet ID is correct
- Ensure Google Sheets API is enabled

#### 3. Bot Not Responding

**Check:**
```bash
# Bot polling
journalctl -u finance_bot -n 20 | grep "getUpdates"

# Telegram connection
curl -s "https://api.telegram.org/bot$TOKEN/getMe"
```

**Solution:**
- Restart bot: `systemctl restart finance_bot`
- Check Telegram API status
- Verify bot token

#### 4. Encoding Issues

**Error:** "UnicodeDecodeError" or "charmap codec can't encode"

**Solution:**
```bash
# Set locale
export LANG=en_US.UTF-8
export LC_ALL=en_US.UTF-8

# Update service file to include
nano /etc/systemd/system/finance_bot.service
# Add: Environment="LANG=en_US.UTF-8"
# Add: Environment="LC_ALL=en_US.UTF-8"

# Reload and restart
systemctl daemon-reload
systemctl restart finance_bot
```

---

## Rollback Procedure

### Before Deployment: Create Backup

```bash
# Backup current version
cd /root
tar -czf finance_bot_backup_$(date +%Y%m%d_%H%M%S).tar.gz finance_bot/

# List backups
ls -lh finance_bot_backup_*
```

### Rollback Steps

```bash
# Stop current version
systemctl stop finance_bot

# Restore from backup
cd /root
tar -xzf finance_bot_backup_YYYYMMDD_HHMMSS.tar.gz

# Restart
systemctl start finance_bot
systemctl status finance_bot
```

### Git Rollback

```bash
cd /root/finance_bot

# View commits
git log --oneline -10

# Rollback to specific commit
git reset --hard COMMIT_HASH

# Restart
systemctl restart finance_bot
```

---

## Security Checklist

### ✅ Pre-Deployment Security

- [ ] All secrets in .env (not in code)
- [ ] service_account.json has 600 permissions
- [ ] .env has 600 permissions
- [ ] No secrets in git history
- [ ] SSH key authentication enabled
- [ ] Root password is strong
- [ ] Firewall configured (ufw)

### ✅ Post-Deployment Security

```bash
# Check file permissions
ls -la /root/finance_bot/.env
ls -la /root/finance_bot/service_account.json

# Should be: -rw------- (600)

# Configure firewall
ufw status
ufw allow 22/tcp
ufw allow 80/tcp
ufw allow 443/tcp
ufw enable

# Disable password authentication (use SSH keys)
nano /etc/ssh/sshd_config
# Set: PasswordAuthentication no
systemctl restart sshd
```

### ✅ Regular Maintenance

- [ ] Update system packages weekly
- [ ] Review logs weekly
- [ ] Backup database weekly
- [ ] Rotate logs monthly
- [ ] Update dependencies monthly
- [ ] Security audit quarterly

---

## Deployment Checklist

### Pre-Deployment

- [ ] Code reviewed and tested locally
- [ ] All tests passing
- [ ] Documentation updated
- [ ] Backup created
- [ ] Rollback plan prepared

### Deployment

- [ ] Code deployed to VPS
- [ ] Dependencies installed
- [ ] Configuration updated
- [ ] Service restarted
- [ ] Health check passed

### Post-Deployment

- [ ] Bot responding to commands
- [ ] Logs show no errors
- [ ] Create request flow tested
- [ ] Payment flow tested
- [ ] Stakeholders notified

---

## Quick Reference

### Essential Commands

```bash
# Restart bot
systemctl restart finance_bot

# View logs
journalctl -u finance_bot -f

# Check status
systemctl status finance_bot

# Test bot
cd /root/finance_bot && source venv/bin/activate && python3 -c "from sheets import SheetsManager; print('OK')"

# Update code
cd /root/finance_bot && git pull && systemctl restart finance_bot
```

### Important Paths

```
/root/finance_bot/              # Application root
/root/finance_bot/.env          # Environment variables
/root/finance_bot/service_account.json  # Google credentials
/etc/systemd/system/finance_bot.service  # Service file
/var/log/journal/               # System logs (journalctl)
```

### Important URLs

- VPS IP: `195.177.94.189`
- Telegram Bot: `@YourBotUsername`
- Google Sheet: `https://docs.google.com/spreadsheets/d/YOUR_SHEET_ID`

---

## Support

### Getting Help

1. Check logs first: `journalctl -u finance_bot -n 100`
2. Review [Troubleshooting Guide](docs/troubleshooting/TROUBLESHOOTING_GUIDE.md)
3. Check [GitHub Issues](https://github.com/yourusername/finance_bot/issues)
4. Contact team lead

### Emergency Contacts

- System Admin: [Contact Info]
- DevOps: [Contact Info]
- On-call: [Contact Info]

---

**Last Updated:** 2026-02-13
**Version:** 2.5.0
