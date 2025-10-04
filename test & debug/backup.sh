#!/bin/bash

# Asset Management Backup Script
# ============================

set -e

# Konfiguration
BACKUP_DIR="${BACKUP_DIR:-$HOME/backups}"
RETENTION_DAYS="${RETENTION_DAYS:-30}"
PROJECT_DIR="$HOME/asset-management"

# Farben
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Backup-Verzeichnis erstellen
mkdir -p "$BACKUP_DIR"

# Timestamp für Backup
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
BACKUP_NAME="asset_management_backup_$TIMESTAMP"

log_info "Starte Backup: $BACKUP_NAME"

# 1. Datenbank sichern
if [ -f "$PROJECT_DIR/app.db" ]; then
    log_info "Datenbank wird gesichert..."
    cp "$PROJECT_DIR/app.db" "$BACKUP_DIR/db_$TIMESTAMP.db"
else
    log_warn "Keine Datenbank gefunden"
fi

# 2. Uploads sichern
if [ -d "$PROJECT_DIR/uploads" ]; then
    log_info "Uploads werden gesichert..."
    tar -czf "$BACKUP_DIR/uploads_$TIMESTAMP.tar.gz" -C "$PROJECT_DIR" uploads/
fi

# 3. Konfigurationsdateien sichern
log_info "Konfigurationsdateien werden gesichert..."
tar -czf "$BACKUP_DIR/config_$TIMESTAMP.tar.gz" \
    -C "$PROJECT_DIR" \
    .env \
    --exclude=.git \
    --exclude=__pycache__ \
    --exclude=*.pyc \
    --exclude=.venv \
    --exclude=backups \
    --exclude=*.log 2>/dev/null || true

# 4. Alte Backups löschen
log_info "Alte Backups werden gelöscht..."
find "$BACKUP_DIR" -name "*.db" -o -name "*.tar.gz" -type f -mtime +$RETENTION_DAYS -delete

# 5. Backup-Größe anzeigen
BACKUP_SIZE=$(du -sh "$BACKUP_DIR" | cut -f1)
log_info "Backup abgeschlossen. Backup-Größe: $BACKUP_SIZE"

# 6. Backup-Liste anzeigen
echo ""
echo "📦 Aktuelle Backups:"
ls -la "$BACKUP_DIR" | tail -10

echo ""
log_info "✅ Backup erfolgreich erstellt: $BACKUP_NAME"
