#!/bin/bash
# TelegramHub Backup Script
# Creates backups of session files and data
#
# Usage:
#   ./backup.sh                    # Create backup
#   ./backup.sh --restore backup.tar.gz  # Restore from backup

set -e

# Configuration
INSTALL_DIR="/opt/telegramhub"
BACKUP_DIR="/opt/telegramhub/backups"
MAX_BACKUPS=7  # Keep last 7 backups

# Create backup directory
mkdir -p "$BACKUP_DIR"

# Function to create backup
create_backup() {
    TIMESTAMP=$(date +%Y%m%d_%H%M%S)
    BACKUP_FILE="$BACKUP_DIR/telegramhub_backup_$TIMESTAMP.tar.gz"

    echo "Creating backup: $BACKUP_FILE"

    # Stop service temporarily to ensure consistent backup
    echo "Stopping TelegramHub service..."
    systemctl stop telegramhub 2>/dev/null || true

    # Create backup
    tar -czf "$BACKUP_FILE" \
        -C "$INSTALL_DIR" \
        accounts/sessions \
        data \
        drafts \
        context 2>/dev/null || true

    # Restart service
    echo "Starting TelegramHub service..."
    systemctl start telegramhub 2>/dev/null || true

    echo "Backup created: $BACKUP_FILE"

    # Clean old backups
    echo "Cleaning old backups (keeping last $MAX_BACKUPS)..."
    ls -t "$BACKUP_DIR"/telegramhub_backup_*.tar.gz 2>/dev/null | tail -n +$((MAX_BACKUPS + 1)) | xargs rm -f 2>/dev/null || true

    # Show backup size
    ls -lh "$BACKUP_FILE"
}

# Function to restore backup
restore_backup() {
    BACKUP_FILE="$1"

    if [ ! -f "$BACKUP_FILE" ]; then
        echo "Error: Backup file not found: $BACKUP_FILE"
        exit 1
    fi

    echo "Restoring from: $BACKUP_FILE"
    echo "WARNING: This will overwrite current data!"
    read -p "Continue? (y/n) " -n 1 -r
    echo

    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "Cancelled."
        exit 0
    fi

    # Stop service
    echo "Stopping TelegramHub service..."
    systemctl stop telegramhub 2>/dev/null || true

    # Restore backup
    echo "Restoring files..."
    tar -xzf "$BACKUP_FILE" -C "$INSTALL_DIR"

    # Fix permissions
    chown -R telegramhub:telegramhub "$INSTALL_DIR/accounts" 2>/dev/null || true
    chown -R telegramhub:telegramhub "$INSTALL_DIR/data" 2>/dev/null || true
    chown -R telegramhub:telegramhub "$INSTALL_DIR/drafts" 2>/dev/null || true
    chown -R telegramhub:telegramhub "$INSTALL_DIR/context" 2>/dev/null || true
    chmod 600 "$INSTALL_DIR/accounts/sessions"/*.session 2>/dev/null || true

    # Start service
    echo "Starting TelegramHub service..."
    systemctl start telegramhub

    echo "Restore complete!"
}

# Function to list backups
list_backups() {
    echo "Available backups:"
    ls -lh "$BACKUP_DIR"/telegramhub_backup_*.tar.gz 2>/dev/null || echo "No backups found."
}

# Parse arguments
case "$1" in
    --restore)
        if [ -z "$2" ]; then
            echo "Usage: $0 --restore <backup_file>"
            exit 1
        fi
        restore_backup "$2"
        ;;
    --list)
        list_backups
        ;;
    *)
        create_backup
        ;;
esac
