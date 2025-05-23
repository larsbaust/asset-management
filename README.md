# Asset Management

A Flask-based asset management system for tracking inventory, managing assets, and conducting inventory checks.

## Neue Features & Änderungen (Mai 2025)

- **Inventur-Abschluss Bugfix:**  
  Der Abschluss einer Inventur aus der Planungsansicht funktioniert jetzt wieder zuverlässig.  
  Der Abschluss-Button ist nun ein eigenes Formular und sendet korrekt an die Abschluss-Route.  
  Nach dem Abschluss wird wie gewohnt ein Bericht erstellt und die Inventur als abgeschlossen angezeigt.
- **Login-Sicherheit:**  
  Accounts werden nach 5 Fehlversuchen für 10 Minuten gesperrt. Nutzer erhalten klare Hinweise.
- **Admin-Passwort-Reset:**  
  Admins können im User-Edit-Bereich ein neues Passwort generieren und direkt per E-Mail an den User senden.
- **Hilfetexte & Fehlermeldungen:**  
  Alle wichtigen Felder (Benutzername, Passwort, E-Mail) haben jetzt Tooltips und Hilfetexte. Fehlermeldungen sind klarer.
- **Passwort-Features:**  
  Sichtbarkeit umschaltbar, Live-Stärkeanzeige bei Eingabe.
- **E-Mail-Benachrichtigung:**  
  Nutzer werden bei Passwortänderungen automatisch informiert.
- **DB-Änderungen:**  
  Neue Felder `failed_logins` und `lock_until` in der User-Tabelle.  
  → Bei bestehenden Installationen ggf. `add_missing_user_columns.py` ausführen!
- **Backup-Hinweis:**  
  Vor Migrationen/Updates immer ein Backup der Datenbank anlegen!

### Manuelles Datenbank-Update (nur bei bestehenden Installationen)

Falls nach dem Update Fehler wie `no such column: user.failed_logins` auftreten, führe das Skript `add_missing_user_columns.py` aus:

```bash
python add_missing_user_columns.py
```

Das Skript ergänzt die neuen Spalten in der Datenbank. Vorher unbedingt ein Backup der Datei `instance/app.db` anlegen!


## Deployment to PythonAnywhere

1. Go to [PythonAnywhere](https://www.pythonanywhere.com/) and create a free account

2. Once logged in:
   - Click on "Web" in the top navigation
   - Click "Add a new web app"
   - Choose "Manual configuration"
   - Choose Python 3.9

3. In the "Code" section:
   - Go to "Files"
   - Upload all project files or use Git to clone the repository

4. In the "Web" section, configure:
   - Source code: /home/yourusername/asset-management
   - Working directory: /home/yourusername/asset-management
   - WSGI configuration file: Update the path in the WSGI file to point to your project's wsgi.py

5. Set up your virtual environment:
   ```bash
   mkvirtualenv --python=/usr/bin/python3.9 myenv
   pip install -r requirements.txt
   ```

6. Configure environment variables:
   - Go to the "Files" section
   - Create a .env file in your project directory
   - Add your environment variables:
     ```
     FLASK_APP=app
     FLASK_ENV=production
     SECRET_KEY=your-secret-key-here
     DATABASE_URL=sqlite:///app.db
     ```

7. Create the database:
   ```bash
   flask db upgrade
   ```

8. Reload your web app from the "Web" tab

Your application should now be live at yourusername.pythonanywhere.com

## Local Development

1. Create a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

---

## Password Reset via Email

### Features
- Nutzer können über „Passwort vergessen?“ einen Link zum Zurücksetzen ihres Passworts per E-Mail anfordern.
- Es wird ein sicherer Token verwendet (ablaufbar, keine Information ob E-Mail existiert).
- Das neue Passwort wird über einen Link in der E-Mail gesetzt.

### Einrichtung: Flask-Mail mit Gmail
1. Aktiviere 2-Faktor-Authentifizierung für dein Gmail-Konto.
2. Erstelle ein App-Passwort unter https://myaccount.google.com/apppasswords
3. Trage die Zugangsdaten in `app/__init__.py` ein:
   ```python
   app.config['MAIL_SERVER'] = 'smtp.gmail.com'
   app.config['MAIL_PORT'] = 587
   app.config['MAIL_USE_TLS'] = True
   app.config['MAIL_USERNAME'] = 'DEINE.GMAIL@GMAIL.COM'
   app.config['MAIL_PASSWORD'] = 'DEIN-APP-PASSWORT'
   app.config['MAIL_DEFAULT_SENDER'] = 'DEINE.GMAIL@GMAIL.COM'
   ```
   **Hinweis:** Niemals dein normales Gmail-Passwort verwenden!

### Sicherheit
- Der Rücksetz-Link ist 1 Stunde gültig.
- Es wird immer eine neutrale Rückmeldung angezeigt, egal ob die E-Mail existiert (Schutz vor Enumeration).
- Nach erfolgreichem Zurücksetzen kann sich der Nutzer mit dem neuen Passwort anmelden.

### Testen
1. Klicke auf „Passwort vergessen?“ im Login-Bereich.
2. Gib die E-Mail-Adresse deines Accounts ein.
3. Prüfe dein Postfach und folge dem Link.
4. Setze ein neues Passwort und logge dich ein.

---


3. Set up environment variables:
   - Copy .env.example to .env
   - Update the values as needed

4. Initialize the database:
   ```bash
   flask db upgrade
   ```

5. Run the application:
   ```bash
   flask run
   ```

## Features

- Asset Management
- Inventory Control
- Image Upload Support
- Multiple Assignments
- Manufacturer & Supplier Management
- Inventory Reports
- Search Functionality
