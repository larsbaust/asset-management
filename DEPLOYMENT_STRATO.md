# Asset Management - Strato Deployment Guide
# ===========================================

## 🚀 Übersicht

Dieses Dokument beschreibt die vollständige Einrichtung Ihrer Asset Management Anwendung auf einem Strato Linux-Server (Ubuntu/Debian).

## 📋 Voraussetzungen

- Strato VM mit Ubuntu 20.04 oder 22.04
- SSH-Zugang zur VM
- Domain/Subdomain (optional für SSL)
- GitHub Repository-Zugang

## 🛠️ Schritt-für-Schritt Anleitung

### 1. Erstmalige Server-Einrichtung

#### SSH-Verbindung herstellen
```bash
ssh ihr-benutzername@ihre-server-ip
```

#### Deployment-Script ausführen
```bash
# Script von GitHub herunterladen
wget https://raw.githubusercontent.com/IHR-USERNAME/asset-management/main/deploy_strato.sh

# Script ausführbar machen
chmod +x deploy_strato.sh

# Deployment starten
./deploy_strato.sh
```

Das Script führt automatisch aus:
- ✅ System-Updates
- ✅ Installation aller benötigten Pakete (Python, Nginx, etc.)
- ✅ Firewall-Konfiguration
- ✅ Git-Repository Setup
- ✅ Python Virtual Environment
- ✅ Abhängigkeiten-Installation
- ✅ Nginx-Konfiguration
- ✅ Systemd-Service-Erstellung
- ✅ Service-Start

### 2. Nach der Installation

#### .env Datei konfigurieren
```bash
cd ~/asset-management
nano .env
```

**Wichtige Einstellungen:**

```env
# Starkes Secret Key generieren
SECRET_KEY=abcdef1234567890abcdef1234567890abcdef1234567890abcdef1234567890

# Datenbank (SQLite für Einfachheit)
DATABASE_URL=sqlite:///app.db

# E-Mail (Gmail App-Password verwenden!)
MAIL_USERNAME=ihre-email@gmail.com
MAIL_PASSWORD=ihr-app-password

# Domain
DOMAIN=assets.ihre-domain.de
```

#### Datenbank migrieren
```bash
source venv/bin/activate
export FLASK_APP=app
flask db upgrade
```

### 3. SSL-Zertifikat (empfohlen)

Falls Sie eine Domain haben, aktivieren Sie SSL:

```bash
sudo certbot --nginx -d assets.ihre-domain.de
```

### 4. Anwendung testen

1. **Browser öffnen:** `http://ihre-server-ip` oder `https://assets.ihre-domain.de`
2. **Anmelden mit:** `admin` / `admin` (Standard-Account)
3. **Passwort ändern** nach erstem Login!

## 🔧 Verwaltung & Wartung

### Services verwalten

```bash
# Status prüfen
sudo systemctl status asset-management

# Logs ansehen
sudo journalctl -u asset-management -f

# Neustart
sudo systemctl restart asset-management

# Stoppen
sudo systemctl stop asset-management
```

### Updates durchführen

```bash
cd ~/asset-management
./deploy_strato.sh
```

### Backups

```bash
# Automatisches Backup aktivieren
sudo crontab -e

# Backup-Job hinzufügen:
# 0 2 * * * /home/ihr-user/asset-management/backup.sh
```

## 🔒 Sicherheit

### Firewall
- ✅ UFW ist aktiviert
- ✅ Nur SSH (22) und HTTP/HTTPS (80/443) offen
- ✅ Alle anderen Ports gesperrt

### Sicherheitstipps
- ✅ Starke Passwörter verwenden
- ✅ Regelmäßige Updates
- ✅ Fail2Ban für SSH-Schutz aktivieren
- ✅ Logs überwachen

## 📊 Monitoring

### Wichtige Logs
```bash
# Anwendungs-Logs
sudo journalctl -u asset-management -f

# Nginx-Logs
sudo tail -f /var/log/nginx/asset_access.log
sudo tail -f /var/log/nginx/asset_error.log

# System-Logs
sudo dmesg | tail -20
```

### System-Metriken
```bash
# Speicher
free -h

# Festplatten
df -h

# Last
uptime
```

## 🚨 Troubleshooting

### Häufige Probleme

#### 1. Anwendung startet nicht
```bash
# Logs prüfen
sudo journalctl -u asset-management --no-pager

# Service neu starten
sudo systemctl restart asset-management
```

#### 2. Datenbank-Fehler
```bash
# Datenbank neu migrieren
flask db upgrade

# Datenbank zurücksetzen (VORSICHT!)
flask db downgrade base
flask db upgrade
```

#### 3. Berechtigungsfehler
```bash
# Richtige Berechtigungen setzen
sudo chown -R ihr-user:ihr-user ~/asset-management
sudo chmod -R 755 ~/asset-management
```

#### 4. Nginx-Fehler
```bash
# Nginx-Konfiguration testen
sudo nginx -t

# Nginx neu laden
sudo systemctl reload nginx
```

### Support-Kontakt

Bei Problemen:
1. Logs prüfen (siehe oben)
2. GitHub Issues erstellen
3. Support kontaktieren

## 📚 Zusätzliche Ressourcen

- [Flask Deployment Guide](https://flask.palletsprojects.com/en/2.3.x/deploying/)
- [Gunicorn Dokumentation](https://docs.gunicorn.org/)
- [Nginx Dokumentation](https://nginx.org/en/docs/)
- [Let's Encrypt Guide](https://letsencrypt.org/getting-started/)

---

**Erstellt:** $(date)
**Version:** 1.0.0
