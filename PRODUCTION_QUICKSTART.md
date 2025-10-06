# 🚀 Production Deployment - Quick Start

## Schnellübersicht für Deployment auf techkopf.de

---

## ⏱️ Geschätzte Zeit: 30-60 Minuten

---

## 📝 Schritt 1: Lokale Vorbereitung (5 Min)

### `.env.production` erstellen:

```bash
# Datei erstellen
cp .env.example .env.production

# Bearbeiten
nano .env.production
```

**Wichtige Änderungen:**
```bash
APP_BASE_URL=https://techkopf.de  # ← WICHTIG!
SECRET_KEY=HIER-RANDOM-STRING     # ← python -c "import secrets; print(secrets.token_hex(32))"
OCI_SHOP_API_LOGIN_ID=204927
OCI_SHOP_API_USERNAME=Lars_Baust
OCI_SHOP_API_PASSWORD=Vonh3rz3n!
```

### Code committen:
```bash
git add .
git commit -m "Production-ready: OCI integration"
git push origin main
```

---

## 📝 Schritt 2: Server-Zugang (2 Min)

```bash
ssh USER@techkopf.de
```

**Benötigte Informationen:**
- SSH-User: `_____________`
- SSH-Password/Key: `_____________`
- Projekt-Pfad: `/var/www/` (Standard) oder `_____________`

---

## 📝 Schritt 3: Code deployen (5 Min)

```bash
cd /var/www/
git clone https://DEIN-REPO-URL/asset-management.git
# ODER: cd asset-management && git pull origin main

cd asset-management
```

---

## 📝 Schritt 4: `.env` auf Server erstellen (3 Min)

```bash
nano .env
```

**Kopiere Inhalt von `.env.production`** (siehe Schritt 1)

**Speichern:** `CTRL+O`, `ENTER`, `CTRL+X`

---

## 📝 Schritt 5: Python Environment (5 Min)

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

---

## 📝 Schritt 6: Datenbank (2 Min)

```bash
flask db upgrade
# ODER: python run.py (dann CTRL+C)
```

---

## 📝 Schritt 7: Webserver-Konfiguration (10-20 Min)

### Welcher Webserver läuft auf techkopf.de?

**Option A: Apache**
```bash
sudo nano /etc/apache2/sites-available/techkopf.de.conf
```

Siehe `OCI_PRODUCTION_DEPLOYMENT.md` → "2.5 Webserver-Konfiguration → Option A"

```bash
sudo a2ensite techkopf.de
sudo systemctl reload apache2
```

**Option B: Nginx + Gunicorn**
```bash
sudo nano /etc/nginx/sites-available/techkopf.de
sudo nano /etc/systemd/system/asset-management.service
```

Siehe `OCI_PRODUCTION_DEPLOYMENT.md` → "2.5 Webserver-Konfiguration → Option B"

```bash
sudo systemctl enable asset-management
sudo systemctl start asset-management
sudo nginx -t
sudo systemctl reload nginx
```

---

## 📝 Schritt 8: SSL-Zertifikat (5 Min)

**Falls noch nicht installiert:**

**Apache:**
```bash
sudo apt install certbot python3-certbot-apache -y
sudo certbot --apache -d techkopf.de
```

**Nginx:**
```bash
sudo apt install certbot python3-certbot-nginx -y
sudo certbot --nginx -d techkopf.de
```

**Falls bereits installiert:** ✅ Überspringen

---

## 📝 Schritt 9: Test OCI-Endpoint (2 Min)

```bash
curl -X POST https://techkopf.de/oci/inbound \
  -d "NEW_ITEM-QUANTITY[0]=1" \
  -d "NEW_ITEM-VENDORMAT[0]=TEST123"
```

**Erwartete Ausgabe:**
- **Gut:** Redirect (302) oder HTML-Seite
- **Schlecht:** 404 Not Found

---

## 📝 Schritt 10: Vollständiger OCI-Test (5 Min)

1. Öffne **https://techkopf.de/md3/order/wizard/step1**
2. Login (falls nötig)
3. Step 1: Lieferant wählen → Weiter
4. **Step 2: "Katalog öffnen"**
5. shop.api.de → Artikel auswählen
6. "Bestellung übermitteln"
7. ✅ **Zurück zu techkopf.de/md3/order/wizard/step2**
8. ✅ **Asset ist in der Liste!**

---

## ✅ Checkliste

- [ ] `.env.production` lokal erstellt
- [ ] `APP_BASE_URL=https://techkopf.de` gesetzt
- [ ] Code auf Server deployed
- [ ] `.env` auf Server erstellt
- [ ] Virtual Environment installiert
- [ ] Dependencies installiert (`pip install -r requirements.txt`)
- [ ] Datenbank migriert
- [ ] Webserver konfiguriert (Apache ODER Nginx)
- [ ] SSL-Zertifikat vorhanden
- [ ] OCI-Endpoint erreichbar (`curl` Test)
- [ ] Vollständiger OCI-Flow getestet
- [ ] ngrok gestoppt (nicht mehr benötigt!)

---

## 🆘 Troubleshooting

### Problem: 404 bei `/oci/inbound`

**Lösung:** Webserver neu starten
```bash
# Apache
sudo systemctl restart apache2

# Nginx
sudo systemctl restart asset-management
sudo systemctl restart nginx
```

### Problem: 500 Internal Server Error

**Logs checken:**
```bash
# Apache
tail -f /var/log/apache2/error.log

# Nginx + Gunicorn
journalctl -u asset-management -f
```

### Problem: OCI-Import funktioniert nicht

**Debug-Modus aktivieren:**

In `app/oci/routes.py` sind bereits Debug-Ausgaben vorhanden:
```python
print("🔍 OCI INBOUND DEBUG - Empfangene Daten:")
# ...
```

Diese erscheinen in den Logs (siehe oben).

---

## 📞 Support-Kontakte

**Server-Admin:** `_____________`  
**Hosting-Provider:** `_____________`  
**DNS-Provider:** `_____________`

---

## 🎉 Nach erfolgreichem Deployment

**ngrok kann gestoppt werden!** 🎉

Die OCI-Integration läuft jetzt vollständig über:
```
https://techkopf.de
```

**Optional:**
- [ ] Debug-Logs in `routes.py` auskommentieren (für weniger Logs)
- [ ] shop.api.de HOOK_URL in deren System updaten (falls gespeichert)
- [ ] Backup-Strategie einrichten (`cron` für `app.db`)

---

## 📚 Weiterführende Dokumentation

- **Vollständiges Deployment-Guide:** `OCI_PRODUCTION_DEPLOYMENT.md`
- **OCI-Integration-Details:** `OCI_INTEGRATION_GUIDE.md`
- **Code-Dokumentation:** `app/oci/`

---

**Viel Erfolg beim Deployment!** 🚀
