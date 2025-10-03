from app import create_app
from app.models import Order, Asset, Location, OrderItem, Supplier
from datetime import datetime, timedelta

app = create_app()
with app.app_context():
    print("=== RECENT ORDERS DEBUG ===")
    
    # Die letzten 5 Bestellungen
    recent_orders = Order.query.order_by(Order.id.desc()).limit(5).all()
    
    print(f"Last 5 orders:")
    for order in recent_orders:
        location_name = "Unknown Location"
        if order.location_obj:
            location_name = order.location_obj.name
        elif order.location:
            # Fallback: direkt aus Location-Tabelle laden
            loc = Location.query.get(order.location)
            location_name = loc.name if loc else f"Location ID {order.location}"
        
        supplier_name = order.supplier.name if order.supplier else f"Supplier ID {order.supplier_id}"
        
        print(f"  Order {order.id}: {location_name} | {supplier_name} | Status: {order.status} | Items: {len(order.items)} | Created: {order.order_date}")
        
        # Check if this contains Synology
        has_synology = any('synology' in item.asset.name.lower() for item in order.items if item.asset)
        if has_synology:
            print(f"    → Contains Synology item(s)")
            for item in order.items:
                if item.asset and 'synology' in item.asset.name.lower():
                    print(f"      - {item.asset.name} (Qty: {item.quantity})")
    
    print(f"\n=== BIELEFELD LOCATION CHECK ===")
    bielefeld = Location.query.filter_by(name='Frittenwerk Bielefeld').first()
    if bielefeld:
        print(f"Bielefeld Location ID: {bielefeld.id}")
        
        # Check alle Bestellungen mit dieser Location ID - both old and new location fields
        all_bielefeld_orders_old = Order.query.filter_by(location=bielefeld.id).all()
        all_bielefeld_orders_new = Order.query.filter_by(location_id=bielefeld.id).all()
        print(f"Bielefeld orders (old location field): {len(all_bielefeld_orders_old)}")
        print(f"Bielefeld orders (new location_id field): {len(all_bielefeld_orders_new)}")
        
        for order in all_bielefeld_orders_old + all_bielefeld_orders_new:
            print(f"  Order {order.id}: Status {order.status}, Created {order.order_date}")
    
    print(f"\n=== CHECK TODAY'S ORDERS ===")
    today = datetime.now().date()
    today_orders = Order.query.filter(Order.order_date >= today).all()
    
    print(f"Orders created today: {len(today_orders)}")
    for order in today_orders:
        location_name = order.location_obj.name if order.location_obj else f"Location ID {order.location}"
        supplier_name = order.supplier.name if order.supplier else f"Supplier ID {order.supplier_id}"
        
        print(f"  Order {order.id}: {location_name} | {supplier_name} | Status: {order.status}")
        
        # Debug location assignment
        print(f"    Raw location field: {order.location}")
        print(f"    Raw location_id field: {order.location_id}")
        print(f"    Raw supplier_id field: {order.supplier_id}")
        
        # Test import für heute's orders
        if 'synology' in str([item.asset.name for item in order.items if item.asset]).lower():
            print(f"    → This order contains Synology - testing import")
            from app.order.order_utils import import_assets_from_order
            try:
                created_assets, skipped_items = import_assets_from_order(order)
                print(f"      Import result: {len(created_assets)} created, {len(skipped_items)} skipped")
            except Exception as e:
                print(f"      Import ERROR: {e}")
    
    print(f"\n=== WIZARD REDIRECT DEBUG ===")
    print("Checking for wizard_routes.py import redirect...")
    
    # Check if there are other redirect routes that might interfere
    import os
    wizard_file = os.path.join(app.root_path, 'order', 'wizard_routes.py')
    if os.path.exists(wizard_file):
        with open(wizard_file, 'r', encoding='utf-8') as f:
            content = f.read()
            
        # Find all redirect lines
        lines = content.split('\n')
        redirect_lines = [i for i, line in enumerate(lines, 1) if 'redirect' in line and 'import' in lines[max(0, i-5):i+5]]
        
        print(f"Redirect lines near 'import':")
        for line_num in redirect_lines:
            start = max(0, line_num - 2)
            end = min(len(lines), line_num + 2)
            for i in range(start, end):
                marker = " → " if i == line_num - 1 else "   "
                print(f"{marker}{i+1:4}: {lines[i]}")
            print()
    
    print(f"\n=== ABC TECHNIK RECENT ORDERS ===")
    abc_supplier = Supplier.query.filter_by(name='ABC Technik AG').first()
    if abc_supplier:
        abc_orders = Order.query.filter_by(supplier_id=abc_supplier.id).order_by(Order.id.desc()).limit(3).all()
        print(f"Recent ABC Technik orders: {len(abc_orders)}")
        
        for order in abc_orders:
            location_name = order.location_obj.name if order.location_obj else f"Location ID {order.location}"
            print(f"  Order {order.id}: {location_name} | Status: {order.status} | Created: {order.created_at}")
            
            synology_items = [item for item in order.items if item.asset and 'synology' in item.asset.name.lower()]
            if synology_items:
                print(f"    Synology items: {len(synology_items)}")
                for item in synology_items:
                    print(f"      - {item.asset.name}")
