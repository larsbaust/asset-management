# 🔍 Debug: OCI Feldnamen herausfinden

## Problem:
OCI-Login bei shop.api.de schlägt fehl, manueller Login funktioniert.

## Lösung: Echte Feldnamen extrahieren

### Schritt 1: Browser DevTools öffnen
1. Öffne https://shop.api.de/login?subUserLogin=1 im Browser
2. Drücke **F12** (DevTools)
3. Tab **"Network"** auswählen

### Schritt 2: Manuell einloggen
1. Trage ein:
   - Kundennummer: 204927
   - Mitbenutzer: Lars_Baust
   - Passwort: Vonh3rz3n!
2. Klick "Anmelden"

### Schritt 3: POST-Request analysieren
1. Im Network-Tab: Suche nach dem **Login-Request** (meist "login" oder ähnlich)
2. Klick drauf
3. Tab **"Payload"** oder **"Form Data"** anschauen

### Schritt 4: Feldnamen notieren

**Beispiel was du sehen könntest:**
```
customerNumber: 204927
subUser: Lars_Baust
password: Vonh3rz3n!
_csrf: abc123...
```

### Diese Feldnamen brauchen wir für die OCI-Konfiguration!

---

## Alternative: Quellcode inspizieren

1. Rechtsklick auf ein Formular-Feld → "Element untersuchen"
2. Suche nach `<input name="???">`

**Beispiel:**
```html
<input type="text" name="customerNumber" id="login-customer">
<input type="text" name="subUser" id="login-subuser">
<input type="password" name="password" id="login-password">
```

Der `name="..."` Attribut ist das, was wir brauchen!
