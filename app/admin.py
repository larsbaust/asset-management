from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from .models import User, db, AssetLog
from .forms import RegisterForm, RoleForm, EditUserForm

# Decorator für Admin-Zugriff
from functools import wraps

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            flash('Zugriff verweigert: Nicht eingeloggt!', 'danger')
            return redirect(url_for('main.index'))
        if not getattr(current_user, 'role', None):
            flash('Zugriff verweigert: Keine Rolle zugewiesen! Wende dich an den Administrator.', 'danger')
            return redirect(url_for('main.index'))
        if getattr(current_user.role, 'name', None) != 'Admin':
            flash(f'Zugriff verweigert: Nur für Admins! (Aktueller User: {current_user.username}, Rolle: {getattr(current_user.role, "name", None)})', 'danger')
            return redirect(url_for('main.index'))
        return f(*args, **kwargs)
    return decorated_function

# Granularer Rechte-Decorator

def permission_required(permission_name):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated:
                flash('Zugriff verweigert: Nicht eingeloggt!', 'danger')
                return redirect(url_for('main.index'))
            if not getattr(current_user, 'role', None):
                flash('Zugriff verweigert: Keine Rolle zugewiesen! Wende dich an den Administrator.', 'danger')
                return redirect(url_for('main.index'))
            if not any(p.name == permission_name for p in current_user.role.permissions):
                flash(f'Zugriff verweigert: Fehlendes Recht ({permission_name})', 'danger')
                return redirect(url_for('main.index'))
            return f(*args, **kwargs)
        return decorated_function
    return decorator

admin = Blueprint('admin', __name__, url_prefix='/admin')

@admin.route('/permissions_matrix')
@login_required
@admin_required
def permissions_matrix():
    from .models import Role, Permission
    roles = Role.query.order_by(Role.name).all()
    permissions = Permission.query.order_by(Permission.name).all()
    return render_template('admin/permissions_matrix.html', roles=roles, permissions=permissions)


# Decorator für Admin-Zugriff
from functools import wraps

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            flash('Zugriff verweigert: Nicht eingeloggt!', 'danger')
            return redirect(url_for('main.index'))
        if not getattr(current_user, 'role', None):
            flash('Zugriff verweigert: Keine Rolle zugewiesen! Wende dich an den Administrator.', 'danger')
            return redirect(url_for('main.index'))
        if getattr(current_user.role, 'name', None) != 'Admin':
            flash(f'Zugriff verweigert: Nur für Admins! (Aktueller User: {current_user.username}, Rolle: {getattr(current_user.role, "name", None)})', 'danger')
            return redirect(url_for('main.index'))
        return f(*args, **kwargs)
    return decorated_function

# Granularer Rechte-Decorator

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

# Asset-Logbuch im Adminbereich
@admin.route('/asset_log')
@login_required
@admin_required
def asset_log():
    logs = AssetLog.query.order_by(AssetLog.timestamp.desc()).limit(200).all()
    return render_template('admin/asset_log.html', logs=logs)

# Beispiel: Route für CSV-Import, geschützt durch das Recht 'import_csv'
@admin.route('/import')
@login_required
@permission_required('import_csv')
def import_csv():
    return render_template('admin/import_csv.html')

# --- Backup & Restore ---
import zipfile, io, os, shutil
from flask import send_file, request
from datetime import datetime

