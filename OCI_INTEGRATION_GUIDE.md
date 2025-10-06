# 🛒 OCI Integration Guide - shop.api.de

Vollständige Anleitung zur OCI (Open Catalog Interface) Integration mit shop.api.de.

---

## 📋 Was ist OCI?

**OCI (Open Catalog Interface)** ist ein Standard-Protokoll für E-Procurement im B2B-Bereich. Es ermöglicht die nahtlose Integration von externen Katalogen in Warenwirtschaftssysteme.

### Workflow:
```
1. User klickt "Katalog öffnen" in deinem System
2. → System öffnet shop.api.de mit OCI-Parametern
3. User sucht & wählt Artikel im shop.api.de Katalog
4. User klickt "Übernehmen" bei shop.api.de
5. → shop.api.de sendet Warenkorb zurück (POST)
6. System erstellt automatisch Assets aus Warenkorb
7. ✅ Bestellung kann abgeschlossen werden
```

---

## 🔑 Zugangsdaten

### shop.api.de OCI-Credentials:
```
URL:           https://shop.api.de/login?subUserLogin=1
Kundennummer:  204927
Mitbenutzer:   Lars_Baust
Passwort:      Vonh3rz3n!
```

**Wichtig:** SubUser-Login ist aktiviert (`subUserLogin=1`), daher wird `ausUserId` immer mit dem Mitbenutzer-Namen gesendet.

**⚠️ WICHTIG:** Diese Credentials sind in `app/oci/config.py` hinterlegt.

---

## 🚀 Setup & Installation

### 1. Dependencies prüfen
```bash
pip install -r requirements.txt
```

Benötigt: Flask, Flask-Login, SQLAlchemy

### 2. Umgebungsvariablen setzen

Erstelle `.env` (falls noch nicht vorhanden):
```bash
cp .env.example .env
```

**Wichtig:** Setze `APP_BASE_URL` für OCI-Callbacks:

#### Für lokale Entwicklung:
```env
APP_BASE_URL=http://127.0.0.1:5000
```

**Problem:** shop.api.de kann localhost nicht erreichen! 

**Lösung:** Verwende **ngrok** für externe Erreichbarkeit:

```bash
# ngrok installieren & starten
ngrok http 5000

# Kopiere die ngrok-URL (z.B. https://abc123.ngrok.io)
# In .env eintragen:
APP_BASE_URL=https://abc123.ngrok.io
```

#### Für Production (techkopf.de):
```env
APP_BASE_URL=https://techkopf.de
```

**OCI HOOK_URL wird dann:** `https://techkopf.de/oci/inbound`

### 3. Datenbank migrieren

Falls noch nicht geschehen:
```bash
flask db upgrade
```

### 4. Server starten
```bash
python run.py
```

---

## 📊 OCI-Felder (shop.api.de)

### Outbound (Request zu shop.api.de):
```python
loginId: '204927'              # Kundennummer (name="loginId" im HTML-Formular)
subUserId: 'Lars_Baust'        # Mitbenutzer (name="subUserId" im HTML-Formular)
password: 'Vonh3rz3n!'         # Passwort (name="password" im HTML-Formular)
HOOK_URL: 'https://..../oci/inbound'  # OCI Callback URL
```

**URL:** `https://shop.api.de/login?subUserLogin=1`

**Wichtig:** Die Feldnamen wurden aus dem HTML-Formular von shop.api.de extrahiert und stimmen exakt überein.

### Inbound (Response von shop.api.de):
```python
NEW_ITEM-QUANTITY[n]        # Anzahl des Produktes
NEW_ITEM-VENDORMAT[n]       # SKU
NEW_ITEM-DESCRIPTION[n]     # Titel
NEW_ITEM-PRICE[n]           # Preis
NEW_ITEM-CURRENCY[n]        # Währung (EUR)
NEW_ITEM-UNIT[n]            # Mengeneinheit
NEW_ITEM-VENDOR[n]          # SRM - Lieferantennummer
NEW_ITEM-MATGROUP[n]        # SRM - Warengruppe
NEW_ITEM-LEADTIME[n]        # Lieferzeit
NEW_ITEM-PRICEUNIT[n]       # Preiseinheit (1)
NEW_ITEM-CUST_FIELD1[n]     # Mehrwertsteuer (19%)
NEW_ITEM-LONGTEXT_1:132[]   # Beschreibung
```

---

## 🎯 Verwendung

### 1. Aus Bestellassistent

```
1. Öffne: http://127.0.0.1:5000/md3/order/wizard/step1
2. Step 1: "Alle Lieferanten" → Weiter
3. Step 2: "Katalog öffnen" Button klicken
4. → shop.api.de öffnet sich
5. Artikel suchen & auswählen
6. "Übernehmen" klicken
7. → Zurück zum System (Warenkorb-Vorschau)
8. "Assets erstellen & weiter" klicken
9. ✅ Assets werden erstellt, Bestellung fortsetzen
```

### 2. Direkt (für Tests)

