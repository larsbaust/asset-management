# 🚀 Asset Management auf Strato - KOMPLETTE Anleitung von Anfang an
# ================================================================

## 📋 ABSOLUTE GRUNDLAGEN - Was Sie brauchen:

### 1. Strato Account
- ✅ **Strato Konto** (strato.de)
- ✅ **Linux VM gebucht** (Ubuntu/Debian)

### 2. Ihr Computer
- ✅ **Windows/Mac/Linux** Computer
- ✅ **Internetverbindung**

---

## 🌐 TEIL 1: Strato VM einrichten und Zugangsdaten bekommen

### Schritt 1.1: Strato Kundenbereich öffnen
1. **Gehe zu:** https://www.strato.de/login
2. **Anmelden** mit Ihren Strato-Zugangsdaten
3. **"Server" oder "Cloud" Bereich öffnen**

### Schritt 1.2: VM-Details finden
1. **Ihre VM finden** in der Server-Liste
2. **Klicken Sie auf Ihre VM**
3. **Suchen Sie diese Informationen:**

#### 📋 **Wichtige Daten notieren:**
- **Server-IP:** `192.168.x.x` oder `10.x.x.x`
- **Benutzername:** `root` oder `ihr-name`
- **Passwort:** Das von Strato vergebene

**Beispiel:**
```
Server-IP:     85.214.123.456
Benutzername:  root
Passwort:      ABCdef123!@#
```

### Schritt 1.3: SSH-Schlüssel (empfohlen)
**Für bessere Sicherheit - aber für Anfänger optional:**

1. **Strato Dashboard → Server → SSH-Schlüssel**
2. **Ihren öffentlichen SSH-Schlüssel hochladen**

**Ohne SSH-Schlüssel geht es auch mit Passwort.**

---

## 🖥️ TEIL 2: Verbindung zum Server herstellen

### Option A: Windows mit PuTTY (Empfohlen für Anfänger)

#### 2.1: PuTTY herunterladen und installieren
1. **Gehe zu:** https://www.putty.org/
2. **"Download PuTTY" klicken**
3. **putty.exe herunterladen**
4. **PuTTY starten** (Installation nicht nötig)

#### 2.2: Verbindung aufbauen
1. **PuTTY öffnen**
2. **Links:** "Session"
3. **Eingeben:**
   ```
   Host Name: 85.214.123.456  (Ihre Server-IP)
   Port: 22
   Connection Type: SSH
   ```
4. **"Open" klicken**

#### 2.3: Erstes Mal - Sicherheit bestätigen
- **Warnung erscheint:** "Yes" klicken
- **Server-Host-Key speichern**

#### 2.4: Anmelden
```
login as: root  (oder Ihr Benutzername)
Password: IhrPasswort
```

**✅ Erfolg:** Sie sehen `root@servername:~#`

### Option B: Windows PowerShell (Terminal)

1. **PowerShell öffnen** (Windows-Taste + "powershell")
2. **Verbinden:**
   ```powershell
   ssh root@85.214.123.456
   ```
3. **Passwort eingeben**

### Option C: Mac/Linux Terminal

1. **Terminal öffnen**
2. **Verbinden:**
   ```bash
   ssh root@85.214.123.456
   ```

---

## ⚙️ TEIL 3: Grundlegende Server-Konfiguration

### Schritt 3.1: Nicht-Root-Benutzer erstellen (Sicherheit)

```bash
# Neuen Benutzer erstellen
adduser meinname

# Administrator-Rechte geben
usermod -aG sudo meinname

# Testen
su - meinname
```

### Schritt 3.2: SSH-Schlüssel für neuen Benutzer (optional)

```bash
# Als neuer Benutzer:
mkdir ~/.ssh
chmod 700 ~/.ssh
nano ~/.ssh/authorized_keys

# Ihren öffentlichen SSH-Schlüssel einfügen
# Speichern: Strg+O, Enter, Strg+X
```

---

## 📁 TEIL 4: Projekt auf den Server laden

### Schritt 4.1: Projekt-Verzeichnis erstellen

```bash
# Als Ihr Benutzer (nicht root):
mkdir -p ~/asset-management
cd ~/asset-management
```

### Schritt 4.2: Git Repository klonen

**Ersetzen Sie `IHR-GITHUB-USERNAME`:**

```bash
git clone https://github.com/IHR-GITHUB-USERNAME/asset-management.git .
```

**Beispiel:**
```bash
git clone https://github.com/meinname/asset-management.git .
```

### Schritt 4.3: Erfolgsprüfung

```bash
ls -la
```