@admin.route('/backup', methods=['GET'])
@login_required
@admin_required
def backup():
    db_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'instance', 'app.db')
    uploads_path = os.path.join(os.path.dirname(__file__), 'uploads')
    static_path = os.path.join(os.path.dirname(__file__), 'static')
    static_uploads = os.path.join(static_path, 'uploads')
    static_location_images = os.path.join(static_path, 'location_images')
    static_location_gallery = os.path.join(static_path, 'location_gallery')
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zipf:
        # DB
        if os.path.exists(db_path):
            zipf.write(db_path, arcname='app.db')
        # Uploads (app/uploads)
        if os.path.exists(uploads_path):
            for root, dirs, files in os.walk(uploads_path):
                for file in files:
                    full_path = os.path.join(root, file)
                    rel_path = os.path.relpath(full_path, uploads_path)
                    zipf.write(full_path, arcname=os.path.join('uploads', rel_path))
        # Static uploads (app/static/uploads)
        if os.path.exists(static_uploads):
            for root, dirs, files in os.walk(static_uploads):
                for file in files:
                    full_path = os.path.join(root, file)
                    rel_path = os.path.relpath(full_path, static_path)
                    zipf.write(full_path, arcname=rel_path)
        # Static location_images
        if os.path.exists(static_location_images):
            for root, dirs, files in os.walk(static_location_images):
                for file in files:
                    full_path = os.path.join(root, file)
                    rel_path = os.path.relpath(full_path, static_path)
                    zipf.write(full_path, arcname=rel_path)
        # Static location_gallery
        if os.path.exists(static_location_gallery):
            for root, dirs, files in os.walk(static_location_gallery):
                for file in files:
                    full_path = os.path.join(root, file)
                    rel_path = os.path.relpath(full_path, static_path)
                    zipf.write(full_path, arcname=rel_path)

    zip_buffer.seek(0)
    timestamp =  datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
    return send_file(zip_buffer, as_attachment=True, download_name=f'backup_{timestamp}.zip', mimetype='application/zip')

@admin.route('/restore', methods=['GET', 'POST'])
@login_required
@permission_required('restore_data')
def restore():
    if request.method == 'POST':
        file = request.files.get('backup_zip')
        if not file or not file.filename.endswith('.zip'):
            flash('Bitte eine gültige ZIP-Datei auswählen.', 'danger')
            return redirect(url_for('admin.restore'))
        db_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'instance', 'app.db')
        uploads_path = os.path.join(os.path.dirname(__file__), 'uploads')
        static_path = os.path.join(os.path.dirname(__file__), 'static')
        static_uploads = os.path.join(static_path, 'uploads')
        static_location_images = os.path.join(static_path, 'location_images')
        static_location_gallery = os.path.join(static_path, 'location_gallery')
        # Backup aktuelle DB/Uploads/Static (Safety)
        if os.path.exists(db_path):
            shutil.copy2(db_path, db_path + '.bak')
        if os.path.exists(uploads_path):
            shutil.copytree(uploads_path, uploads_path + '_bak', dirs_exist_ok=True)
        if os.path.exists(static_uploads):
            shutil.copytree(static_uploads, static_uploads + '_bak', dirs_exist_ok=True)
        if os.path.exists(static_location_images):
            shutil.copytree(static_location_images, static_location_images + '_bak', dirs_exist_ok=True)
        if os.path.exists(static_location_gallery):
            shutil.copytree(static_location_gallery, static_location_gallery + '_bak', dirs_exist_ok=True)
        # Restore: Zielordner leeren
        for folder in [uploads_path, static_uploads, static_location_images, static_location_gallery]:
            if os.path.exists(folder):
                shutil.rmtree(folder)
            os.makedirs(folder, exist_ok=True)
        # Restore ZIP
        with zipfile.ZipFile(file, 'r') as zipf:
            for member in zipf.namelist():
                if member == 'app.db':
                    zipf.extract(member, os.path.join(os.path.dirname(os.path.dirname(__file__)), 'instance'))
                elif member.startswith('uploads/'):
                    target = os.path.join(uploads_path, member[len('uploads/'):])
                    os.makedirs(os.path.dirname(target), exist_ok=True)
                    with zipf.open(member) as src, open(target, 'wb') as dst:
                        shutil.copyfileobj(src, dst)
                elif member.startswith('static/uploads/'):
                    target = os.path.join(static_path, member[len('static/'):])
                    os.makedirs(os.path.dirname(target), exist_ok=True)
                    with zipf.open(member) as src, open(target, 'wb') as dst:
                        shutil.copyfileobj(src, dst)
                elif member.startswith('static/location_images/'):
                    target = os.path.join(static_path, member[len('static/'):])
                    os.makedirs(os.path.dirname(target), exist_ok=True)
                    with zipf.open(member) as src, open(target, 'wb') as dst:
                        shutil.copyfileobj(src, dst)
                elif member.startswith('static/location_gallery/'):
                    target = os.path.join(static_path, member[len('static/'):])
                    os.makedirs(os.path.dirname(target), exist_ok=True)
                    with zipf.open(member) as src, open(target, 'wb') as dst:
                        shutil.copyfileobj(src, dst)
        flash('Backup erfolgreich wiederhergestellt! Bitte Anwendung neu starten.', 'success')
        return redirect(url_for('admin.backup_restore'))
    return render_template('admin/backup_restore.html')

