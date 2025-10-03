# 🚀 Asset Management auf Strato - Einfache Anleitung für Anfänger
# ==============================================================

## 📋 Bevor wir starten - Was Sie brauchen:

1. **Strato Server-Zugang** (Sie haben bereits eine VM)
2. **SSH-Programm** (PuTTY oder Terminal)
3. **Etwa 15-20 Minuten Zeit**
4. **Ihre GitHub Repository-URL**

---

## 🖥️ Schritt 1: Verbindung zum Server herstellen

### Option A: Windows mit PuTTY
1. **PuTTY herunterladen:** https://www.putty.org/
2. **PuTTY öffnen**
3. **Server-Details eingeben:**
   - Host Name: `ihre-server-ip` (z.B. 192.168.1.100)
   - Port: 22
   - Connection Type: SSH
4. **"Open" klicken**
5. **Erstes Mal:** "Yes" bei Sicherheitswarnung klicken
6. **Anmelden mit:**
   - Login as: `ihr-benutzername`
   - Password: `ihr-passwort`

### Option B: Windows mit PowerShell/CMD
```cmd
ssh ihr-benutzername@ihre-server-ip
```
Passwort eingeben wenn gefragt.

### ✅ Erfolgsanzeichen:
Sie sehen eine Zeile wie: `ihr-benutzername@servername:~$`

---

## 📁 Schritt 2: Grundlegende Server-Vorbereitung

### 2.1: Server aktualisieren
```bash
sudo apt update
sudo apt upgrade -y
```
**Warten Sie bis fertig** (ca. 2-3 Minuten)

### 2.2: Git installieren (falls nicht vorhanden)
```bash
sudo apt install -y git
```

### 2.3: Projekt-Verzeichnis erstellen
```bash
mkdir -p ~/asset-management
cd ~/asset-management
```

---

## 💾 Schritt 3: Projekt herunterladen

### 3.1: Repository klonen
**Ersetzen Sie `IHR-GITHUB-USERNAME` mit Ihrem echten GitHub-Benutzernamen:**

```bash
git clone https://github.com/IHR-GITHUB-USERNAME/asset-management.git .
```

**Beispiel:**
```bash
git clone https://github.com/meinname/asset-management.git .
```

### 3.2: Erfolgsprüfung
```bash
ls -la
```
**Sie sollten sehen:** app/, requirements.txt, deploy_strato.sh, etc.

---

## 🐍 Schritt 4: Python-Umgebung einrichten

### 4.1: Python Virtual Environment erstellen
```bash
python3 -m venv venv
```

### 4.2: Virtual Environment aktivieren
```bash
source venv/bin/activate
```

**Erfolgsanzeichen:** `(venv)` am Anfang der Zeile

### 4.3: Pakete installieren
```bash
pip install -r requirements.txt
```

**Warten Sie bis fertig** (ca. 3-5 Minuten)

---

## ⚙️ Schritt 5: Konfiguration anpassen

### 5.1: .env Datei bearbeiten
```bash
nano .env
```

**Ändern Sie diese Zeilen:**

```env
# Diese Zeile ändern - starkes Passwort generieren:
SECRET_KEY=mein-sehr-langes-und-sicheres-passwort-123

# E-Mail Einstellungen (falls Sie E-Mails wollen):
MAIL_USERNAME=ihre-email@gmail.com
MAIL_PASSWORD=ihr-gmail-app-passwort

# Domain (optional - für korrekte Links):
DOMAIN=ihre-domain.de
```

**Speichern:** Strg+O, Enter, Strg+X

### 5.2: Datenbank einrichten
```bash
export FLASK_APP=app
flask db upgrade
```

---

## 🚀 Schritt 6: Anwendung starten (Test)

### 6.1: Einfacher Start für Test
```bash
python app/__init__.py
```

**Sie sollten sehen:**
```
Running on http://127.0.0.1:5000/
```

### 6.2: Test im Browser
1. **Öffnen Sie:** http://ihre-server-ip:5000
2. **Sie sollten die Login-Seite sehen**
3. **Anmelden mit:** admin / admin

### 6.3: Stoppen (Strg+C)

---

## 🌐 Schritt 7: Produktions-Setup (Nginx + SSL)

