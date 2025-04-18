from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_migrate import Migrate
import os

db = SQLAlchemy()
login_manager = LoginManager()

def create_app():
    app = Flask(__name__)
    app.config['SECRET_KEY'] = 'your-secret-key'  # In production, use a secure key
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///app.db'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['UPLOAD_FOLDER'] = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'uploads')

    # Ensure upload directory exists
    if not os.path.exists(app.config['UPLOAD_FOLDER']):
        os.makedirs(app.config['UPLOAD_FOLDER'])

    db.init_app(app)
    migrate = Migrate(app, db)

    # Login manager setup
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'

    from app.models import User
    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    # Register blueprints
    from app.main import main as main_blueprint
    app.register_blueprint(main_blueprint)

    from app.auth import auth as auth_blueprint
    app.register_blueprint(auth_blueprint)

    from app.order import order as order_blueprint
    app.register_blueprint(order_blueprint)

    from app.suppliers import suppliers as suppliers_blueprint
    app.register_blueprint(suppliers_blueprint)

    with app.app_context():
        db.create_all()
        # Create test user if it doesn't exist
        if not User.query.filter_by(username='admin').first():
            user = User(username='admin')
            user.set_password('admin')
            db.session.add(user)
            db.session.commit()

        # Beispiel-Lieferanten anlegen
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

    return app

if __name__ == '__main__':
    app = create_app()
    app.run(debug=True)