@admin.route('/backup_restore')
@login_required
@admin_required
def backup_restore():
    return render_template('admin/backup_restore.html')


# --- Datenbank Reset Funktionen ---
import sys
import os
import shutil
from datetime import datetime
from sqlalchemy import text

def backup_database_for_reset():
    """Erstellt ein Backup der Datenbank vor dem Zurücksetzen"""
    try:
        # Datenbank-Datei identifizieren (standardmäßig instance/app.db)
        db_path = os.path.join('instance', 'app.db')
        timestamp = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
        backup_name = f'db_reset_backup_{timestamp}.db'
        backup_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'backups')
        os.makedirs(backup_dir, exist_ok=True)
        backup_path = os.path.join(backup_dir, backup_name)
        
        # Datenbank kopieren
        shutil.copy2(db_path, backup_path)
        return backup_path
    except Exception as e:
        return None

def reset_assets_database():
    """Direkte SQL-Ausführung zum Löschen aller Asset-bezogenen Daten"""
    try:
        # Tabellen, die gelöscht werden müssen (in Reihenfolge der Abhängigkeiten)
        tables = [
            'asset_log',           # Asset-Logs
            'inventory_item',      # Inventur-Positionen
            'loan',                # Leihverhältnisse
            'document',            # Dokumente (mit asset_id)
            'cost_entry',          # Kosteneinträge
            'asset_suppliers',     # Asset-Lieferanten (Zuordnungstabelle)
            'asset_manufacturers', # Asset-Hersteller (Zuordnungstabelle)
            'asset',               # Assets selbst
        ]
        
        # Gelöschte Einträge zählen
        deleted = {}
        
        # Daten löschen
        for table in tables:
            try:
                if table == 'document':
                    # Bei Dokumenten nur die mit asset_id löschen
                    result = db.session.execute(text("DELETE FROM document WHERE asset_id IS NOT NULL"))
                    deleted[table] = result.rowcount
                else:
                    # Alle Daten löschen
                    result = db.session.execute(text(f"DELETE FROM {table}"))
                    deleted[table] = result.rowcount
            except Exception as e:
                db.session.rollback()
                raise e
        
        # Auto-Increment-IDs zurücksetzen (SQLite-spezifisch)
        for table in tables:
            db.session.execute(text(f"DELETE FROM sqlite_sequence WHERE name='{table}'"))
        
        # Änderungen speichern
        db.session.commit()
        return True, deleted
    except Exception as e:
        db.session.rollback()
        return False, {}

def reset_orders_database():
    """Direkte SQL-Ausführung zum Löschen aller Bestellungen"""
    try:
        # Tabellen, die gelöscht werden müssen (in Reihenfolge der Abhängigkeiten)
        tables = [
            'order_item',     # Bestellpositionen
            '"order"',       # Bestellungen selbst - mit Anführungszeichen, da SQL-Reserviertes Wort
        ]
        
        # Gelöschte Einträge zählen
        deleted = {}
        
        # Daten löschen
        for table in tables:
            try:
                result = db.session.execute(text(f"DELETE FROM {table}"))
                deleted[table] = result.rowcount
            except Exception as e:
                db.session.rollback()
                raise e
        
        # Auto-Increment-IDs zurücksetzen
        for table in tables:
            db.session.execute(text(f"DELETE FROM sqlite_sequence WHERE name='{table}'"))
        
        # Änderungen speichern
        db.session.commit()
        return True, deleted
    except Exception as e:
        db.session.rollback()
        return False, {}
        
