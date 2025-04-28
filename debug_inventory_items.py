from app import create_app, db
from app.models import InventorySession, InventoryItem

app = create_app()

with app.app_context():
    session = InventorySession.query.filter_by(status='completed').order_by(InventorySession.end_date.desc()).first()
    print(f'Inventur: {session.id}, {session.name}')
    print('ID | Asset-ID | Name | Soll | Ist | Status')
    for item in session.items:
        print(f'{item.id} | {item.asset_id} | {getattr(item.asset, "name", None)} | {item.expected_quantity} | {item.counted_quantity} | {item.status}')
