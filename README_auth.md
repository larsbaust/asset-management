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

---

# RBAC & Rechteverwaltung (Stand Mai 2025)

## Überblick
Das System verwendet jetzt eine flexible rollenbasierte Rechteverwaltung (RBAC), mit der Zugriffe und Aktionen granular gesteuert werden können. Rechte ("Permissions") werden Rollen zugewiesen. Benutzer erhalten ihre Rechte über die zugewiesene Rolle.

### 1. Datenmodell
- **Role**: Name, Beschreibung, viele-zu-viele-Beziehung zu Permissions
- **Permission**: Name (z.B. `manage_users`, `edit_assets`), Beschreibung
- **User**: hat genau eine Rolle

### 2. Rechtezuweisung im UI
- Im Bereich "Rollenverwaltung" (`/admin/roles`) können Rollen beliebige Rechte per Checkbox zugewiesen werden.
- Neue Rechte können im Code (siehe `ensure_default_permissions()` in `admin.py`) ergänzt werden.

### 3. Rechteprüfung im Backend
- Granulare Prüfungen erfolgen mit dem Decorator:

```python
def permission_required(permission_name):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated or not current_user.role:
                flash('Nicht eingeloggt oder keine Rolle!', 'danger')
                return redirect(url_for('main.index'))
            if not any(p.name == permission_name for p in current_user.role.permissions):
                flash(f'Keine Berechtigung für: {permission_name}', 'danger')
                return redirect(url_for('main.index'))
            return f(*args, **kwargs)
        return decorated_function
    return decorator
```

**Beispiel:**
```python
@admin.route('/users')
@login_required
@permission_required('manage_users')
def user_management():
    ...
```

### 4. Rechteprüfung im Frontend (Jinja2)
- Über einen Jinja-Global kann im Template direkt geprüft werden, ob ein User ein bestimmtes Recht besitzt:

```python
# in create_app() in __init__.py
app.jinja_env.globals['has_permission'] = has_permission

def has_permission(user, perm_name):
    return user and user.role and any(p.name == perm_name for p in user.role.permissions)
```

**Beispiel im Template:**
```jinja
{% if has_permission(current_user, 'manage_users') %}
  <a href="{{ url_for('admin.user_management') }}">Benutzerverwaltung</a>
{% endif %}
```

### 5. Backup & Restore (ab 18.05.2025)

#### Neue Rechte
- **backup_data**: Darf Backups (ZIP) mit Datenbank und allen Uploads/Bildern erstellen
- **restore_data**: Darf Backups wiederherstellen (DB und Uploads werden überschrieben)
- Rechte können in der Rollenverwaltung beliebigen Rollen zugewiesen werden

#### UI/Bedienung
- Menüpunkt "Backup & Restore" nur sichtbar für Nutzer mit `backup_data`
- Restore-Button/Upload nur sichtbar für Nutzer mit `restore_data` (sonst Hinweis "keine Berechtigung")
- Backup erzeugt ZIP mit:
  - `instance/app.db`
  - `app/uploads/`
  - `app/static/uploads/`, `app/static/location_images/`, `app/static/location_gallery/`
- Restore spielt alle Bereiche zurück, legt vorher Sicherheitskopien an und leert die Zielordner

#### Absicherung
- Backend-Routen granular geschützt mit `@permission_required('backup_data')` bzw. `@permission_required('restore_data')`
- UI prüft Rechte mit `has_permission(current_user, 'backup_data')` und `has_permission(current_user, 'restore_data')`

#### Rechte zuweisen
- Im Adminbereich unter "Rollenverwaltung" (Checkboxen für neue Rechte)
- Beispiel: Admin-Rolle beide Häkchen setzen, andere Rollen nach Bedarf

**Letztes Update:** 18.05.2025
