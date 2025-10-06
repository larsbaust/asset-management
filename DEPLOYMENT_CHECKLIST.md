# 🚀 Deployment Checklist - techkopf.de

Checkliste für das Deployment der OCI-Integration auf **https://techkopf.de/**

---

## ✅ Vor dem Deployment

### 1. Lokale Tests abgeschlossen
- [ ] OCI-Outbound funktioniert (Katalog öffnet sich)
- [ ] OCI-Inbound funktioniert (Warenkorb kommt zurück)
- [ ] Assets werden korrekt erstellt
- [ ] Preisvergleich zeigt OCI-Preise an
- [ ] Hybrid-Preisvergleich (OCI + WWW) funktioniert

### 2. Production-Konfiguration vorbereiten

**Erstelle `.env` für Production:**

```bash
# Production Environment
FLASK_ENV=production
SECRET_KEY=<DEIN-SICHERER-SECRET-KEY>
DATABASE_URL=<DEINE-PRODUCTION-DB>

# OCI Integration - Production Domain
APP_BASE_URL=https://techkopf.de

# Optional: API Keys
GOOGLE_CUSTOM_SEARCH_API_KEY=<falls-vorhanden>
GOOGLE_SHOPPING_ENGINE_ID=<falls-vorhanden>
```

**⚠️ WICHTIG:** `SECRET_KEY` muss ein starker, zufälliger String sein!

Generieren:
```python
import secrets
print(secrets.token_hex(32))
```

### 3. Credentials sichern

**OCI Credentials aus Code entfernen:**

Aktuell in `app/oci/config.py`:
```python
SHOP_API_URL = 'https://shop.api.de/login?subUserLogin=1'
SHOP_API_LOGIN_ID = '204927'
SHOP_API_USERNAME = 'Lars_Baust'
SHOP_API_PASSWORD = 'Vonh3rz3n!'
```

**Verschieben nach `.env`:**
```bash
OCI_SHOP_API_LOGIN_ID=204927
OCI_SHOP_API_PASSWORD=Vonh3rz3n!
OCI_SHOP_API_USERNAME=Lars_Baust
```

**Dann in `config.py` ändern:**
```python
import os
SHOP_API_LOGIN_ID = os.getenv('OCI_SHOP_API_LOGIN_ID', '204927')
SHOP_API_PASSWORD = os.getenv('OCI_SHOP_API_PASSWORD')
SHOP_API_USERNAME = os.getenv('OCI_SHOP_API_USERNAME', 'Lars_Baust')
```

---

## 🔧 Deployment-Schritte

### 1. Code auf Server hochladen

```bash
# Git commit & push
git add .
git commit -m "Add OCI integration + Hybrid price comparison"
git push origin main

# Auf Server: Pull latest code
cd /path/to/techkopf.de
git pull origin main
```

### 2. Dependencies installieren

```bash
pip install -r requirements.txt
```

**Prüfe besonders:**
- beautifulsoup4 (für Scraping)
- Flask, Flask-Login, Flask-SQLAlchemy

### 3. Datenbank migrieren

```bash
flask db upgrade
```

**Prüft:**
- AssetSupplierPrice Tabelle erstellt
- Alle Migrations erfolgreich

### 4. .env konfigurieren

```bash
# Auf Server: .env erstellen
nano .env

# Oder von lokaler .env kopieren (ohne lokale Werte!)
```

**Setze:**
```
APP_BASE_URL=https://techkopf.de
```

### 5. OCI HOOK_URL bei shop.api.de prüfen

**Finale OCI-Callback-URL:**
```
https://techkopf.de/oci/inbound
```

**Falls shop.api.de IP-Whitelist hat:**
- Server-IP von techkopf.de bei shop.api.de hinterlegen

### 6. Webserver neu starten

```bash
# Beispiel für Gunicorn
sudo systemctl restart gunicorn

# Oder Apache/Nginx
sudo systemctl restart apache2
sudo systemctl restart nginx
```

### 7. SSL-Zertifikat prüfen

```bash
# Prüfe ob HTTPS funktioniert
curl -I https://techkopf.de

# Sollte 200 OK zurückgeben
```

**OCI benötigt HTTPS für HOOK_URL!**

---

## 🧪 Production-Tests

### Test 1: OCI-Outbound
```
1. Öffne: https://techkopf.de/md3/order/wizard/step1
2. Step 2 → "Katalog öffnen" klicken
3. ✅ shop.api.de öffnet sich
4. ✅ Login funktioniert automatisch
```

### Test 2: OCI-Inbound
```
1. Im shop.api.de Katalog: Artikel auswählen
2. "Übernehmen" klicken
3. ✅ Redirect zu https://techkopf.de/oci/cart-preview
4. ✅ Warenkorb-Artikel werden angezeigt
```

### Test 3: Asset-Erstellung
```
1. In Warenkorb-Vorschau: "Assets erstellen" klicken
2. ✅ Assets werden erstellt
3. ✅ Lieferantenpreise hinterlegt
4. ✅ Weiterleitung zu Step 2
```

