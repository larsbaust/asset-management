from app import create_app, db
from app.models import Asset, InventorySession, InventoryItem, Document, Loan, CostEntry, InventoryTeam

def init_db():
    app = create_app()
    with app.app_context():
        # Datenbank löschen und neu erstellen
        db.drop_all()
        db.create_all()
        
        print("Datenbank wurde erfolgreich initialisiert!")

if __name__ == '__main__':
    init_db()
