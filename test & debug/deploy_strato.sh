#!/bin/bash

# Asset Management Deployment Script für Strato VM
# Dieses Skript richtet die komplette Anwendung ein

set -e  # Bei Fehlern abbrechen

echo "🚀 Asset Management Deployment für Strato VM"
echo "============================================="

# Farben für Ausgaben
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Hilfsfunktionen
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Prüfen ob wir als root laufen (für apt commands)
if [ "$EUID" -eq 0 ]; then
    log_error "Bitte nicht als root ausführen!"
    exit 1
fi

# 1. System-Updates durchführen
log_info "System wird aktualisiert..."
sudo apt update && sudo apt upgrade -y

# 2. Erforderliche Pakete installieren
log_info "System-Pakete werden installiert..."
sudo apt install -y python3 python3-pip python3-venv nginx certbot python3-certbot-nginx ufw git curl wget

# 3. Firewall konfigurieren
log_info "Firewall wird konfiguriert..."
sudo ufw --force reset
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow ssh
sudo ufw allow 'Nginx Full'
sudo ufw --force enable

# 4. Projektverzeichnis erstellen und wechseln
PROJECT_DIR="$HOME/asset-management"
if [ ! -d "$PROJECT_DIR" ]; then
    log_info "Projektverzeichnis wird erstellt..."
    mkdir -p "$PROJECT_DIR"
else
    log_info "Projektverzeichnis existiert bereits"
fi

cd "$PROJECT_DIR"

# 5. Git Repository klonen oder aktualisieren
if [ ! -d ".git" ]; then
    log_info "Repository wird geklont..."
    git clone https://github.com/IHR-USERNAME/asset-management.git .
else
    log_info "Repository wird aktualisiert..."
    git pull origin main
fi

# 6. Python Virtual Environment erstellen
if [ ! -d "venv" ]; then
    log_info "Python Virtual Environment wird erstellt..."
    python3 -m venv venv
fi

log_info "Virtual Environment wird aktiviert..."
source venv/bin/activate

# 7. Python-Abhängigkeiten installieren
log_info "Python-Abhängigkeiten werden installiert..."
pip install --upgrade pip
pip install -r requirements.txt

# 8. Datenbank initialisieren
if [ ! -f "app.db" ]; then
    log_info "Datenbank wird initialisiert..."
    export FLASK_APP=app
    flask db upgrade
else
    log_info "Datenbank existiert bereits"
fi

# 9. Umgebungsvariablen konfigurieren
log_info "Umgebungsvariablen werden konfiguriert..."
if [ ! -f ".env" ]; then
    cp .env.example .env
    log_warn "Bitte .env Datei bearbeiten:"
    log_warn "  - SECRET_KEY setzen (starkes Passwort generieren)"
    log_warn "  - DATABASE_URL für PostgreSQL setzen (falls gewünscht)"
    log_warn "  - MAIL_PASSWORD für Gmail setzen"
    log_warn "  - Domain für die Anwendung setzen"
    echo ""
    echo "Beispiel .env Inhalt:"
    echo "FLASK_APP=app"
    echo "FLASK_ENV=production"
    echo "SECRET_KEY=$(openssl rand -hex 32)"
    echo "DATABASE_URL=postgresql://user:pass@localhost/asset_db"
    echo "MAIL_SERVER=smtp.gmail.com"
    echo "MAIL_PORT=587"
    echo "MAIL_USE_TLS=True"
    echo "MAIL_USERNAME=ihre-email@gmail.com"
    echo "MAIL_PASSWORD=ihr-app-passwort"
    echo "DOMAIN=ihre-domain.de"
fi

# 10. Nginx konfigurieren
NGINX_CONF="/etc/nginx/sites-available/asset-management"
sudo tee "$NGINX_CONF" > /dev/null << EOF
server {
    listen 80;
    server_name _;

    # Logging
    access_log /var/log/nginx/asset_access.log;
    error_log /var/log/nginx/asset_error.log;

    # Static files
    location /static/ {
        alias $PROJECT_DIR/static/;
        expires 1y;
        add_header Cache-Control "public, immutable";
    }

    # Uploads
    location /uploads/ {
        alias $PROJECT_DIR/uploads/;
        expires 1M;
    }

    # Main application
    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;

        # WebSocket support für Live-Chat
        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection "upgrade";
    }

    # Security headers
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header Referrer-Policy "no-referrer-when-downgrade" always;
    add_header Content-Security-Policy "default-src 'self' http: https: data: blob: 'unsafe-inline'" always;
}
EOF

# Nginx Site aktivieren
sudo ln -sf "$NGINX_CONF" "/etc/nginx/sites-enabled/"
sudo rm -f "/etc/nginx/sites-enabled/default"

# 11. Systemd Service erstellen
SERVICE_FILE="/etc/systemd/system/asset-management.service"
sudo tee "$SERVICE_FILE" > /dev/null << EOF
[Unit]
Description=Asset Management Application
After=network.target

[Service]
User=$USER
Group=$USER
WorkingDirectory=$PROJECT_DIR
Environment="PATH=$PROJECT_DIR/venv/bin"
ExecStart=$PROJECT_DIR/venv/bin/gunicorn --bind 127.0.0.1:8000 --workers 3 wsgi:application
Restart=always
RestartSec=5

# Security settings
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ReadWritePaths=$PROJECT_DIR

[Install]
WantedBy=multi-user.target
EOF

# 12. Services starten
log_info "Services werden gestartet..."
sudo systemctl daemon-reload
sudo systemctl enable asset-management
sudo systemctl restart asset-management
sudo systemctl restart nginx

# 13. Let's Encrypt SSL (optional)
read -p "Möchten Sie SSL mit Let's Encrypt einrichten? (y/n): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    log_info "SSL-Zertifikat wird eingerichtet..."
    YOUR_DOMAIN=""
    read -p "Bitte geben Sie Ihre Domain ein (z.B. assets.ihre-domain.de): " YOUR_DOMAIN

    if [ ! -z "$YOUR_DOMAIN" ]; then
        sudo certbot --nginx -d "$YOUR_DOMAIN"
        sudo systemctl reload nginx
        log_info "SSL-Zertifikat erfolgreich eingerichtet!"
    fi
fi

# 14. Bereinigung
log_info "Bereinigung wird durchgeführt..."
sudo apt autoremove -y
sudo apt autoclean

# 15. Abschluss
log_info "🎉 Deployment erfolgreich abgeschlossen!"
echo ""
echo "📋 Nächste Schritte:"
echo "1. .env Datei bearbeiten mit Ihren Einstellungen"
echo "2. Datenbank migrieren: flask db upgrade"
echo "3. Anwendung testen: http://ihre-domain.de"
echo "4. Admin-Account erstellen oder bestehenden verwenden"
echo ""
echo "🔧 Verwaltung:"
echo "  Status prüfen: sudo systemctl status asset-management"
echo "  Logs ansehen:  sudo journalctl -u asset-management -f"
echo "  Neustart:      sudo systemctl restart asset-management"
echo "  Updates:       ./deploy.sh"
echo ""
echo "⚠️  Sicherheitshinweise:"
echo "  - Ändern Sie alle Passwörter in .env"
echo "  - Aktivieren Sie Fail2Ban für SSH-Schutz"
echo "  - Überwachen Sie die Logs regelmäßig"

# Virtual Environment deaktivieren
deactivate
