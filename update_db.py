from app import create_app, db
from app.models import CostEntry
from sqlalchemy import text

app = create_app()

# Erstelle die neue Tabelle
with app.app_context():
    with db.engine.connect() as conn:
        conn.execute(text("""
        CREATE TABLE cost_entry (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            asset_id INTEGER NOT NULL,
            date DATE NOT NULL,
            cost_type VARCHAR(50) NOT NULL,
            amount FLOAT NOT NULL,
            description TEXT,
            receipt_file VARCHAR(255),
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (asset_id) REFERENCES asset (id)
        )
        """))
        conn.commit()
    
print("Datenbank wurde erfolgreich aktualisiert!")
