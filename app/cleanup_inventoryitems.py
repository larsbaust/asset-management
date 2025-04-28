# Skript zum Bereinigen doppelter/verwaister InventoryItems in einer Session
# Behalte pro Asset nur das zuletzt gezählte oder das mit gezählter Menge, lösche alle anderen

from app import create_app
from app.models import db, InventoryItem

app = create_app()

SESSION_ID = 30  # <-- Passe ggf. die Session-ID an

def cleanup_inventoryitems(session_id):
    items = InventoryItem.query.filter_by(session_id=session_id).all()
    print(f"Vorher: {len(items)} InventoryItems in Session {session_id}")
    # Asset-ID -> Liste von Items
    from collections import defaultdict
    asset_items = defaultdict(list)
    for item in items:
        asset_items[item.asset_id].append(item)
    to_delete = []
    for asset_id, item_list in asset_items.items():
        # Sortiere: gezählte Items zuerst, dann nach counted_at (falls vorhanden)
        item_list.sort(key=lambda x: (x.counted_quantity is not None, x.counted_at or 0), reverse=True)
        # Behalte das erste, lösche alle weiteren
        for item in item_list[1:]:
            to_delete.append(item)
    for item in to_delete:
        print(f"Lösche InventoryItem ID {item.id} (Asset-ID {item.asset_id}, counted_quantity={item.counted_quantity}, status={item.status})")
        db.session.delete(item)
    db.session.commit()
    print(f"Bereinigt! Jetzt gibt es noch {InventoryItem.query.filter_by(session_id=session_id).count()} Items in Session {session_id}.")

if __name__ == "__main__":
    with app.app_context():
        cleanup_inventoryitems(SESSION_ID)