### Test 4: Hybrid-Preisvergleich
```
1. Bei Asset: "Preisvergleich" klicken
2. ✅ B2B-Sektion zeigt shop.api.de Preise
3. ✅ WWW-Sektion zeigt Idealo/Geizhals Preise
4. ✅ Beste Preise werden korrekt sortiert
```

---

## 🔐 Security-Checks

### HTTPS erzwingen
```python
# In app/__init__.py (falls noch nicht vorhanden)
if not app.debug:
    @app.before_request
    def before_request():
        if request.url.startswith('http://'):
            url = request.url.replace('http://', 'https://', 1)
            return redirect(url, code=301)
```

### Rate Limiting für OCI
```python
# Optional: Flask-Limiter
from flask_limiter import Limiter

limiter = Limiter(app, key_func=get_remote_address)

@oci_bp.route('/inbound', methods=['POST'])
@limiter.limit("10 per minute")  # Max 10 OCI-Callbacks pro Minute
def inbound():
    ...
```

### Logging aktivieren
```python
# In config.py
import logging

logging.basicConfig(
    filename='oci.log',
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
```

---

## 📊 Monitoring nach Deployment

### Logs prüfen (erste 24h)
```bash
# OCI-spezifische Logs
grep "OCI" /var/log/flask/app.log

# Fehler prüfen
grep "ERROR" /var/log/flask/app.log
```

### Datenbank prüfen
```sql
-- Anzahl OCI-Preise
SELECT COUNT(*) FROM asset_supplier_price 
WHERE supplier_id = (SELECT id FROM supplier WHERE name='shop.api.de');

-- Neueste OCI-Assets
SELECT * FROM asset 
WHERE category='OCI Import' 
ORDER BY id DESC LIMIT 10;
```

### Performance testen
```bash
# Response-Zeit für OCI-Endpoints
time curl -X POST https://techkopf.de/oci/inbound
```

---

## ⚠️ Troubleshooting (Production)

### Problem: OCI-Callback erreicht Server nicht

**Check 1: Firewall**
```bash
# Prüfe ob Port 443 offen ist
sudo ufw status
sudo ufw allow 443/tcp
```

**Check 2: DNS**
```bash
# Prüfe DNS-Auflösung
nslookup techkopf.de
# Sollte zur Server-IP auflösen
```

**Check 3: Webserver-Config**
```bash
# Apache: Prüfe VirtualHost
sudo apache2ctl -S

# Nginx: Prüfe Config
sudo nginx -t
```

### Problem: Assets werden nicht erstellt

**Debug-Modus kurz aktivieren:**
```python
# In .env
FLASK_ENV=development
FLASK_DEBUG=1
```

**Logs prüfen:**
```bash
tail -f /var/log/flask/app.log
```

### Problem: Preise nicht im Vergleich sichtbar

**Prüfe AssetSupplierPrice:**
```sql
SELECT * FROM asset_supplier_price WHERE asset_id=<DEINE_ASSET_ID>;
```

**Falls leer: Manuell einfügen (Test):**
```sql
INSERT INTO asset_supplier_price 
(asset_id, supplier_id, price, last_updated)
VALUES 
(1, (SELECT id FROM supplier WHERE name='shop.api.de'), 1200.00, NOW());
```

---

## ✅ Post-Deployment Checklist

- [ ] OCI-Outbound funktioniert auf techkopf.de
- [ ] OCI-Inbound empfängt Callbacks
- [ ] Assets werden korrekt erstellt
- [ ] Lieferantenpreise werden gespeichert
- [ ] Hybrid-Preisvergleich funktioniert
- [ ] HTTPS ist erzwungen
- [ ] Logs werden geschrieben
- [ ] Performance ist gut (<2s Response)
- [ ] Keine Fehler in Logs
- [ ] shop.api.de wurde über Go-Live informiert

---

## 📞 Support-Kontakte

**Bei Problemen mit OCI:**
1. shop.api.de Support (OCI-spezifisch)
2. Logs prüfen: `/var/log/flask/app.log`
3. Test-Endpoint: `https://techkopf.de/oci/test-inbound`

**Bei Deployment-Problemen:**
1. Server-Logs prüfen
2. Webserver-Config prüfen
3. Firewall-Regeln prüfen

---

## 🎉 Nach erfolgreichem Deployment

**shop.api.de informieren:**
- [ ] OCI-Integration auf techkopf.de ist live
- [ ] HOOK_URL: `https://techkopf.de/oci/inbound`
- [ ] Kundennummer: 204927
- [ ] Kontakt: Lars_Baust

**Interne Dokumentation:**
- [ ] OCI-Workflow dokumentieren
- [ ] Screenshots für User-Guide
- [ ] FAQ für Mitarbeiter

---

**Viel Erfolg beim Deployment! 🚀**
