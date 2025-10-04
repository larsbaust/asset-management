from app import create_app
from app.models import Order, Asset, Location, OrderItem
from app.order.order_utils import import_assets_from_order
from datetime import datetime

app = create_app()
with app.app_context():
    print("=== BESTELLUNG #44 DETAILED DEBUG ===")
    
    # Bestellung #44 laden (neueste aus Screenshot)
    order = Order.query.get(44)
    
    if not order:
        # Finde die neueste Bestellung
        latest_order = Order.query.order_by(Order.id.desc()).first()
        print(f"Order 44 not found, latest order: {latest_order.id if latest_order else 'None'}")
        order = latest_order
    
    if order:
        print(f"Order Details:")
        print(f"  ID: {order.id}")
        print(f"  Status: {order.status}")
        print(f"  Location ID: {order.location_id}")
        print(f"  Location Object: {order.location_obj.name if order.location_obj else 'None'}")
        print(f"  Supplier: {order.supplier.name if order.supplier else 'None'}")
        print(f"  Created: {order.order_date}")
        
        print(f"\nOrder Items ({len(order.items)}):")
        total_expected_assets = 0
        for i, item in enumerate(order.items, 1):
            asset_name = item.asset.name if item.asset else "No Asset"
            print(f"  {i}. Asset: {asset_name}")
            print(f"     Asset ID: {item.asset_id}")
            print(f"     Quantity: {item.quantity}")
            print(f"     Serial: {item.serial_number}")
            total_expected_assets += item.quantity
            
        print(f"\nTotal Expected Assets: {total_expected_assets}")
        
        # Check bereits importierte Assets für diese Bestellung
        bielefeld = Location.query.filter_by(name='Frittenwerk Bielefeld').first()
        if bielefeld:
            print(f"\n=== ASSETS IN BIELEFELD BEFORE RE-IMPORT ===")
            existing_assets = Asset.query.filter_by(location=bielefeld.id).all()
            print(f"Total assets in Bielefeld: {len(existing_assets)}")
            
            # Assets created today
            today = datetime.now().date()
            today_assets = [a for a in existing_assets if a.created_at and a.created_at.date() == today]
            print(f"Assets created today: {len(today_assets)}")
            
            for asset in today_assets:
                print(f"  - {asset.name} (ID: {asset.id}, Serial: {asset.serial_number})")
        
        # Test Re-Import
        print(f"\n=== TESTING RE-IMPORT ===")
        try:
            created_assets, skipped_items = import_assets_from_order(order)
            
            print(f"Import Results:")
            print(f"  Created Assets: {len(created_assets)}")
            print(f"  Skipped Items: {len(skipped_items)}")
            
            if created_assets:
                print(f"  Created Details:")
                for asset in created_assets:
                    print(f"    + {asset.name} (ID: {asset.id})")
                    print(f"      Location: {asset.location}/{asset.location_id}")
                    print(f"      Status: {asset.status}")
                    print(f"      Serial: {asset.serial_number}")
            
            if skipped_items:
                print(f"  Skipped Details:")
                for item_info, reason in skipped_items:
                    print(f"    - {item_info}: {reason}")
                    
            # Erwartet vs. Tatsächlich
            print(f"\nComparison:")
            print(f"  Expected new assets: {total_expected_assets}")
            print(f"  Actually created: {len(created_assets)}")
            print(f"  Difference: {total_expected_assets - len(created_assets)}")
                    
        except Exception as e:
            print(f"ERROR during import: {e}")
            import traceback
            traceback.print_exc()
        
        # Final verification
        print(f"\n=== FINAL VERIFICATION ===")
        if bielefeld:
            final_assets = Asset.query.filter_by(location=bielefeld.id).all()
            final_today = [a for a in final_assets if a.created_at and a.created_at.date() == today]
            
            print(f"Final count:")
            print(f"  Total assets in Bielefeld: {len(final_assets)}")
            print(f"  Assets created today: {len(final_today)}")
            
            # Check for specific assets from the order
            for item in order.items:
                if item.asset:
                    matching_assets = Asset.query.filter(
                        Asset.name == item.asset.name,
                        Asset.location == bielefeld.id,
                        Asset.created_at >= today
                    ).all()
                    
                    print(f"  {item.asset.name}: {len(matching_assets)} found (expected: {item.quantity})")
                    for asset in matching_assets:
                        print(f"    - ID {asset.id}, Serial: {asset.serial_number}")
        
        # Check MD3 Assets page visibility
        print(f"\n=== MD3 ASSETS PAGE VISIBILITY TEST ===")
        
        with app.test_client() as client:
            # Mock authentication
            with client.session_transaction() as sess:
                sess['user_id'] = 1
                sess['_user_id'] = '1'
                sess['_fresh'] = True
            
            # Test MD3 assets page with location filter
            params = f"?location={bielefeld.id if bielefeld else ''}"
            response = client.get(f'/md3/assets{params}')
            print(f"MD3 Assets with location filter: HTTP {response.status_code}")
            
            if response.status_code == 200:
                response_text = response.get_data(as_text=True)
                # Count asset rows in response
                asset_rows = response_text.count('<tr class="asset-row"')
                print(f"Asset rows found in HTML: {asset_rows}")
                
                # Check for order items in response
                for item in order.items:
                    if item.asset and item.asset.name in response_text:
                        print(f"  ✓ {item.asset.name} found in HTML")
                    else:
                        print(f"  ✗ {item.asset.name} NOT found in HTML")
    
    else:
        print("No order found for testing")
