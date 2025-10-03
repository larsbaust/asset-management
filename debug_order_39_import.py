from app import create_app
from app.models import Order, Asset, Location, OrderItem
from app.order.order_utils import import_assets_from_order

app = create_app()
with app.app_context():
    print("=== ORDER 39 BIELEFELD IMPORT DEBUG ===")
    
    # Order 39 laden
    order = Order.query.get(39)
    
    if not order:
        print("ERROR: Order 39 not found!")
    else:
        print(f"Order 39 Details:")
        print(f"  Status: {order.status}")
        print(f"  Location (old field): {order.location}")
        print(f"  Location_id (new field): {order.location_id}")
        print(f"  Supplier ID: {order.supplier_id}")
        print(f"  Items: {len(order.items)}")
        
        # Location object check
        if order.location_obj:
            print(f"  Location Object: {order.location_obj.name} (ID: {order.location_obj.id})")
        else:
            print("  No location object found")
            
        # Items details
        print(f"\nOrder Items:")
        for item in order.items:
            asset_name = item.asset.name if item.asset else "No Asset"
            print(f"  - Asset: {asset_name}")
            print(f"    Asset ID: {item.asset_id}")
            print(f"    Quantity: {item.quantity}")
            print(f"    Serial Number: {item.serial_number}")
            
            # Check if this asset contains Synology
            if item.asset and 'synology' in asset_name.lower():
                print(f"    -> SYNOLOGY ITEM FOUND!")
        
        # Test Import
        print(f"\n=== TESTING IMPORT FOR ORDER 39 ===")
        try:
            created_assets, skipped_items = import_assets_from_order(order)
            
            print(f"Import Results:")
            print(f"  Created Assets: {len(created_assets)}")
            print(f"  Skipped Items: {len(skipped_items)}")
            
            if created_assets:
                print(f"  Created Assets Details:")
                for asset in created_assets:
                    location_name = asset.location_obj.name if asset.location_obj else f"Location ID {asset.location}"
                    print(f"    - {asset.name} (ID: {asset.id}) -> Location: {location_name}")
            
            if skipped_items:
                print(f"  Skipped Items Details:")
                for item_info, reason in skipped_items:
                    print(f"    - {item_info} -> Reason: {reason}")
                    
        except Exception as e:
            print(f"ERROR during import: {e}")
            import traceback
            traceback.print_exc()
    
    # Check current Synology assets in Bielefeld
    print(f"\n=== CURRENT SYNOLOGY ASSETS IN BIELEFELD ===")
    bielefeld = Location.query.filter_by(name='Frittenwerk Bielefeld').first()
    if bielefeld:
        synology_assets = Asset.query.filter(
            Asset.name.ilike('%synology%'),
            Asset.location == bielefeld.id
        ).all()
        
        print(f"Synology assets in Bielefeld: {len(synology_assets)}")
        for asset in synology_assets:
            print(f"  - {asset.name} (ID: {asset.id}, Status: {asset.status})")
    
    # Check all recent assets created today
    from datetime import datetime
    today = datetime.now().date()
    recent_assets = Asset.query.filter(Asset.created_at >= today).all()
    
    print(f"\n=== ASSETS CREATED TODAY ===")
    print(f"Total assets created today: {len(recent_assets)}")
    
    for asset in recent_assets:
        location_name = asset.location_obj.name if asset.location_obj else f"Location ID {asset.location}"
        print(f"  - {asset.name} -> Location: {location_name} (Created: {asset.created_at})")
        
        if 'synology' in asset.name.lower():
            print(f"    *** SYNOLOGY ASSET FOUND! ***")