```python
# OCI Outbound
GET http://127.0.0.1:5000/oci/outbound

# OCI Inbound (wird von shop.api.de aufgerufen)
POST http://127.0.0.1:5000/oci/inbound
```

---

## 🧪 Testing

### Test-Endpunkt (ohne shop.api.de)

Für Entwicklung ohne echte shop.api.de Anbindung:

```
http://127.0.0.1:5000/oci/test-inbound
```

Simuliert einen OCI-Warenkorb mit Test-Daten.

---

## 🔧 Troubleshooting

### Problem: "HOOK_URL nicht erreichbar"

**Ursache:** shop.api.de kann `http://127.0.0.1:5000` nicht erreichen

**Lösung:** Verwende ngrok:
```bash
ngrok http 5000
# Setze APP_BASE_URL in .env auf die ngrok-URL
```

### Problem: "Keine Artikel im Warenkorb"

**Ursache:** OCI-Response wird nicht korrekt geparst

**Debug:**
1. Prüfe Logs: `flask run --debug`
2. Schaue in `app/oci/service.py` → `parse_inbound_response()`
3. Prüfe ob OCI-Feldnamen korrekt sind

### Problem: "Assets werden nicht erstellt"

**Ursache:** Supplier "shop.api.de" existiert nicht

**Lösung:** Wird automatisch angelegt. Prüfe DB:
```python
from app.models import Supplier
Supplier.query.filter_by(name='shop.api.de').first()
```

---

## 📁 Dateistruktur

```
app/
├── oci/
│   ├── __init__.py           # OCI-Modul
│   ├── config.py             # OCI-Konfiguration & Credentials
│   ├── service.py            # Business Logic (Parser, Asset-Erstellung)
│   └── routes.py             # Flask-Endpunkte
├── templates/
│   └── oci/
│       ├── outbound.html     # Auto-Submit zu shop.api.de
│       └── cart_preview.html # Warenkorb-Vorschau
└── __init__.py               # OCI-Blueprint registriert
```

---

## 🎨 UI-Integration

### Bestellassistent (Step 2)

**Datei:** `app/templates/md3/order/wizard/step2.html`

OCI-Button-Sektion:
```html
<div class="md3-card wizard-card">
  <div>🛒 Artikel aus shop.api.de Katalog</div>
  <a href="{{ url_for('oci.outbound') }}">
    Katalog öffnen
  </a>
</div>
```

### Preisvergleich-Modal

OCI-Preise werden automatisch im Hybrid-Preisvergleich angezeigt:
```
🏢 B2B-Lieferanten:
• shop.api.de: 1.200€ (aus OCI-Sync)
```

---

## 🔐 Sicherheit

### Best Practices:

1. **Credentials nicht im Code:** ✅ In `config.py` ausgelagert
2. **HTTPS in Production:** ⚠️ Für OCI-Callbacks zwingend
3. **Session-Validierung:** ✅ Implementiert in `routes.py`
4. **CSRF-Protection:** ⚠️ Nicht für `/oci/inbound` (externe Calls)

### Production Checklist:

- [ ] APP_BASE_URL auf HTTPS-Domain setzen
- [ ] Credentials in Umgebungsvariablen verschieben
- [ ] Rate-Limiting für OCI-Endpunkte aktivieren
- [ ] Logging für OCI-Requests aktivieren
- [ ] Error-Handling testen

---

## 📈 Erweiterte Features (Optional)

### 1. Automatische Preis-Synchronisation

OCI-Preise automatisch in `AssetSupplierPrice` speichern:

```python
from app.oci.service import OCIService

# Nach OCI-Inbound
items = OCIService.parse_inbound_response(form_data)
OCIService.sync_prices_from_oci(items)
```

### 2. Multi-Supplier-OCI

Weitere Lieferanten hinzufügen:

```python
# app/oci/config.py
OCI_SUPPLIERS = {
    'shop.api.de': {
        'url': 'https://shop.api.de/login',
        'loginId': '204927',
        'username': 'Lars_Baust',
        'password': 'Vonh3rz3n!'
    },
    'supplier2.de': {
        'url': 'https://supplier2.de/oci',
        'loginId': 'xxx',
        # ...
    }
}
```

### 3. OCI-Bestellhistorie

Tracking aller OCI-Bestellungen:

```python
class OCIOrder(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    supplier = db.Column(db.String(100))
    items_json = db.Column(db.Text)  # JSON der OCI-Items
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
```

---

## 🤝 Support

Bei Fragen zur OCI-Integration:

1. **shop.api.de Support:** Für OCI-spezifische Fragen
2. **Logs prüfen:** `flask run --debug`
3. **Test-Endpunkt:** `/oci/test-inbound`

---

## ✅ Fertig!

Die OCI-Integration ist vollständig implementiert und ready for use!

**Next Steps:**
1. ngrok starten (für lokale Tests)
2. APP_BASE_URL in `.env` setzen
3. Server starten: `python run.py`
4. Bestellassistent öffnen & "Katalog öffnen" testen

**Viel Erfolg! 🚀**
