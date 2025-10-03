from app import create_app
from app.models import Asset, Order, OrderItem, Location

app = create_app()
with app.app_context():
    # Prüfe Assets für Nürnberg Location
    nuremberg_location = Location.query.filter(Location.name.ilike('%Nürnberg%')).first()
    
    if nuremberg_location:
        print(f"=== NÜRNBERG LOCATION GEFUNDEN ===")
        print(f"Location ID: {nuremberg_location.id}, Name: {nuremberg_location.name}")
        
        # Alle Assets für diese Location
        nuremberg_assets = Asset.query.filter_by(location_id=nuremberg_location.id).order_by(Asset.id.desc()).all()
        print(f"Assets in Nürnberg gesamt: {len(nuremberg_assets)}")
        
        # Heute erstellte Assets
        today_assets = Asset.query.filter(
            Asset.location_id == nuremberg_location.id,
            Asset.created_at >= '2025-08-23'
        ).order_by(Asset.created_at.desc()).all()
        
        print(f"Heute erstellte Assets in Nürnberg: {len(today_assets)}")
        for asset in today_assets:
            print(f"  - ID {asset.id}: {asset.name} (Status: {asset.status}) - {asset.created_at}")
    else:
        print("❌ KEINE NÜRNBERG LOCATION GEFUNDEN!")
        # Suche ähnliche Namen
        all_locations = Location.query.filter(Location.name.ilike('%berg%')).all()
        print("Ähnliche Locations:")
        for loc in all_locations:
            print(f"  - ID {loc.id}: {loc.name}")
    
    # Prüfe neueste Bestellungen
    print(f"\n=== NEUESTE BESTELLUNGEN ===")
    recent_orders = Order.query.order_by(Order.id.desc()).limit(3).all()
    for order in recent_orders:
        location_name = order.location_obj.name if order.location_obj else "Keine Location"
        created_date = getattr(order, 'created_at', 'Unbekannt')
        print(f"Order ID {order.id}: {location_name} - Status: {order.status} - Created: {created_date}")
        
        # OrderItems für diese Bestellung
        items = OrderItem.query.filter_by(order_id=order.id).all()
        print(f"  Items: {len(items)}")
        for item in items:
            asset_name = item.asset.name if item.asset else "Template Asset"
            print(f"    - Asset: {asset_name}, Qty: {item.quantity}, Serial: {item.serial_number}")
    
    # Prüfe Assets der letzten Stunde
    print(f"\n=== ASSETS DER LETZTEN STUNDE ===")
    from datetime import datetime, timedelta
    one_hour_ago = datetime.now() - timedelta(hours=1)
    recent_assets = Asset.query.filter(Asset.created_at >= one_hour_ago).order_by(Asset.created_at.desc()).all()
    
    print(f"Assets der letzten Stunde: {len(recent_assets)}")
    for asset in recent_assets:
        location_name = asset.location_obj.name if asset.location_obj else "Keine Location"
        print(f"  - ID {asset.id}: {asset.name} - Location: {location_name} - {asset.created_at}")