def reset_inventory_database():
    """Direkte SQL-Ausführung zum Löschen aller Inventurdaten"""
    try:
        # Tabellen, die gelöscht werden müssen (in Reihenfolge der Abhängigkeiten)
        # Hinweis: inventory_item wird bereits bei den Assets behandelt
        tables = [
            'inventory_team',    # Inventur-Teams
            'inventory_session', # Inventur-Sessions/Vorgänge
        ]
        
        # Gelöschte Einträge zählen
        deleted = {}
        
        # Daten löschen
        for table in tables:
            try:
                result = db.session.execute(text(f"DELETE FROM {table}"))
                deleted[table] = result.rowcount
            except Exception as e:
                db.session.rollback()
                raise e
        
        # Auto-Increment-IDs zurücksetzen
        for table in tables:
            db.session.execute(text(f"DELETE FROM sqlite_sequence WHERE name='{table}'"))
        
        # Änderungen speichern
        db.session.commit()
        return True, deleted
    except Exception as e:
        db.session.rollback()
        return False, {}
        
def reset_suppliers_database():
    """Direkte SQL-Ausführung zum Löschen aller Lieferanten"""
    try:
        # Tabellen, die gelöscht werden müssen
        # Hinweis: asset_suppliers wird bereits bei den Assets behandelt
        tables = ['supplier']
        
        # Gelöschte Einträge zählen
        deleted = {}
        
        # Daten löschen
        for table in tables:
            try:
                result = db.session.execute(text(f"DELETE FROM {table}"))
                deleted[table] = result.rowcount
            except Exception as e:
                db.session.rollback()
                raise e
        
        # Auto-Increment-IDs zurücksetzen
        for table in tables:
            db.session.execute(text(f"DELETE FROM sqlite_sequence WHERE name='{table}'"))
        
        # Änderungen speichern
        db.session.commit()
        return True, deleted
    except Exception as e:
        db.session.rollback()
        return False, {}
        
def reset_locations_database():
    """Direkte SQL-Ausführung zum Löschen aller Standorte"""
    try:
        # Tabellen, die gelöscht werden müssen
        tables = ['location']
        
        # Gelöschte Einträge zählen
        deleted = {}
        
        # Daten löschen
        for table in tables:
            try:
                result = db.session.execute(text(f"DELETE FROM {table}"))
                deleted[table] = result.rowcount
            except Exception as e:
                db.session.rollback()
                raise e
        
        # Auto-Increment-IDs zurücksetzen
        for table in tables:
            db.session.execute(text(f"DELETE FROM sqlite_sequence WHERE name='{table}'"))
        
        # Änderungen speichern
        db.session.commit()
        return True, deleted
    except Exception as e:
        db.session.rollback()
        return False, {}
        
def reset_manufacturers_database():
    """Direkte SQL-Ausführung zum Löschen aller Hersteller"""
    try:
        # Tabellen, die gelöscht werden müssen
        # Hinweis: asset_manufacturers wird bereits bei den Assets behandelt
        tables = ['manufacturer']
        
        # Gelöschte Einträge zählen
        deleted = {}
        
        # Daten löschen
        for table in tables:
            try:
                result = db.session.execute(text(f"DELETE FROM {table}"))
                deleted[table] = result.rowcount
            except Exception as e:
                db.session.rollback()
                raise e
        
        # Auto-Increment-IDs zurücksetzen
        for table in tables:
            db.session.execute(text(f"DELETE FROM sqlite_sequence WHERE name='{table}'"))
        
        # Änderungen speichern
        db.session.commit()
        return True, deleted
    except Exception as e:
        db.session.rollback()
        return False, {}
        
def reset_assignments_database():
    """Direkte SQL-Ausführung zum Löschen aller Zuordnungen"""
    try:
        # Tabellen, die gelöscht werden müssen
        tables = ['assignment']
        
        # Gelöschte Einträge zählen
        deleted = {}
        
        # Daten löschen
        for table in tables:
            try:
                result = db.session.execute(text(f"DELETE FROM {table}"))
                deleted[table] = result.rowcount
            except Exception as e:
                db.session.rollback()
                raise e
        
        # Auto-Increment-IDs zurücksetzen
        for table in tables:
            db.session.execute(text(f"DELETE FROM sqlite_sequence WHERE name='{table}'"))
        
        # Änderungen speichern
        db.session.commit()
        return True, deleted
    except Exception as e:
        db.session.rollback()
        return False, {}

