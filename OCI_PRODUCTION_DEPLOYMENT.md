# OCI Integration - Production Deployment Guide

## 🎯 Ziel
OCI-Integration von Entwicklung (localhost + ngrok) zu Production (https://techkopf.de) migrieren.

---

## ✅ Voraussetzungen

### Server-Anforderungen:
- ✅ Linux Server (Ubuntu/Debian empfohlen)
- ✅ Python 3.8+ installiert
- ✅ Webserver (Apache oder Nginx)
- ✅ SSL-Zertifikat für HTTPS (Let's Encrypt)
- ✅ Domain: `techkopf.de` mit DNS konfiguriert

### Netzwerk:
- ✅ Port 443 (HTTPS) muss öffentlich erreichbar sein
- ✅ Firewall erlaubt eingehende Verbindungen auf Port 443

---

## 📋 Phase 1: Lokale Vorbereitung

### 1.1 `.env` Datei für Production erstellen

Auf dem **lokalen Rechner**:

1. Kopiere `.env.example` zu `.env.production`:
```bash
cp .env.example .env.production
```

2. Bearbeite `.env.production`:
```bash
FLASK_APP=app
FLASK_ENV=production
SECRET_KEY=HIER-EINEN-SICHEREN-RANDOM-STRING-GENERIEREN
DATABASE_URL=sqlite:///app.db

# ✅ WICHTIG: Production Base URL
APP_BASE_URL=https://techkopf.de

# OCI Integration (shop.api.de)
OCI_SHOP_API_LOGIN_ID=204927
OCI_SHOP_API_USERNAME=Lars_Baust
OCI_SHOP_API_PASSWORD=Vonh3rz3n!

# Price Comparison APIs (optional)
GOOGLE_CUSTOM_SEARCH_API_KEY=your-api-key-if-available
GOOGLE_SHOPPING_ENGINE_ID=your-engine-id-if-available
```

**WICHTIG:** 
- `SECRET_KEY` generieren: `python -c "import secrets; print(secrets.token_hex(32))"`
- `APP_BASE_URL` MUSS `https://techkopf.de` sein (kein Trailing Slash!)

### 1.2 Debug-Logs entfernen (optional)

In `app/oci/routes.py` alle `print()` Debug-Ausgaben entfernen oder auskommentieren:

```python
# DEBUG: Log alle empfangenen Daten
# print("\n" + "="*80)
# print("🔍 OCI INBOUND DEBUG - Empfangene Daten:")
# ...
```

### 1.3 Code-Änderungen committen

```bash
git add .
git commit -m "Production-ready: OCI credentials in .env, HOOK_URL configurable"
git push origin main
```

---

## 📋 Phase 2: Server-Setup

### 2.1 Code auf Server deployen

SSH in deinen Server:
```bash
ssh user@techkopf.de
```

Projekt klonen oder updaten:
```bash
cd /var/www/
git clone https://github.com/YOUR-REPO/asset-management.git
# ODER: git pull origin main
```

### 2.2 `.env` Datei auf Server erstellen

```bash
cd /var/www/asset-management
nano .env
```

Füge die **Production-Konfiguration** ein (siehe 1.1):
```
APP_BASE_URL=https://techkopf.de
OCI_SHOP_API_LOGIN_ID=204927
OCI_SHOP_API_USERNAME=Lars_Baust
OCI_SHOP_API_PASSWORD=Vonh3rz3n!
...
```

**Speichern:** `CTRL+O`, `ENTER`, `CTRL+X`

### 2.3 Python Virtual Environment

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 2.4 Datenbank initialisieren

```bash
flask db upgrade
# ODER: python run.py (einmal starten und stoppen)
```

### 2.5 Webserver-Konfiguration

#### **Option A: Apache (mit mod_wsgi)**

Erstelle `/etc/apache2/sites-available/techkopf.de.conf`:

```apache
<VirtualHost *:443>
    ServerName techkopf.de
    ServerAdmin admin@techkopf.de

    # SSL Configuration
    SSLEngine on
    SSLCertificateFile /etc/letsencrypt/live/techkopf.de/fullchain.pem
    SSLCertificateKeyFile /etc/letsencrypt/live/techkopf.de/privkey.pem

    # WSGI Configuration
    WSGIDaemonProcess asset_management python-home=/var/www/asset-management/venv
    WSGIProcessGroup asset_management
    WSGIScriptAlias / /var/www/asset-management/wsgi.py

    <Directory /var/www/asset-management>
        <Files wsgi.py>
            Require all granted
        </Files>
    </Directory>

    # Static Files
    Alias /static /var/www/asset-management/app/static
    <Directory /var/www/asset-management/app/static>
        Require all granted
    </Directory>

    # Logs
    ErrorLog ${APACHE_LOG_DIR}/techkopf_error.log
    CustomLog ${APACHE_LOG_DIR}/techkopf_access.log combined
</VirtualHost>

# HTTP to HTTPS Redirect
<VirtualHost *:80>
    ServerName techkopf.de
    Redirect permanent / https://techkopf.de/
</VirtualHost>
```

`wsgi.py` erstellen:
```python
import sys
import os

# Add project directory to path
sys.path.insert(0, '/var/www/asset-management')

# Load .env
from dotenv import load_dotenv
load_dotenv('/var/www/asset-management/.env')

from app import create_app
application = create_app()
```

Aktivieren:
```bash
sudo a2ensite techkopf.de
sudo systemctl reload apache2
```

#### **Option B: Nginx + Gunicorn**

`/etc/nginx/sites-available/techkopf.de`:
```nginx
server {
    listen 80;
    server_name techkopf.de;
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name techkopf.de;

    ssl_certificate /etc/letsencrypt/live/techkopf.de/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/techkopf.de/privkey.pem;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location /static {
        alias /var/www/asset-management/app/static;
    }
}
```

Gunicorn starten:
```bash
gunicorn -w 4 -b 127.0.0.1:8000 'app:create_app()'
```

**Besser: Systemd Service** (`/etc/systemd/system/asset-management.service`):
```ini
[Unit]
Description=Asset Management Application
After=network.target

[Service]
User=www-data
WorkingDirectory=/var/www/asset-management
Environment="PATH=/var/www/asset-management/venv/bin"
ExecStart=/var/www/asset-management/venv/bin/gunicorn -w 4 -b 127.0.0.1:8000 'app:create_app()'

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl enable asset-management
sudo systemctl start asset-management
sudo systemctl reload nginx
```

### 2.6 SSL-Zertifikat (Let's Encrypt)

Falls noch nicht vorhanden:
```bash
sudo apt install certbot python3-certbot-apache
sudo certbot --apache -d techkopf.de
```

ODER für Nginx:
```bash
sudo apt install certbot python3-certbot-nginx
sudo certbot --nginx -d techkopf.de
```

---

## 📋 Phase 3: OCI bei shop.api.de konfigurieren

### 3.1 HOOK_URL testen

Teste, ob der OCI-Inbound-Endpoint erreichbar ist:

```bash
curl -X POST https://techkopf.de/oci/inbound \
  -d "NEW_ITEM-QUANTITY[0]=1" \
  -d "NEW_ITEM-VENDORMAT[0]=TEST123"
```

**Erwartetes Ergebnis:** Redirect zu Login oder Fehlermeldung (nicht 404!)

### 3.2 shop.api.de HOOK_URL updaten

**WICHTIG:** Falls shop.api.de die HOOK_URL speichert:

1. Logge dich in dein shop.api.de Konto ein
2. Gehe zu **Einstellungen → OCI-Konfiguration** (oder ähnlich)
3. Ändere HOOK_URL von:
   ```
   https://unfaced-delaney-bumpkinly.ngrok-free.dev/oci/inbound
   ```
   zu:
   ```
   https://techkopf.de/oci/inbound
   ```

**Falls shop.api.de HOOK_URL dynamisch akzeptiert:**
- Keine Änderung nötig! Die HOOK_URL wird bei jedem Outbound-Request mitgesendet.

---

## 📋 Phase 4: Production-Testing

### 4.1 Vollständiger OCI-Flow testen

1. Öffne https://techkopf.de/md3/order/wizard/step1
2. Wähle Lieferant & Standort → Weiter
3. **Step 2:** Klicke "Katalog öffnen"
4. shop.api.de öffnet sich → Artikel auswählen
5. "Bestellung übermitteln" klicken
6. ✅ Sollte zurück zu https://techkopf.de/md3/order/wizard/step2 redirecten
7. ✅ Asset sollte in der Liste erscheinen
8. Asset auswählen → Step 3 → Step 4 → Abschließen

### 4.2 Logs checken

**Apache:**
```bash
tail -f /var/log/apache2/techkopf_error.log
```

**Nginx + Gunicorn:**
```bash
journalctl -u asset-management -f
```

**Suche nach:**
```
✅ Geparste Items: 1
  Item 1: Schneider Kugelschreiber...
```

### 4.3 Troubleshooting

| Problem | Lösung |
|---------|--------|
| 404 bei `/oci/inbound` | Blueprint nicht registriert? `app.register_blueprint(oci_bp)` |
| CSRF-Fehler | `csrf.exempt(oci_bp)` fehlt in `app/__init__.py` |
| 500 Internal Server Error | Logs checken: `tail -f error.log` |
| Assets nicht erstellt | DB-Permissions? Supplier "shop.api.de" existiert? |
| Redirect zu Login | Session-Problem? `session.permanent = True` gesetzt? |

---

## 📊 Checkliste vor Go-Live

- [ ] `.env` mit Production-Werten erstellt
- [ ] `APP_BASE_URL=https://techkopf.de` gesetzt
- [ ] `SECRET_KEY` generiert (sicher & random)
- [ ] Code auf Server deployed (`git pull`)
- [ ] Virtual Environment aktiviert & Dependencies installiert
- [ ] Datenbank migriert (`flask db upgrade`)
- [ ] Webserver konfiguriert (Apache/Nginx)
- [ ] SSL-Zertifikat installiert & gültig
- [ ] OCI-Endpoint erreichbar: `curl https://techkopf.de/oci/inbound`
- [ ] shop.api.de HOOK_URL aktualisiert (falls nötig)
- [ ] Vollständiger OCI-Flow getestet
- [ ] Logs gecheckt (keine Fehler)
- [ ] ngrok gestoppt (nicht mehr benötigt!)

---

## 🔒 Sicherheits-Tipps

1. **Credentials nie in Git committen**
   - `.env` ist in `.gitignore` ✅
   - Nur `.env.example` committen

2. **Firewall konfigurieren**
   ```bash
   sudo ufw allow 80/tcp
   sudo ufw allow 443/tcp
   sudo ufw enable
   ```

3. **Regelmäßige Updates**
   ```bash
   sudo apt update && sudo apt upgrade
   pip install --upgrade -r requirements.txt
   ```

4. **Backups**
   - Datenbank regelmäßig sichern: `cp app.db app.db.backup`

---

## 📞 Support

Falls Probleme auftreten:
1. Logs checken
2. OCI Debug-Ausgaben aktivieren (temporär)
3. `curl`-Tests für HOOK_URL

---

## ✅ Nach erfolgreichem Deployment

**ngrok nicht mehr benötigt!** 🎉

Die OCI-Integration läuft jetzt vollständig über:
```
https://techkopf.de/oci/outbound  → shop.api.de
shop.api.de → https://techkopf.de/oci/inbound
```

**Gratulation!** 🚀
