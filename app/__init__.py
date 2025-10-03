from flask import Flask, render_template
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_migrate import Migrate
from flask_mail import Mail  # Flask-Mail für E-Mail-Versand
from flask_wtf import CSRFProtect
from flask_wtf.csrf import CSRFError
import os

mail = Mail()  # Mail-Objekt global initialisieren

db = SQLAlchemy()
from app.models import (
    Message, User, OrderComment, Asset, Assignment, Category, Manufacturer, Supplier, 
    Maintenance, Document, Loan, CostEntry, InventorySession, InventoryTeam, 
    InventoryItem, Location, LocationImage, AssetLog, Role, Permission
)
login_manager = LoginManager()
csrf = CSRFProtect()

from jinja2 import ChoiceLoader, FileSystemLoader
from .chat_socket import socketio, chat_bp

def create_app():
    app = Flask(__name__)
    # SVG-Placeholder-Funktion für Templates bereitstellen
    from app.utils import svg_placeholder
    app.jinja_env.globals['svg_placeholder'] = svg_placeholder

    # Rechte-Check als Jinja-Global
    def has_permission(user, perm_name):
        # Admin-Rolle hat automatisch ALLE Permissions
        if user and user.role and user.role.name == 'Admin':
            return True
        return user and user.role and any(p.name == perm_name for p in user.role.permissions)
    app.jinja_env.globals['has_permission'] = has_permission
    
    # Benutzerdefinierte Filter für Zahlenkonvertierung
    def safe_int(value, default=1):
        """Konvertiert einen Wert sicher zu einem Integer"""
        if value is None:
            return default
        try:
            if isinstance(value, str) and value.strip() == '':
                return default
            return int(float(value)) if int(float(value)) > 0 else default
        except (ValueError, TypeError):
            return default
    
    def safe_float(value, default=0.0):
        """Konvertiert einen Wert sicher zu einem Float"""
        if value is None:
            return default
        try:
            if isinstance(value, str) and value.strip() == '':
                return default
            return float(value)
        except (ValueError, TypeError):
            return default
    
    # Filter zur Verfügung stellen
    app.jinja_env.filters['safe_int'] = safe_int
    app.jinja_env.filters['safe_float'] = safe_float
    app.config['SECRET_KEY'] = 'your-secret-key'
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///app.db'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['UPLOAD_FOLDER'] = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'uploads')

    # === Flask-Mail Konfiguration für Gmail ===
    # Hinweis: Für Gmail wird ein App-Passwort benötigt (nicht das normale Login-Passwort!)
    app.config['MAIL_SERVER'] = 'smtp.gmail.com'
    app.config['MAIL_PORT'] = 587
    app.config['MAIL_USE_TLS'] = True
    app.config['MAIL_USERNAME'] = 'baust.lars@gmail.com'  # <-- HIER DEINE GMAIL EINTRAGEN
    app.config['MAIL_PASSWORD'] = 'kvki tnsv vgie udtu'      # <-- HIER APP-PASSWORT EINTRAGEN
    app.config['MAIL_DEFAULT_SENDER'] = 'baust.lars@gmail.com'
    mail.init_app(app)

    # Beide Template-Ordner bekannt machen
    app.jinja_loader = ChoiceLoader([
        FileSystemLoader(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'templates')),
        FileSystemLoader(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'templates'))
    ])

    # Blueprints registrieren
    from .auth import auth as auth_blueprint
    app.register_blueprint(auth_blueprint)
    from .main import main as main_blueprint
    app.register_blueprint(main_blueprint)
    from .admin import admin as admin_blueprint
    app.register_blueprint(admin_blueprint)
    from .routes_profile import profile_bp
    app.register_blueprint(profile_bp)
    from .messages import messages_bp
    app.register_blueprint(messages_bp)
    app.register_blueprint(chat_bp)
    # Der Order Blueprint wurde möglicherweise schon woanders registriert
    try:
        from .order import order as order_module
        app.register_blueprint(order_module, name='order_module')
    except ValueError as e:
        print(f"Info: {e}")
        
    # Location Blueprint registrieren
    from .location import location as location_module
    app.register_blueprint(location_module, url_prefix='/locations', name='location_module')
    
    # MD3 Inventory Blueprint registrieren
    from .inventory.md3_routes import inventory_bp
    app.register_blueprint(inventory_bp, url_prefix='/md3/inventory', name='md3_inventory')

    # MD3 Order Blueprint registrieren
    try:
        from .order.md3_routes import md3_order_bp
        app.register_blueprint(md3_order_bp)
    except Exception as e:
        print("Warnung: MD3 Order Blueprint konnte nicht registriert werden:", e)

    # MD3 Categories Blueprint registrieren
    from .categories import categories_bp
    app.register_blueprint(categories_bp, url_prefix='/md3/categories', name='md3_categories')

    # MD3 Manufacturers Blueprint registrieren
    from .manufacturers import manufacturers_bp
    app.register_blueprint(manufacturers_bp, url_prefix='/md3/manufacturers', name='md3_manufacturers')

    print("JINJA LOADER SUCHT IN:")
    for loader in app.jinja_loader.loaders:
        print("  -", getattr(loader, 'searchpath', None))
    pfad = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'deployment', 'app', 'templates', 'inventory', 'check_item.html')
    print("PFAD:", pfad)
    print("EXISTIERT:", os.path.exists(pfad))

    # Ensure upload directory exists
    if not os.path.exists(app.config['UPLOAD_FOLDER']):
        os.makedirs(app.config['UPLOAD_FOLDER'])

    db.init_app(app)
    migrate = Migrate(app, db)

    # CSP-Header für alle Antworten setzen
    @app.after_request
    def set_csp(response):
        response.headers['Content-Security-Policy'] = (
            "script-src 'self' 'unsafe-inline' https://unpkg.com https://cdn.jsdelivr.net https://cdnjs.cloudflare.com "
            "https://maps.googleapis.com https://cdn.socket.io; "
            "style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net https://cdnjs.cloudflare.com https://fonts.googleapis.com "
            "https://unpkg.com https://maps.googleapis.com; "
            "img-src 'self' data: https://*.googleapis.com https://*.gstatic.com https://*.ggpht.com; "
            "connect-src 'self' https://*.googleapis.com; "
            "font-src 'self' https://fonts.gstatic.com https://cdnjs.cloudflare.com data:;"
        )
        return response

    # Flask-Mail initialisieren
    mail.init_app(app)

    # Login manager setup
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'
    # CSRF protection
    csrf.init_app(app)

    # Freundlicher Fehler-Handler für CSRF-Fehler
    @app.errorhandler(CSRFError)
    def handle_csrf_error(e):
        # Render a friendly MD3-styled error page
        reason = getattr(e, 'description', 'CSRF-Validierung fehlgeschlagen')
        return render_template('errors/csrf_error.html', reason=reason), 400

    from app.models import User
    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))


    from app.order import order as order_blueprint
    app.register_blueprint(order_blueprint)

    from app.suppliers import suppliers as suppliers_blueprint
    app.register_blueprint(suppliers_blueprint)

    # Import/Export Blueprints registrieren
    from app.import_assets import import_assets
    app.register_blueprint(import_assets)
    from app.export_assets import export_assets
    app.register_blueprint(export_assets)
    
    # MD3 Inventory Blueprint registrieren (bereits oben registriert mit URL-Prefix)

    # Routes aus routes.py    # Routen registrieren
    from . import routes
    routes.init_app(app)
    
    # API-Routen registrieren
    from . import api_routes
    api_routes.init_api_routes(app)
    
    # Calendar API Blueprint registrieren
    from app.api import bp as api_bp
    app.register_blueprint(api_bp)
    
    with app.app_context():
        db.create_all()
    # Create test user if it doesn't exist
    with app.app_context():
        from app.models import Role
        admin_role = Role.query.filter_by(name='Admin').first()
        if not admin_role:
            admin_role = Role(name='Admin', description='Vollzugriff auf alle Funktionen')
            db.session.add(admin_role)
            db.session.commit()
        admin_user = User.query.filter_by(username='admin').first()
        if not admin_user:
            admin_user = User(username='admin', role=admin_role)
            admin_user.set_password('admin')
            db.session.add(admin_user)
            db.session.commit()
        else:
            if not admin_user.role_id or admin_user.role_id != admin_role.id:
                admin_user.role = admin_role
                db.session.commit()

    # Beispiel-Lieferanten anlegen im Application Context
    with app.app_context():
        from app.models import Supplier
        if Supplier.query.count() == 0:
            beispiel_lieferanten = [
                Supplier(name='Muster GmbH', address='Musterstraße 1, 12345 Musterstadt', phone='01234 567890', email='info@muster.de', website='www.muster.de', customer_number='10001', creditor_number='20001'),
                Supplier(name='ABC Technik AG', address='Industriestr. 12, 54321 Technikstadt', phone='09876 543210', email='kontakt@abc-technik.de', website='www.abc-technik.de', customer_number='10002', creditor_number='20002'),
                Supplier(name='Bürobedarf Schmitt', address='Büroallee 5, 11111 Bürostadt', phone='030 123456', email='service@schmitt-buero.de', website='www.schmitt-buero.de', customer_number='10003', creditor_number='20003'),
                Supplier(name='Zeta Solutions', address='Zetaweg 7, 22222 Zetastadt', phone='040 987654', email='kontakt@zeta.de', website='www.zeta.de', customer_number='10004', creditor_number='20004'),
                Supplier(name='Delta Logistik', address='Logistikpark 99, 33333 Logistown', phone='0201 998877', email='info@delta-logistik.de', website='www.delta-logistik.de', customer_number='10005', creditor_number='20005')
            ]
            db.session.bulk_save_objects(beispiel_lieferanten)
            db.session.commit()


    # Eigene Route für Profilbilder, falls Flask Static nicht greift
    @app.route('/static/profile_images/<filename>')
    def serve_profile_image(filename):
        print("Custom static route called for:", filename)
        import os
        from flask import send_from_directory
        static_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'static', 'profile_images')
        return send_from_directory(static_dir, filename)

    @app.route('/test_static/<filename>')
    def test_serve_profile_image(filename):
        print("TEST STATIC ROUTE:", filename)
        import os
        from flask import send_from_directory
        static_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'static', 'profile_images')
        return send_from_directory(static_dir, filename)

    return app

if __name__ == '__main__':
    app = create_app()
    app.run(debug=True)
