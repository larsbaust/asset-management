# Authentifizierungs- und Navigationslogik

## Übersicht
Dieses Dokument beschreibt die aktuelle Logik zur Authentifizierung und Navigation in der Asset Management Anwendung.

---

## 1. Zugriffsbeschränkung
- **Nur angemeldete Nutzer** können interne Seiten wie Dashboard, Assets, Standorte usw. sehen.
- **Nicht angemeldete Nutzer** werden automatisch zur Login-Seite weitergeleitet.
- Die Startseite `/` leitet direkt auf das Dashboard weiter, ist aber ebenfalls geschützt.

## 2. Navigation & Sichtbarkeit
- Navigationspunkte (z.B. Dashboard, Assets, Inventur) werden **nur angezeigt**, wenn der Nutzer eingeloggt ist.
- Die Navigation wird in `base.html` über `{% if current_user.is_authenticated %}` gesteuert.

## 3. Rollen & Registrierung
- Das Rollenfeld im Registrierungsformular ist **nur für Admins sichtbar**.
- Normale Nutzer können sich nur als "Benutzer" registrieren, die Rolle wird automatisch zugewiesen.
- Rollen können nur von Admins vergeben oder geändert werden (z.B. im Admin-Bereich).

## 4. Flash-Nachrichten
- Flash-Nachrichten erscheinen **immer oben rechts** (außer beim Login, dort mittig über dem Formular).
- Es wird immer nur **die letzte Nachricht** angezeigt.
- Die Anzeige wird in `base.html` und für Login in `login.html` gesteuert.

## 5. Wichtige Dateien
- `app/main.py`: Routen-Logik, Login-Schutz mit `@login_required`
- `app/templates/base.html`: Navigation, Flash-Nachrichten, Layout
- `app/templates/auth/login.html`: Login-Formular und Flash-Messages
- `app/templates/auth/register.html`: Registrierungsformular, Rollenfeld nur für Admins
- `app/admin.py`: Admin-Funktionen, Benutzerverwaltung

## 6. Besonderheiten & Hinweise
- Neue Nutzer erhalten automatisch die Rolle "Benutzer", wenn sie sich selbst registrieren.
- Nur Admins dürfen Rollen auswählen/ändern.
- Flash-Nachrichten werden automatisch nach 3 Sekunden ausgeblendet.

---

## Beispielablauf
1. **Nicht eingeloggt:**
   - Zugriff auf `/dashboard` → Weiterleitung zu `/login`
   - Navigation zeigt nur "Registrieren" und "Login"
2. **Registrierung als normaler Nutzer:**
   - Kein Rollenfeld sichtbar
   - Nach Registrierung automatisch als "Benutzer" eingeloggt
3. **Admin legt neuen Nutzer an:**
   - Rollenfeld sichtbar, Admin kann Rolle wählen

---

## Erweiterung/Änderung
- Neue geschützte Routen immer mit `@login_required` versehen.
- Für neue Rollen: Anpassung in Datenbank und Formularen erforderlich.

---

## Kontakt & Wartung
Bei Fragen oder für Erweiterungen bitte in diesem Dokument nachlesen oder direkt im Code (siehe oben genannte Dateien) nachschauen.