**Sollte zeigen:**
```
app/  requirements.txt  deploy_strato.sh  README.md  ...
```

---

## 🐍 TEIL 5: Python und Anwendung einrichten

### Schritt 5.1: Python Virtual Environment

```bash
python3 -m venv venv
source venv/bin/activate
```

**Erfolgsanzeichen:** `(venv)` vor dem Prompt

### Schritt 5.2: Pakete installieren

```bash
pip install -r requirements.txt
```

**Warten bis fertig** (ca. 3-5 Minuten)

### Schritt 5.3: .env Datei konfigurieren

```bash
nano .env
```

**Ändern Sie diese wichtigen Zeilen:**

```env
# Starkes Passwort (generieren Sie eins!)
SECRET_KEY=mein-langes-sicheres-passwort-123456789

# E-Mail (optional für jetzt)
MAIL_USERNAME=ihre-email@gmail.com
MAIL_PASSWORD=ihr-app-passwort

# Domain (falls vorhanden)
DOMAIN=ihre-domain.de
```

**Speichern:** Strg+O, Enter, Strg+X

### Schritt 5.4: Datenbank einrichten

```bash
export FLASK_APP=app
flask db upgrade
```

---

## 🚀 TEIL 6: Erster Test

### Schritt 6.1: Anwendung starten

```bash
python app/__init__.py
```

**Sollte zeigen:**
```
Running on http://127.0.0.1:5000/
```

### Schritt 6.2: Im Browser testen

1. **Browser öffnen**
2. **Adresse eingeben:** `http://85.214.123.456:5000`
3. **Login-Seite sollte erscheinen**
4. **Anmelden mit:** `admin` / `admin`

### Schritt 6.3: Stoppen

Terminal: **Strg+C** drücken

---

## 🌐 TEIL 7: Produktions-Setup

### Schritt 7.1: Nginx installieren

```bash
sudo apt update
sudo apt install -y nginx
```

### Schritt 7.2: Nginx konfigurieren

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

**Ersetzen Sie `ihr-benutzername` mit Ihrem Benutzernamen!**

### Schritt 7.3: Nginx aktivieren

```bash
sudo ln -sf /etc/nginx/sites-available/asset-management /etc/nginx/sites-enabled/
sudo rm -f /etc/nginx/sites-enabled/default
sudo nginx -t
sudo systemctl restart nginx
```

### Schritt 7.4: Anwendung als Service einrichten

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

**Ersetzen Sie `ihr-benutzername` mit Ihrem Benutzernamen!**

### Schritt 7.5: Service starten

```bash
sudo systemctl daemon-reload
sudo systemctl enable asset-management
sudo systemctl start asset-management
```

---

## ✅ TEIL 8: Finale Tests

### Schritt 8.1: Anwendung testen

**Browser öffnen:** `http://85.214.123.456`

**Sollte zeigen:**
- ✅ Login-Seite
- ✅ Anmeldung funktioniert
- ✅ Dashboard lädt

### Schritt 8.2: Services prüfen

```bash
sudo systemctl status asset-management
sudo systemctl status nginx
```

**Beide sollten:** `active (running)`

---

## 🔒 TEIL 9: Sicherheit und SSL (Optional)

### Firewall aktivieren
```bash
sudo ufw allow ssh
sudo ufw allow 'Nginx Full'
sudo ufw --force enable
```

### SSL-Zertifikat (wenn Sie eine Domain haben)
```bash
sudo apt install -y certbot python3-certbot-nginx
sudo certbot --nginx -d ihre-domain.de
```

---

## 🚨 TEIL 10: Häufige Probleme

### Problem: "Connection refused"
**Lösung:**
```bash
# Falsche IP? Prüfen Sie die Server-IP bei Strato
# Firewall blockiert? sudo ufw status
```

### Problem: "Permission denied"
**Lösung:**
```bash
# Richtiger Benutzername? Nicht als root arbeiten!
chmod +x setup_einfach.sh
```

### Problem: "Module not found"
**Lösung:**
```bash
source venv/bin/activate
pip install -r requirements.txt
```

---

## 🎯 **ZUSAMMENFASSUNG:**

Sie haben jetzt:
- ✅ **Strato VM-Zugang eingerichtet**
- ✅ **SSH-Verbindung hergestellt**
- ✅ **Projekt heruntergeladen**
- ✅ **Python-Umgebung konfiguriert**
- ✅ **Anwendung installiert**
- ✅ **Webserver konfiguriert**

**🚀 Ihre Anwendung läuft auf:** `http://ihre-server-ip`

---

**Viel Erfolg!** Bei Fragen einfach nachfragen! 😊
