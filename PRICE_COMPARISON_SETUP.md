# 💰 Preisvergleich Setup-Anleitung

## 📋 Übersicht

Das Preisvergleich-Feature nutzt eine **Multi-Backend-Architektur**:

1. **Google Shopping API** (primär)
2. **Mock-Daten** (Fallback)

Ohne API-Konfiguration funktioniert das System mit Mock-Daten (Phase 1).

---

## 🔧 Google Shopping API Setup (Optional)

### **Schritt 1: Google Cloud Console**

1. Gehe zu [Google Cloud Console](https://console.cloud.google.com/)
2. Erstelle ein neues Projekt oder wähle ein bestehendes
3. Aktiviere die **Custom Search JSON API**:
   - Navigation: APIs & Services → Library
   - Suche nach "Custom Search API"
   - Klicke auf "Enable"

### **Schritt 2: API-Key erstellen**

1. Gehe zu: APIs & Services → Credentials
2. Klicke auf "Create Credentials" → "API Key"
3. Kopiere den API-Key
4. **Wichtig:** Beschränke den Key auf "Custom Search API" für Sicherheit

### **Schritt 3: Custom Search Engine erstellen**

1. Gehe zu [Programmable Search Engine](https://programmablesearchengine.google.com/)
2. Klicke auf "Add" (neue Suchmaschine erstellen)
3. Konfiguration:
   - **Sites to search:** Leer lassen (oder spezifische Shopping-Sites)
   - **Language:** Deutsch
   - **Name:** "Product Price Comparison"
4. Klicke auf "Create"
5. Gehe zu **Setup** → **Basic**
6. Aktiviere: **Image search:** OFF
7. Aktiviere: **Search the entire web:** ON
8. Kopiere die **Search engine ID** (Format: `abc123def456:xyz789`)

### **Schritt 4: .env Datei konfigurieren**

Erstelle eine `.env` Datei im Projekt-Root (oder nutze die bestehende):

```env
# Google Shopping API
GOOGLE_CUSTOM_SEARCH_API_KEY=dein-api-key-hier
GOOGLE_SHOPPING_ENGINE_ID=dein-search-engine-id-hier
```

---

## 💵 Kosten

### **Google Custom Search API**
- ✅ **100 Anfragen pro Tag:** Kostenlos
- ❌ **Darüber hinaus:** $5 pro 1.000 Anfragen

### **Empfehlung für Produktion**
Implementiere **Caching** (bereits im Code vorbereitet):
- Cache Ergebnisse für 24 Stunden
- Reduziert API-Calls drastisch
- Spart Kosten

---

## 🧪 Testen

### **Ohne API-Keys (Mock-Modus)**
```bash
python run.py
```
→ System nutzt automatisch Mock-Daten

### **Mit API-Keys**
```bash
# .env Datei mit Keys füllen
python run.py
```
→ System nutzt echte Google Shopping Daten

---

## 🔍 Debugging

### **API-Key funktioniert nicht?**

Prüfe in den Logs:
```
Google Shopping API not configured, using fallback
```

**Lösung:**
1. API-Key korrekt in `.env`?
2. Custom Search API aktiviert?
3. Search Engine ID korrekt?

### **Keine Ergebnisse?**

**Mögliche Ursachen:**
- EAN/GTIN nicht hinterlegt beim Asset
- Produkt nicht in Google Shopping
- Rate Limit erreicht (100/Tag)

**Lösung:**
- EAN-Codes in Asset-Verwaltung pflegen
- Fallback auf Mock-Daten aktiviert

---

## 🚀 Erweiterungen (Zukunft)

### **Alternative APIs hinzufügen**

Die Architektur unterstützt beliebige Backends:

```python
# app/services/price_comparison.py

class BingShoppingBackend(PriceComparisonBackend):
    def search_prices(self, query, ean, gtin):
        # Bing API Implementation
        pass

# In PriceComparisonService.__init__()
self.backends = [
    GoogleShoppingBackend(),
    BingShoppingBackend(),  # NEU!
    MockBackend(),
]
```

### **Caching implementieren**

```python
from flask_caching import Cache

cache = Cache()

@cache.memoize(timeout=86400)  # 24 Stunden
def get_cached_prices(asset_id):
    # ...
```

---

## 📚 Weitere Ressourcen

- [Google Custom Search Documentation](https://developers.google.com/custom-search/v1/overview)
- [Google Cloud Pricing Calculator](https://cloud.google.com/products/calculator)
- [Alternative APIs: Bing Product Search](https://www.microsoft.com/en-us/bing/apis/bing-web-search-api)

---

## ✅ Checkliste

- [ ] Google Cloud Projekt erstellt
- [ ] Custom Search API aktiviert
- [ ] API-Key erstellt und beschränkt
- [ ] Custom Search Engine erstellt
- [ ] Search Engine ID kopiert
- [ ] `.env` Datei konfiguriert
- [ ] Getestet mit echten Daten
- [ ] EAN-Codes bei Assets gepflegt

---

**Bei Fragen:** Siehe Flask-Logs für detaillierte Fehlermeldungen!
