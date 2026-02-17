#!/bin/bash
# Setup automatic daily backups via cron
# Run as root: sudo bash setup_backup_cron.sh

set -e

BACKUP_SCRIPT="/opt/telegramhub/deploy/backup.sh"

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    echo "Please run as root (sudo bash setup_backup_cron.sh)"
    exit 1
fi

# Make backup script executable
chmod +x "$BACKUP_SCRIPT"

# Create cron job for daily backup at 3 AM
CRON_JOB="0 3 * * * $BACKUP_SCRIPT >> /var/log/telegramhub/backup.log 2>&1"

# Check if cron job already exists
if crontab -l 2>/dev/null | grep -q "telegramhub"; then
    echo "Cron job already exists. Updating..."
    crontab -l | grep -v "telegramhub" | crontab -
fi

# Add cron job
(crontab -l 2>/dev/null; echo "$CRON_JOB") | crontab -

echo "Automatic backup configured!"
echo "Backup will run daily at 3:00 AM"
echo ""
echo "Cron job added:"
echo "$CRON_JOB"
echo ""
echo "To view scheduled backups: crontab -l"
echo "To run backup manually: $BACKUP_SCRIPT"
echo "To list backups: $BACKUP_SCRIPT --list"
echo "To restore: $BACKUP_SCRIPT --restore <backup_file>"