@admin.route('/reset', methods=['GET'])
@login_required
@admin_required
def reset_overview():
    return render_template('admin/reset_data.html')

@admin.route('/reset/execute', methods=['POST'])
@login_required
@admin_required
def execute_reset():
    # Sicherheitsabfrage - überprüfen Sie, ob der Benutzer ein spezielles Feld ausgefüllt hat
    confirmation = request.form.get('confirmation_text', '')
    if confirmation != 'RESET':
        flash('Der Reset wurde abgebrochen. Bitte geben Sie "RESET" ein, um zu bestätigen.', 'danger')
        return redirect(url_for('admin.reset_overview'))
        
    # Optionale Reset-Optionen
    reset_suppliers = 'reset_suppliers' in request.form
    reset_locations = 'reset_locations' in request.form
    reset_manufacturers = 'reset_manufacturers' in request.form
    reset_assignments = 'reset_assignments' in request.form
    
    # Backup erstellen
    backup_path = backup_database_for_reset()
    if not backup_path:
        flash('Backup konnte nicht erstellt werden! Reset abgebrochen.', 'danger')
        return redirect(url_for('admin.reset_overview'))
    
    results = {
        'backup': os.path.basename(backup_path),
        'assets': { 'success': False, 'deleted': {} },
        'orders': { 'success': False, 'deleted': {} },
        'inventory': { 'success': False, 'deleted': {} },
        'suppliers': { 'success': True, 'deleted': {}, 'skipped': not reset_suppliers },
        'locations': { 'success': True, 'deleted': {}, 'skipped': not reset_locations },
        'manufacturers': { 'success': True, 'deleted': {}, 'skipped': not reset_manufacturers },
        'assignments': { 'success': True, 'deleted': {}, 'skipped': not reset_assignments }
    }
    
    # Assets zurücksetzen
    try:
        success, deleted = reset_assets_database()
        results['assets']['success'] = success
        results['assets']['deleted'] = deleted
    except Exception as e:
        results['assets']['error'] = str(e)
    
    # Bestellungen zurücksetzen
    try:
        success, deleted = reset_orders_database()
        results['orders']['success'] = success
        results['orders']['deleted'] = deleted
    except Exception as e:
        results['orders']['error'] = str(e)
    
    # Inventurdaten zurücksetzen
    try:
        success, deleted = reset_inventory_database()
        results['inventory']['success'] = success
        results['inventory']['deleted'] = deleted
    except Exception as e:
        results['inventory']['error'] = str(e)
        
    # Optional: Lieferanten zurücksetzen
    if reset_suppliers:
        try:
            success, deleted = reset_suppliers_database()
            results['suppliers']['success'] = success
            results['suppliers']['deleted'] = deleted
        except Exception as e:
            results['suppliers']['success'] = False
            results['suppliers']['error'] = str(e)
    
    # Optional: Standorte zurücksetzen
    if reset_locations:
        try:
            success, deleted = reset_locations_database()
            results['locations']['success'] = success
            results['locations']['deleted'] = deleted
        except Exception as e:
            results['locations']['success'] = False
            results['locations']['error'] = str(e)
            
    # Optional: Hersteller zurücksetzen
    if reset_manufacturers:
        try:
            success, deleted = reset_manufacturers_database()
            results['manufacturers']['success'] = success
            results['manufacturers']['deleted'] = deleted
        except Exception as e:
            results['manufacturers']['success'] = False
            results['manufacturers']['error'] = str(e)
            
    # Optional: Zuordnungen zurücksetzen
    if reset_assignments:
        try:
            success, deleted = reset_assignments_database()
            results['assignments']['success'] = success
            results['assignments']['deleted'] = deleted
        except Exception as e:
            results['assignments']['success'] = False
            results['assignments']['error'] = str(e)
    
    # Erfolg überprüfen - für optionale Tabellen nur prüfen wenn sie zurückgesetzt werden sollten
    success = results['assets']['success'] and results['orders']['success'] and results['inventory']['success']
    if reset_suppliers:
        success = success and results['suppliers']['success']
    if reset_locations:
        success = success and results['locations']['success']
    if reset_manufacturers:
        success = success and results['manufacturers']['success']
    if reset_assignments:
        success = success and results['assignments']['success']
        
    if success:
        flash(f'Alle Daten wurden erfolgreich zurückgesetzt! Backup wurde erstellt: {results["backup"]}', 'success')
    else:
        flash('Es sind Fehler beim Zurücksetzen aufgetreten. Details finden Sie in den Ergebnissen.', 'warning')
    
    return render_template('admin/reset_results.html', results=results)

