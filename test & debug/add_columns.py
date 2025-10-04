from app import create_app, db
from app.models import Asset

app = create_app()

with app.app_context():
    # Füge die neuen Spalten hinzu
    with db.engine.connect() as conn:
        conn.execute(db.text("ALTER TABLE asset ADD COLUMN location VARCHAR(100);"))
        conn.execute(db.text("ALTER TABLE asset ADD COLUMN purchase_date DATETIME;"))
        conn.commit()

    print("Datenbank erfolgreich aktualisiert!")