### 7.1: Nginx installieren
```bash
sudo apt install -y nginx certbot python3-certbot-nginx
```

### 7.2: Firewall konfigurieren
```bash
sudo ufw allow ssh
sudo ufw allow 'Nginx Full'
sudo ufw --force enable
```

### 7.3: Nginx-Konfiguration erstellen
```bash
sudo nano /etc/nginx/sites-available/asset-management
```

**Kopieren Sie diese komplette Konfiguration:**

```nginx
server {
    listen 80;
    server_name _;

    location /static/ {
        alias /home/ihr-benutzername/asset-management/static/;
        expires 1y;
    }

    location /uploads/ {
        alias /home/ihr-benutzername/asset-management/uploads/;
    }

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

**Speichern:** Strg+O, Enter, Strg+X

### 7.4: Nginx aktivieren
```bash
sudo ln -sf /etc/nginx/sites-available/asset-management /etc/nginx/sites-enabled/
sudo rm -f /etc/nginx/sites-enabled/default
sudo nginx -t
sudo systemctl restart nginx
```

---

## 🔧 Schritt 8: Anwendung als Service einrichten

### 8.1: Service-Datei erstellen
```bash
sudo nano /etc/systemd/system/asset-management.service
```

**Kopieren Sie diese komplette Konfiguration:**

```ini
[Unit]
Description=Asset Management Application
After=network.target

[Service]
User=ihr-benutzername
WorkingDirectory=/home/ihr-benutzername/asset-management
Environment="PATH=/home/ihr-benutzername/asset-management/venv/bin"
ExecStart=/home/ihr-benutzername/asset-management/venv/bin/gunicorn --bind 127.0.0.1:8000 wsgi:application
Restart=always

[Install]
WantedBy=multi-user.target
```

**Ersetzen Sie `ihr-benutzername` mit Ihrem echten Benutzernamen!**

### 8.2: Service starten
```bash
sudo systemctl daemon-reload
sudo systemctl enable asset-management
sudo systemctl start asset-management
```

### 8.3: Status prüfen
```bash
sudo systemctl status asset-management
```

**Sollte zeigen:** `active (running)`

---

## 🔒 Schritt 9: SSL-Zertifikat (optional)

**Nur wenn Sie eine Domain haben:**

```bash
sudo certbot --nginx -d ihre-domain.de
```

---

## ✅ Schritt 10: Finale Tests

### 10.1: Anwendung testen
**Öffnen Sie:** http://ihre-server-ip

**Sollte zeigen:**
- ✅ Login-Seite
- ✅ Anmeldung mit admin/admin funktioniert
- ✅ Dashboard lädt

### 10.2: Services prüfen
```bash
sudo systemctl status asset-management
sudo systemctl status nginx
```

**Beide sollten `active (running)` zeigen**

---

## 🚨 Häufige Probleme und Lösungen

### Problem: "Permission denied"
**Lösung:**
```bash
chmod +x deploy_strato.sh
```

### Problem: "Module not found"
**Lösung:**
```bash
source venv/bin/activate
pip install -r requirements.txt
```

### Problem: "Port already in use"
**Lösung:**
```bash
sudo systemctl stop asset-management
sudo systemctl start asset-management
```

### Problem: Anwendung lädt nicht
**Lösung:**
```bash
# Logs prüfen:
sudo journalctl -u asset-management -f

# Nginx Logs:
sudo tail -f /var/log/nginx/asset_error.log
```

---

## 📞 Support

Bei Problemen:
1. **Logs prüfen** (siehe oben)
2. **Services neu starten:**
   ```bash
   sudo systemctl restart asset-management
   sudo systemctl restart nginx
   ```
3. **Bei anhaltenden Problemen:** Screenshot der Fehlermeldung machen

---

## 🎯 Zusammenfassung

Sie haben jetzt:
- ✅ **Server vorbereitet**
- ✅ **Anwendung installiert**
- ✅ **Datenbank eingerichtet**
- ✅ **Webserver konfiguriert**
- ✅ **Sicherheit aktiviert**

**Die Anwendung läuft jetzt auf:** http://ihre-server-ip

**Viel Erfolg!** 🚀