@admin.route('/changelog', methods=['GET', 'POST'])
@login_required
@admin_required
def changelog():
    import os
    from app.utils import generate_ai_changelog
    changelog_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'CHANGELOG.md')
    changelog_text = ''
    ai_summary = None
    if os.path.exists(changelog_path):
        with open(changelog_path, encoding='utf-8') as f:
            changelog_text = f.read()
    if request.method == 'POST' and 'generate_ai' in request.form:
        api_key = os.environ.get('OPENAI_API_KEY')
        if not api_key:
            flash('OpenAI API-Key nicht gesetzt! Bitte Umgebungsvariable OPENAI_API_KEY konfigurieren.', 'danger')
        else:
            ai_summary = generate_ai_changelog(api_key, n=10)
            if ai_summary:
                flash('KI-Changelog erfolgreich generiert.', 'success')
            else:
                flash('Fehler bei der KI-Zusammenfassung.', 'danger')
    if request.method == 'POST' and 'save_ai' in request.form and request.form.get('ai_text'):
        with open(changelog_path, 'w', encoding='utf-8') as f:
            f.write(request.form['ai_text'] + '\n\n' + changelog_text)
        flash('KI-Changelog wurde gespeichert.', 'success')
        return redirect(url_for('admin.changelog'))
    return render_template('admin/changelog.html', changelog_text=changelog_text, ai_summary=ai_summary)

@admin.route('/changelog/generate', methods=['POST'])
@login_required
@admin_required
def generate_changelog_route():
    from app.utils import generate_changelog
    msg = generate_changelog()
    flash(msg, 'success' if 'erfolgreich' in msg else 'danger')
    return redirect(url_for('admin.changelog'))

# --- Rollen & Rechte Verwaltung ---
from .models import Role, Permission

def ensure_default_permissions():
    # Standardrechte, falls noch keine existieren
    default_perms = [
        ('view_assets', 'Assets anzeigen'),
        ('edit_assets', 'Assets bearbeiten'),
        ('delete_assets', 'Assets löschen'),
        ('archive_asset', 'Assets archivieren'),
        ('restore_asset', 'Archivierte Assets wiederherstellen'),
        ('import_csv', 'CSV-Import'),
        ('manage_users', 'Benutzerverwaltung'),
        ('manage_roles', 'Rollenverwaltung'),
        ('backup_data', 'Backup erstellen'),
        ('restore_data', 'Backup wiederherstellen')
    ]
    for name, desc in default_perms:
        if not Permission.query.filter_by(name=name).first():
            db.session.add(Permission(name=name, description=desc))
    db.session.commit()

@admin.route('/roles')
@login_required
@admin_required
def role_management():
    ensure_default_permissions()
    roles = Role.query.order_by(Role.id).all()
    return render_template('admin/role_management.html', roles=roles)

@admin.route('/roles/add', methods=['GET', 'POST'])
@login_required
@admin_required
def add_role():
    ensure_default_permissions()
    form = RoleForm()
    if form.validate_on_submit():
        role = Role(name=form.name.data, description=form.description.data)
        role.permissions = Permission.query.filter(Permission.id.in_(form.permissions.data)).all()
        db.session.add(role)
        db.session.commit()
        flash('Rolle erfolgreich angelegt.', 'success')
        return redirect(url_for('admin.role_management'))
    return render_template('admin/edit_role.html', form=form, role=None)

