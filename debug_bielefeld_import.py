from app import create_app
from app.models import Order, Asset, Location, OrderItem
from app.order.order_utils import import_assets_from_order
from datetime import datetime

app = create_app()
with app.app_context():
    print("=== BIELEFELD SYNOLOGY IMPORT DEBUG ===")
    
    # Finde die neueste Bestellung für Bielefeld
    bielefeld_location = Location.query.filter_by(name='Frittenwerk Bielefeld').first()
    
    if not bielefeld_location:
        print("ERROR: Location 'Frittenwerk Bielefeld' not found!")
        all_locations = Location.query.all()
        print("Available locations:")
        for loc in all_locations:
            print(f"  - {loc.name} (ID: {loc.id})")
    else:
        print(f"Location found: {bielefeld_location.name} (ID: {bielefeld_location.id})")
        
        # Neueste Bestellung für Bielefeld
        recent_order = Order.query.filter_by(location=bielefeld_location.id).order_by(Order.id.desc()).first()
        
        if not recent_order:
            print("No orders found for Bielefeld")
        else:
            print(f"\nNewest Bielefeld Order: ID {recent_order.id}")
            print(f"  Status: {recent_order.status}")
            print(f"  Supplier: {recent_order.supplier}")
            print(f"  Created: {recent_order.created_at}")
            
            print(f"\nOrder Items ({len(recent_order.items)}):")
            for item in recent_order.items:
                asset_name = item.asset.name if item.asset else "No Asset"
                print(f"  - {asset_name} (Qty: {item.quantity}, SN: {item.serial_number})")
                
                # Check if assets already exist for this order item
                existing_assets = Asset.query.filter_by(
                    name=asset_name,
                    location=bielefeld_location.id
                ).all()
                
                if existing_assets:
                    print(f"    → {len(existing_assets)} existing assets found")
                else:
                    print(f"    → No existing assets found")
            
            # Teste Import für diese Bestellung
            print(f"\n=== TESTING IMPORT FOR ORDER {recent_order.id} ===")
            try:
                created_assets, skipped_items = import_assets_from_order(recent_order)
                
                print(f"Import Result:")
                print(f"  Created Assets: {len(created_assets)}")
                print(f"  Skipped Items: {len(skipped_items)}")
                
                for asset in created_assets:
                    print(f"    ✓ Created: {asset.name} (ID: {asset.id}) - Location: {asset.location}")
                    
                for item, reason in skipped_items:
                    print(f"    ✗ Skipped: {item} - Reason: {reason}")
                    
            except Exception as e:
                print(f"ERROR during import: {e}")
                import traceback
                traceback.print_exc()
                
    # Check für Synology Assets in Bielefeld
    print(f"\n=== SYNOLOGY ASSETS IN BIELEFELD ===")
    if bielefeld_location:
        synology_assets = Asset.query.filter(
            Asset.name.ilike('%synology%'),
            Asset.location == bielefeld_location.id
        ).all()
        
        print(f"Found {len(synology_assets)} Synology assets in Bielefeld:")
        for asset in synology_assets:
            print(f"  - {asset.name} (ID: {asset.id}, Status: {asset.status}, Created: {asset.created_at})")
    
    # Check für alle Synology Assets
    print(f"\n=== ALL SYNOLOGY ASSETS ===")
    all_synology = Asset.query.filter(Asset.name.ilike('%synology%')).all()
    print(f"Total Synology assets: {len(all_synology)}")
    for asset in all_synology:
        location_name = asset.location_obj.name if asset.location_obj else "No Location"
        print(f"  - {asset.name} (Location: {location_name}, Created: {asset.created_at})")
