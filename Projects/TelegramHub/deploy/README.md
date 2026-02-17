# TelegramHub Server Deployment

## Quick Start (Linux Server)

### 1. Upload Files to Server

```bash
# From your local machine
scp -r TelegramHub user@server:/home/user/
```

### 2. Run Setup Script

```bash
ssh user@server
cd /home/user/TelegramHub
sudo bash deploy/setup_server.sh
```

### 3. Copy Session Files

Copy your `.session` files to the server:

```bash
scp accounts/sessions/*.session user@server:/opt/telegramhub/accounts/sessions/
sudo chown telegramhub:telegramhub /opt/telegramhub/accounts/sessions/*.session
sudo chmod 600 /opt/telegramhub/accounts/sessions/*.session
```

### 4. Configure AI (Optional)

Edit the service file to add your AI API key:

```bash
sudo nano /etc/systemd/system/telegramhub.service
```

Uncomment and set:
```
Environment=AI_API_KEY=sk-your-openai-key
Environment=AI_PROVIDER=openai
Environment=AI_MODEL=gpt-4o-mini
```

Or create an environment file:
```bash
sudo nano /opt/telegramhub/.env
```
```
AI_API_KEY=sk-your-openai-key
AI_PROVIDER=openai
AI_MODEL=gpt-4o-mini
```

### 5. Start Service

```bash
sudo systemctl daemon-reload
sudo systemctl start telegramhub
sudo systemctl status telegramhub
```

### 6. Access Dashboard

Open in browser: `http://your-server-ip:8765`

---

## Service Management

```bash
# Start
sudo systemctl start telegramhub

# Stop
sudo systemctl stop telegramhub

# Restart
sudo systemctl restart telegramhub

# View logs
sudo journalctl -u telegramhub -f

# View log files
tail -f /var/log/telegramhub/telegramhub.log
```

---

## Security Recommendations

### Option 1: SSH Tunnel (Recommended for Single User)

Don't expose port 8765 publicly. Use SSH tunnel:

```bash
# On your local machine
ssh -L 8765:localhost:8765 user@server
```

Then access: `http://localhost:8765`

### Option 2: Nginx Reverse Proxy with HTTPS

```bash
sudo apt install nginx certbot python3-certbot-nginx
```

Create `/etc/nginx/sites-available/telegramhub`:

```nginx
server {
    server_name your-domain.com;

    location / {
        proxy_pass http://127.0.0.1:8765;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_cache_bypass $http_upgrade;
    }
}
```

```bash
sudo ln -s /etc/nginx/sites-available/telegramhub /etc/nginx/sites-enabled/
sudo certbot --nginx -d your-domain.com
sudo systemctl restart nginx
```

### Option 3: Basic Authentication

Add to nginx config:

```nginx
location / {
    auth_basic "TelegramHub";
    auth_basic_user_file /etc/nginx/.htpasswd;
    proxy_pass http://127.0.0.1:8765;
}
```

Create password file:
```bash
sudo htpasswd -c /etc/nginx/.htpasswd admin
```

---

## Updating

```bash
# Upload new files
scp -r server/* user@server:/opt/telegramhub/server/

# Restart service
sudo systemctl restart telegramhub
```

---

## Troubleshooting

### Service won't start

```bash
# Check status
sudo systemctl status telegramhub

# Check logs
sudo journalctl -u telegramhub -n 50

# Test manually
sudo -u telegramhub /opt/telegramhub/venv/bin/python /opt/telegramhub/server/main.py
```

### Session errors

- Ensure session files are owned by telegramhub user
- Check file permissions (should be 600)
- Session might be expired - re-authorize using auth_web.py

### AI not working

- Check AI_API_KEY is set correctly
- Verify API key has credits
- Check logs for API errors

---

## File Locations

| Path | Description |
|------|-------------|
| `/opt/telegramhub/` | Main installation directory |
| `/opt/telegramhub/server/` | Python server files |
| `/opt/telegramhub/accounts/sessions/` | Telegram session files |
| `/opt/telegramhub/data/` | CRM data (tags, templates) |
| `/opt/telegramhub/drafts/` | Draft messages |
| `/opt/telegramhub/context/` | Cursor AI context files |
| `/var/log/telegramhub/` | Log files |
| `/etc/systemd/system/telegramhub.service` | Service file |