@admin.route('/roles/edit/<int:role_id>', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_role(role_id):
    ensure_default_permissions()
    role = Role.query.get_or_404(role_id)
    form = RoleForm(obj=role)
    if request.method == 'GET':
        form.permissions.data = [p.id for p in role.permissions]
    if form.validate_on_submit():
        role.name = form.name.data
        role.description = form.description.data
        role.permissions = Permission.query.filter(Permission.id.in_(form.permissions.data)).all()
        db.session.commit()
        flash('Rolle aktualisiert.', 'success')
        return redirect(url_for('admin.role_management'))
    return render_template('admin/edit_role.html', form=form, role=role)

@admin.route('/roles/delete/<int:role_id>')
@login_required
@admin_required
def delete_role(role_id):
    role = Role.query.get_or_404(role_id)
    if role.name == 'Admin':
        flash('Die Admin-Rolle kann nicht gelöscht werden.', 'danger')
        return redirect(url_for('admin.role_management'))
    db.session.delete(role)
    db.session.commit()
    flash('Rolle gelöscht.', 'success')
    return redirect(url_for('admin.role_management'))


@admin.route('/users')
@login_required
@admin_required
def user_management():
    users = User.query.order_by(User.id).all()
    return render_template('admin/user_management.html', users=users)

@admin.route('/users/add', methods=['GET', 'POST'])
@login_required
@admin_required
def add_user():
    import os
    from werkzeug.utils import secure_filename
    form = RegisterForm()
    if form.validate_on_submit():
        if User.query.filter_by(username=form.username.data).first():
            flash('Benutzername bereits vergeben.', 'danger')
            return render_template('admin/add_user.html', form=form)
        if User.query.filter_by(email=form.email.data).first():
            flash('E-Mail-Adresse bereits vergeben.', 'danger')
            return render_template('admin/add_user.html', form=form)
        from .models import Role
        user = User(
            username=form.username.data,
            role=Role.query.get(form.role.data),
            vorname=form.vorname.data,
            nachname=form.nachname.data,
            email=form.email.data,
            street=form.street.data,
            postal_code=form.postal_code.data,
            city=form.city.data,
            phone=form.phone.data
        )
        user.set_password(form.password.data)
        # Profilbild speichern
        if form.profile_image.data:
            filename = secure_filename(form.profile_image.data.filename)
            img_path = os.path.join('static/profile_images', filename)
            os.makedirs(os.path.dirname(img_path), exist_ok=True)
            form.profile_image.data.save(img_path)
            user.profile_image = filename
        db.session.add(user)
        db.session.commit()
        flash('Benutzer erfolgreich angelegt.', 'success')
        return redirect(url_for('admin.user_management'))
    return render_template('admin/add_user.html', form=form)

import secrets
from flask_mail import Message

@admin.route('/users/edit/<int:user_id>', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_user(user_id):
    from werkzeug.utils import secure_filename
    user = User.query.get_or_404(user_id)
    form = EditUserForm(obj=user)
    if request.method == 'GET':
        if user.role_id:
            form.role.data = user.role_id
    if request.method == 'POST' and form.validate_on_submit():
        user.username = form.username.data
        from .models import Role
        user.role = Role.query.get(form.role.data)
        user.vorname = form.vorname.data
        user.nachname = form.nachname.data
        user.email = form.email.data
        user.street = form.street.data
        user.postal_code = form.postal_code.data
        user.city = form.city.data
        user.phone = form.phone.data
        if form.password.data:
            user.set_password(form.password.data)
        # Profilbild speichern
        if form.profile_image.data:
            filename = secure_filename(form.profile_image.data.filename)
            img_path = os.path.join('static/profile_images', filename)
            os.makedirs(os.path.dirname(img_path), exist_ok=True)
            form.profile_image.data.save(img_path)
            user.profile_image = filename
        db.session.commit()
        flash('Benutzerdaten aktualisiert.', 'success')
        return redirect(url_for('admin.user_management'))
    form.password.data = ''
    return render_template('admin/edit_user.html', form=form, user=user)

@admin.route('/users/delete/<int:user_id>')
@login_required
@admin_required
def delete_user(user_id):
    user = User.query.get_or_404(user_id)
    if user.username == 'admin':
        flash('Der Haupt-Admin kann nicht gelöscht werden.', 'danger')
        return redirect(url_for('admin.user_management'))
    db.session.delete(user)
    db.session.commit()
    flash('Benutzer gelöscht.', 'success')
    return redirect(url_for('admin.user_management'))
