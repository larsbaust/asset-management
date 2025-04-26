# Skript zum Fixieren der expected_quantity für alle InventoryItems
# Setzt expected_quantity auf 1, wenn der Wert None oder 0 ist

from app import create_app
from app.models import db, InventoryItem

app = create_app()

with app.app_context():
    items = InventoryItem.query.filter((InventoryItem.expected_quantity == None) | (InventoryItem.expected_quantity == 0)).all()
    print(f"{len(items)} InventoryItems werden aktualisiert...")
    for item in items:
        item.expected_quantity = 1
    db.session.commit()
    print("Fertig. Alle InventoryItems mit None/0 wurden auf 1 gesetzt.")
