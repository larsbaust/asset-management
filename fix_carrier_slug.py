# Script: fix_carrier_slug.py
# Setzt alle Bestellungen mit tracking_carrier 'dpd' auf 'dpd-de'

from app import create_app, db
from app.models import Order

app = create_app()

with app.app_context():
    orders = Order.query.filter_by(tracking_carrier='dpd').all()
    print(f"{len(orders)} Bestellungen werden angepasst...")
    for order in orders:
        print(f"Order #{order.id}: Carrier '{order.tracking_carrier}' -> 'dpd-de'")
        order.tracking_carrier = 'dpd-de'
    db.session.commit()
    print("Fertig. Alle Carrier wurden angepasst.")
